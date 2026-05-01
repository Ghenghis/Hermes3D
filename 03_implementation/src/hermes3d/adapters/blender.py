"""Blender adapter skeleton (Phase 1 — detect/version/capabilities only)."""

from __future__ import annotations

import shutil

from .base import SkeletonAdapter, _safe_version_command
from .registry import register
from .types import AdapterState, DetectResult


@register
class BlenderAdapter(SkeletonAdapter):
    key = "blender"
    display_name = "Blender"
    category = "3d"
    dangerous = True

    _CAPABILITIES = frozenset({"gui", "headless_smoke", "dry_run_supported"})

    def detect(self) -> DetectResult:
        path = shutil.which("blender")
        if path:
            return self._detect_result(True, AdapterState.DETECTED, f"binary at {path}")
        return self._detect_result(False, AdapterState.UNINSTALLED, "blender not on PATH")

    def version(self) -> str | None:
        path = shutil.which("blender")
        if not path:
            return None
        return _safe_version_command([path, "--version"])

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
