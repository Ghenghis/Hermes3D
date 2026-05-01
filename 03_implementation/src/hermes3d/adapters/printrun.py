"""Printrun (USB printer control) skeleton (Phase 1 — detect/version/capabilities only)."""

from __future__ import annotations

import shutil

from .base import SkeletonAdapter, _safe_version_command
from .registry import register
from .types import AdapterState, DetectResult


@register
class PrintrunAdapter(SkeletonAdapter):
    key = "printrun"
    display_name = "Printrun / Pronterface / Pronsole"
    category = "printer"
    dangerous = True  # USB G-code writes — Phase 6 enforces gated execute()

    _CAPABILITIES = frozenset({"cli", "gui", "usb", "e_stop", "dry_run_supported"})

    def detect(self) -> DetectResult:
        path = shutil.which("pronsole")
        if path:
            return self._detect_result(True, AdapterState.DETECTED, f"pronsole at {path}")
        return self._detect_result(
            False,
            AdapterState.UNINSTALLED,
            "pronsole not on PATH",
        )

    def version(self) -> str | None:
        path = shutil.which("pronsole")
        if not path:
            return None
        return _safe_version_command([path, "--help"])  # pronsole --help banner contains version

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES
