"""Tests for hermes3d.core.safety.bed_adhesion."""

from __future__ import annotations

import math

import pytest
from hermes3d.core.safety.bed_adhesion import (
    build_violation_payload,
    check_bed_adhesion_precondition,
)


def test_bed_adhesion_passes_at_target_offset_and_hot_bed() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.20,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=58.3,
        bed_target_c=60.0,
    )
    assert result.passed
    assert result.bed_min_c == pytest.approx(58.2)
    assert result.z_delta_mm == pytest.approx(0.0)


def test_z_offset_outside_tolerance_fails() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.27,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=60.0,
        bed_target_c=60.0,
    )
    assert not result.passed
    assert any("Z offset delta" in reason for reason in result.reasons)


def test_z_offset_boundaries_are_inclusive() -> None:
    low = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.15,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=60.0,
        bed_target_c=60.0,
    )
    high = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.25,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=60.0,
        bed_target_c=60.0,
    )
    just_over = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.2501,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=60.0,
        bed_target_c=60.0,
    )
    assert low.passed
    assert high.passed
    assert not just_over.passed


def test_negative_z_offsets_are_supported() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=-0.18,
        target_first_layer_z_offset_mm=-0.20,
        bed_actual_c=60.0,
        bed_target_c=60.0,
    )
    assert result.passed


def test_bed_below_temperature_fraction_fails() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.20,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=57.0,
        bed_target_c=60.0,
    )
    assert not result.passed
    assert any("below 97%" in reason for reason in result.reasons)


def test_bed_temperature_boundary_is_inclusive() -> None:
    exact = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.20,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=58.2,
        bed_target_c=60.0,
    )
    below = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.20,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=58.19,
        bed_target_c=60.0,
    )
    above = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.20,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=61.0,
        bed_target_c=60.0,
    )
    assert exact.passed
    assert not below.passed
    assert above.passed


def test_combined_failures_are_all_reported() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.12,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=40.0,
        bed_target_c=60.0,
    )
    assert not result.passed
    assert len(result.reasons) == 2


def test_custom_thresholds() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.24,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=54.0,
        bed_target_c=60.0,
        z_tolerance_mm=0.04,
        min_bed_fraction=0.90,
    )
    assert result.passed


def test_nonfinite_telemetry_fails_closed() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=math.nan,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=math.inf,
        bed_target_c=60.0,
    )
    assert not result.passed
    assert any("first_layer_z_offset_mm must be finite" in reason for reason in result.reasons)
    assert any("bed_actual_c must be finite" in reason for reason in result.reasons)


def test_already_homed_fails_as_too_late() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.20,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=60.0,
        bed_target_c=60.0,
        homed=True,
    )
    assert not result.passed
    assert any("before homing" in reason for reason in result.reasons)


def test_invalid_thresholds_raise() -> None:
    with pytest.raises(ValueError, match="z_tolerance"):
        check_bed_adhesion_precondition(
            first_layer_z_offset_mm=0.20,
            target_first_layer_z_offset_mm=0.20,
            bed_actual_c=60.0,
            bed_target_c=60.0,
            z_tolerance_mm=-0.01,
        )
    with pytest.raises(ValueError, match="z_tolerance"):
        check_bed_adhesion_precondition(
            first_layer_z_offset_mm=0.20,
            target_first_layer_z_offset_mm=0.20,
            bed_actual_c=60.0,
            bed_target_c=60.0,
            z_tolerance_mm=math.nan,
        )
    with pytest.raises(ValueError, match="min_bed_fraction"):
        check_bed_adhesion_precondition(
            first_layer_z_offset_mm=0.20,
            target_first_layer_z_offset_mm=0.20,
            bed_actual_c=60.0,
            bed_target_c=60.0,
            min_bed_fraction=1.2,
        )
    with pytest.raises(ValueError, match="min_bed_fraction"):
        check_bed_adhesion_precondition(
            first_layer_z_offset_mm=0.20,
            target_first_layer_z_offset_mm=0.20,
            bed_actual_c=60.0,
            bed_target_c=60.0,
            min_bed_fraction=math.inf,
        )


def test_violation_payload_shape() -> None:
    result = check_bed_adhesion_precondition(
        first_layer_z_offset_mm=0.30,
        target_first_layer_z_offset_mm=0.20,
        bed_actual_c=45.0,
        bed_target_c=60.0,
    )
    payload = build_violation_payload(job_id="job-9", printer_id="flsun_t1_a", result=result)
    assert payload["kind"] == "safety.violation"
    assert payload["gate"] == "safety.bed_adhesion_precondition"
    assert payload["job_id"] == "job-9"
    assert payload["printer_id"] == "flsun_t1_a"
    assert payload["result"]["passed"] is False
    assert payload["result"]["bed_min_c"] == pytest.approx(58.2)
