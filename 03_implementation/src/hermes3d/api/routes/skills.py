"""W15 A20 — /api/skills.

Honest skill-registry surface. No fake skill names. If no registry is
configured (current state), the endpoint returns ``accepted=false`` with a
machine-readable ``reason``. UI agents (A11–A19) consume this contract to
render an empty-state, not a fabricated list.

References:
- FastAPI bigger applications / routers:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- OpenAPI collection convention: GET /resource returns a top-level object
  with ``items`` + envelope metadata so the response is forward-compatible
  with future pagination + filter fields.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class Skill(BaseModel):
    id: str
    display_name: str
    kind: Literal["agent_capability", "tool", "workflow"]
    description: str
    enabled: bool
    source: str


class SkillsResponse(BaseModel):
    accepted: bool
    status: Literal["ready", "unknown", "blocked"]
    reason: str | None = None
    items: list[Skill] = Field(default_factory=list)
    total: int = 0


@router.get("/api/skills", response_model=SkillsResponse)
def list_skills() -> SkillsResponse:
    """Return registered skills.

    No registry is wired today. Per the W15 A20 honest-blocked contract,
    we return ``accepted=false`` with a stable ``reason`` token so UI
    agents can render a deterministic empty state instead of inventing
    capability names.
    """
    return SkillsResponse(
        accepted=False,
        status="unknown",
        reason="skill_registry_not_yet_implemented",
        items=[],
        total=0,
    )
