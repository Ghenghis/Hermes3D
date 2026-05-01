"""Blender MCP provider-manager skeleton (Phase 1 — detect/version/capabilities only)."""

from __future__ import annotations

import shutil

from .base import SkeletonAdapter
from .registry import register
from .types import AdapterState, DetectResult


@register
class BlenderMCPAdapter(SkeletonAdapter):
    key = "blender_mcp"
    display_name = "Blender MCP (provider manager)"
    category = "3d-mcp"
    dangerous = True

    _CAPABILITIES = frozenset({"mcp", "dry_run_supported"})

    def detect(self) -> DetectResult:
        # `uvx` is the MCP provider launcher; presence of uvx implies we *could*
        # reach the provider. Phase 3 will run `claude mcp list` to confirm.
        path = shutil.which("uvx")
        if path:
            return self._detect_result(True, AdapterState.DETECTED, f"uvx at {path}")
        return self._detect_result(
            False,
            AdapterState.UNINSTALLED,
            "uvx not on PATH — install uv then `uvx blender-mcp`",
        )

    def version(self) -> str | None:
        # `uvx blender-mcp --version` would download the provider on first call;
        # that is not Phase-1-safe. Defer to Phase 3 when we have a configured
        # provider cache.
        return None

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
