"""Mainsail (Moonraker UI) adapter skeleton (Phase 1 — detect/version/capabilities only).

Mainsail is a web UI served by an external host. Writes go through the
MoonrakerAdapter, so this adapter is non-dangerous.
"""

from __future__ import annotations

from .base import SkeletonAdapter
from .registry import register
from .types import AdapterState, DetectResult


@register
class MainsailAdapter(SkeletonAdapter):
    key = "mainsail"
    display_name = "Mainsail"
    category = "printer-ui"
    dangerous = False

    _CAPABILITIES = frozenset({"dock_iframe", "read_only"})

    def detect(self) -> DetectResult:
        return self._detect_result(
            False,
            AdapterState.UNINSTALLED,
            "Phase 1 cannot probe network endpoints; configure URL (Phase 3)",
        )

    def version(self) -> str | None:
        return None

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
