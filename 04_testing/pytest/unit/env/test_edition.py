"""Phase 1 Task 18 — edition resolution rule."""

from __future__ import annotations

from hermes3d.env.edition import resolve_edition


def test_windows_with_nvidia_is_desktop_worker():
    assert resolve_edition("windows", "NVIDIA", True) == "desktop_gpu_worker"


def test_linux_without_cuda_is_vps():
    assert resolve_edition("linux", "none", False) == "ubuntu_vps_control_server"
    assert resolve_edition("linux", "AMD", False) == "ubuntu_vps_control_server"


def test_linux_with_cuda_is_desktop_worker():
    assert resolve_edition("linux", "NVIDIA", True) == "desktop_gpu_worker"


def test_macos_is_blocked():
    assert resolve_edition("macos", "none", False) == "blocked_no_gpu"
    assert resolve_edition("macos", "AMD", False) == "blocked_no_gpu"


def test_windows_without_nvidia_is_blocked():
    assert resolve_edition("windows", "AMD", False) == "blocked_no_gpu"
    assert resolve_edition("windows", "Intel", False) == "blocked_no_gpu"
    assert resolve_edition("windows", "none", False) == "blocked_no_gpu"


def test_unknown_platform_is_blocked():
    assert resolve_edition("other", "NVIDIA", True) == "blocked_no_gpu"
