"""Slicer integration: real PrusaSlicer / OrcaSlicer CLI wrapper.

This module SHELLS OUT to a slicer CLI binary that the user provides. It
does NOT bundle a slicer (correctly delegated to the installer per the
contract: large binaries belong in the installer, not the kit ZIP).

When the binary is missing, ``slice_mesh`` raises ``SlicerNotFound`` so the
caller can present a clear, actionable error.

Public API:
    find_slicer() -> Path | None
    slice_mesh(stl_path, *, slicer=None, profile=None, output_dir=None)
        -> SliceResult
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)


class SlicerError(RuntimeError):
    """Raised on any slicer failure."""


class SlicerNotFound(SlicerError):
    """Raised when no slicer binary is available on this machine."""


@dataclass
class SliceResult:
    """Outcome of a slice operation."""

    slicer_binary: str
    stl_path: str
    gcode_path: str
    return_code: int
    duration_seconds: float
    estimated_minutes: float | None
    estimated_filament_mm: float | None
    estimated_filament_g: float | None
    layer_count: int | None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slicer_binary": self.slicer_binary,
            "stl_path": self.stl_path,
            "gcode_path": self.gcode_path,
            "return_code": self.return_code,
            "duration_seconds": self.duration_seconds,
            "estimated_minutes": self.estimated_minutes,
            "estimated_filament_mm": self.estimated_filament_mm,
            "estimated_filament_g": self.estimated_filament_g,
            "layer_count": self.layer_count,
            "extra": self.extra,
        }


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _windows_candidates() -> list[Path]:
    program_files = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    portable = ["C:/Hermes3D-OS/prusaslicer", "C:/Hermes3D-OS/orcaslicer"]

    cand: list[Path] = []
    for root in [r for r in program_files if r]:
        for sub in (
            "Prusa3D/PrusaSlicer/prusa-slicer-console.exe",
            "Prusa3D/PrusaSlicer/prusa-slicer.exe",
            "OrcaSlicer/orca-slicer-console.exe",
            "OrcaSlicer/orca-slicer.exe",
        ):
            cand.append(Path(root) / sub)
    for p in portable:
        cand.extend(
            [
                Path(p) / "prusa-slicer-console.exe",
                Path(p) / "prusa-slicer.exe",
                Path(p) / "orca-slicer-console.exe",
                Path(p) / "orca-slicer.exe",
            ]
        )
    return cand


def _posix_candidates() -> list[Path]:
    out: list[Path] = []
    for name in (
        "prusa-slicer",
        "PrusaSlicer",
        "prusaslicer",
        "orca-slicer",
        "OrcaSlicer",
        "orcaslicer",
    ):
        which = shutil.which(name)
        if which:
            out.append(Path(which))
    out.extend(
        [
            Path.home() / "PrusaSlicer/prusa-slicer",
            Path("/opt/PrusaSlicer/prusa-slicer"),
            Path("/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer"),
            Path("/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"),
        ]
    )
    return out


def find_slicer() -> Path | None:
    """Auto-detect a usable slicer binary. Honours the env var
    ``HERMES3D_SLICER_BIN`` for explicit overrides.

    Returns the first existing executable, or None.
    """
    explicit = os.environ.get("HERMES3D_SLICER_BIN")
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
        LOG.warning("HERMES3D_SLICER_BIN set to %s but file does not exist", explicit)

    cands = _windows_candidates() if sys.platform.startswith("win") else _posix_candidates()
    for p in cands:
        if p.is_file():
            return p
    return None


# ---------------------------------------------------------------------------
# G-code metadata parsing
# ---------------------------------------------------------------------------


# These patterns match the well-known headers that PrusaSlicer / OrcaSlicer
# write into the top of every g-code file (and the END for OrcaSlicer).
# We read a bounded chunk from BOTH ends so we don't load the entire file.
_TIME_PATTERNS = (
    re.compile(r"; *estimated printing time \(normal mode\) *= *(.+)$", re.IGNORECASE),
    re.compile(r"; *estimated printing time *= *(.+)$", re.IGNORECASE),
    re.compile(r"; *total estimated time *: *(.+)$", re.IGNORECASE),
)
_FILAMENT_USED_MM = re.compile(r"; *filament used \[mm\] *= *([0-9.]+)", re.IGNORECASE)
_FILAMENT_USED_G = re.compile(r"; *filament used \[g\] *= *([0-9.]+)", re.IGNORECASE)
_LAYER_COUNT = re.compile(r"; *(?:total layer number|num layers) *: *([0-9]+)", re.IGNORECASE)


def _hms_to_minutes(text: str) -> float | None:
    """Parse '1h 23m 45s' / '1:23:45' / '23m 5s' / '5m' formats."""
    text = text.strip()
    # h/m/s with units
    m = re.match(
        r"(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?\s*$",
        text,
        flags=re.IGNORECASE,
    )
    if m and any(m.groups()):
        d, h, mi, s = (int(g) if g else 0 for g in m.groups())
        return d * 1440 + h * 60 + mi + s / 60.0
    # H:M:S / M:S
    parts = text.split(":")
    if all(p.strip().isdigit() for p in parts) and len(parts) in (2, 3):
        ints = [int(p) for p in parts]
        if len(ints) == 3:
            h, mi, s = ints
        else:
            h, (mi, s) = 0, ints
        return h * 60 + mi + s / 60.0
    return None


def parse_gcode_metadata(
    gcode_path: str | Path, head_bytes: int = 65536, tail_bytes: int = 65536
) -> dict[str, Any]:
    """Read the head + tail of a g-code file and parse the standard metadata."""
    p = Path(gcode_path)
    if not p.is_file():
        raise FileNotFoundError(f"g-code not found: {p}")

    size = p.stat().st_size
    with open(p, "rb") as fp:
        head = fp.read(min(head_bytes, size)).decode("utf-8", errors="replace")
        if size > head_bytes + tail_bytes:
            fp.seek(-tail_bytes, os.SEEK_END)
            tail = fp.read().decode("utf-8", errors="replace")
        else:
            tail = ""
    text = head + "\n" + tail

    out: dict[str, Any] = {
        "estimated_minutes": None,
        "estimated_filament_mm": None,
        "estimated_filament_g": None,
        "layer_count": None,
    }
    for line in text.splitlines():
        for pat in _TIME_PATTERNS:
            m = pat.search(line)
            if m and out["estimated_minutes"] is None:
                out["estimated_minutes"] = _hms_to_minutes(m.group(1))
        m = _FILAMENT_USED_MM.search(line)
        if m and out["estimated_filament_mm"] is None:
            out["estimated_filament_mm"] = float(m.group(1))
        m = _FILAMENT_USED_G.search(line)
        if m and out["estimated_filament_g"] is None:
            out["estimated_filament_g"] = float(m.group(1))
        m = _LAYER_COUNT.search(line)
        if m and out["layer_count"] is None:
            out["layer_count"] = int(m.group(1))
    return out


# ---------------------------------------------------------------------------
# Slicing
# ---------------------------------------------------------------------------


def slice_mesh(
    stl_path: str | Path,
    *,
    slicer: str | Path | None = None,
    profile: str | Path | None = None,
    output_dir: str | Path | None = None,
    timeout_seconds: int = 600,
) -> SliceResult:
    """Slice an STL via PrusaSlicer/OrcaSlicer CLI and parse the metadata.

    Args:
        stl_path: Input STL/OBJ/3MF.
        slicer: Path to the slicer binary. If None, ``find_slicer()`` is used.
        profile: Optional .ini profile passed via ``--load``.
        output_dir: Where to write the .gcode. Defaults to STL parent dir.
        timeout_seconds: Hard timeout on the subprocess.

    Returns ``SliceResult``.

    Raises:
        SlicerNotFound: no slicer available.
        SlicerError: slicer exited non-zero or output missing.
        FileNotFoundError: STL missing.
    """
    stl = Path(stl_path)
    if not stl.is_file():
        raise FileNotFoundError(f"stl not found: {stl}")

    bin_path = Path(slicer) if slicer else find_slicer()
    if bin_path is None or not bin_path.is_file():
        raise SlicerNotFound(
            "No PrusaSlicer/OrcaSlicer binary found. Install PrusaSlicer or "
            "OrcaSlicer, or set HERMES3D_SLICER_BIN to the binary's path."
        )

    out_dir = Path(output_dir) if output_dir else stl.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    gcode_path = out_dir / (stl.stem + ".gcode")

    cmd: list[str] = [
        str(bin_path),
        "--export-gcode",
        "--output",
        str(gcode_path),
    ]
    if profile is not None:
        cmd.extend(["--load", str(profile)])
    cmd.append(str(stl))

    LOG.info("Running slicer: %s", " ".join(cmd))
    t0 = time.time()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    duration = time.time() - t0

    if proc.returncode != 0 or not gcode_path.is_file():
        raise SlicerError(f"Slicer failed (rc={proc.returncode}). STDERR: {proc.stderr[-2000:]}")

    metadata = parse_gcode_metadata(gcode_path)
    return SliceResult(
        slicer_binary=str(bin_path),
        stl_path=str(stl.resolve()),
        gcode_path=str(gcode_path.resolve()),
        return_code=int(proc.returncode),
        duration_seconds=float(duration),
        estimated_minutes=metadata["estimated_minutes"],
        estimated_filament_mm=metadata["estimated_filament_mm"],
        estimated_filament_g=metadata["estimated_filament_g"],
        layer_count=metadata["layer_count"],
        extra={
            "stdout_tail": proc.stdout[-1500:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-1500:] if proc.stderr else "",
            "argv": cmd,
        },
    )


__all__ = [
    "SliceResult",
    "SlicerError",
    "SlicerNotFound",
    "find_slicer",
    "parse_gcode_metadata",
    "slice_mesh",
]
