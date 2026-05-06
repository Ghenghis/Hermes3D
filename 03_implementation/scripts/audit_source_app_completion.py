#!/usr/bin/env python3
"""Write a compact Source OS 60-app completion audit.

This audit is intentionally a proof summary, not an installer. It records the
current source registry truth, the runtime/setup queue truth when the local API
is reachable, and the remaining runner work required before a source checkout
can be called a runnable Hermes3D app.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
PROOF_DIR = REPO_ROOT / "03_implementation" / "proof"
SOURCE_AUDIT_PATH = PROOF_DIR / "SOURCE_REGISTRY_TRUTH_AUDIT.json"
OUTPUT_PATH = PROOF_DIR / "SOURCE_APP_60_COMPLETION_AUDIT.json"
RUNTIME_QUEUE_URL = "http://127.0.0.1:8765/api/modules/runtime/setup-queue"
RUNTIME_VERIFIERS_URL = "http://127.0.0.1:8765/api/modules/runtime/verifiers"
CLI_SURFACE_URL = "http://127.0.0.1:8765/api/modules/runtime/cli-surface"
MODULES_URL = "http://127.0.0.1:8765/api/modules"
SRC_PATH = REPO_ROOT / "03_implementation" / "src"
RUNTIME_ENDPOINT_TIMEOUT_S = 30


def main() -> int:
    sys.path.insert(0, str(SRC_PATH))
    from hermes3d.services.module_runtime import registered_runtime_probe_ids

    source_audit = read_json(SOURCE_AUDIT_PATH)
    modules = source_audit.get("modules") if isinstance(source_audit, dict) else []
    modules = modules if isinstance(modules, list) else []
    runtime_queue = read_runtime_queue()
    runtime_verifiers = read_runtime_verifiers()
    cli_surface = read_cli_surface()
    api_modules = read_modules()
    records = runtime_queue.get("records") if isinstance(runtime_queue, dict) else []
    records = records if isinstance(records, list) else []
    runner_counts = Counter(str(record.get("runner_status") or "blocked") for record in records if isinstance(record, dict))
    queue_counts = runtime_queue.get("counts", {}) if isinstance(runtime_queue, dict) else {}
    runtime_ready_count = int(queue_counts.get("runtime_ready", runner_counts.get("runtime_ready", 0)) or 0) if runtime_queue else None
    remaining_runner_gap = int(queue_counts.get("runner_not_registered", max(0, 60 - runner_counts.get("runtime_ready", 0))) or 0) if runtime_queue else None
    launch_kind_counts = Counter(
        str(record.get("launchKind") or record.get("launch_kind") or "unknown")
        for record in api_modules
        if isinstance(record, dict)
    )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target": {
            "source_backed_apps": 60,
            "note": "User corrected the active Source OS completion target to 60 source-backed apps.",
        },
        "source_registry": {
            "path": str(SOURCE_AUDIT_PATH),
            "registry_entries_unique": int(source_audit.get("summary", {}).get("registry_entries_unique", len(modules))) if isinstance(source_audit.get("summary"), dict) else len(modules),
            "installed_git": int(source_audit.get("summary", {}).get("installed_git", 0)) if isinstance(source_audit.get("summary"), dict) else 0,
            "not_operational": len(source_audit.get("not_operational", [])) if isinstance(source_audit, dict) and isinstance(source_audit.get("not_operational"), list) else 0,
            "by_section": source_audit.get("by_section", {}) if isinstance(source_audit, dict) else {},
        },
        "runtime_setup_queue": {
            "source": RUNTIME_QUEUE_URL if runtime_queue else "unavailable",
            "count": int(runtime_queue.get("count", 0)) if isinstance(runtime_queue, dict) else 0,
            "counts": queue_counts if isinstance(queue_counts, dict) else {},
            "runner_status_counts": dict(sorted(runner_counts.items())),
            "registered_runtime_probe_ids": registered_runtime_probe_ids(),
            "registered_runtime_verifiers": {
                "source": RUNTIME_VERIFIERS_URL if runtime_verifiers else "service fallback",
                "count": int(runtime_verifiers.get("count", 0)) if isinstance(runtime_verifiers, dict) else len(registered_runtime_probe_ids()),
                "enabled_count": int(runtime_verifiers.get("enabled_count", 0)) if isinstance(runtime_verifiers, dict) else len(registered_runtime_probe_ids()),
                "registered_ids": runtime_verifiers.get("registered_ids", registered_runtime_probe_ids()) if isinstance(runtime_verifiers, dict) else registered_runtime_probe_ids(),
            },
            "execution_mode": runtime_queue.get("execution_mode") if isinstance(runtime_queue, dict) else None,
            "agent_gate": runtime_queue.get("agent_gate") if isinstance(runtime_queue, dict) else "Local runtime setup queue API was not reachable during this audit.",
        },
        "cli_surface": {
            "source": CLI_SURFACE_URL if cli_surface else "unavailable",
            "proof_source": cli_surface.get("proof_source") if isinstance(cli_surface, dict) else None,
            "summary": cli_surface.get("summary", {}) if isinstance(cli_surface, dict) else {},
            "rule": cli_surface.get("target", {}).get("rule") if isinstance(cli_surface.get("target"), dict) else None,
        },
        "launch_kind_classification": {
            "source": MODULES_URL if api_modules else "unavailable",
            "count": len(api_modules),
            "unknown": launch_kind_counts.get("unknown", 0),
            "by_launch_kind": dict(sorted(launch_kind_counts.items())),
        },
        "completion": {
            "source_rows_complete": len(modules) == 60 and payload_truth(source_audit),
            "runtime_ready_complete": runtime_ready_count == 60,
            "remaining_runner_gap": remaining_runner_gap,
            "blocked_rows": runner_counts.get("blocked", 0),
            "unknown_launch_kind_rows": launch_kind_counts.get("unknown", 0),
            "status": "api_unavailable" if runtime_ready_count is None else "runner_gap" if runtime_ready_count < 60 else "complete",
        },
        "next_actions": [
            "Keep the visible Source OS app count at 60 until SOURCE_REGISTRY_TRUTH_AUDIT.json and /api/modules agree.",
            "Register safe verifiers before moving a source-ready row to runtime-ready.",
            "Add app-family smoke gates for CLI apps, Python workers, web apps, desktop launchers, GPU workers, firmware references, and catalog/reference rows.",
            "Keep unregistered setup as plan-only for Hermes Agents; no install/build/update should execute without a registered runner, backup path, proof event, and rollback policy.",
            "Rerun TypeScript, Playwright Source OS/Plugins/Roadmap/Settings tests, and the active UI no-fake scan after changing runner status or UI wording.",
        ],
    }

    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "path": str(OUTPUT_PATH),
        "source_backed_apps": payload["target"]["source_backed_apps"],
        "runtime_ready": payload["runtime_setup_queue"]["counts"].get("runtime_ready"),
        "remaining_runner_gap": payload["completion"]["remaining_runner_gap"],
        "status": payload["completion"]["status"],
    }, indent=2, sort_keys=True))
    return 0


def payload_truth(source_audit: dict) -> bool:
    summary = source_audit.get("summary", {})
    if not isinstance(summary, dict):
        return False
    return (
        summary.get("registry_entries_unique") == 60
        and summary.get("installed_git") == 60
        and summary.get("source_available_missing_checkout") == 0
        and summary.get("unavailable_no_verified_repo") == 0
        and summary.get("failed_path") == 0
    )


def read_json(path: Path) -> dict:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_runtime_queue() -> dict:
    request = Request(RUNTIME_QUEUE_URL, headers={"accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=RUNTIME_ENDPOINT_TIMEOUT_S) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_runtime_verifiers() -> dict:
    request = Request(RUNTIME_VERIFIERS_URL, headers={"accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=RUNTIME_ENDPOINT_TIMEOUT_S) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_cli_surface() -> dict:
    request = Request(CLI_SURFACE_URL, headers={"accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=RUNTIME_ENDPOINT_TIMEOUT_S) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def read_modules() -> list[dict]:
    request = Request(MODULES_URL, headers={"accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
