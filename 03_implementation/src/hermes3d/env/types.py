"""Typed env-detection report."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Edition = Literal[
    "desktop_gpu_worker",
    "ubuntu_vps_control_server",
    "blocked_no_gpu",
]
Vendor = Literal["NVIDIA", "AMD", "Intel", "none", "unknown"]
DetectionSource = Literal["nvidia-smi", "torch.cuda", "wmi", "unavailable"]


@dataclass(frozen=True)
class EnvReport:
    timestamp_utc: str
    platform: str  # "windows" | "linux" | "macos" | "other"
    python_version: str
    edition: Edition
    vendor: Vendor
    detection_source: DetectionSource
    cuda_available: bool
    gpu_name: str | None = None
    vram_total_mib: int | None = None
    vram_free_mib: int | None = None
    driver_version: str | None = None
    node_version: str | None = None
    shells: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        d = asdict(self)
        # tuples -> lists for JSON friendliness
        d["shells"] = list(self.shells)
        return d
