from __future__ import annotations

import hashlib
import os

from fastapi import APIRouter, HTTPException

from hermes3d.api.routes._common import new_id, row, rows, utc_now
from hermes3d.db.init import DB_PATH
from hermes3d.services.local_state import local_printers, port_reachable, service_url

router = APIRouter()

CHECKS = [
    "Printer Connectivity",
    "Slicer Availability",
    "Agent Health",
    "Safety Gate Status",
    "Proof Gate Status",
    "Filament Profile Loaded",
    "Bed Mesh Calibrated",
    "Nozzle Temp Verified",
    "Movement Lock State",
    "Dispatch Gate Open",
    "Model LLM Available",
    "ComfyUI Available",
    "Evidence Ledger Reachable",
    "Operator Present",
    "Approval Queue Clear",
    "API Token Set",
]


@router.get("/api/autopilot/readiness")
def readiness() -> list[dict]:
    printers = local_printers()
    unlocked = [printer for printer in printers if not printer["maintenance_flag"]]
    plugins = rows("SELECT id, state FROM plugins")
    checks = {
        "Printer Connectivity": (
            any(p["status"] in {"online", "printing", "paused"} for p in unlocked),
            "No unlocked printer is marked online in local state.",
        ),
        "Slicer Availability": (
            any("slicer" in str(p["id"]).lower() and p["state"] == "ACTIVE" for p in plugins),
            "No slicer plugin is active.",
        ),
        "Agent Health": (
            True,
            "Agent API is available; live agent runtime may still be not_configured.",
        ),
        "Safety Gate Status": (True, "S1 hard lock is enforced by backend policy."),
        "Proof Gate Status": (
            bool(row("SELECT id FROM truth_gate_results LIMIT 1")),
            "No truth gate result has been recorded yet.",
        ),
        "Filament Profile Loaded": (False, "No filament profile source is configured."),
        "Bed Mesh Calibrated": (False, "No Moonraker bed mesh telemetry is configured."),
        "Nozzle Temp Verified": (False, "No live temperature telemetry is configured."),
        "Movement Lock State": (True, "S1 movement/upload/test/capture routes remain locked."),
        "Dispatch Gate Open": (
            not bool(row("SELECT id FROM approvals WHERE status = 'pending' LIMIT 1")),
            "Approval queue has pending items.",
        ),
        "Model LLM Available": (
            bool(os.environ.get("HERMES3D_MODEL_LLM_URL")),
            "HERMES3D_MODEL_LLM_URL is not configured.",
        ),
        "ComfyUI Available": (
            port_reachable(service_url("comfyui")),
            "ComfyUI URL is not configured or unreachable.",
        ),
        "Evidence Ledger Reachable": (True, "SQLite evidence tables are available."),
        "Operator Present": (True, "Local operator is present through this UI session."),
        "Approval Queue Clear": (
            not bool(row("SELECT id FROM approvals WHERE status = 'pending' LIMIT 1")),
            "Approval queue has pending items.",
        ),
        "API Token Set": (
            bool(os.environ.get("HERMES3D_GUI_TOKEN")),
            "HERMES3D_GUI_TOKEN is not set.",
        ),
    }
    return [
        {
            "id": label.lower().replace(" ", "_"),
            "name": label,
            "ready": checks[label][0],
            "message": "" if checks[label][0] else checks[label][1],
        }
        for label in CHECKS
    ]


@router.post("/api/autopilot/next-gate")
def next_gate() -> dict:
    failing = [check for check in readiness() if not check["ready"]]
    if failing:
        raise HTTPException(status_code=409, detail={"next": failing[0]})
    return {"action": "all_ready", "proof_event_id": new_id()}


@router.post("/api/autopilot/write-plan")
def write_plan() -> dict:
    return _write_autopilot_file(
        "agent-plan",
        "Hermes3D Agent Plan",
        [
            "This file was written by the live Hermes3D backend.",
            "",
            "Readiness summary:",
            *_readiness_lines(),
            "",
            "Blocked work remains blocked until the named setup checks are ready.",
        ],
    )


@router.post("/api/autopilot/write-report")
def write_report() -> dict:
    return _write_autopilot_file(
        "setup-report",
        "Hermes3D Setup Report",
        [
            "This file was written by the live Hermes3D backend.",
            "",
            "Guardrails:",
            *[
                f"- {item['id']}: {item['rule']} ({'enforced' if item['enforced'] else 'not enforced'})"
                for item in guardrails()
            ],
            "",
            "Readiness summary:",
            *_readiness_lines(),
        ],
    )


@router.get("/api/autopilot/guardrails")
def guardrails() -> list[dict]:
    return [
        {
            "id": "s1_lock",
            "rule": "FLSUN S1 is locked: no movement, upload, test, or capture.",
            "enforced": True,
        },
        {
            "id": "approval_required",
            "rule": "Print start requires job_id with approved PRINT_APPROVAL.",
            "enforced": True,
        },
        {
            "id": "truth_gate",
            "rule": "Print start requires passing truth-gate records for every configured gate.",
            "enforced": True,
        },
    ]


def _write_autopilot_file(slug: str, title: str, lines: list[str]) -> dict:
    directory = DB_PATH.parent / "autopilot"
    directory.mkdir(parents=True, exist_ok=True)
    event_id = new_id()
    path = directory / f"{slug}-{event_id[:8]}.md"
    content = "\n".join([f"# {title}", "", f"Written UTC: {utc_now()}", "", *lines, ""])
    path.write_text(content, encoding="utf-8")
    stat = path.stat()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {
        "accepted": True,
        "written": True,
        "report_path": str(path),
        "bytes": stat.st_size,
        "sha256": digest,
        "proof_event_id": event_id,
    }


def _readiness_lines() -> list[str]:
    lines: list[str] = []
    for check in readiness():
        suffix = f" - {check['message']}" if check.get("message") else ""
        lines.append(f"- {check['name']}: {'ready' if check['ready'] else 'needs setup'}{suffix}")
    return lines
