"""FLSUN Slicer adapter skeleton (Phase 1 — detect/version/capabilities only).

User-supplied zip on Windows; CLI may not exist depending on build. Phase 1
detects only via PATH or known install location lookup (no zip extraction).
"""

from __future__ import annotations

import shutil

from .base import SkeletonAdapter
from .registry import register
from .types import AdapterState, DetectResult


@register
class FLSunSlicerAdapter(SkeletonAdapter):
    key = "flsun_slicer"
    display_name = "FLSUN Slicer"
    category = "slicer"
    dangerous = True

    _CAPABILITIES = frozenset({"gui", "dry_run_supported"})

    def _which(self) -> str | None:
        for name in ("FLSlicer", "flsun-slicer", "FlsunSlicer"):
            path = shutil.which(name)
            if path:
                return path
        return None

    def detect(self) -> DetectResult:
        path = self._which()
        if path:
            return self._detect_result(True, AdapterState.DETECTED, f"binary at {path}")
        return self._detect_result(
            False,
            AdapterState.UNINSTALLED,
            "FLSUN Slicer not on PATH (extract user-provided zip and add to PATH)",
        )

    def version(self) -> str | None:
        # FLSUN Slicer binaries (forks of PrusaSlicer/OrcaSlicer) may or may not
        # support --version reliably. Defer to Phase 3 where we read the bundled
        # build-info file from the extracted zip.
        return None

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
