"""Cascade GPU + environment detection.

Order: nvidia-smi -> torch.cuda -> WMI -> safe-unavailable. Each step takes a
`runner` injection point so tests can mock subprocess without ever spawning
real processes (Phase 1 boundary: subprocess calls are strictly harmless and
mocked/test-gated).
"""

from __future__ import annotations

import datetime as _dt
import platform as _plat
import shutil
import subprocess
import sys
from collections.abc import Sequence
from typing import Callable

from .edition import resolve_edition
from .types import EnvReport, Vendor


def _platform_name() -> str:
    s = _plat.system().lower()
    if s.startswith("win"):
        return "windows"
    if s == "linux":
        return "linux"
    if s == "darwin":
        return "macos"
    return "other"


def _now_utc() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds")


# Runner type alias — tests pass a fake runner to bypass subprocess.
Runner = Callable[..., subprocess.CompletedProcess]


def _default_runner(args: Sequence[str], timeout: float = 5.0) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 -- shell=False, fixed args, short timeout, harmless flag
        list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )


def _try_nvidia_smi(runner: Runner = _default_runner) -> tuple[bool, dict]:
    if not shutil.which("nvidia-smi"):
        return False, {}
    try:
        r = runner(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            5.0,
        )
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False, {}
    if r.returncode != 0 or not (r.stdout or "").strip():
        return False, {}
    first = r.stdout.strip().splitlines()[0].split(",")
    if len(first) < 4:
        return False, {}
    name, total, free, drv = (s.strip() for s in first[:4])
    try:
        vram_total = int(total)
        vram_free = int(free)
    except ValueError:
        return False, {}
    return True, {
        "vendor": "NVIDIA",
        "gpu_name": name,
        "vram_total_mib": vram_total,
        "vram_free_mib": vram_free,
        "driver_version": drv,
        "cuda_available": True,
        "detection_source": "nvidia-smi",
    }


def _try_torch_cuda() -> tuple[bool, dict]:
    try:
        import torch  # type: ignore[import-untyped]
    except ImportError:
        return False, {}
    cuda = getattr(torch, "cuda", None)
    if cuda is None or not cuda.is_available():
        return False, {}
    try:
        idx = torch.cuda.current_device()
        return True, {
            "vendor": "NVIDIA",
            "gpu_name": torch.cuda.get_device_name(idx),
            "cuda_available": True,
            "detection_source": "torch.cuda",
        }
    except Exception:  # noqa: BLE001 -- torch error surface is broad; fall through to next step
        return False, {}


def _try_wmi(runner: Runner = _default_runner) -> tuple[bool, dict]:
    if _platform_name() != "windows":
        return False, {}
    try:
        r = runner(["wmic", "path", "win32_VideoController", "get", "name"], 5.0)
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False, {}
    lines = [
        ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip() and ln.strip() != "Name"
    ]
    if not lines:
        return False, {}
    name = lines[0]
    name_upper = name.upper()
    vendor: Vendor
    if "NVIDIA" in name_upper:
        vendor = "NVIDIA"
    elif "AMD" in name_upper or "RADEON" in name_upper:
        vendor = "AMD"
    elif "INTEL" in name_upper:
        vendor = "Intel"
    else:
        vendor = "unknown"
    return True, {
        "vendor": vendor,
        "gpu_name": name,
        "cuda_available": False,  # WMI doesn't tell us CUDA; nvidia-smi above would have
        "detection_source": "wmi",
    }


def _node_version(runner: Runner = _default_runner) -> str | None:
    if not shutil.which("node"):
        return None
    try:
        r = runner(["node", "--version"], 3.0)
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip() or None


def _shells() -> tuple[str, ...]:
    return tuple(sh for sh in ("bash", "pwsh", "cmd") if shutil.which(sh))


def detect_env(runner: Runner | None = None) -> EnvReport:
    """Run the cascade and return a fully-populated EnvReport.

    `runner` is the subprocess runner; pass a fake one in tests to avoid
    spawning real processes. Defaults to a 5s-timeout `subprocess.run`.
    """
    run = runner or _default_runner

    base: dict = {
        "timestamp_utc": _now_utc(),
        "platform": _platform_name(),
        "python_version": sys.version.split()[0],
        "node_version": _node_version(run),
        "shells": _shells(),
        "vendor": "none",
        "detection_source": "unavailable",
        "cuda_available": False,
        "gpu_name": None,
        "vram_total_mib": None,
        "vram_free_mib": None,
        "driver_version": None,
    }

    # Cascade in order — first hit wins.
    for step in (
        lambda: _try_nvidia_smi(run),
        _try_torch_cuda,
        lambda: _try_wmi(run),
    ):
        ok, data = step()
        if ok:
            base.update(data)
            break

    base["edition"] = resolve_edition(base["platform"], base["vendor"], base["cuda_available"])
    return EnvReport(**base)
