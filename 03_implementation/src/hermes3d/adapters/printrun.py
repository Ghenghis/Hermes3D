"""Printrun (USB printer control) adapter.

Detection is source/runtime aware: the source checkout is tracked by Source OS,
while the user's existing Windows launchers in G:/Github/apps are treated as
local runtime tools. Launching Pronterface opens the real application only; it
does not send serial commands or move/upload to any printer.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from .base import SkeletonAdapter
from .registry import register
from .types import AdapterState, DetectResult, LaunchResult

APPS_ROOT = Path(os.environ.get("HERMES3D_APPS_ROOT", "G:/Github/apps"))
SOURCE_ROOT = APPS_ROOT / "Printrun-printrun-2.2.0"
_LAUNCHED_PROCESS: subprocess.Popen[bytes] | subprocess.Popen[str] | None = None


def _first_path(names: tuple[str, ...]) -> Path | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def _existing_candidates() -> dict[str, Path]:
    candidates = {
        "pronsole_path": _first_path(("pronsole", "pronsole.exe")),
        "pronterface_path": _first_path(("pronterface", "pronterface.exe")),
        "pronsole_windows": APPS_ROOT / "Pronsole.exe",
        "pronterface_windows": APPS_ROOT / "Pronterface.exe",
        "source_pronsole": SOURCE_ROOT / "pronsole.py",
        "source_pronterface": SOURCE_ROOT / "pronterface.py",
    }
    return {name: path for name, path in candidates.items() if path and path.exists()}


def _preferred_launcher() -> Path | None:
    candidates = _existing_candidates()
    for key in ("pronterface_windows", "pronterface_path", "source_pronterface", "pronsole_windows", "pronsole_path"):
        path = candidates.get(key)
        if path:
            return path
    return None


def _source_version() -> str | None:
    version_path = SOURCE_ROOT / "printrun" / "printcore.py"
    if not version_path.exists():
        return None
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", version_path.read_text(encoding="utf-8", errors="ignore"))
    return match.group(1) if match else None


@register
class PrintrunAdapter(SkeletonAdapter):
    key = "printrun"
    display_name = "Printrun / Pronterface / Pronsole"
    category = "printer"
    dangerous = True  # USB G-code writes — Phase 6 enforces gated execute()

    _CAPABILITIES = frozenset({"cli", "gui", "usb", "e_stop", "dry_run_supported"})

    def detect(self) -> DetectResult:
        candidates = _existing_candidates()
        if candidates:
            detail = "; ".join(f"{name}={path}" for name, path in sorted(candidates.items()))
            return self._detect_result(True, AdapterState.DETECTED, detail)
        return self._detect_result(
            False,
            AdapterState.UNINSTALLED,
            f"Printrun runtime not found on PATH or under {APPS_ROOT}",
        )

    def version(self) -> str | None:
        return _source_version()

    def capabilities(self) -> frozenset[str]:
        return self._CAPABILITIES

    def open_external(self) -> LaunchResult:
        global _LAUNCHED_PROCESS
        launcher = _preferred_launcher()
        if not launcher:
            return LaunchResult(
                ok=False,
                mode="external",
                detail=f"Pronterface/Pronsole launcher was not found on PATH or under {APPS_ROOT}.",
            )
        if _LAUNCHED_PROCESS and _LAUNCHED_PROCESS.poll() is None:
            return LaunchResult(
                ok=True,
                mode="external",
                pid=_LAUNCHED_PROCESS.pid,
                detail=f"Printrun already running from {launcher}; serial commands remain user-gated.",
            )
        try:
            _LAUNCHED_PROCESS = subprocess.Popen(  # noqa: S603 -- fixed local executable path, no shell.
                [str(launcher)],
                cwd=str(launcher.parent),
                shell=False,
            )
        except OSError as exc:
            return LaunchResult(ok=False, mode="external", detail=f"Launch failed: {exc}")
        return LaunchResult(
            ok=True,
            mode="external",
            pid=_LAUNCHED_PROCESS.pid,
            detail=f"Launched {launcher}; no serial commands were sent.",
        )

    def stop_external(self) -> LaunchResult:
        global _LAUNCHED_PROCESS
        if not _LAUNCHED_PROCESS or _LAUNCHED_PROCESS.poll() is not None:
            _LAUNCHED_PROCESS = None
            return LaunchResult(ok=False, mode="external", detail="No Hermes3D-launched Printrun process is running.")
        pid = _LAUNCHED_PROCESS.pid
        _LAUNCHED_PROCESS.terminate()
        return LaunchResult(ok=True, mode="external", pid=pid, detail="Terminate signal sent to Hermes3D-launched Printrun process.")
