"""PrusaSlicer adapter skeleton (Phase 1 — detect/version/capabilities only)."""

from __future__ import annotations

import shutil

from .base import SkeletonAdapter, _safe_version_command
from .registry import register
from .types import AdapterState, DetectResult


@register
class PrusaSlicerAdapter(SkeletonAdapter):
    key = "prusa_slicer"
    display_name = "PrusaSlicer"
    category = "slicer"
    dangerous = True

    _CAPABILITIES = frozenset({"cli", "gui", "dry_run_supported"})

    def _which(self) -> str | None:
        for name in ("prusa-slicer", "prusa-slicer-console"):
            path = shutil.which(name)
            if path:
                return path
        return None

    def detect(self) -> DetectResult:
        path = self._which()
        if path:
            return self._detect_result(True, AdapterState.DETECTED, f"binary at {path}")
        return self._detect_result(False, AdapterState.UNINSTALLED, "prusa-slicer not on PATH")

    def version(self) -> str | None:
        path = self._which()
        if not path:
            return None
        return _safe_version_command([path, "--version"])

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
