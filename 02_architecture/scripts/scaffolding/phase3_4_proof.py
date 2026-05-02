#!/usr/bin/env python3
"""Assemble the Phase 3.4 real-provider probe proof bundle.

The bundle is evidence-only: it snapshots the plan/ADR, an offline ledger with
provider.probe, planner.fallback, budget.exceeded, and llm.complete rows,
provider probe replay data, deterministic plan-preview/provider-health replay
data, UI build hashes, and the Playwright JSON report. It also verifies that the
sidecar manifest exactly matches the zip contents and that bundled probe traces
remain redacted.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import re
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = REPO_ROOT / "06_release" / "phase3.4-bundle"
DIST_DIR = REPO_ROOT / "03_implementation" / "ui" / "dist"

REQUIRED_DOCS = {
    "docs/PHASE3_4_PLAN.md": REPO_ROOT / "00_overview" / "PHASE3_4_PLAN.md",
    "docs/ADR-012-real-provider-probes.md": REPO_ROOT
    / "02_architecture"
    / "adr"
    / "ADR-012-real-provider-probes.md",
}

REQUIRED_LEDGER_TOOLS = frozenset({"provider.probe", "planner.fallback", "budget.exceeded"})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--playwright-json", type=Path, required=True)
    args = parser.parse_args()

    run_id = args.run_id or _default_run_id()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    zip_path = OUTPUT_DIR / f"{run_id}.zip"
    manifest_path = OUTPUT_DIR / f"{run_id}.manifest.json"
    sha_path = OUTPUT_DIR / f"{run_id}.sha256"

    with tempfile.TemporaryDirectory(prefix=f"{run_id}-") as tmp:
        staging = Path(tmp)
        entries: dict[str, Path] = {}
        for archive_name, source in REQUIRED_DOCS.items():
            _require_file(source)
            entries[archive_name] = source

        ledger_snapshot = staging / "ledger_snapshot.sqlite3"
        provider_probe_replay = staging / "provider_probe_replay.json"
        plan_preview_replay = staging / "plan_preview_replay.json"
        _write_phase34_replay(
            ledger_snapshot=ledger_snapshot,
            provider_probe_replay=provider_probe_replay,
            plan_preview_replay=plan_preview_replay,
        )
        entries["evidence/ledger_snapshot.sqlite3"] = ledger_snapshot
        entries["evidence/provider_probe_replay.json"] = provider_probe_replay
        entries["evidence/plan_preview_replay.json"] = plan_preview_replay

        ui_hashes = staging / "ui_build_output_hash.json"
        _write_ui_build_hashes(ui_hashes)
        entries["evidence/ui_build_output_hash.json"] = ui_hashes

        playwright_json = args.playwright_json.resolve()
        _require_file(playwright_json)
        entries["evidence/playwright_report.json"] = playwright_json

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for archive_name in sorted(entries):
                zf.write(entries[archive_name], archive_name)

        manifest = _build_manifest(run_id, zip_path)
        manifest_path.write_text(_canonical_json(manifest), encoding="utf-8")
        digest = _sha256_file(zip_path)
        sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")

    verified = verify_bundle(zip_path, manifest_path)
    ledger_counts = _ledger_counts_from_zip(zip_path)
    manifest_count = len(json.loads(manifest_path.read_text(encoding="utf-8"))["files"])
    print(
        json.dumps(
            {
                "bundle": str(zip_path.relative_to(REPO_ROOT)),
                "ledger_counts": ledger_counts,
                "manifest": str(manifest_path.relative_to(REPO_ROOT)),
                "manifest_count": manifest_count,
                "sha256": digest,
                "verified": verified,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def verify_bundle(zip_path: Path, manifest_path: Path) -> bool:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {entry["path"]: entry for entry in manifest["files"]}
    with zipfile.ZipFile(zip_path, "r") as zf:
        actual_names = sorted(info.filename for info in zf.infolist())
        if actual_names != sorted(expected):
            missing = sorted(set(expected) - set(actual_names))
            extra = sorted(set(actual_names) - set(expected))
            raise RuntimeError(f"manifest mismatch: missing={missing}, extra={extra}")
        for name in actual_names:
            data = zf.read(name)
            digest = hashlib.sha256(data).hexdigest()
            size = len(data)
            expected_entry = expected[name]
            if digest != expected_entry["sha256"] or size != expected_entry["size"]:
                raise RuntimeError(f"manifest hash/size mismatch for {name}")

        replay = json.loads(zf.read("evidence/provider_probe_replay.json"))
        _assert_no_redaction_regex_matches(replay)
        with tempfile.TemporaryDirectory(prefix="phase34-verify-") as tmp:
            db_path = Path(tmp) / "ledger_snapshot.sqlite3"
            db_path.write_bytes(zf.read("evidence/ledger_snapshot.sqlite3"))
            counts, verdicts, fallback_messages = _ledger_evidence_from_db(db_path)
        missing_tools = sorted(tool for tool in REQUIRED_LEDGER_TOOLS if counts.get(tool, 0) < 1)
        if missing_tools:
            raise RuntimeError(f"ledger missing required tools: {missing_tools}")
        if verdicts.get(("provider.probe", "pass"), 0) < 1:
            raise RuntimeError("ledger missing successful provider.probe row")
        if verdicts.get(("provider.probe", "fail"), 0) < 1:
            raise RuntimeError("ledger missing failed provider.probe row")
        if not any("provider_not_probed" in message for message in fallback_messages):
            raise RuntimeError("ledger missing planner.fallback provider_not_probed evidence")
    return True


def _write_phase34_replay(
    *,
    ledger_snapshot: Path,
    provider_probe_replay: Path,
    plan_preview_replay: Path,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "03_implementation" / "src"))
    sys.path.insert(0, str(REPO_ROOT / "04_testing" / "fixtures"))

    from hermes3d.agents.planner import PlannerAgent
    from hermes3d.gateways.budget import fresh_budget_state
    from hermes3d.gateways.llm import LLMGateway, LLMPolicy
    from hermes3d.gateways.probe import ProbeOutcome, ProviderProbeGateway
    from hermes3d.gateways.providers import load_probe_policy
    from hermes3d.orchestration import Err, OfflineSupervisor, Ok, PlanRequest
    from hermes3d.orchestration.bridge import BridgeState
    from hermes3d.orchestration.ledger import OrchestrationLedger
    from hermes3d.orchestration.types import BudgetState, LLMRequest, LLMResponse
    from llm import create_app as create_llm_app
    from providers.server import create_app as create_provider_app
    from starlette.testclient import TestClient

    llm_policy = LLMPolicy(
        default_mode="llm",
        provider_allowlist=("openai-fixture",),
        cost_cap_usd_per_run=Decimal("0.05"),
        cost_cap_usd_per_day=Decimal("1.00"),
        timeout_seconds=30,
        prompt_max_bytes=4096,
        retry_max=1,
        rate_per_second=1,
        input_usd_per_token=Decimal("0.000001"),
        output_usd_per_token=Decimal("0.000001"),
        max_completion_tokens=128,
        fallback_mode="template",
    )

    probe_policy = load_probe_policy()
    replays: list[dict[str, object]] = []

    def fixture_probe_caller(provider_id: str, mode: str):
        client = TestClient(create_provider_app(provider_id=provider_id, mode=mode))

        def caller(_config: object) -> ProbeOutcome:
            response = client.get("/v1/models")
            return ProbeOutcome(
                http_status=response.status_code,
                latency_ms=11 if mode == "happy" else 19,
                body=response.text,
            )

        return caller

    def fixture_llm_caller(mode: str):
        client = TestClient(create_llm_app(mode=mode))

        def caller(request: LLMRequest) -> LLMResponse:
            response = client.post(
                "/v1/completions",
                json={"prompt": request.prompt, "max_tokens": request.max_completion_tokens},
            )
            response.raise_for_status()
            payload = response.json()
            return LLMResponse(
                redacted_text=str(payload["text"]),
                tokens_in=int(payload.get("tokens_in", 4)),
                tokens_out=int(payload.get("tokens_out", 4)),
                cost_usd_estimate=Decimal("0.000008"),
            )

        return caller

    with tempfile.TemporaryDirectory(prefix="phase34-ledger-") as tmp:
        tmp_db = Path(tmp) / "ledger.sqlite3"
        ledger = OrchestrationLedger(tmp_db)
        supervisor = OfflineSupervisor(ledger=ledger)
        probe_gateway = ProviderProbeGateway(
            ledger=ledger,
            providers=probe_policy.providers,
            probe_freshness_minutes=probe_policy.probe_freshness_minutes,
            probe_budget_usd_per_day=probe_policy.probe_budget_usd_per_day,
            probe_rate_per_minute=probe_policy.probe_rate_per_minute,
        )
        llm_gateway = LLMGateway(ledger=ledger, policy=llm_policy)
        planner = PlannerAgent(supervisor=supervisor, ledger=ledger)

        now = datetime.now(UTC)
        minimax_probe = probe_gateway.probe(
            "minimax",
            token=_issue_token(
                supervisor,
                agent_id="proof.probe",
                tools=frozenset({"provider.probe"}),
                scopes=frozenset({"phase3.4-minimax-probe"}),
            ),
            budget=fresh_budget_state(now_utc=now),
            probe_caller=fixture_probe_caller("minimax", "happy"),
            now_utc=now,
        )
        if not isinstance(minimax_probe, Ok) or not minimax_probe.value.success:
            raise RuntimeError(f"minimax probe failed: {minimax_probe}")
        replays.append(_probe_replay_entry("minimax", "happy", minimax_probe.value))

        deepseek_probe = probe_gateway.probe(
            "deepseek",
            token=_issue_token(
                supervisor,
                agent_id="proof.probe",
                tools=frozenset({"provider.probe"}),
                scopes=frozenset({"phase3.4-deepseek-probe"}),
            ),
            budget=fresh_budget_state(now_utc=now),
            probe_caller=fixture_probe_caller("deepseek", "unauthorized"),
            now_utc=now,
        )
        if not isinstance(deepseek_probe, Ok) or deepseek_probe.value.success:
            raise RuntimeError(f"deepseek failure probe did not record failure: {deepseek_probe}")
        replays.append(_probe_replay_entry("deepseek", "unauthorized", deepseek_probe.value))

        completion = llm_gateway.complete(
            "calibration cube",
            token=_issue_token(
                supervisor,
                agent_id="proof.llm",
                tools=frozenset({"llm.complete"}),
                scopes=frozenset({"phase3.4-minimax-complete"}),
            ),
            budget=fresh_budget_state(now_utc=now),
            caller=fixture_llm_caller("happy"),
            provider_id="minimax",
            now_utc=now,
        )
        if not isinstance(completion, Ok):
            raise RuntimeError(f"probe-verified completion failed: {completion}")

        exhausted_budget = BudgetState(
            spent_usd_run=Decimal("0"),
            spent_usd_day=probe_policy.probe_budget_usd_per_day,
            day_started_utc=fresh_budget_state(now_utc=now).day_started_utc,
        )
        budget_refusal = supervisor.issue_token(
            agent_id="proof.probe",
            tools=frozenset({"provider.probe"}),
            scopes=frozenset({"phase3.4-r10"}),
            budget=exhausted_budget,
            now_utc=now,
        )
        if not isinstance(budget_refusal, Err) or budget_refusal.code != "budget_exceeded":
            raise RuntimeError("probe budget scenario did not refuse provider.probe token")

        class DeepSeekGateway:
            def complete(self, prompt: str, *, token: object, budget: object, caller: object):
                return llm_gateway.complete(
                    prompt,
                    token=token,
                    budget=budget,
                    caller=caller,
                    provider_id="deepseek",
                    now_utc=now,
                )

        fallback_plan = planner.plan(
            PlanRequest(
                run_id="phase3.4-r9-fallback",
                agent_id="proof.planner",
                prompt="calibration cube",
            ),
            token=_issue_token(
                supervisor,
                agent_id="proof.planner",
                tools=frozenset({"planner.plan"}),
                scopes=frozenset({"phase3.4-r9-fallback"}),
            ),
            llm_token=_issue_token(
                supervisor,
                agent_id="proof.planner",
                tools=frozenset({"llm.complete"}),
                scopes=frozenset({"phase3.4-r9-fallback"}),
            ),
            budget=fresh_budget_state(now_utc=now),
            gateway=DeepSeekGateway(),
            caller=fixture_llm_caller("happy"),
            policy=llm_policy,
            mode="llm",
        )
        if not isinstance(fallback_plan.result, Ok):
            raise RuntimeError(f"R9 fallback plan failed: {fallback_plan.result}")
        if fallback_plan.result.value.metadata.get("planner_mode") != "template":
            raise RuntimeError("R9 fallback did not return planner_mode=template")

        bridge_state = BridgeState(
            ledger=ledger,
            supervisor=supervisor,
            planner=PlannerAgent(supervisor=supervisor, ledger=ledger),
        )
        preview = bridge_state.preview_plan("calibration cube")
        health = bridge_state.provider_health()
        if preview["metadata"].get("planner_mode") != "template":
            raise RuntimeError("bridge preview did not surface planner_mode=template")
        if not any(
            provider.get("provider_id") == "minimax" and provider.get("status") == "green"
            for provider in health["providers"]
        ):
            raise RuntimeError("provider health replay did not surface minimax green state")

        plan_preview_replay.write_text(
            _canonical_json(
                {
                    "plan_preview": {
                        "request": {"prompt": "calibration cube"},
                        "response": preview,
                        "route": "POST /api/plan/preview",
                    },
                    "provider_health": {
                        "response": health,
                        "route": "GET /api/providers/health",
                    },
                }
            ),
            encoding="utf-8",
        )
        provider_probe_replay.write_text(
            _canonical_json({"provider_probe_replay": replays}),
            encoding="utf-8",
        )

        counts = _ledger_counts(ledger)
        if counts.get("provider.probe", 0) < 2:
            raise RuntimeError("ledger has fewer than two provider.probe rows")
        if counts.get("planner.fallback", 0) < 1:
            raise RuntimeError("ledger has no planner.fallback rows")
        if counts.get("budget.exceeded", 0) < 1:
            raise RuntimeError("ledger has no budget.exceeded rows")
        if counts.get("llm.complete", 0) < 1:
            raise RuntimeError("ledger has no llm.complete rows")

        gc.collect()
        ledger_snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_db, ledger_snapshot)


def _probe_replay_entry(provider_id: str, mode: str, result: Any) -> dict[str, object]:
    return {
        "http_status": result.http_status,
        "latency_ms": result.latency_ms,
        "mode": mode,
        "provider_id": provider_id,
        "probed_at_utc": result.probed_at_utc,
        "redacted_excerpt": result.redacted_excerpt,
        "response_sha256": result.response_sha256,
        "success": result.success,
    }


def _issue_token(
    supervisor: Any,
    *,
    agent_id: str,
    tools: frozenset[str],
    scopes: frozenset[str],
) -> Any:
    from hermes3d.orchestration import Err

    token = supervisor.issue_token(agent_id=agent_id, tools=tools, scopes=scopes)
    if isinstance(token, Err):
        raise RuntimeError(f"token issuance failed: {token}")
    return token


def _ledger_counts(ledger: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in ledger.events():
        counts[event.tool] = counts.get(event.tool, 0) + 1
    return counts


def _write_ui_build_hashes(path: Path) -> None:
    if not DIST_DIR.exists():
        raise FileNotFoundError(f"UI dist not found; run npm run build first: {DIST_DIR}")
    files: list[dict[str, Any]] = []
    for file_path in sorted(p for p in DIST_DIR.rglob("*") if p.is_file()):
        files.append(
            {
                "path": str(file_path.relative_to(DIST_DIR)).replace("\\", "/"),
                "sha256": _sha256_file(file_path),
                "size": file_path.stat().st_size,
            }
        )
    rollup = hashlib.sha256(_canonical_json(files).encode("utf-8")).hexdigest()
    path.write_text(_canonical_json({"dist": files, "rollup_sha256": rollup}), encoding="utf-8")


def _build_manifest(run_id: str, zip_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        files = [
            {
                "path": info.filename,
                "sha256": hashlib.sha256(zf.read(info.filename)).hexdigest(),
                "size": info.file_size,
            }
            for info in sorted(zf.infolist(), key=lambda item: item.filename)
        ]
    return {
        "schema_version": "phase3.4-bundle-1.0.0",
        "run_id": run_id,
        "created_utc": datetime.now(UTC).isoformat(),
        "git": _git_metadata(),
        "env": {
            "python": platform.python_version(),
            "python_impl": platform.python_implementation(),
            "os": platform.platform(),
            "machine": platform.machine(),
        },
        "files": files,
    }


def _git_metadata() -> dict[str, Any]:
    branch, sha = _read_git_head()
    return {
        "branch": branch,
        "sha": sha,
        "dirty": "not-computed",
    }


def _default_run_id() -> str:
    _branch, sha = _read_git_head()
    return f"{sha[:12]}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"


def _read_git_head() -> tuple[str, str]:
    git_dir = REPO_ROOT / ".git"
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return "detached", head

    ref = head.removeprefix("ref: ").strip()
    ref_path = git_dir / ref
    if ref_path.exists():
        sha = ref_path.read_text(encoding="utf-8").strip()
    else:
        sha = _read_packed_ref(git_dir / "packed-refs", ref)
    branch = ref.removeprefix("refs/heads/")
    return branch, sha


def _read_packed_ref(path: Path, ref: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Git ref not found: {ref}")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or line.startswith("^") or not line.strip():
            continue
        parts = line.split(" ", 1)
        if len(parts) != 2:
            continue
        sha, packed_ref = parts
        if packed_ref == ref:
            return sha
    raise FileNotFoundError(f"Git ref not found in packed-refs: {ref}")


def _require_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ledger_counts_from_zip(zip_path: Path) -> dict[str, int]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        with tempfile.TemporaryDirectory(prefix="phase34-counts-") as tmp:
            db_path = Path(tmp) / "ledger_snapshot.sqlite3"
            db_path.write_bytes(zf.read("evidence/ledger_snapshot.sqlite3"))
            counts, _verdicts, _fallback_messages = _ledger_evidence_from_db(db_path)
            return counts


def _ledger_evidence_from_db(
    db_path: Path,
) -> tuple[dict[str, int], dict[tuple[str, str], int], list[str]]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT tool, verdict, message FROM events").fetchall()
    finally:
        conn.close()
    counts: dict[str, int] = {}
    verdicts: dict[tuple[str, str], int] = {}
    fallback_messages: list[str] = []
    for tool, verdict, message in rows:
        tool_text = str(tool)
        verdict_text = str(verdict)
        message_text = str(message)
        counts[tool_text] = counts.get(tool_text, 0) + 1
        key = (tool_text, verdict_text)
        verdicts[key] = verdicts.get(key, 0) + 1
        if tool_text == "planner.fallback":
            fallback_messages.append(message_text)
    return counts, verdicts, fallback_messages


def _assert_no_redaction_regex_matches(value: Any) -> None:
    sys.path.insert(0, str(REPO_ROOT / "03_implementation" / "src"))
    import hermes3d.gateways.redaction as redaction

    patterns = [
        pattern
        for name, pattern in vars(redaction).items()
        if name.endswith("_RE") and isinstance(pattern, re.Pattern)
    ]
    for text in _iter_strings(value):
        for pattern in patterns:
            if pattern.search(text):
                raise RuntimeError(f"redaction pattern {pattern.pattern!r} matched bundled trace")


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for key, item in value.items():
            strings.extend(_iter_strings(str(key)))
            strings.extend(_iter_strings(item))
        return strings
    if isinstance(value, list | tuple):
        strings = []
        for item in value:
            strings.extend(_iter_strings(item))
        return strings
    return []


def _canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), indent=2, sort_keys=True) + "\n"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
