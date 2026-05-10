"""W15 A20 — /api/settings/themes.

Returns the 6 named theme palettes that the GUI ships with. Palette JSON
lives at ``03_implementation/data/themes/{id}.json`` and is loaded on
each request (cheap: 6 small files). The set is finite, named, and
auditable:

    default, cyberpunk, matrix, tron, industrial_forge, aurora_operator

These are real assets — A17 (Settings UI) renders them as picker
options. If a palette file is missing on disk, we surface the failure
honestly via ``status="blocked"`` for that entry rather than synthesizing
a fake palette.

This endpoint is read-only. Theme *selection* is persisted via the
existing ``PUT /api/settings/theme`` in ``settings.py`` — out of scope
for this lane.

References:
- FastAPI bigger applications / routers:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- OpenAPI design convention: separate read-only ``/{resource}/themes``
  catalog endpoint from the mutable selection endpoint to keep the
  catalog cacheable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


# 03_implementation/src/hermes3d/api/routes/settings_themes.py
#   -> routes -> api -> hermes3d -> src -> 03_implementation
THEMES_DIR = Path(__file__).resolve().parents[4] / "data" / "themes"


THEME_IDS: tuple[str, ...] = (
    "default",
    "cyberpunk",
    "matrix",
    "tron",
    "industrial_forge",
    "aurora_operator",
)


class ThemeTokens(BaseModel):
    bg_root: str
    bg_panel: str
    bg_elevated: str
    fg_primary: str
    fg_secondary: str
    fg_muted: str
    accent_primary: str
    accent_secondary: str
    border_subtle: str
    border_strong: str
    status_success: str
    status_warning: str
    status_danger: str
    status_info: str
    highlight: str


class Theme(BaseModel):
    id: str
    display_name: str
    description: str
    kind: Literal["dark", "light"]
    tokens: ThemeTokens
    status: Literal["ready", "blocked"] = "ready"
    reason: str | None = None


class ThemesResponse(BaseModel):
    accepted: bool
    status: Literal["ready", "partial", "blocked"]
    reason: str | None = None
    items: list[Theme] = Field(default_factory=list)
    total: int = 0


def _load_theme(theme_id: str) -> Theme:
    path = THEMES_DIR / f"{theme_id}.json"
    if not path.exists():
        # Honest blocked: do not synthesize a palette.
        return Theme(
            id=theme_id,
            display_name=theme_id,
            description="palette file not found on disk",
            kind="dark",
            tokens=ThemeTokens(
                bg_root="#000000",
                bg_panel="#000000",
                bg_elevated="#000000",
                fg_primary="#FFFFFF",
                fg_secondary="#FFFFFF",
                fg_muted="#FFFFFF",
                accent_primary="#FFFFFF",
                accent_secondary="#FFFFFF",
                border_subtle="#000000",
                border_strong="#000000",
                status_success="#FFFFFF",
                status_warning="#FFFFFF",
                status_danger="#FFFFFF",
                status_info="#FFFFFF",
                highlight="#000000",
            ),
            status="blocked",
            reason=f"theme_palette_missing:{path.name}",
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Theme(
        id=raw["id"],
        display_name=raw["display_name"],
        description=raw["description"],
        kind=raw.get("kind", "dark"),
        tokens=ThemeTokens(**raw["tokens"]),
        status="ready",
        reason=None,
    )


@router.get("/api/settings/themes", response_model=ThemesResponse)
def list_themes() -> ThemesResponse:
    """Return the 6 named theme palettes shipped with Hermes3D."""
    items = [_load_theme(theme_id) for theme_id in THEME_IDS]
    blocked = [item for item in items if item.status == "blocked"]
    if not blocked:
        overall_status: Literal["ready", "partial", "blocked"] = "ready"
        reason = None
    elif len(blocked) < len(items):
        overall_status = "partial"
        reason = f"{len(blocked)}/{len(items)} palettes blocked"
    else:
        overall_status = "blocked"
        reason = "all_theme_palettes_missing"
    return ThemesResponse(
        accepted=bool(items),
        status=overall_status,
        reason=reason,
        items=items,
        total=len(items),
    )
