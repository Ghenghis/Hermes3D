from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import execute, row, rows

router = APIRouter()


class ApprovalNotes(BaseModel):
    notes: str = ""
    reason: str = ""


@router.get("/api/approvals")
def list_approvals(status: str = "pending") -> list[dict]:
    statuses = [s.strip() for s in status.split(",") if s.strip()]
    return rows(
        "SELECT * FROM approvals WHERE status IN (SELECT value FROM json_each(?)) ORDER BY requested_at DESC",
        (__import__("json").dumps(statuses),),
    )


def _decide(
    approval_id: str, status: str, decided_by: str, notes: str | None, reason: str | None
) -> dict:
    existing = row("SELECT * FROM approvals WHERE id = ?", (approval_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="approval not found")
    if existing["status"] != "pending":
        raise HTTPException(status_code=409, detail="approval already decided")
    execute(
        """
        UPDATE approvals
        SET status = ?, decided_by = ?, decided_at = datetime('now'), notes = ?, reason = ?
        WHERE id = ?
        """,
        (status, decided_by, notes, reason, approval_id),
    )
    return row("SELECT * FROM approvals WHERE id = ?", (approval_id,)) or {}


@router.post("/api/approvals/{approval_id}/approve")
def approve(approval_id: str, body: ApprovalNotes) -> dict:
    return _decide(approval_id, "approved", "operator", body.notes, None)


@router.post("/api/approvals/{approval_id}/reject")
def reject(approval_id: str, body: ApprovalNotes) -> dict:
    return _decide(approval_id, "rejected", "operator", None, body.reason)


@router.post("/api/approvals/{approval_id}/defer")
def defer(approval_id: str, body: ApprovalNotes) -> dict:
    """W18-A13 — defer a pending approval (move to ``deferred`` status).

    Deferred is a non-terminal verdict: the approval is taken out of the
    pending queue without being rejected so an operator/agent can revisit
    later. The audit (W18-A3) flagged this as ``FAIL_BACKEND_MISSING``
    — the FE ``adapters.live.ts:deferApprovalLive`` was POSTing to a
    404. This handler mirrors :func:`reject` but stores ``deferred`` as
    the status and the operator-supplied note as the reason.

    Pending → deferred is the only legal transition; once deferred the
    approval is re-enqueued by callers through the standard POST to a
    fresh approval, not by mutating this row.
    """
    return _decide(approval_id, "deferred", "operator", None, body.reason)
