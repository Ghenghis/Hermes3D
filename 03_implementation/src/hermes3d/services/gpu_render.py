"""Optional GPU-accelerated render service for modeling proof envelopes.

W18-A20: exercises the Blender Cycles CUDA code path to produce a real
thumbnail of an exported STL. Used by the design intake to add proof that
the local RTX 3090 Ti can be exercised through the modeling backend.

Critical contract: this service NEVER fakes GPU usage. If Blender or a
CUDA device cannot be located, it returns ``{"used": False, "reason": ...}``
with the exact reason. The proof envelope writer then records
``gpu_used: false`` honestly.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes3d.services.gpu_probe import probe_gpu, sample_gpu_utilization

LOG = logging.getLogger(__name__)

# Windows install locations to fall back to when blender.exe is not on PATH.
_BLENDER_FALLBACK_PATHS = (
    r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_blender() -> str | None:
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    for candidate in _BLENDER_FALLBACK_PATHS:
        if Path(candidate).is_file():
            return candidate
    return None


def render_stl_thumbnail_gpu(
    *,
    stl_path: str | Path,
    out_path: str | Path,
    samples: int = 16,
    width: int = 640,
    height: int = 480,
    timeout_s: float = 180.0,
) -> dict[str, Any]:
    """Render an STL thumbnail through Blender Cycles CUDA.

    Returns a dict with at minimum ``used: bool`` and ``reason`` (when False).
    When True, also includes ``backend``, ``device``, ``render_seconds``,
    ``samples``, ``output_path``, ``vram_used_mib_pre``, ``vram_used_mib_peak``,
    and ``utilization_pct_peak``.
    """
    stl_p = Path(stl_path).resolve()
    out_p = Path(out_path).resolve()
    if not stl_p.is_file():
        return {
            "used": False,
            "reason": f"STL not found: {stl_p}",
            "attempted_at": _utc_now(),
        }

    blender = _find_blender()
    if not blender:
        return {
            "used": False,
            "reason": "Blender executable not found on PATH or known install dirs.",
            "attempted_at": _utc_now(),
        }

    script_path = Path(__file__).resolve().parents[3] / "scripts" / "w18_a20_blender_gpu_render.py"
    if not script_path.is_file():
        return {
            "used": False,
            "reason": f"Blender render script missing at {script_path}.",
            "attempted_at": _utc_now(),
        }

    pre_gpu = probe_gpu()
    if not pre_gpu.get("available"):
        return {
            "used": False,
            "reason": f"nvidia-smi reports GPU unavailable: {pre_gpu.get('reason', 'no reason')}",
            "attempted_at": _utc_now(),
        }

    pre_vram = int(pre_gpu.get("vram_used_mib") or 0)

    out_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        blender,
        "--background",
        "--python",
        str(script_path),
        "--",
        "--stl",
        str(stl_p),
        "--out",
        str(out_p),
        "--samples",
        str(samples),
        "--width",
        str(width),
        "--height",
        str(height),
    ]

    t0 = time.perf_counter()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired as exc:
        return {
            "used": False,
            "reason": f"Blender render timed out after {timeout_s}s: {exc}",
            "attempted_at": _utc_now(),
        }
    elapsed = time.perf_counter() - t0

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    combined = stdout + "\n" + stderr

    # Refuse silent CPU fallback — Blender script raises on no-CUDA.
    if result.returncode != 0:
        tail = combined.strip().splitlines()[-30:]
        return {
            "used": False,
            "reason": (f"Blender exit code {result.returncode}. Tail:\n" + "\n".join(tail)),
            "attempted_at": _utc_now(),
        }

    # Confirm Cycles selected a CUDA device.
    cuda_line = next(
        (line for line in stdout.splitlines() if "W18A20-CYCLES-DEVICES" in line),
        None,
    )
    if not cuda_line or "CUDA" not in cuda_line:
        return {
            "used": False,
            "reason": "Blender script did not announce CUDA device selection.",
            "attempted_at": _utc_now(),
            "blender_stdout_tail": stdout.strip().splitlines()[-20:],
        }

    if not out_p.is_file() or out_p.stat().st_size <= 0:
        return {
            "used": False,
            "reason": f"Render produced no file at {out_p}.",
            "attempted_at": _utc_now(),
        }

    # Parse the W18A20-RENDER-OK line for the inside-Blender wall time.
    render_seconds: float | None = None
    for line in stdout.splitlines():
        if line.startswith("W18A20-RENDER-OK"):
            for piece in line.split():
                if piece.startswith("seconds="):
                    try:
                        render_seconds = float(piece.split("=", 1)[1])
                    except ValueError:
                        render_seconds = None
                    break

    # Snapshot post-render GPU state (one sample — render is too short to poll).
    post_sample = sample_gpu_utilization()
    peak_util: int | None = None
    peak_vram: int | None = None
    if post_sample.get("available"):
        peak_util = int(post_sample.get("utilization_pct") or 0)
        peak_vram = int(post_sample.get("vram_used_mib") or 0)

    return {
        "used": True,
        "backend": "blender_cycles",
        "device": "CUDA",
        "blender_path": blender,
        "render_seconds": render_seconds if render_seconds is not None else elapsed,
        "wall_seconds_total": elapsed,
        "samples": samples,
        "resolution": [width, height],
        "output_path": str(out_p),
        "output_size_bytes": out_p.stat().st_size,
        "vram_used_mib_pre": pre_vram,
        "vram_used_mib_peak": peak_vram,
        "utilization_pct_peak": peak_util,
        "cycles_devices_line": cuda_line.strip(),
        "attempted_at": _utc_now(),
    }


__all__ = ["render_stl_thumbnail_gpu"]
