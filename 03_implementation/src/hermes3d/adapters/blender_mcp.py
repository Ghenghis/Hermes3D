"""Blender MCP provider manager.

Provider choice is backend-configured. Detection is deliberately conservative:
we report launcher availability and do not claim a provider is connected until
a real Blender/MCP session validates it.
"""

from __future__ import annotations

import shutil

from hermes3d.api.routes._common import row

from .base import SkeletonAdapter
from .registry import register
from .types import AdapterState, DetectResult


@register
class BlenderMCPAdapter(SkeletonAdapter):
    key = "blender_mcp"
    display_name = "Blender MCP (provider manager)"
    category = "3d-mcp"
    dangerous = True

    _CAPABILITIES = frozenset({
        "mcp",
        "provider_switch",
        "execute_blender_python_after_validation",
        "scene_inspection",
        "dry_run_supported",
    })

    def detect(self) -> DetectResult:
        active = _active_provider()
        if active == "official_blender":
            return self._detect_result(
                True,
                AdapterState.CONFIGURED,
                "Official Blender connector selected; requires live Blender add-on validation before use.",
            )
        path = shutil.which("uvx")
        if path:
            return self._detect_result(True, AdapterState.DETECTED, f"{active} selected; uvx at {path}")
        return self._detect_result(
            False,
            AdapterState.UNINSTALLED,
            f"{active} selected; uvx not on PATH and no validated Blender MCP session is connected.",
        )

    def version(self) -> str | None:
        # `uvx blender-mcp --version` would download the provider on first call;
        # that is not Phase-1-safe. Defer to Phase 3 when we have a configured
        # provider cache.
        return None

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES


def _active_provider() -> str:
    setting = row("SELECT value FROM settings WHERE key = 'source_os.blender_mcp_candidates.active_provider'")
    if setting:
        return str(setting["value"])
    legacy = row("SELECT value FROM settings WHERE key = 'source_os.blender_mcp.active_provider'")
    return str(legacy["value"]) if legacy else "official_blender"
