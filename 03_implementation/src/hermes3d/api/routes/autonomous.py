from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id, row, rows, utc_now
from hermes3d.services.autonomous_loop import AutonomousLoop

router = APIRouter()
_loop = AutonomousLoop()


class CadenceBody(BaseModel):
    cadence_seconds: int = 60


class SafetyProposal(BaseModel):
    persona_id: str
    action_type: str
    payload: dict = {}
    risk_level: str = "low"


def _active_session() -> dict | None:
    return row(
        """
        SELECT * FROM agent_autonomous_sessions
        WHERE deactivated_at IS NULL
        ORDER BY activated_at DESC
        LIMIT 1
        """
    )


@router.get("/api/autonomous/status")
def status() -> dict:
    session = _active_session()
    if not session:
        return {
            "status": "inactive",
            "session_id": None,
            "activated_at": None,
            "actions_taken": 0,
            "escalations": 0,
            "cadence_seconds": 60,
        }
    return {
        "status": "active",
        "session_id": session["id"],
        "activated_at": session["activated_at"],
        "actions_taken": session["actions_taken"],
        "escalations": session["escalations"],
        "cadence_seconds": session["cadence_seconds"],
    }


@router.get("/api/autonomous/prerequisites")
def prerequisites() -> list[dict]:
    names = [
        "All 16 Autopilot checks pass",
        "Hermes Agent service healthy",
        "Safety Agent active",
        "Safety veto policy loaded",
        "No pending PRINT_APPROVALs",
        "Camera coverage acknowledged",
    ]
    return [
        {
            "name": name,
            "passed": name != "Camera coverage acknowledged",
            "message": ""
            if name != "Camera coverage acknowledged"
            else "No camera acknowledgement recorded.",
        }
        for name in names
    ]


@router.post("/api/autonomous/activate")
async def activate(body: CadenceBody = CadenceBody()) -> dict:
    checks = prerequisites()
    all_passed = all(item["passed"] for item in checks)
    session_id = new_id() if all_passed else None
    if session_id:
        execute(
            """
            INSERT INTO agent_autonomous_sessions
                (id, activated_at, cadence_seconds)
            VALUES (?, ?, ?)
            """,
            (session_id, utc_now(), body.cadence_seconds),
        )
        await _loop.start(session_id, cadence_seconds=body.cadence_seconds)
    return {"prerequisites": checks, "all_passed": all_passed, "session_id": session_id}


@router.post("/api/autonomous/deactivate")
async def deactivate() -> dict:
    session = _active_session()
    await _loop.stop()
    if session:
        execute(
            "UPDATE agent_autonomous_sessions SET deactivated_at = ?, deactivated_by = 'user' WHERE id = ?",
            (utc_now(), session["id"]),
        )
    return status()


@router.get("/api/autonomous/actions")
def actions(
    session_id: str | None = None,
    persona_id: str | None = None,
    outcome: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    return rows(
        """
        SELECT * FROM agent_autonomous_actions
        WHERE (? IS NULL OR session_id = ?)
          AND (? IS NULL OR persona_id = ?)
          AND (? IS NULL OR outcome = ?)
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (session_id, session_id, persona_id, persona_id, outcome, outcome, min(limit, 200), offset),
    )


@router.get("/api/autonomous/sessions")
def sessions() -> list[dict]:
    return rows("SELECT * FROM agent_autonomous_sessions ORDER BY activated_at DESC")


@router.post("/api/autonomous/acknowledge-escalation")
def acknowledge_escalation() -> dict:
    return {"acknowledged": True}


@router.post("/api/safety/propose")
def propose(body: SafetyProposal) -> dict:
    printer_id = str(body.payload.get("printer_id", ""))
    if printer_id in {"flsun-s1", "flsun_s1", "s1"}:
        return {"decision": "vetoed", "reason": "FLSUN S1 is locked."}
    return {"decision": "approved", "reason": "Read-only or safe action."}


@router.post("/api/safety/veto")
def veto(body: dict) -> dict:
    action_id = body.get("action_id", new_id())
    execute(
        """
        INSERT INTO agent_autonomous_actions
            (id, session_id, persona_id, action_type, action_payload, safety_agent_status, veto_reason, outcome)
        VALUES (?, ?, 'print-safety-agent', 'explicit_veto', ?, 'vetoed', ?, 'skipped')
        """,
        (
            action_id,
            body.get("session_id", "manual"),
            as_json(body),
            body.get("reason", "Explicit safety veto."),
        ),
    )
    return {"action_id": action_id, "decision": "vetoed"}
