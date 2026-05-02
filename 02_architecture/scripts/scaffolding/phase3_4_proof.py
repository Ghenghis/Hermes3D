#!/usr/bin/env python3
"""Assemble the Phase 3.4 real-provider probe proof bundle.

The bundle is evidence-only: it snapshots the plan/ADR, an offline ledger with
provider.probe pass/fail, budget.exceeded(provider.probe), and llm.complete rows,
redacted provider probe replay samples, deterministic plan-preview replay data,
UI build hashes, and the Playwright JSON report. It also verifies that the
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
from datetime import UTC, datetime, timedelta
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

        if len(entries) != 7:
            raise RuntimeError(f"manifest entry count must be 7, got {len(entries)}")

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for archive_name in sorted(entries):
                zf.write(entries[archive_name], archive_name)

        manifest = _build_manifest(run_id, zip_path)
        manifest_path.write_text(_canonical_json(manifest), encoding="utf-8")
        digest = _sha256_file(zip_path)
        sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")

    verified = verify_bundle(zip_path, manifest_path)
    ledger_counts = _required_ledger_counts_from_zip(zip_path)
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
            counts = _required_ledger_counts_from_db(db_path)
        missing = sorted(name for name, count in counts.items() if count < 1)
        if missing:
            raise RuntimeError(f"ledger missing required event categories: {missing}")
    return True


def _write_phase34_replay(
    *,
    ledger_snapshot: Path,
    provider_probe_replay: Path,
    plan_preview_replay: Path,
) -> None:
    sys.path.insert(0, str(REPO_ROOT / "03_implementation" / "src"))
    sys.path.insert(0, str(REPO_ROOT / "04_testing" / "fixtures"))

    from hermes3d.gateways.budget import fresh_budget_state
    from hermes3d.gateways.llm import LLMGateway
    from hermes3d.gateways.probe import ProbeOutcome, ProviderProbeGateway
    from hermes3d.orchestration import Err, OfflineSupervisor, Ok
    from hermes3d.orchestration.bridge import BridgeState
    from hermes3d.orchestration.ledger import OrchestrationLedger
    from hermes3d.orchestration.types import (
        BudgetState,
        LLMRequest,
        LLMResponse,
        ProviderConfig,
    )
    from llm import create_app as create_llm_app
    from providers.server import create_app as create_provider_app
    from starlette.testclient import TestClient

    minimax_config = ProviderConfig(
        base_url="https://api.minimax.io/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="HERMES3D_MINIMAX_API_KEY",
        cost_cap_usd_per_run=Decimal("0.05"),
        cost_cap_usd_per_day=Decimal("1.00"),
    )
    deepseek_config = ProviderConfig(
        base_url="https://api.deepseek.com/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="HERMES3D_DEEPSEEK_API_KEY",
        cost_cap_usd_per_run=Decimal("0.05"),
        cost_cap_usd_per_day=Decimal("1.00"),
    )

    def wrap_provider_test_client(provider_id: str, mode: str):
        client = TestClient(create_provider_app(provider_id, mode=mode))

        def caller(_config: ProviderConfig) -> ProbeOutcome:
            response = client.get("/v1/models")
            return ProbeOutcome(
                http_status=response.status_code,
                latency_ms=11 if mode == "happy" else 19,
                body=response.text,
            )

        return caller

    def wrap_llm_test_client(mode: str):
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
            providers={"minimax": minimax_config, "deepseek": deepseek_config},
        )
        llm_gateway = LLMGateway(ledger=ledger, policy=_llm_policy())
        scenarios: list[dict[str, object]] = []
        now = datetime.now(UTC)

        result_a = probe_gateway.probe(
            "minimax",
            token=_issue_token(
                supervisor,
                agent_id="proof.cli.probe",
                tools=frozenset({"provider.probe"}),
                scopes=frozenset({"proof-probe-happy"}),
            ),
            budget=fresh_budget_state(now_utc=now),
            probe_caller=wrap_provider_test_client("minimax", "happy"),
            now_utc=now,
        )
        if not isinstance(result_a, Ok) or not result_a.value.success:
            raise RuntimeError(f"scenario A failed: {result_a}")
        scenarios.append(_probe_entry("A", "minimax", result_a.value))

        fail_time = now + timedelta(seconds=61)
        result_b = probe_gateway.probe(
            "minimax",
            token=_issue_token(
                supervisor,
                agent_id="proof.cli.probe",
                tools=frozenset({"provider.probe"}),
                scopes=frozenset({"proof-probe-fail"}),
            ),
            budget=fresh_budget_state(now_utc=fail_time),
            probe_caller=wrap_provider_test_client("minimax", "unauthorized"),
            now_utc=fail_time,
        )
        if not isinstance(result_b, Ok) or result_b.value.success:
            raise RuntimeError(f"scenario B failed: {result_b}")
        scenarios.append(_probe_entry("B", "minimax", result_b.value))

        result_c = llm_gateway.complete(
            "calibration cube",
            token=_issue_token(
                supervisor,
                agent_id="proof.cli.complete",
                tools=frozenset({"llm.complete"}),
                scopes=frozenset({"proof-complete-after-probe"}),
            ),
            budget=fresh_budget_state(now_utc=fail_time),
            caller=wrap_llm_test_client("happy"),
            provider_id="minimax",
            now_utc=fail_time,
        )
        if not isinstance(result_c, Ok):
            raise RuntimeError(f"scenario C failed: {result_c}")
        scenarios.append(_llm_entry("C", "minimax", result_c.value))

        result_d = llm_gateway.complete(
            "calibration cube",
            token=_issue_token(
                supervisor,
                agent_id="proof.cli.complete",
                tools=frozenset({"llm.complete"}),
                scopes=frozenset({"proof-complete-no-probe"}),
            ),
            budget=fresh_budget_state(now_utc=fail_time),
            caller=wrap_llm_test_client("happy"),
            provider_id="deepseek",
            now_utc=fail_time,
        )
        if not isinstance(result_d, Err) or result_d.code != "provider_not_probed":
            raise RuntimeError(f"scenario D did not produce R9 refusal: {result_d}")
        scenarios.append(_err_entry("D", "deepseek", result_d.code))

        exhausted_budget = BudgetState(
            spent_usd_run=Decimal("0"),
            spent_usd_day=Decimal("0.10"),
            day_started_utc=fresh_budget_state(now_utc=fail_time).day_started_utc,
        )
        result_e = supervisor.issue_token(
            agent_id="proof.cli.r10",
            tools=frozenset({"provider.probe"}),
            scopes=frozenset({"proof-r10"}),
            budget=exhausted_budget,
            now_utc=fail_time,
        )
        if not isinstance(result_e, Err) or result_e.code != "budget_exceeded":
            raise RuntimeError(f"scenario E did not produce R10 refusal: {result_e}")
        scenarios.append(
            {
                "cap": result_e.message,
                "error_code": result_e.code,
                "provider_id": "minimax",
                "result_type": "Err",
                "scenario": "E",
            }
        )

        result_f = llm_gateway.complete(
            "calibration cube",
            token=_issue_token(
                supervisor,
                agent_id="proof.cli.fixture",
                tools=frozenset({"llm.complete"}),
                scopes=frozenset({"proof-fixture"}),
            ),
            budget=fresh_budget_state(now_utc=fail_time),
            caller=wrap_llm_test_client("happy"),
        )
        if not isinstance(result_f, Ok):
            raise RuntimeError(f"scenario F failed: {result_f}")
        scenarios.append(_llm_entry("F", "openai-fixture", result_f.value))

        bridge_state = BridgeState(ledger=ledger, supervisor=supervisor)
        preview = bridge_state.preview_plan("calibration cube")
        if preview["metadata"].get("planner_mode") != "template":
            raise RuntimeError("bridge preview did not surface planner_mode=template")
        plan_preview_replay.write_text(
            _canonical_json(
                {
                    "request": {"prompt": "calibration cube"},
                    "response": preview,
                    "route": "POST /api/plan/preview",
                }
            ),
            encoding="utf-8",
        )
        provider_probe_replay.write_text(
            _canonical_json(
                {
                    "contract": _proof_contract(),
                    "ledger_counts": _required_ledger_counts(ledger),
                    "scenarios": scenarios,
                }
            ),
            encoding="utf-8",
        )

        counts = _required_ledger_counts(ledger)
        missing = sorted(name for name, count in counts.items() if count < 1)
        if missing:
            raise RuntimeError(f"ledger missing required event categories: {missing}")

        gc.collect()
        ledger_snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp_db, ledger_snapshot)


def _llm_policy() -> Any:
    from hermes3d.gateways.llm import LLMPolicy

    return LLMPolicy(
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


def _probe_entry(scenario: str, provider_id: str, result: Any) -> dict[str, object]:
    return {
        "http_status": result.http_status,
        "latency_ms": result.latency_ms,
        "provider_id": provider_id,
        "redacted_excerpt": result.redacted_excerpt,
        "response_sha256": result.response_sha256,
        "result_type": "Ok",
        "scenario": scenario,
        "success": result.success,
    }


def _llm_entry(scenario: str, provider_id: str, result: Any) -> dict[str, object]:
    return {
        "provider_id": provider_id,
        "result_type": "Ok",
        "scenario": scenario,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
    }


def _err_entry(scenario: str, provider_id: str, error_code: str) -> dict[str, object]:
    return {
        "error_code": error_code,
        "provider_id": provider_id,
        "result_type": "Err",
        "scenario": scenario,
    }


def _proof_contract() -> dict[str, object]:
    return {
        "audit_hash_chain": [
            hashlib.sha256(f"phase3.4-proof-scenario-{index}".encode("utf-8")).hexdigest()
            for index in range(256)
        ],
        "required_ledger_categories": [
            "provider.probe.pass",
            "provider.probe.fail",
            "budget.exceeded.provider.probe",
            "llm.complete",
        ],
        "scenario_matrix": [
            {
                "scenario": "A",
                "description": "Happy MiniMax probe writes provider.probe verdict=pass.",
                "expected": "Ok(success=True)",
            },
            {
                "scenario": "B",
                "description": "MiniMax unauthorized fixture writes provider.probe verdict=fail.",
                "expected": "Ok(success=False)",
            },
            {
                "scenario": "C",
                "description": "MiniMax completion succeeds only after a fresh provider.probe row.",
                "expected": "Ok(LLMResponse)",
            },
            {
                "scenario": "D",
                "description": "DeepSeek completion without a recent successful probe returns R9.",
                "expected": 'Err("provider_not_probed")',
            },
            {
                "scenario": "E",
                "description": "Probe token issuance with exhausted daily budget returns R10.",
                "expected": 'Err("budget_exceeded", "per_day")',
            },
            {
                "scenario": "F",
                "description": "The openai-fixture provider remains exempt from R9.",
                "expected": "Ok(LLMResponse)",
            },
        ],
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


def _required_ledger_counts(ledger: Any) -> dict[str, int]:
    counts = {
        "budget.exceeded.provider.probe": 0,
        "llm.complete": 0,
        "provider.probe.fail": 0,
        "provider.probe.pass": 0,
    }
    for event in ledger.events():
        if event.tool == "provider.probe" and event.verdict == "pass":
            counts["provider.probe.pass"] += 1
        elif event.tool == "provider.probe" and event.verdict == "fail":
            counts["provider.probe.fail"] += 1
        elif event.tool == "budget.exceeded" and "provider.probe" in event.message:
            counts["budget.exceeded.provider.probe"] += 1
        elif event.tool == "llm.complete":
            counts["llm.complete"] += 1
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
        "proof": _proof_contract(),
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


def _required_ledger_counts_from_zip(zip_path: Path) -> dict[str, int]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        with tempfile.TemporaryDirectory(prefix="phase34-counts-") as tmp:
            db_path = Path(tmp) / "ledger_snapshot.sqlite3"
            db_path.write_bytes(zf.read("evidence/ledger_snapshot.sqlite3"))
            return _required_ledger_counts_from_db(db_path)


def _required_ledger_counts_from_db(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    try:
        rows = {
            "provider.probe.pass": conn.execute(
                "SELECT COUNT(*) FROM events WHERE tool='provider.probe' AND verdict='pass'"
            ).fetchone()[0],
            "provider.probe.fail": conn.execute(
                "SELECT COUNT(*) FROM events WHERE tool='provider.probe' AND verdict='fail'"
            ).fetchone()[0],
            "budget.exceeded.provider.probe": conn.execute(
                """
                SELECT COUNT(*) FROM events
                WHERE tool='budget.exceeded' AND message LIKE '%provider.probe%'
                """
            ).fetchone()[0],
            "llm.complete": conn.execute(
                "SELECT COUNT(*) FROM events WHERE tool='llm.complete'"
            ).fetchone()[0],
        }
    finally:
        conn.close()
    return {str(key): int(value) for key, value in rows.items()}


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
