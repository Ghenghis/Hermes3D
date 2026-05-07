"""Source OS readiness aggregation route.

GET /api/sources/readiness

Reads proof JSON files from the proof/ directory and returns aggregated
readiness information for all source tool categories, used by the SourceOS
tab CLI readiness panel.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter()

IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[4]
PROOF_DIR = IMPLEMENTATION_ROOT / "proof"

# Canonical category → section mapping that aligns with the proof audit
CATEGORY_SECTION_MAP: dict[str, str] = {
    "slicers": "slicers",
    "modelers": "modelers",
    "print_farm": "print_farm",
    "firmware": "firmware",
    "gen3d": "three_d_generation",
}

# Display labels for each category
CATEGORY_LABELS: dict[str, str] = {
    "slicers": "Slicers",
    "modelers": "Modelers",
    "print_farm": "Print Farm",
    "firmware": "Firmware Tools",
    "gen3d": "3D Generation (Gen3D)",
}

# Key tools to highlight per category (module_id values)
CATEGORY_KEY_TOOLS: dict[str, list[str]] = {
    "slicers": ["prusaslicer", "orcaslicer", "curaengine", "bambustudio"],
    "modelers": ["blender", "openscad", "freecad"],
    "print_farm": ["moonraker", "octoprint", "mainsail", "fluidd"],
    "firmware": ["firmware_klipper", "marlin", "prusa_firmware"],
    "gen3d": ["comfyui", "trellis"],
}

# Proof JSON file paths
CLI_READINESS_PATH = PROOF_DIR / "SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json"
CLI_SURFACE_PATH = PROOF_DIR / "SOURCE_APP_CLI_SURFACE_AUDIT.json"
LOCAL_TOOLING_PATH = PROOF_DIR / "LOCAL_TOOLING_AUDIT.json"
COMPLETION_PATH = PROOF_DIR / "SOURCE_APP_60_COMPLETION_AUDIT.json"


def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON file, returning an empty dict on any error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[return-value]
    except Exception:
        return {}


def _tool_status(runtime_status: str, executed: bool, return_code: int | None) -> str:
    """Map runtime fields to a simple human-readable status string."""
    if runtime_status == "ready" and executed and return_code == 0:
        return "verified"
    if runtime_status == "ready":
        return "detected"
    if runtime_status == "source_ready":
        return "source_ready"
    if runtime_status == "not_installed":
        return "not_installed"
    return "unavailable"


@router.get("/api/sources/readiness")
def get_sources_readiness() -> dict[str, Any]:
    """Return aggregated CLI readiness across all source tool categories.

    Reads proof JSON files only — no subprocess calls, no writes.
    """
    cli_data = _read_json(CLI_READINESS_PATH)
    local_tooling = _read_json(LOCAL_TOOLING_PATH)
    cli_surface = _read_json(CLI_SURFACE_PATH)

    proof_rows: list[dict[str, Any]] = cli_data.get("rows") or []
    local_tools: dict[str, Any] = local_tooling.get("tools") or {}
    surface_records: list[dict[str, Any]] = cli_surface.get("records") or []

    # Index surface records by module_id for quick lookup
    surface_by_module: dict[str, dict[str, Any]] = {
        r["module_id"]: r for r in surface_records if isinstance(r, dict) and r.get("module_id")
    }

    # Index proof rows by module_id
    proof_by_module: dict[str, dict[str, Any]] = {
        r["module_id"]: r for r in proof_rows if isinstance(r, dict) and r.get("module_id")
    }

    categories: dict[str, Any] = {}
    for category_id, section_id in CATEGORY_SECTION_MAP.items():
        section_rows = [r for r in proof_rows if r.get("section") == section_id]

        key_tools_detail: list[dict[str, Any]] = []
        for module_id in CATEGORY_KEY_TOOLS.get(category_id, []):
            row = proof_by_module.get(module_id)
            surface = surface_by_module.get(module_id)

            if row:
                status = _tool_status(
                    row.get("runtime_status", ""),
                    bool(row.get("executed")),
                    row.get("return_code"),
                )
                key_tools_detail.append({
                    "module_id": module_id,
                    "display": row.get("display", module_id),
                    "status": status,
                    "runtime_status": row.get("runtime_status", ""),
                    "agent_execution_tier": row.get("agent_execution_tier", ""),
                    "path": row.get("path"),
                    "verifier": row.get("verifier"),
                    "return_code": row.get("return_code"),
                    "executed": bool(row.get("executed")),
                    "cli_surface_status": surface.get("cli_surface_status") if surface else None,
                    "next_action": row.get("next_action"),
                })
            else:
                # Tool not in proof yet — check local tooling audit
                # local tools use slightly different naming conventions
                local_key = next(
                    (k for k in local_tools if module_id in k or k.startswith(module_id[:6])),
                    None,
                )
                local_entry = local_tools.get(local_key) if local_key else None
                if local_entry:
                    detected = bool(local_entry.get("detected"))
                    executed = bool(local_entry.get("executed"))
                    rc = local_entry.get("return_code")
                    status = _tool_status(
                        "ready" if detected else "not_installed",
                        executed,
                        rc,
                    )
                    key_tools_detail.append({
                        "module_id": module_id,
                        "display": module_id.replace("_", " ").title(),
                        "status": status,
                        "runtime_status": "ready" if detected else "not_installed",
                        "agent_execution_tier": "launcher_metadata_only" if detected and not executed else "",
                        "path": local_entry.get("path"),
                        "verifier": "local_tooling_audit",
                        "return_code": rc,
                        "executed": executed,
                        "cli_surface_status": None,
                        "next_action": None,
                    })
                else:
                    key_tools_detail.append({
                        "module_id": module_id,
                        "display": module_id.replace("_", " ").title(),
                        "status": "unavailable",
                        "runtime_status": "not_installed",
                        "agent_execution_tier": "",
                        "path": None,
                        "verifier": None,
                        "return_code": None,
                        "executed": False,
                        "cli_surface_status": None,
                        "next_action": "Tool not found in proof files; run tooling audit.",
                    })

        # Count readiness states across all rows in this section
        status_counts: dict[str, int] = {
            "verified": 0,
            "detected": 0,
            "source_ready": 0,
            "not_installed": 0,
            "unavailable": 0,
        }
        for r in section_rows:
            s = _tool_status(
                r.get("runtime_status", ""),
                bool(r.get("executed")),
                r.get("return_code"),
            )
            status_counts[s] = status_counts.get(s, 0) + 1

        categories[category_id] = {
            "id": category_id,
            "label": CATEGORY_LABELS[category_id],
            "section": section_id,
            "total": len(section_rows),
            "status_counts": status_counts,
            "key_tools": key_tools_detail,
        }

    # Global summary from the proof audit
    proof_summary: dict[str, Any] = cli_data.get("summary") or {}
    surface_summary: dict[str, Any] = cli_surface.get("summary") or {}

    generated_at = cli_data.get("generated_at_utc") or local_tooling.get("generated_at_utc") or ""

    return {
        "generated_at_utc": generated_at,
        "proof_files": {
            "cli_readiness": str(CLI_READINESS_PATH),
            "cli_surface": str(CLI_SURFACE_PATH),
            "local_tooling": str(LOCAL_TOOLING_PATH),
        },
        "summary": {
            "verified_agent_cli": proof_summary.get("verified_agent_cli", 0),
            "runner_gaps": proof_summary.get("runner_gaps", 0),
            "agent_enabled_cli": surface_summary.get("agent_enabled_cli", 0),
            "candidate_needs_verifier": surface_summary.get("candidate_needs_verifier", 0),
        },
        "categories": categories,
        "artifacts_url": "/api/artifacts",
    }
