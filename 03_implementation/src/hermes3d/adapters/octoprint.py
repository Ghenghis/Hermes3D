"""OctoPrint adapter skeleton (Phase 1 — detect/version/capabilities only).

OctoPrint is a network service. Same Phase 1 constraint as Moonraker:
detect() returns UNINSTALLED unconditionally; Phase 3 adds config-driven
detection via API key + base_url.
"""

from __future__ import annotations

from .base import SkeletonAdapter
from .registry import register
from .types import AdapterState, DetectResult


@register
class OctoPrintAdapter(SkeletonAdapter):
    key = "octoprint"
    display_name = "OctoPrint"
    category = "printer"
    dangerous = True

    _CAPABILITIES = frozenset(
        {"rest_api", "dock_iframe", "streaming_logs", "e_stop", "dry_run_supported"}
    )

    def detect(self) -> DetectResult:
        return self._detect_result(
            False,
            AdapterState.UNINSTALLED,
            "Phase 1 cannot probe network endpoints; configure base_url + api_key (Phase 3)",
        )

    def version(self) -> str | None:
        return None

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
