from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
PROOF_DIR = IMPLEMENTATION_ROOT / "proof"
READINESS_JSON = PROOF_DIR / "SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json"
CLI_SURFACE_JSON = PROOF_DIR / "SOURCE_APP_CLI_SURFACE_AUDIT.json"
COMPLETION_JSON = PROOF_DIR / "SOURCE_APP_60_COMPLETION_AUDIT.json"
OUTPUT = PROOF_DIR / "SOURCE_APP_RUNTIME_ACTION_PLAN.md"
sys.path.insert(0, str(IMPLEMENTATION_ROOT / "src"))
try:
    from hermes3d.services.module_runtime import BUILTIN_RUNTIME_PROBES, SERVICE_START_RUNNERS
except Exception:
    BUILTIN_RUNTIME_PROBES = {}
    SERVICE_START_RUNNERS = {}

GAP_TIERS = {
    "cli_preferred_gap",
    "desktop_app_gap",
    "gpu_worker_gap",
    "npm_package_gap",
    "python_worker_gap",
    "runner_gap",
    "service_gap",
    "web_app_gap",
}


def main() -> int:
    readiness = read_json(READINESS_JSON)
    cli_surface = read_json(CLI_SURFACE_JSON)
    completion = read_json(COMPLETION_JSON)
    readiness_rows = list(readiness.get("rows") or [])
    surface_rows = list(cli_surface.get("records") or [])
    surface_by_id = {
        str(row.get("module_id")): row for row in surface_rows if isinstance(row, dict)
    }
    gaps = [
        row
        for row in readiness_rows
        if isinstance(row, dict) and str(row.get("agent_execution_tier")) in GAP_TIERS
    ]
    verified = [
        row
        for row in readiness_rows
        if isinstance(row, dict) and row.get("agent_execution_tier") == "verified_agent_cli"
    ]
    launcher_only = [
        row
        for row in readiness_rows
        if isinstance(row, dict) and row.get("agent_execution_tier") == "launcher_metadata_only"
    ]
    read_only_runner_rows = [
        row
        for row in readiness_rows
        if isinstance(row, dict) and row.get("read_only_runner_available")
    ]
    executable_path_runner_rows = [
        row
        for row in readiness_rows
        if isinstance(row, dict) and row.get("executable_path_runner_available")
    ]
    python_import_repair_rows = [
        row
        for row in readiness_rows
        if isinstance(row, dict) and row.get("python_import_repair_available")
    ]
    cli_install_config_rows = [
        row
        for row in readiness_rows
        if isinstance(row, dict) and row.get("cli_install_config_available")
    ]
    candidate_rows = [
        row
        for row in surface_rows
        if isinstance(row, dict)
        and str(row.get("cli_surface_status", "")).endswith("_needs_verifier")
    ]

    gap_counts = Counter(str(row.get("agent_execution_tier")) for row in gaps)
    candidate_counts = Counter(str(row.get("cli_surface_status")) for row in candidate_rows)
    completion_counts = (
        completion.get("runtime_setup_queue", {}).get("counts", {})
        if isinstance(completion.get("runtime_setup_queue"), dict)
        else {}
    )
    runner_not_registered = completion_counts.get("runner_not_registered")
    runtime_repair_required = completion_counts.get("runtime_repair_required", 0)
    source_install_available = completion_counts.get("source_install_available", 0)
    blocked_rows = completion_counts.get("blocked", 0)

    lines: list[str] = [
        "# Source OS Runtime Action Plan",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        "This plan is generated from the Source OS proof JSONs. It is the durable queue for the remaining 60-app runtime work: no app row is considered Hermes Agent usable unless a bounded verifier proves it and the UI shows that proof.",
        "",
        "## Current Truth",
        "",
        f"- Source-backed apps: {completion.get('target', {}).get('source_backed_apps', readiness.get('target', {}).get('source_backed_apps', 60))}",
        f"- Runtime-ready apps: {completion_counts.get('runtime_ready', readiness.get('target', {}).get('registered_verifiers', 'unknown'))}",
        f"- Runner-not-registered rows: {runner_not_registered if runner_not_registered is not None else 'unknown'}",
        f"- Runtime-repair-required rows: {runtime_repair_required}",
        f"- Source-install-available rows: {source_install_available}",
        f"- Open P0 runner/repair rows: {len(gaps)}",
        f"- Verified Hermes Agent CLIs: {readiness.get('summary', {}).get('verified_agent_cli', len(verified))}",
        f"- Agent-executable runner contracts: {readiness.get('summary', {}).get('agent_executable', len(verified))}",
        f"- Read-only runner smoke rows: {readiness.get('summary', {}).get('read_only_runner_available', len(read_only_runner_rows))}",
        f"- Executable path runner smoke rows: {readiness.get('summary', {}).get('executable_path_runner_available', len(executable_path_runner_rows))}",
        f"- Python import repair preflight rows: {readiness.get('summary', {}).get('python_import_repair_available', len(python_import_repair_rows))}",
        f"- CLI install/config preflight rows: {readiness.get('summary', {}).get('cli_install_config_available', len(cli_install_config_rows))}",
        f"- CLI/service signals needing verifiers: {cli_surface.get('summary', {}).get('candidate_needs_verifier', len(candidate_rows))}",
        f"- Blocked rows: {blocked_rows}",
        "",
        "## Correction Rules",
        "",
        "- A source checkout is not a working app by itself.",
        "- A README command, package script, or desktop launcher is only a signal until a local non-destructive verifier passes.",
        "- Hermes Agents may execute only verifier-backed runners, never raw unreviewed shell commands from docs.",
        "- Read-only runner smoke is allowed only for already-ready package/import/local API verifier rows and cannot launch, install, update, write output, or touch printers.",
        "- Executable path runner smoke is allowed only for installed launcher metadata rows and can read file metadata/hash only; it cannot launch apps, install, update, write output, or touch printers.",
        "- Python import repair preflight is allowed only for failed Python import verifier rows with a local source checkout. It can read source/dependency metadata only; it cannot install packages, create environments, start workers, write output, or touch printers.",
        "- CLI install/config preflight is allowed only for Slic3r/SuperSlicer rows with source/schema/profile proof. It can read metadata only; it cannot install apps, launch slicers, slice files, write output, update source, or touch printers.",
        "- Setup/update/install stays plan-only until backup, smoke gate, proof event, and rollback policy exist.",
        "- S1 remains camera/read-only and action-locked until the user changes printer policy.",
        "",
        "## Safe Service Start Runner Contracts",
        "",
        "These rows now have a registered setup/start preflight contract at `/api/modules/{module_id}/runtime/start-runner`. The contract checks the configured local/private URL key, local checkout, command family, and port state, writes proof, and still does not launch a process until a sandbox/process supervisor gate is enabled. Runtime-ready status still requires the health/version verifier to pass after startup.",
        "",
        "| App | Env key | Default URL | Command family | Start command preview | Current execution mode |",
        "| --- | --- | --- | --- | --- | --- |",
        *service_start_runner_rows(),
        "",
        "## Read-Only Runner Smoke Rows",
        "",
        "These rows now have `/api/modules/{module_id}/runtime/read-only-runner`. The route reruns only the registered package/import/local API proof and appends evidence. It is not full app execution and does not mutate source, files, services, or printers.",
        "",
        "| App | Section | Verifier | Proof gate | Route |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in sorted(
        read_only_runner_rows,
        key=lambda item: (str(item.get("section")), str(item.get("display"))),
    ):
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("display")),
                    cell(row.get("section")),
                    cell(row.get("verifier")),
                    cell(row.get("proof_gate_version")),
                    cell(row.get("read_only_runner_route")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Executable Path Runner Smoke Rows",
            "",
            "These rows now have `/api/modules/{module_id}/runtime/executable-path-runner`. The route reads only installed executable metadata/hash and appends evidence. It is not a CLI bridge, desktop automation bridge, or launch permission.",
            "",
            "| App | Section | Launcher | Proof gate | Route |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(
        executable_path_runner_rows,
        key=lambda item: (str(item.get("section")), str(item.get("display"))),
    ):
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("display")),
                    cell(row.get("section")),
                    cell(row.get("path")),
                    cell(row.get("proof_gate_version")),
                    cell(row.get("executable_path_runner_route")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Python Import Repair Preflight Rows",
            "",
            "These rows now have `/api/modules/{module_id}/runtime/python-import-repair-runner`. The route reads only the failed import proof plus source/dependency manifest metadata and appends evidence. It is not package installation, worker startup, or runtime readiness.",
            "",
            "| App | Section | Verifier | Proof gate | Route |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(
        python_import_repair_rows,
        key=lambda item: (str(item.get("section")), str(item.get("display"))),
    ):
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("display")),
                    cell(row.get("section")),
                    cell(row.get("verifier")),
                    cell(row.get("proof_gate_version")),
                    cell(row.get("python_import_repair_route")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## CLI Install/Config Preflight Rows",
            "",
            "These rows now have `/api/modules/{module_id}/runtime/cli-install-config-runner`. The route reads only Slic3r/SuperSlicer source checkout, adapter schema, profile/config, and candidate executable metadata. It is not install permission, launch permission, slicing permission, or runtime readiness.",
            "",
            "| App | Section | Verifier | Proof gate | Route |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(
        cli_install_config_rows,
        key=lambda item: (str(item.get("section")), str(item.get("display"))),
    ):
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("display")),
                    cell(row.get("section")),
                    cell(row.get("verifier")),
                    cell(row.get("proof_gate_version")),
                    cell(row.get("cli_install_config_route")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Verified Agent CLI Rows",
            "",
            "| App | Section | Verifier | Proof gate | Next safe work |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(
        verified, key=lambda item: (str(item.get("section")), str(item.get("display")))
    ):
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("display")),
                    cell(row.get("section")),
                    cell(row.get("verifier")),
                    cell(row.get("proof_gate_version")),
                    cell(row.get("next_action")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## P0 Runner Gaps",
            "",
            "These rows are installed/source-ready but not Hermes Agent runnable yet. They must remain disabled or plan-only until the acceptance gate passes.",
            "",
            f"Open P0 rows: {len(gaps)}",
            "",
        ]
    )

    for tier, rows in grouped(gaps, "agent_execution_tier").items():
        lines.extend(
            [
                f"### {tier.replace('_', ' ').title()} ({len(rows)})",
                "",
                "| App | Section | Launch kind | CLI surface | Required correction | Acceptance gate |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in rows:
            surface = surface_by_id.get(str(row.get("module_id")), {})
            lines.append(
                "| "
                + " | ".join(
                    [
                        cell(row.get("display")),
                        cell(row.get("section")),
                        cell(row.get("launch_kind")),
                        cell(surface.get("cli_surface_status", "not scanned")),
                        cell(required_correction(row, surface)),
                        cell(row.get("acceptance_gate") or acceptance_gate(row, surface)),
                    ]
                )
                + " |"
            )
        lines.append("")

    contract_counts = readiness.get("summary", {}).get("by_runner_contract_status", {})
    if isinstance(contract_counts, dict) and contract_counts:
        lines.extend(
            [
                "## Runner Contract Status",
                "",
                "/api/modules/runtime/runner-contracts is the canonical execution matrix for Hermes Agents. A row is executable only when its contract says `agent_executable=true`; all other rows stay Verify/Setup Plan only.",
                "",
                *[f"- {key}: {value}" for key, value in sorted(contract_counts.items())],
                "",
            ]
        )

    lines.extend(
        [
            "## P1 CLI/Service Signals Needing Verifiers",
            "",
            "These include some rows that are already source/reference/package ready. They still are not agent-executable unless they also appear in the verified Agent CLI list above.",
            "",
            "| App | Section | Signal type | Current proof tier | Next verifier |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(
        candidate_rows, key=lambda item: (str(item.get("section")), str(item.get("display")))
    ):
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("display")),
                    cell(row.get("section")),
                    cell(row.get("cli_surface_status")),
                    cell(row.get("agent_execution_tier")),
                    cell(row.get("next_action")),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Launcher Metadata Only",
            "",
            "These can prove local desktop app presence, but they are not Hermes Agent CLI runners yet.",
            "",
            "| App | Section | Launcher | Required correction |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in sorted(
        launcher_only, key=lambda item: (str(item.get("section")), str(item.get("display")))
    ):
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(row.get("display")),
                    cell(row.get("section")),
                    cell(row.get("path")),
                    cell(
                        row.get("executable_path_runner_route")
                        or row.get("next_action")
                    ),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Rollup",
            "",
            "### Runner Gap Tiers",
            "",
            *[f"- {key}: {value}" for key, value in sorted(gap_counts.items())],
            "",
            "### CLI Surface Candidate Tiers",
            "",
            *[f"- {key}: {value}" for key, value in sorted(candidate_counts.items())],
            "",
            "## Verification Commands",
            "",
            "Run these after any Source OS runtime, verifier, or UI wording change:",
            "",
            "```powershell",
            "python 03_implementation\\scripts\\audit_source_registry_truth.py",
            "python 03_implementation\\scripts\\audit_source_cli_agent_readiness.py",
            "python 03_implementation\\scripts\\audit_source_cli_surface.py",
            "python 03_implementation\\scripts\\audit_source_app_completion.py",
            "python 03_implementation\\scripts\\write_source_runtime_action_plan.py",
            "python 03_implementation\\scripts\\scan_active_ui_no_fake.py",
            'cd 03_implementation\\ui; npm run lint; npx.cmd playwright test --config=playwright.e2e.config.ts --grep "Source OS|Plugins|Roadmap|Settings Environment"',
            "```",
            "",
        ]
    )

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {"path": str(OUTPUT), "runner_gaps": len(gaps), "cli_candidates": len(candidate_rows)},
            indent=2,
        )
    )
    return 0


def read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def service_start_runner_rows() -> list[str]:
    rows: list[str] = []
    for module_id, runner in sorted(SERVICE_START_RUNNERS.items()):
        probe = (
            BUILTIN_RUNTIME_PROBES.get(module_id, {})
            if isinstance(BUILTIN_RUNTIME_PROBES, dict)
            else {}
        )
        args = probe.get("args") if isinstance(probe, dict) else []
        env_name = str(args[0]) if isinstance(args, list) and args else ""
        command = (
            " ".join(str(item) for item in runner.get("command") or []) or "wrapper inside ComfyUI"
        )
        rows.append(
            "| "
            + " | ".join(
                [
                    cell(probe.get("label") or module_id),
                    cell(env_name),
                    cell(probe.get("default_url")),
                    cell(runner.get("command_family")),
                    cell(command),
                    "preflight/proof only; no process launch until supervisor gate",
                ]
            )
            + " |"
        )
    return rows or ["| none | none | none | none | none | no registered service start contracts |"]


def grouped(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "unknown")].append(row)
    return {
        group_key: sorted(
            group_rows, key=lambda item: (str(item.get("section")), str(item.get("display")))
        )
        for group_key, group_rows in sorted(groups.items())
    }


def required_correction(row: dict[str, Any], surface: dict[str, Any]) -> str:
    tier = str(row.get("agent_execution_tier") or "")
    launch_kind = str(row.get("launch_kind") or "")
    if tier == "cli_preferred_gap":
        return (
            row.get("required_verifier_family")
            or "Locate or install the real CLI, then register a bounded version/help/dry-run verifier."
        )
    if tier == "python_worker_gap":
        return (
            row.get("required_verifier_family")
            or "Create an isolated Python env/import or module --help verifier before runner exposure."
        )
    if tier == "npm_package_gap":
        return (
            row.get("required_verifier_family")
            or "Run a package metadata/build verifier without secrets, then add a safe node runner."
        )
    if tier in {"service_gap", "web_app_gap"}:
        return (
            row.get("required_verifier_family")
            or "Add a non-mutating local health/version endpoint smoke before start/stop controls."
        )
    if tier == "gpu_worker_gap":
        return (
            row.get("required_verifier_family")
            or "Add a lightweight dependency/model-cache verifier before any GPU job launch."
        )
    if tier == "desktop_app_gap":
        return "Find a safe CLI/headless mode or add an explicit desktop bridge smoke."
    if launch_kind == "firmware_source":
        return "Use source/reference proof only until a safe compile/version verifier is defined."
    return cell(surface.get("next_action") or row.get("next_action"))


def acceptance_gate(row: dict[str, Any], surface: dict[str, Any]) -> str:
    module_id = str(row.get("module_id") or "module")
    tier = str(row.get("agent_execution_tier") or "")
    if tier in {"cli_preferred_gap", "desktop_app_gap", "npm_package_gap"}:
        return f"`/api/modules/{module_id}/runtime/verify` returns ready with executed=true and proof gate."
    if tier in {"python_worker_gap", "service_gap", "web_app_gap", "gpu_worker_gap"}:
        return "Safe verifier returns ready and Source OS shows Agent CLI/API runner or precise blocked reason."
    if str(row.get("launch_kind") or "") == "firmware_source":
        return (
            "Document no-runtime/reference-only or register safe version/build metadata verifier."
        )
    return cell(surface.get("next_action") or row.get("next_action"))


def cell(value: Any) -> str:
    text = str(value or "").replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|")


if __name__ == "__main__":
    raise SystemExit(main())
