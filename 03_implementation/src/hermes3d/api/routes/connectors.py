"""W15 A20 — /api/connectors.

Honest MCP/external connector surface. Mirrors the /api/skills contract:
when no connector registry is wired, return ``accepted=false`` with the
stable ``reason="connector_registry_not_yet_implemented"`` token. The UI
must NOT render fabricated connectors.

References:
- FastAPI bigger applications / routers:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- OpenAPI collection convention: enveloped GET response keeps room for
  future filtering and per-connector health flags without breaking
  consumers.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class Connector(BaseModel):
    id: str
    display_name: str
    kind: Literal["mcp", "http", "websocket", "local_process"]
    description: str
    configured: bool
    reachable: bool | None = None
    config_redacted: dict = Field(default_factory=dict)


class ConnectorsResponse(BaseModel):
    accepted: bool
    status: Literal["ready", "unknown", "blocked"]
    reason: str | None = None
    items: list[Connector] = Field(default_factory=list)
    total: int = 0


@router.get("/api/connectors", response_model=ConnectorsResponse)
def list_connectors() -> ConnectorsResponse:
    """Return registered external connectors.

    No connector registry is wired today. Per the W15 A20 honest-blocked
    contract, return ``accepted=false`` with a stable ``reason`` token.
    """
    return ConnectorsResponse(
        accepted=False,
        status="unknown",
        reason="connector_registry_not_yet_implemented",
        items=[],
        total=0,
    )
