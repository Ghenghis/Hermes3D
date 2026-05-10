"""W15 A20 — /api/dashboard/layouts.

Per-user dashboard layout persistence. Stores layout JSON in the
existing ``agent_config`` table (key/value text) under a namespaced key:

    dashboard.layouts.<user_id>

This avoids a schema migration. If a future migration introduces a
dedicated ``dashboard_layouts`` table, the read/write helpers below are
the only call sites that need to move.

Honest contract:
- ``GET`` returns an enveloped list. ``items`` may legitimately be ``[]``
  when no user has saved a layout — that is NOT a failure.
- ``POST`` validates the body and persists, returning the stored row.
- If the database is unreachable (e.g. running without ``init_db`` or in
  a sandboxed test that swapped the path), FastAPI bubbles the sqlite
  error up; we do not silently swallow it.

References:
- FastAPI bigger applications / routers:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- OpenAPI: collection ``GET`` + create ``POST`` on same path; idempotent
  upsert keyed by ``user_id`` keeps the surface flat.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hermes3d.api.routes._common import execute, rows

router = APIRouter()

_KEY_PREFIX = "dashboard.layouts."


class DashboardLayout(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    layout: dict[str, Any]
    updated_at: str | None = None


class DashboardLayoutCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    layout: dict[str, Any]


class DashboardLayoutsResponse(BaseModel):
    accepted: bool
    status: Literal["ready", "blocked"]
    reason: str | None = None
    items: list[DashboardLayout] = Field(default_factory=list)
    total: int = 0


def _row_to_layout(row: dict[str, Any]) -> DashboardLayout:
    return DashboardLayout(
        user_id=str(row["key"]).removeprefix(_KEY_PREFIX),
        layout=json.loads(row["value"] or "{}"),
        updated_at=row.get("updated_at"),
    )


@router.get("/api/dashboard/layouts", response_model=DashboardLayoutsResponse)
def list_dashboard_layouts() -> DashboardLayoutsResponse:
    """Return all saved per-user dashboard layouts."""
    records = rows(
        "SELECT key, value, updated_at FROM agent_config WHERE key LIKE ? ORDER BY key",
        (f"{_KEY_PREFIX}%",),
    )
    items = [_row_to_layout(record) for record in records]
    return DashboardLayoutsResponse(
        accepted=True,
        status="ready",
        reason=None,
        items=items,
        total=len(items),
    )


@router.post(
    "/api/dashboard/layouts",
    response_model=DashboardLayout,
    status_code=201,
)
def create_dashboard_layout(body: DashboardLayoutCreate) -> DashboardLayout:
    """Create or replace the dashboard layout for ``user_id``."""
    if not body.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id must not be empty")
    key = f"{_KEY_PREFIX}{body.user_id}"
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) "
        "VALUES (?, ?, datetime('now'))",
        (key, json.dumps(body.layout, separators=(",", ":"))),
    )
    stored = rows(
        "SELECT key, value, updated_at FROM agent_config WHERE key = ?",
        (key,),
    )
    if not stored:
        raise HTTPException(
            status_code=500,
            detail="dashboard layout failed to persist",
        )
    return _row_to_layout(stored[0])
