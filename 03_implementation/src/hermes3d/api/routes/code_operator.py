"""Hermes Agent code-operation APIs for source-backed programming work."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hermes3d.services import code_history

router = APIRouter(prefix="/api/code-operator", tags=["code-operator"])


class SnapshotRequest(BaseModel):
    relative_path: str
    agent_id: str = "hermes-agent"
    action_id: str | None = None
    reason: str | None = None


class RestoreRequest(BaseModel):
    relative_path: str
    snapshot_id: str
    agent_id: str = "hermes-agent"
    reason: str | None = None


class SnapshotQuery(BaseModel):
    relative_path: str
    limit: int = Field(default=100, ge=1, le=500)


@router.get("/programming-readiness")
def programming_readiness() -> dict[str, Any]:
    return code_history.programming_readiness()


@router.get("/history/files")
def touched_files(limit: int = 200) -> dict[str, Any]:
    return code_history.list_touched_files(limit=limit)


@router.post("/history/snapshots")
def create_snapshot(body: SnapshotRequest) -> dict[str, Any]:
    try:
        return code_history.snapshot_file(
            body.relative_path,
            agent_id=body.agent_id,
            action_id=body.action_id,
            reason=body.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/history/list")
def snapshots_for_file(body: SnapshotQuery) -> dict[str, Any]:
    try:
        return code_history.list_snapshots(body.relative_path, limit=body.limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.get("/history/diff/{snapshot_id}")
def snapshot_diff(snapshot_id: str, relative_path: str) -> dict[str, Any]:
    try:
        return code_history.snapshot_diff(relative_path, snapshot_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc


@router.post("/history/restore")
def restore_snapshot(body: RestoreRequest) -> dict[str, Any]:
    try:
        return code_history.restore_snapshot(
            body.relative_path,
            body.snapshot_id,
            agent_id=body.agent_id,
            reason=body.reason,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc

