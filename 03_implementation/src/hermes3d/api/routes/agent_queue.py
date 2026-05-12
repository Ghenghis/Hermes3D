"""W21-A4 MVP-2 — FastAPI surface for the orchestrator queue bridge.

Exposes:
  GET  /api/agents/queue/status              — counts + per-state task list
  POST /api/agents/queue/claim/{task_id}     — operator-triggered claim
  POST /api/agents/queue/complete/{task_id}  — operator-triggered completion
  POST /api/agents/queue/block/{task_id}     — operator-triggered block
  POST /api/agents/queue/release/{task_id}   — operator-triggered release

The auto-poller in :mod:`hermes3d.services.queue_poller` calls these same
underlying primitives, but the HTTP endpoints exist so the UI can drive
the bridge manually and so operators can override the poller.

All endpoints return JSON envelopes that match the W15-A20 honest-blocked
contract (``accepted``, ``status``, ``reason``) so the React layer can
branch on readiness without parsing per-endpoint shapes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from hermes3d.services import queue_bridge

router = APIRouter()


def _workspace_root() -> Path:
    """Workspace root used by the bridge. Mirrors the convention in
    :mod:`hermes3d.api.routes.mcp_locks` so both the locks and the
    queue read from the same ``.hermes3d_orchestrator`` directory."""
    # The Hermes3D workspace is the parent of this src tree; resolve via
    # the env var the orchestrator MCP sets if present, else infer from
    # the import path.
    import os

    env_root = os.environ.get("HERMES3D_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root)
    # Infer from this file: src/hermes3d/api/routes/agent_queue.py
    # → workspace_root is six parents up.
    return Path(__file__).resolve().parents[5]


class ClaimRequest(BaseModel):
    """Operator-triggered claim. ``persona`` is the Hermes Agent id that
    will own the task. The persona MUST match the task's
    ``target_owner_pattern`` — the bridge does not relax that rule."""

    persona: str = Field(min_length=1, max_length=64)


class BlockRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=512)
    persona: str | None = Field(default=None, max_length=64)


@router.get("/api/agents/queue/status")
def queue_status() -> dict[str, Any]:
    """Read-only snapshot of the orchestrator task queue.

    Lag-protected by design: this endpoint is idempotent and cheap (it
    reads directory entries + parses JSON in O(n)), so the UI can poll
    it without coordination. Returned counts come from the filesystem
    state, never from an in-memory cache.
    """
    root = _workspace_root()
    counts = queue_bridge.status_counts(root)
    pending = [t.to_dict() for t in queue_bridge.list_tasks(root, "pending")]
    claimed = [t.to_dict() for t in queue_bridge.list_tasks(root, "claimed")]
    done = [t.to_dict() for t in queue_bridge.list_tasks(root, "done")]
    blocked = [t.to_dict() for t in queue_bridge.list_tasks(root, "blocked")]
    return {
        "accepted": True,
        "status": "ready",
        "reason": None,
        "counts": counts,
        "pending": pending,
        "claimed": claimed,
        "done": done,
        "blocked": blocked,
    }


def _persona_matches_or_400(target_owner_pattern: str, persona: str) -> None:
    match = queue_bridge.match_persona(target_owner_pattern, [persona])
    if match is None:
        raise HTTPException(
            status_code=400,
            detail={
                "accepted": False,
                "status": "blocked",
                "reason": (
                    f"persona {persona!r} does not match task's "
                    f"target_owner_pattern {target_owner_pattern!r}"
                ),
            },
        )


@router.post("/api/agents/queue/claim/{task_id}")
def claim(task_id: str, body: ClaimRequest = Body(...)) -> dict[str, Any]:
    root = _workspace_root()
    pending_path = queue_bridge.pending_dir(root) / f"{task_id}.json"
    if not pending_path.is_file():
        raise HTTPException(
            status_code=404,
            detail={
                "accepted": False,
                "status": "blocked",
                "reason": f"task {task_id!r} is not in pending state",
            },
        )
    # Read the task once to validate persona match BEFORE the claim move.
    pending = queue_bridge.list_tasks(root, "pending")
    target = next((t for t in pending if t.task_id == task_id), None)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail={
                "accepted": False,
                "status": "blocked",
                "reason": f"task {task_id!r} not visible to bridge",
            },
        )
    _persona_matches_or_400(target.target_owner_pattern, body.persona)
    snap = queue_bridge.claim_task(root, task_id, body.persona)
    if snap is None:
        raise HTTPException(
            status_code=409,
            detail={
                "accepted": False,
                "status": "blocked",
                "reason": "task was moved out of pending by a concurrent claimer",
            },
        )
    return {"accepted": True, "status": "claimed", "task": snap.to_dict()}


@router.post("/api/agents/queue/release/{task_id}")
def release(task_id: str) -> dict[str, Any]:
    root = _workspace_root()
    ok = queue_bridge.release_task(root, task_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={
                "accepted": False,
                "status": "blocked",
                "reason": f"task {task_id!r} is not currently claimed",
            },
        )
    return {"accepted": True, "status": "released"}


@router.post("/api/agents/queue/complete/{task_id}")
def complete(task_id: str, body: ClaimRequest = Body(...)) -> dict[str, Any]:
    root = _workspace_root()
    ok = queue_bridge.complete_task(root, task_id, persona=body.persona)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={
                "accepted": False,
                "status": "blocked",
                "reason": (f"task {task_id!r} not in claimed state for persona {body.persona!r}"),
            },
        )
    return {"accepted": True, "status": "done"}


@router.post("/api/agents/queue/block/{task_id}")
def block(task_id: str, body: BlockRequest = Body(...)) -> dict[str, Any]:
    root = _workspace_root()
    ok = queue_bridge.block_task(root, task_id, body.reason, persona=body.persona)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={
                "accepted": False,
                "status": "blocked",
                "reason": f"task {task_id!r} cannot be blocked from current state",
            },
        )
    return {"accepted": True, "status": "blocked", "reason": body.reason}


@router.post("/api/agents/queue/execute-now")
def execute_now() -> dict[str, Any]:
    """W21-MVP-3: operator-triggered persona executor pass.

    Runs the persona executor synchronously against the current
    ``claimed/`` queue, bounded by ``HERMES3D_PERSONA_EXEC_MAX_PER_TICK``
    (default 2 tasks). Each task is classified and either:

    * ``done`` — handoff_path markdown generated via MiniMax and the
      task is moved to ``done/`` with a proof_events row.
    * ``blocked`` — task class has no automated executor; moved to
      ``blocked/`` with reason ``no_automated_executor_for_task_class``
      so the UI surfaces it for human follow-up.

    The route is operator-driven so the auto-poller's behavior can be
    overridden (e.g. when the poller is disabled in tests but the
    operator wants to flush the queue).

    Response shape::

        {
          "accepted": true,
          "status":   "ready",
          "results":  [ {task_id, outcome, reason, handoff, class}, ... ],
          "counts":   {"done": N, "blocked": M}
        }
    """
    from hermes3d.services import persona_executor

    root = _workspace_root()
    results = persona_executor.execute_claimed_tasks(workspace_root=root)
    done_count = sum(1 for r in results if r.get("outcome") == "done")
    blocked_count = sum(1 for r in results if r.get("outcome") == "blocked")
    return {
        "accepted": True,
        "status": "ready",
        "results": results,
        "counts": {"done": done_count, "blocked": blocked_count},
    }
