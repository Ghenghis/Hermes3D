"""Adapter manifest capability guard for Phase 3.1."""

from __future__ import annotations

from dataclasses import dataclass, field

WRITE_CAPABILITIES = frozenset(
    {
        "firmware_restart",
        "gcode_send",
        "home_axis",
        "move_axis",
        "print_cancel",
        "print_pause",
        "print_start",
        "set_temperature",
        "upload_file",
    }
)
PHASE3_READONLY_CAPABILITIES = {
    "planner.plan": {"phase": 3, "dangerous": False},
    "llm.complete": {"phase": 3, "dangerous": False},
    "provider.probe": {"phase": 3, "dangerous": False},
    "gen3d.generate": {"phase": 3, "dangerous": False},
}


class AdapterRegistrationError(ValueError):
    """Raised when an adapter manifest violates the active phase contract."""


@dataclass(frozen=True)
class AdapterManifest:
    adapter_id: str
    display_name: str
    phase: int
    capabilities: frozenset[str] = field(default_factory=frozenset)
    read_only: bool = True


def register_adapter(manifest: AdapterManifest, *, current_phase: int = 3) -> AdapterManifest:
    if not manifest.adapter_id:
        raise AdapterRegistrationError("adapter_id is required")
    if not manifest.display_name:
        raise AdapterRegistrationError("display_name is required")
    if current_phase < 4 and _contains_write_capability(manifest):
        raise AdapterRegistrationError("write capabilities are refused before Phase 4")
    if current_phase < 4 and not manifest.read_only:
        raise AdapterRegistrationError("non-read-only manifests are refused before Phase 4")
    return manifest


def is_write_capability(capability: str) -> bool:
    return capability in WRITE_CAPABILITIES


def capability_phase(capability: str) -> int | None:
    metadata = PHASE3_READONLY_CAPABILITIES.get(capability)
    if metadata is None:
        return None
    return int(metadata["phase"])


def is_dangerous_capability(capability: str) -> bool:
    metadata = PHASE3_READONLY_CAPABILITIES.get(capability)
    if metadata is None:
        return is_write_capability(capability)
    return bool(metadata["dangerous"])


def _contains_write_capability(manifest: AdapterManifest) -> bool:
    return any(is_write_capability(capability) for capability in manifest.capabilities)
