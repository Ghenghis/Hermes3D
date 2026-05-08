"""Optional Rust acceleration bridge for read-only metadata and hash paths.

The Rust helper is intentionally optional. If it is not built or configured,
callers keep using the Python implementation rather than pretending the
accelerator is available.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

LOG = logging.getLogger(__name__)

SUPPORTED_COMMANDS = frozenset({"sha256", "gcode-meta", "stl-meta"})


def implementation_root() -> Path:
    return Path(__file__).resolve().parents[3]


def rust_crate_root() -> Path:
    return implementation_root() / "rust" / "hermes3d_accel"


def rust_accel_binary() -> Path | None:
    explicit = os.environ.get("HERMES3D_RUST_ACCEL_BIN")
    if explicit:
        candidate = Path(explicit)
        return candidate if candidate.is_file() else None

    exe = "hermes3d-accel.exe" if os.name == "nt" else "hermes3d-accel"
    crate = rust_crate_root()
    for profile in ("release", "debug"):
        candidate = crate / "target" / profile / exe
        if candidate.is_file():
            return candidate
    return None


def run_rust_accel(
    command: str,
    path: str | Path,
    *,
    timeout_seconds: float = 10.0,
) -> dict[str, Any] | None:
    if command not in SUPPORTED_COMMANDS:
        raise ValueError(f"unsupported Rust acceleration command: {command}")

    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(target)

    binary = rust_accel_binary()
    if binary is None:
        return None

    proc = subprocess.run(
        [str(binary), command, str(target)],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if proc.returncode != 0:
        LOG.debug("Rust accelerator failed rc=%s stderr=%s", proc.returncode, proc.stderr[-500:])
        return None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        LOG.debug("Rust accelerator returned invalid JSON: %s", proc.stdout[:500])
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def file_sha256_hex(path: str | Path) -> str:
    accelerated = run_rust_accel("sha256", path)
    if accelerated and isinstance(accelerated.get("sha256"), str):
        return str(accelerated["sha256"])

    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_gcode_metadata_accel(path: str | Path) -> dict[str, Any] | None:
    payload = run_rust_accel("gcode-meta", path)
    if not payload:
        return None
    return {
        "estimated_minutes": payload.get("estimated_minutes"),
        "estimated_filament_mm": payload.get("estimated_filament_mm"),
        "estimated_filament_g": payload.get("estimated_filament_g"),
        "layer_count": payload.get("layer_count"),
    }


def binary_stl_metadata_accel(path: str | Path) -> dict[str, Any] | None:
    payload = run_rust_accel("stl-meta", path)
    if not payload or payload.get("format") != "binary_stl":
        return None
    return payload


__all__ = [
    "SUPPORTED_COMMANDS",
    "binary_stl_metadata_accel",
    "file_sha256_hex",
    "implementation_root",
    "parse_gcode_metadata_accel",
    "run_rust_accel",
    "rust_accel_binary",
    "rust_crate_root",
]
