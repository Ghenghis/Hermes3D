"""GPU probe service — real nvidia-smi inspection, no fabrication.

Used by W18-A20 modeling proof envelope work to record real GPU capability
information alongside CAD/mesh artifacts. Honest fallback: if nvidia-smi is
absent or returns nonzero, ``probe_gpu()`` returns ``{"available": False}``
with a precise reason string. Never invents a GPU model or driver.

Output schema (when available):
    {
        "available": True,
        "vendor": "NVIDIA",
        "model": "NVIDIA GeForce RTX 3090 Ti",
        "driver": "591.86",
        "cuda": "13.1",
        "vram_total_mib": 24564,
        "vram_used_mib": 15585,
        "vram_free_mib": 8979,
        "utilization_pct": 0,
        "probed_at": "2026-05-11T10:30:00Z",
        "nvidia_smi_path": "C:/Windows/system32/nvidia-smi.exe",
    }

The probe is intentionally side-effect free: it does NOT load CUDA contexts,
allocate VRAM, or do any work other than parsing nvidia-smi output.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

LOG = logging.getLogger(__name__)

NVIDIA_SMI_QUERY = (
    "name,driver_version,memory.total,memory.used,memory.free,"
    "utilization.gpu"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def probe_gpu() -> dict[str, Any]:
    """Probe local NVIDIA GPU via nvidia-smi.

    Returns a dict with ``available: bool``. When ``available`` is True the
    dict also contains ``vendor``, ``model``, ``driver``, ``cuda`` and VRAM
    fields. When False, ``reason`` explains precisely why (no fabrication).
    """
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {
            "available": False,
            "reason": "nvidia-smi not found on PATH.",
            "probed_at": _utc_now(),
        }

    try:
        result = subprocess.run(
            [
                nvidia_smi,
                f"--query-gpu={NVIDIA_SMI_QUERY}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "reason": "nvidia-smi query timed out after 10 s.",
            "probed_at": _utc_now(),
        }
    except OSError as exc:
        return {
            "available": False,
            "reason": f"nvidia-smi invocation failed: {exc}",
            "probed_at": _utc_now(),
        }

    if result.returncode != 0:
        return {
            "available": False,
            "reason": (
                f"nvidia-smi returned exit code {result.returncode}: "
                f"{(result.stderr or '').strip()[:200]}"
            ),
            "probed_at": _utc_now(),
        }

    first_line = next(
        (line.strip() for line in result.stdout.splitlines() if line.strip()),
        "",
    )
    if not first_line:
        return {
            "available": False,
            "reason": "nvidia-smi produced no GPU rows.",
            "probed_at": _utc_now(),
        }

    parts = [piece.strip() for piece in first_line.split(",")]
    if len(parts) < 6:
        return {
            "available": False,
            "reason": (
                f"nvidia-smi row had {len(parts)} columns; expected 6. "
                f"Raw: {first_line!r}"
            ),
            "probed_at": _utc_now(),
        }

    model, driver, vram_total, vram_used, vram_free, util = parts

    cuda_version = _probe_cuda_version(nvidia_smi)

    try:
        vram_total_i = int(float(vram_total))
        vram_used_i = int(float(vram_used))
        vram_free_i = int(float(vram_free))
        util_i = int(float(util))
    except ValueError as exc:
        return {
            "available": False,
            "reason": f"nvidia-smi numeric parse failed: {exc}",
            "probed_at": _utc_now(),
        }

    return {
        "available": True,
        "vendor": "NVIDIA",
        "model": model,
        "driver": driver,
        "cuda": cuda_version,
        "vram_total_mib": vram_total_i,
        "vram_used_mib": vram_used_i,
        "vram_free_mib": vram_free_i,
        "utilization_pct": util_i,
        "nvidia_smi_path": nvidia_smi,
        "probed_at": _utc_now(),
    }


def _probe_cuda_version(nvidia_smi: str) -> str | None:
    """Get CUDA runtime version from nvidia-smi header. Returns None if absent."""
    try:
        result = subprocess.run(
            [nvidia_smi],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        LOG.debug("CUDA-version probe via nvidia-smi failed: %s", exc)
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "CUDA Version" in line:
            after = line.split("CUDA Version", 1)[1]
            cleaned = after.lstrip(": ").strip()
            cleaned = cleaned.split()[0] if cleaned else ""
            cleaned = cleaned.rstrip("|").strip()
            if cleaned:
                return cleaned
    return None


def sample_gpu_utilization() -> dict[str, Any]:
    """Light-weight current-utilization snapshot for inside-operation polling.

    Returns ``{"available": False, ...}`` on failure rather than raising,
    so the caller can keep polling without breaking the main code path.
    """
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {"available": False, "reason": "nvidia-smi not on PATH."}
    try:
        result = subprocess.run(
            [
                nvidia_smi,
                "--query-gpu=utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"available": False, "reason": f"sample failed: {exc}"}
    if result.returncode != 0:
        return {
            "available": False,
            "reason": f"sample exit {result.returncode}",
        }
    first = next(
        (line.strip() for line in result.stdout.splitlines() if line.strip()),
        "",
    )
    if not first:
        return {"available": False, "reason": "empty sample"}
    parts = [piece.strip() for piece in first.split(",")]
    if len(parts) < 2:
        return {"available": False, "reason": f"bad sample row: {first!r}"}
    try:
        util_i = int(float(parts[0]))
        used_i = int(float(parts[1]))
    except ValueError as exc:
        return {"available": False, "reason": f"sample parse: {exc}"}
    return {
        "available": True,
        "utilization_pct": util_i,
        "vram_used_mib": used_i,
        "sampled_at": _utc_now(),
    }


__all__ = ["probe_gpu", "sample_gpu_utilization"]
