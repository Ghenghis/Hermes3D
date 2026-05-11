"""W17 — /api/mcp/locks (honest-blocked).

Thin read-only proxy over the Hermes MCP orchestrator's on-disk lock
state. The orchestrator (``hermes3d-locks`` MCP server, repo
``Ghenghis/HermesProof``) writes one ``metadata.json`` per active lock
under ``<workspace>/.hermes3d_orchestrator/locks/<lock_id>.lockdir/``.

This endpoint is the HTTP face of that state for the Hermes3D GUI
(Settings → MCP subtab, Service Health page). It MUST be honest:

- When the orchestrator state directory is absent (no orchestrator
  configured for this workspace, or the MCP server has never run here)
  we return ``accepted=false`` with the stable reason token
  ``mcp_server_unreachable`` and an empty list.
- When the directory exists we enumerate the real ``.lockdir`` entries
  and return the real owners/files/TTLs. Stale or expired locks are
  included (the orchestrator itself is the single source of truth for
  cleanup; consumers like Service Health want to see them).
- Any per-entry I/O / JSON parse failure is surfaced as a skipped item
  rather than a 5xx — the route is one of the diagnostics the operator
  uses when *something else* is broken, so it must never crash.

Contract is a stable enveloped collection per the W15 A20 pattern used
by ``/api/skills`` and ``/api/connectors``.

References:
- FastAPI bigger-applications router pattern:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- HermesProof orchestrator lock schema:
  ``03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07
    /agent-infra/hermes3d-mcp-lock-orchestrator.md`` (``src/core/
  lock-manager.mjs`` writes ``metadata.json`` per ``<lock_id>.lockdir``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


# 03_implementation/src/hermes3d/api/routes/mcp_locks.py
#   parents[0] routes
#   parents[1] api
#   parents[2] hermes3d
#   parents[3] src
#   parents[4] 03_implementation
#   parents[5] project root (Hermes3D workspace)
_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_ORCHESTRATOR_STATE_DIRNAME = ".hermes3d_orchestrator"
_LOCKS_SUBDIR = "locks"
_METADATA_FILENAME = "metadata.json"


class LockItem(BaseModel):
    """One active lock as written by the orchestrator's LockManager."""

    lock_id: str
    owner: str
    files: list[str] = Field(default_factory=list)
    role: str | None = None
    task_id: str | None = None
    reason: str | None = None
    acquired_utc: str | None = None
    heartbeat_utc: str | None = None
    expires_utc: str | None = None
    ttl_remaining_seconds: int | None = None
    is_stale: bool = False


class McpLocksResponse(BaseModel):
    accepted: bool
    status: Literal["ready", "unknown", "blocked"]
    reason: str | None = None
    items: list[LockItem] = Field(default_factory=list)
    total: int = 0


def _orchestrator_locks_dir() -> Path:
    """Resolve the orchestrator's locks directory for this workspace."""
    return _PROJECT_ROOT / _ORCHESTRATOR_STATE_DIRNAME / _LOCKS_SUBDIR


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        # The orchestrator emits ISO-8601 with a trailing 'Z'.
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _read_lock_metadata(lockdir: Path) -> LockItem | None:
    """Read one ``<lock_id>.lockdir/metadata.json`` into a :class:`LockItem`.

    Returns ``None`` for any I/O / shape error so the caller can skip
    the entry without failing the whole listing.
    """
    metadata_path = lockdir / _METADATA_FILENAME
    try:
        raw = metadata_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    # The lock-manager.mjs schema records one file per lockdir.
    # Normalize to a list so future multi-file lock layouts don't
    # break this consumer.
    file_value = data.get("file")
    files_value = data.get("files")
    if isinstance(files_value, list):
        files = [str(f) for f in files_value if isinstance(f, str)]
    elif isinstance(file_value, str) and file_value:
        files = [file_value]
    else:
        files = []

    expires_dt = _parse_utc(data.get("expires_utc"))
    now = datetime.now(timezone.utc)
    if expires_dt is not None:
        delta = (expires_dt - now).total_seconds()
        ttl_remaining_seconds = max(0, int(delta))
        is_stale = delta <= 0
    else:
        ttl_remaining_seconds = None
        is_stale = False

    lock_id_value = data.get("lock_id")
    owner_value = data.get("owner")
    if not isinstance(lock_id_value, str) or not isinstance(owner_value, str):
        return None

    return LockItem(
        lock_id=lock_id_value,
        owner=owner_value,
        files=files,
        role=data.get("role") if isinstance(data.get("role"), str) else None,
        task_id=data.get("task_id") if isinstance(data.get("task_id"), str) else None,
        reason=data.get("reason") if isinstance(data.get("reason"), str) else None,
        acquired_utc=data.get("acquired_utc")
        if isinstance(data.get("acquired_utc"), str)
        else None,
        heartbeat_utc=data.get("heartbeat_utc")
        if isinstance(data.get("heartbeat_utc"), str)
        else None,
        expires_utc=data.get("expires_utc") if isinstance(data.get("expires_utc"), str) else None,
        ttl_remaining_seconds=ttl_remaining_seconds,
        is_stale=is_stale,
    )


@router.get("/api/mcp/locks", response_model=McpLocksResponse)
def list_mcp_locks() -> McpLocksResponse:
    """Return active Hermes MCP locks for the current workspace.

    Honest-blocked when the orchestrator state directory is absent —
    that means the MCP server has never been run against this workspace
    (or the workspace is misconfigured). The UI must render the empty
    state rather than fake locks.
    """
    locks_dir = _orchestrator_locks_dir()
    if not locks_dir.is_dir():
        return McpLocksResponse(
            accepted=False,
            status="unknown",
            reason="mcp_server_unreachable",
            items=[],
            total=0,
        )

    items: list[LockItem] = []
    try:
        entries = sorted(locks_dir.iterdir())
    except OSError:
        # Directory exists but we cannot read it — honest blocked, never 5xx.
        return McpLocksResponse(
            accepted=False,
            status="blocked",
            reason="mcp_locks_dir_unreadable",
            items=[],
            total=0,
        )

    for entry in entries:
        if not entry.is_dir() or not entry.name.endswith(".lockdir"):
            continue
        item = _read_lock_metadata(entry)
        if item is not None:
            items.append(item)

    return McpLocksResponse(
        accepted=True,
        status="ready",
        reason=None,
        items=items,
        total=len(items),
    )
