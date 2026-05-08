from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = IMPLEMENTATION_ROOT / "proof" / "SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json"

CLI_PREFERRED_LAUNCH_KINDS = {"cli_worker", "cli_or_python_worker", "desktop_or_cli"}
CLI_POSSIBLE_LAUNCH_KINDS = {"desktop_app", "python_worker", "gpu_worker", "service", "web_app", "npm_package"}
AGENT_CLI_VERIFIER_KINDS = {"cli", "python_module_cli"}


def main() -> int:
    import sys

    sys.path.insert(0, str(IMPLEMENTATION_ROOT / "src"))
    from hermes3d.db.init import connect, init_db
    from hermes3d.db.load_modules import load_modules
    from hermes3d.services.module_runtime import (
        module_runner_contract,
        module_runtime_probe,
        registered_runtime_probe_ids,
    )

    init_db()
    load_modules()
    conn = connect()
    try:
        modules = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, display_name, section, launch_kind, install_state, local_path, repo_url
                  FROM modules
                 ORDER BY section, display_name
                """
            ).fetchall()
        ]
    finally:
        conn.close()

    rows = [classify_module(module_runtime_probe(module, live=False), module, module_runner_contract(module)) for module in modules]
    counts = Counter(row["agent_execution_tier"] for row in rows)
    contract_counts = Counter(row["runner_contract_status"] for row in rows)
    cli_rows = [row for row in rows if row["agent_execution_tier"] == "verified_agent_cli"]
    executable_rows = [row for row in rows if row["agent_executable"]]
    launcher_rows = [row for row in rows if row["agent_execution_tier"] == "launcher_metadata_only"]
    gap_rows = [row for row in rows if row["agent_execution_tier"].endswith("_gap")]
    read_only_rows = [row for row in rows if row["read_only_runner_available"]]
    executable_path_rows = [row for row in rows if row["executable_path_runner_available"]]
    python_import_repair_rows = [row for row in rows if row["python_import_repair_available"]]
    cli_install_config_rows = [row for row in rows if row["cli_install_config_available"]]
    audit = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "target": {
            "source_backed_apps": len(rows),
            "registered_verifiers": len(registered_runtime_probe_ids()),
            "rule": "If an app offers a CLI, Hermes3D must prefer a bounded CLI verifier and Hermes Agent runner; desktop launcher metadata is not agent CLI readiness.",
        },
        "summary": {
            "by_agent_execution_tier": dict(sorted(counts.items())),
            "by_runner_contract_status": dict(sorted(contract_counts.items())),
            "verified_agent_cli": len(cli_rows),
            "agent_executable": len(executable_rows),
            "read_only_runner_available": len(read_only_rows),
            "executable_path_runner_available": len(executable_path_rows),
            "python_import_repair_available": len(python_import_repair_rows),
            "cli_install_config_available": len(cli_install_config_rows),
            "launcher_metadata_only": len(launcher_rows),
            "runner_gaps": len(gap_rows),
            "verified_agent_cli_modules": [row["module_id"] for row in cli_rows],
            "agent_executable_modules": [row["module_id"] for row in executable_rows],
            "read_only_runner_modules": [row["module_id"] for row in read_only_rows],
            "executable_path_runner_modules": [row["module_id"] for row in executable_path_rows],
            "python_import_repair_modules": [
                row["module_id"] for row in python_import_repair_rows
            ],
            "cli_install_config_modules": [
                row["module_id"] for row in cli_install_config_rows
            ],
            "launcher_metadata_only_modules": [row["module_id"] for row in launcher_rows],
        },
        "rows": rows,
        "next_actions": [
            "Keep verified CLI modules agent-usable through bounded help/version/dry-run commands first.",
            "Use /api/modules/runtime/runner-contracts as the canonical Hermes Agent execution matrix.",
            "Use /api/modules/{module_id}/runtime/read-only-runner only for read_only_runner_available rows; it appends proof and cannot install, launch, update, write outputs, or touch printers.",
            "Use /api/modules/{module_id}/runtime/executable-path-runner only for executable_path_runner_available rows; it reads executable metadata/hash only and cannot launch apps or touch printers.",
            "Use /api/modules/{module_id}/runtime/python-import-repair-runner only for python_import_repair_available rows; it reads source/dependency metadata only and cannot install packages or start workers.",
            "Use /api/modules/{module_id}/runtime/cli-install-config-runner only for cli_install_config_available rows; it reads Slic3r/SuperSlicer source/schema/profile metadata only and cannot install, launch, slice, write outputs, or touch printers.",
            "Promote launcher-only rows only after proving a safe CLI, service API, or explicit desktop-bridge smoke.",
            "For CLI-preferred gaps, locate/install the real executable or document no-CLI-with-proof before exposing agent actions.",
            "For Python/Node/GPU/service/web gaps, register import, package, health, or tiny smoke gates before enabling Hermes Agent runners.",
            "Never mark a row agent-executable from source checkout presence alone.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"path": str(OUTPUT), **audit["summary"]}, indent=2, sort_keys=True))
    return 0


def classify_module(runtime: dict[str, Any], module: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    runtime_status = str(runtime.get("status") or "blocked")
    kind = str(runtime.get("kind") or module.get("launch_kind") or "unknown")
    proof_gate = str(runtime.get("proof_gate_version") or "")
    verifier = str(runtime.get("verifier") or "")
    launch_kind = str(module.get("launch_kind") or "unknown")
    execution_tier = "runner_gap"
    if runtime_status == "ready" and kind in AGENT_CLI_VERIFIER_KINDS and bool(runtime.get("executed")):
        execution_tier = "verified_agent_cli"
    elif runtime_status == "ready" and (proof_gate == "desktop-launcher-metadata-v1" or (kind == "desktop_app" and not bool(runtime.get("executed")))):
        execution_tier = "launcher_metadata_only"
    elif runtime_status == "ready" and kind in {"python_import", "python_source_import", "node_package"}:
        execution_tier = "package_or_import_ready"
    elif runtime_status == "ready" and kind == "moonraker_fleet":
        execution_tier = "service_api_ready"
    elif runtime_status == "ready" and kind == "source_inventory":
        execution_tier = "source_reference_ready"
    elif launch_kind in CLI_PREFERRED_LAUNCH_KINDS:
        execution_tier = "cli_preferred_gap"
    elif launch_kind in CLI_POSSIBLE_LAUNCH_KINDS:
        execution_tier = f"{launch_kind}_gap"

    return {
        "module_id": str(module.get("id") or ""),
        "display": str(module.get("display_name") or module.get("id") or ""),
        "section": str(module.get("section") or ""),
        "launch_kind": launch_kind,
        "agent_execution_tier": execution_tier,
        "runtime_status": runtime_status,
        "verifier": verifier,
        "verifier_kind": kind,
        "proof_gate_version": proof_gate,
        "path": str(runtime.get("path") or module.get("local_path") or ""),
        "executed": bool(runtime.get("executed")),
        "return_code": runtime.get("return_code"),
        "capabilities": list(runtime.get("capabilities") or []),
        "reason": runtime.get("reason"),
        "agent_executable": bool(contract.get("agent_executable")),
        "read_only_runner_available": bool(contract.get("read_only_runner_available")),
        "read_only_runner_route": f"/api/modules/{module.get('id')}/runtime/read-only-runner"
        if contract.get("read_only_runner_available")
        else None,
        "executable_path_runner_available": bool(
            contract.get("executable_path_runner_available")
        ),
        "executable_path_runner_route": f"/api/modules/{module.get('id')}/runtime/executable-path-runner"
        if contract.get("executable_path_runner_available")
        else None,
        "python_import_repair_available": bool(
            contract.get("python_import_repair_available")
        ),
        "python_import_repair_route": f"/api/modules/{module.get('id')}/runtime/python-import-repair-runner"
        if contract.get("python_import_repair_available")
        else None,
        "cli_install_config_available": bool(
            contract.get("cli_install_config_available")
        ),
        "cli_install_config_route": f"/api/modules/{module.get('id')}/runtime/cli-install-config-runner"
        if contract.get("cli_install_config_available")
        else None,
        "runner_contract_status": str(contract.get("runner_status") or "blocked"),
        "required_verifier_family": str(contract.get("required_verifier_family") or ""),
        "acceptance_gate": str(contract.get("acceptance_gate") or ""),
        "safe_actions": list(contract.get("safe_actions") or []),
        "next_action": next_action_for(execution_tier, launch_kind, verifier),
    }


def next_action_for(execution_tier: str, launch_kind: str, verifier: str) -> str:
    if execution_tier == "verified_agent_cli":
        return f"Expose bounded Hermes Agent runner using {verifier}; add dry-run smoke before mutating outputs."
    if execution_tier == "launcher_metadata_only":
        return "Do not call this agent CLI-ready; add CLI/API smoke or explicit desktop bridge before agent execution."
    if execution_tier in {"package_or_import_ready", "service_api_ready"}:
        return "Add a tiny non-mutating worker/API smoke gate before enabling write actions."
    if execution_tier == "source_reference_ready":
        return "Use as read-only reference data; do not expose runnable actions unless a real adapter exists."
    if launch_kind in CLI_PREFERRED_LAUNCH_KINDS:
        return "Locate/install the CLI executable or document no local CLI with proof; keep agent actions disabled."
    return "Register a safe module-specific verifier and runner before Hermes Agents can execute this app."


if __name__ == "__main__":
    raise SystemExit(main())
