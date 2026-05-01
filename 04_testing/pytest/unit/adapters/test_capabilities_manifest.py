"""Phase 3.1-B adapter manifest refusal rules."""

from __future__ import annotations

import pytest
from hermes3d.adapters._capabilities import (
    AdapterManifest,
    AdapterRegistrationError,
    is_write_capability,
    register_adapter,
)


def test_read_only_manifest_registers_before_phase_4():
    manifest = AdapterManifest(
        adapter_id="moonraker-readonly",
        display_name="Moonraker Read Only",
        phase=3,
        capabilities=frozenset({"read_only"}),
    )

    assert register_adapter(manifest, current_phase=3) is manifest


def test_write_capability_manifest_is_refused_before_phase_4():
    manifest = AdapterManifest(
        adapter_id="moonraker-write",
        display_name="Moonraker Write",
        phase=3,
        capabilities=frozenset({"read_only", "print_start"}),
    )

    with pytest.raises(AdapterRegistrationError, match="before Phase 4"):
        register_adapter(manifest, current_phase=3)


def test_phase_4_write_manifest_is_refused_during_phase_3():
    manifest = AdapterManifest(
        adapter_id="moonraker-phase4",
        display_name="Moonraker Phase 4",
        phase=4,
        capabilities=frozenset({"gcode_send"}),
    )

    with pytest.raises(AdapterRegistrationError, match="before Phase 4"):
        register_adapter(manifest, current_phase=3)


def test_write_manifest_registers_when_current_phase_is_4():
    manifest = AdapterManifest(
        adapter_id="moonraker-phase4",
        display_name="Moonraker Phase 4",
        phase=4,
        capabilities=frozenset({"gcode_send"}),
        read_only=False,
    )

    assert register_adapter(manifest, current_phase=4) is manifest
    assert is_write_capability("gcode_send") is True
