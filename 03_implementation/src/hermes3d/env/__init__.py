"""Hermes3D environment detection (Phase 1 — read-only, no installs).

Detects OS, Python/Node versions, GPU presence + VRAM (when nvidia-smi is
available), CUDA hints, and resolves the dual-edition rule
(desktop_gpu_worker vs ubuntu_vps_control_server vs blocked_no_gpu).

All detection is read-only and safe-on-any-host: no installs, no mutations,
no network calls. Subprocess calls (nvidia-smi, node --version, wmic) use
short timeouts and never raise on failure.
"""
