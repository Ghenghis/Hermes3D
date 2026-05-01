"""Moonraker (Klipper HTTP API) adapter skeleton (Phase 1 — detect/version/capabilities only).

Moonraker is a network service, not a local binary. Phase 1 cannot detect it
without making network calls (forbidden in foundation phase). detect() returns
UNINSTALLED unconditionally; Phase 3 will add config-driven detection that
reads `printers.user.toml` for the host:port and probes /server/info.
"""

from __future__ import annotations

from .base import SkeletonAdapter
from .registry import register
from .types import AdapterState, DetectResult


@register
class MoonrakerAdapter(SkeletonAdapter):
    key = "moonraker"
    display_name = "Moonraker"
    category = "printer"
    dangerous = True  # write commands move printers — Phase 6 gates execute()

    _CAPABILITIES = frozenset(
        {"rest_api", "websocket", "streaming_logs", "e_stop", "dry_run_supported"}
    )

    def detect(self) -> DetectResult:
        # Phase 3 will read printers.user.toml + probe /server/info.
        # Phase 1 stays network-free.
        return self._detect_result(
            False,
            AdapterState.UNINSTALLED,
            "Phase 1 cannot probe network endpoints; configure in printers.user.toml (Phase 3)",
        )

    def version(self) -> str | None:
        return None  # network-only; Phase 3

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
