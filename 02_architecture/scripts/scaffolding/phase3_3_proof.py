#!/usr/bin/env python3
"""Assemble the Phase 3.3 LLM planner gateway proof bundle.

The bundle is evidence-only: it snapshots the plan/ADR, an offline ledger with
llm.complete, planner.fallback, and budget.exceeded rows, redacted LLM trace
samples, deterministic plan-preview replay data, UI build hashes, and the
Playwright JSON report. It also verifies that the sidecar manifest exactly
matches the zip contents and that bundled traces remain redacted.
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
OUTPUT_DIR = REPO_ROOT / "06_release" / "phase3.3-bundle"
DIST_DIR = REPO_ROOT / "03_implementation" / "ui" / "dist"

REQUIRED_DOCS = {
    "docs/PHASE3_3_PLAN.md": REPO_ROOT / "00_overview" / "PHASE3_3_PLAN.md",
    "docs/ADR-011-llm-planner-gateway.md": REPO_ROOT
    / "02_architecture"
    / "adr"
    / "ADR-011-llm-planner-gateway.md",
}

REQUIRED_LEDGER_TOOLS = frozenset({"llm.complete", "planner.fallback", "budget.exceeded"})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--playwright-json", type=Path, required=True)
    args = parser.parse_args()

    run_id = args.run_id or _default_run_id()
    bundle_dir = OUTPUT_DIR
    bundle_dir.mkdir(parents=True, exist_ok=True)

    zip_path = bundle_dir / f"{run_id}.zip"
    manifest_path = bundle_dir / f"{run_id}.manifest.json"
    sha_path = bundle_dir / f"{run_id}.sha256"

    with tempfile.TemporaryDirectory(prefix=f"{run_id}-") as tmp:
        staging = Path(tmp)
        entries: dict[str, Path] = {}
        for archive_name, source in REQUIRED_DOCS.items():
            _require_file(source)
            entries[archive_name] = source

        ledger_snapshot = staging / "ledger_snapshot.sqlite3"
        llm_redacted_trace_sample = staging / "llm_redacted_trace_sample.json"
        plan_preview_replay = staging / "plan_preview_replay.json"
        _write_phase33_replay(
            ledger_snapshot=ledger_snapshot,
            llm_redacted_trace_sample=llm_redacted_trace_sample,
            plan_preview_replay=plan_preview_replay,
        )
        entries["evidence/ledger_snapshot.sqlite3"] = ledger_snapshot
        entries["evidence/llm_redacted_trace_sample.json"] = llm_redacted_trace_sample
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

        trace = json.loads(zf.read("evidence/llm_redacted_trace_sample.json"))
        _assert_no_redaction_regex_matches(trace)
        with tempfile.TemporaryDirectory(prefix="phase33-verify-") as tmp:
            db_path = Path(tmp) / "ledger_snapshot.sqlite3"
            db_path.write_bytes(zf.read("evidence/ledger_snapshot.sqlite3"))
            counts = _ledger_counts_from_db(db_path)
        missing_tools = sorted(tool for tool in REQUIRED_LEDGER_TOOLS if counts.get(tool, 0) < 1)
        if missing_tools:
            raise RuntimeError(f"ledger missing required tools: {missing_tools}")
    return True


def _write_phase33_replay(
    *,
    ledger_snapshot: Path,
    llm_redacted_trace_sample: Path,
    plan_preview_replay: Path,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "03_implementation" / "src"))
    sys.path.insert(0, str(REPO_ROOT / "04_testing" / "fixtures"))

    from hermes3d.agents.planner import PlannerAgent
    from hermes3d.gateways.budget import fresh_budget_state
    from hermes3d.gateways.llm import LLMGateway, LLMPolicy
    from hermes3d.gateways.redaction import redact_text
    from hermes3d.orchestration import Err, OfflineSupervisor, Ok, PlanRequest
    from hermes3d.orchestration.bridge import BridgeState
    from hermes3d.orchestration.ledger import OrchestrationLedger
    from hermes3d.orchestration.types import BudgetState, LLMRequest, LLMResponse
    from llm import create_app
    from starlette.testclient import TestClient

    policy = LLMPolicy(
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

    traces: list[dict[str, object]] = []

    def append_trace(
        *,
        prompt: str,
        response: LLMResponse,
        mode: str,
        scenario: str,
    ) -> None:
        traces.append(
            {
                "cost_usd_estimate": str(response.cost_usd_estimate),
                "mode": mode,
                "prompt_sha": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12],
                "redacted_text": redact_text(response.redacted_text),
                "scenario": scenario,
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
            }
        )

    def fixture_caller(mode: str, scenario: str):
        client = TestClient(create_app(mode=mode))

        def caller(request: LLMRequest) -> LLMResponse:
            response = client.post(
                "/v1/completions",
                json={"prompt": request.prompt, "max_tokens": request.max_completion_tokens},
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                payload = response.json()
                text = str(payload["text"])
                tokens_in = int(payload.get("tokens_in", 4))
                tokens_out = int(payload.get("tokens_out", 4))
            else:
                text = response.text
                tokens_in = 4
                tokens_out = 4
            llm_response = LLMResponse(
                redacted_text=text,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd_estimate=Decimal("0.000008"),
            )
            append_trace(
                prompt=request.prompt,
                response=llm_response,
                mode=mode,
                scenario=scenario,
            )
            return llm_response

        return caller

    with tempfile.TemporaryDirectory(prefix="phase33-ledger-") as tmp:
        tmp_db = Path(tmp) / "ledger.sqlite3"
        ledger = OrchestrationLedger(tmp_db)
        supervisor = OfflineSupervisor(ledger=ledger)
        gateway = LLMGateway(ledger=ledger, policy=policy)
        planner = PlannerAgent(supervisor=supervisor, ledger=ledger)

        happy = planner.plan(
            PlanRequest(
                run_id="phase3.3-happy",
                agent_id="proof.planner",
                prompt="calibration cube",
            ),
            token=_issue_token(
                supervisor,
                agent_id="proof.planner",
                tools=frozenset({"planner.plan"}),
                scopes=frozenset({"phase3.3-happy"}),
            ),
            llm_token=_issue_token(
                supervisor,
                agent_id="proof.planner",
                tools=frozenset({"llm.complete"}),
                scopes=frozenset({"phase3.3-happy"}),
            ),
            budget=fresh_budget_state(),
            gateway=gateway,
            caller=fixture_caller("happy", "happy"),
            policy=policy,
            mode="llm",
        )
        if not isinstance(happy.result, Ok):
            raise RuntimeError(f"happy planner scenario failed: {happy.result}")
        if happy.result.value.metadata.get("planner_mode") != "llm":
            raise RuntimeError("happy planner scenario did not return planner_mode=llm")
        if _count_tool(ledger, "phase3.3-happy", "llm.complete") != 1:
            raise RuntimeError("happy planner scenario did not write exactly one llm.complete")

        exhausted_budget = BudgetState(
            spent_usd_run=Decimal("0.05"),
            spent_usd_day=Decimal("0"),
            day_started_utc=fresh_budget_state().day_started_utc,
        )
        budget_refusal = supervisor.issue_token(
            agent_id="proof.planner",
            tools=frozenset({"llm.complete"}),
            scopes=frozenset({"phase3.3-budget"}),
            budget=exhausted_budget,
        )
        if not isinstance(budget_refusal, Err) or budget_refusal.code != "budget_exceeded":
            raise RuntimeError("budget scenario did not refuse llm.complete token")
        budget_plan = planner.plan(
            PlanRequest(
                run_id="phase3.3-budget",
                agent_id="proof.planner",
                prompt="calibration cube",
            ),
            token=_issue_token(
                supervisor,
                agent_id="proof.planner",
                tools=frozenset({"planner.plan"}),
                scopes=frozenset({"phase3.3-budget"}),
            ),
            llm_token=None,
            budget=exhausted_budget,
            gateway=gateway,
            caller=fixture_caller("happy", "budget_exhausted"),
            policy=policy,
            mode="llm",
        )
        if not isinstance(budget_plan.result, Ok):
            raise RuntimeError(f"budget fallback scenario failed: {budget_plan.result}")
        if budget_plan.result.value.metadata.get("planner_mode") != "template":
            raise RuntimeError("budget fallback did not return planner_mode=template")

        malformed = planner.plan(
            PlanRequest(
                run_id="phase3.3-malformed",
                agent_id="proof.planner",
                prompt="calibration cube",
            ),
            token=_issue_token(
                supervisor,
                agent_id="proof.planner",
                tools=frozenset({"planner.plan"}),
                scopes=frozenset({"phase3.3-malformed"}),
            ),
            llm_token=_issue_token(
                supervisor,
                agent_id="proof.planner",
                tools=frozenset({"llm.complete"}),
                scopes=frozenset({"phase3.3-malformed"}),
            ),
            budget=fresh_budget_state(),
            gateway=gateway,
            caller=fixture_caller("malformed", "malformed"),
            policy=policy,
            mode="llm",
        )
        if not isinstance(malformed.result, Ok):
            raise RuntimeError(f"malformed fallback scenario failed: {malformed.result}")
        if malformed.result.value.metadata.get("planner_mode") != "template":
            raise RuntimeError("malformed fallback did not return planner_mode=template")

        direct_malformed = gateway.complete(
            "calibration cube",
            token=_issue_token(
                supervisor,
                agent_id="proof.gateway",
                tools=frozenset({"llm.complete"}),
                scopes=frozenset({"phase3.3-malformed-direct"}),
            ),
            budget=fresh_budget_state(),
            caller=fixture_caller("malformed", "malformed_direct_gateway"),
        )
        if not isinstance(direct_malformed, Ok):
            raise RuntimeError(f"direct malformed gateway trace failed: {direct_malformed}")

        bridge_state = BridgeState(
            ledger=ledger,
            supervisor=supervisor,
            planner=PlannerAgent(supervisor=supervisor, ledger=ledger),
        )
        preview = bridge_state.preview_plan("calibration cube")
        if preview["metadata"].get("planner_mode") != "template":
            raise RuntimeError("bridge preview did not surface planner_mode=template")
        preview_events = ledger.events(str(preview["run_id"]))
        plan_preview_replay.write_text(
            _canonical_json(
                {
                    "ledger_events": [
                        {
                            "message": event.message,
                            "tool": event.tool,
                            "verdict": event.verdict,
                        }
                        for event in preview_events
                    ],
                    "request": {"prompt": "calibration cube"},
                    "response": preview,
                    "route": "POST /api/plan/preview",
                }
            ),
            encoding="utf-8",
        )

        llm_redacted_trace_sample.write_text(
            _canonical_json({"traces": traces}),
            encoding="utf-8",
        )

        counts = _ledger_counts(ledger)
        if counts.get("llm.complete", 0) < 1:
            raise RuntimeError("ledger has no llm.complete rows")
        if counts.get("planner.fallback", 0) < 2:
            raise RuntimeError("ledger has fewer than two planner.fallback rows")
        if counts.get("budget.exceeded", 0) < 1:
            raise RuntimeError("ledger has no budget.exceeded rows")

        gc.collect()
        ledger_snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_db, ledger_snapshot)


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


def _count_tool(ledger: Any, run_id: str, tool: str) -> int:
    return sum(1 for event in ledger.events(run_id) if event.tool == tool)


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
        "schema_version": "phase3.3-bundle-1.0.0",
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
        with tempfile.TemporaryDirectory(prefix="phase33-counts-") as tmp:
            db_path = Path(tmp) / "ledger_snapshot.sqlite3"
            db_path.write_bytes(zf.read("evidence/ledger_snapshot.sqlite3"))
            return _ledger_counts_from_db(db_path)


def _ledger_counts_from_db(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT tool, COUNT(*) FROM events GROUP BY tool").fetchall()
    finally:
        conn.close()
    return {str(tool): int(count) for tool, count in rows}


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
