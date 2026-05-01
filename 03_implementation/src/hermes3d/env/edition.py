"""Edition resolution rule per DUAL_EDITION_ENVIRONMENT_BASELINE.md §4."""

from __future__ import annotations

from .types import Edition, Vendor


def resolve_edition(platform: str, vendor: Vendor, cuda_available: bool) -> Edition:
    """Return the dual-edition this host belongs to.

    Rules (per the Phase 0 baseline doc):
    - Windows + NVIDIA       -> desktop_gpu_worker
    - Linux  + no CUDA       -> ubuntu_vps_control_server
    - Linux  + CUDA          -> desktop_gpu_worker (Linux GPU box, secondary)
    - everything else        -> blocked_no_gpu (Mac, Windows-without-NVIDIA, etc.)
    """
    if platform == "windows" and vendor == "NVIDIA":
        return "desktop_gpu_worker"
    if platform == "linux" and not cuda_available:
        return "ubuntu_vps_control_server"
    if platform == "linux" and cuda_available:
        return "desktop_gpu_worker"
    return "blocked_no_gpu"
