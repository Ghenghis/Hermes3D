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


def _decide(approval_id: str, status: str, decided_by: str, notes: str | None, reason: str | None) -> dict:
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
