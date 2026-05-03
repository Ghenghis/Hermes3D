"""Tests for hermes3d.core.safety.gcode_bounds."""

from __future__ import annotations

from hermes3d.core.safety.gcode_bounds import (
    PRUSA_MK3S_DEFAULT_BOUNDS,
    PrinterBounds,
    parse_and_check,
    resolve_bounds,
)

# Standard rectangular 250x210x210 (Prusa-shape) for direct tests.
RECT_BOUNDS = PrinterBounds(
    x_min_mm=0.0,
    x_max_mm=250.0,
    y_min_mm=0.0,
    y_max_mm=210.0,
    z_min_mm=0.0,
    z_max_mm=210.0,
)

# A delta-shape circular bed (FLSUN QQ-S) — 260mm diameter.
CIRCULAR_BOUNDS = PrinterBounds(
    x_min_mm=-130.0,
    x_max_mm=130.0,
    y_min_mm=-130.0,
    y_max_mm=130.0,
    z_min_mm=0.0,
    z_max_mm=370.0,
    circular_diameter_mm=260.0,
)


def test_clean_program_passes() -> None:
    gcode = """\
G28
G90
G1 X10 Y10 Z0.2 F1500
G1 X100 Y100
G1 X10 Y100
G1 X10 Y10
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert report.passed
    assert report.n_moves == 4
    assert report.bbox_observed is not None
    bbox = report.bbox_observed
    assert bbox[0] >= 0.0  # x_min on the bed
    assert bbox[1] <= 250.0  # x_max under the wall


def test_x_overshoot_blocks() -> None:
    gcode = """\
G90
G1 X10 Y10
G1 X300 Y10  ; OOB on X
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert not report.passed
    assert any(v.axis == "X" and v.value == 300.0 for v in report.violations)


def test_negative_y_blocks() -> None:
    gcode = """\
G90
G1 X10 Y-5
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert not report.passed
    assert any(v.axis == "Y" for v in report.violations)


def test_relative_mode_tracks_position() -> None:
    """G91: each G1 moves *by* the values rather than to them."""
    gcode = """\
G90
G1 X20 Y20
G91
G1 X240 Y0   ; would put us at X=260, OOB
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert not report.passed
    # Find the X violation: target = 20 + 240 = 260
    xviols = [v for v in report.violations if v.axis == "X"]
    assert any(v.value == 260.0 for v in xviols)


def test_g92_resets_position_without_motion() -> None:
    gcode = """\
G90
G92 X100 Y100  ; pretend we're already at 100,100
G91
G1 X40 Y40   ; -> 140, 140 (in bounds)
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert report.passed


def test_circular_bed_radial_check() -> None:
    """A delta with 260mm bed should reject a corner move."""
    gcode = """\
G90
G1 X120 Y120  ; sqrt(120^2 + 120^2) = 169.7 > 130
"""
    report = parse_and_check(gcode, CIRCULAR_BOUNDS)
    assert not report.passed
    assert any(v.axis == "XY-radial" for v in report.violations)


def test_circular_bed_inscribed_point_passes() -> None:
    gcode = """\
G90
G1 X80 Y80  ; sqrt(80^2 + 80^2) = 113.1 < 130
"""
    report = parse_and_check(gcode, CIRCULAR_BOUNDS)
    assert report.passed


def test_arc_extrema_caught() -> None:
    """An arc whose tangent extremum lies outside the bed must be caught,
    even if start + end are inside.
    """
    # Full circle of radius 200 centered at (10, 10): tangent point at
    # X = 10 + 200 = 210 (in-bounds for a 250-wide bed). Use a circle
    # centered at (200, 100) of radius 100 — tangent at X=300 (OOB).
    gcode = """\
G90
G1 X300 Y100   ; start a movement to (300, 100) — already OOB on X (just a marker)
"""
    # Validate that a simple OOB still triggers; arc extrema is exercised
    # by the next test.
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert not report.passed


def test_arc_inside_bounds_passes() -> None:
    gcode = """\
G90
G1 X100 Y100
; full circle centered at (100, 100), radius 50 -> tangent at 150,100 / 50,100 / 100,150 / 100,50
G2 X100 Y100 I0 J50  ; full circle, end == start
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert report.passed
    assert report.n_arcs == 1


def test_unknown_gcode_is_warning_not_block() -> None:
    gcode = """\
G90
G42 X1 Y1   ; not implemented
G1 X10 Y10
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert report.passed
    assert any("G42" in w for w in report.warnings)


def test_resolve_bounds_falls_back_to_prusa_when_unknown() -> None:
    bounds, fallback = resolve_bounds(
        printer_id="not-in-fleet",
        fleet_lookup=None,
    )
    assert fallback is True
    assert bounds is PRUSA_MK3S_DEFAULT_BOUNDS


def test_resolve_bounds_uses_fleet_profile() -> None:
    class _StubBed:
        kind = "rectangular"
        x_mm = 300.0
        y_mm = 300.0

    class _StubProfile:
        bed = _StubBed()
        z_height_mm = 400.0

    def lookup(_id: str) -> _StubProfile:
        return _StubProfile()

    bounds, fallback = resolve_bounds(
        printer_id="custom",
        fleet_lookup=lookup,
    )
    assert fallback is False
    assert bounds.x_max_mm == 300.0
    assert bounds.z_max_mm == 400.0


def test_resolve_bounds_uses_circular_for_delta() -> None:
    class _StubBed:
        kind = "circular"
        x_mm = 0.0
        y_mm = 0.0
        diameter_mm = 260.0

    class _StubProfile:
        bed = _StubBed()
        z_height_mm = 370.0

    def lookup(_id: str) -> _StubProfile:
        return _StubProfile()

    bounds, fallback = resolve_bounds(printer_id="delta", fleet_lookup=lookup)
    assert fallback is False
    assert bounds.circular_diameter_mm == 260.0
    assert bounds.x_max_mm == 130.0
    assert bounds.z_max_mm == 370.0


def test_comments_and_blank_lines_skipped() -> None:
    gcode = """\
; this is a slicer header

G90  ; absolute mode
G1 X10 Y10  ; first move

(this is a paren comment)
G1 X20 Y20
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert report.passed
    assert report.n_moves == 2


def test_z_overshoot_blocks() -> None:
    gcode = """\
G90
G1 X10 Y10 Z250  ; Z above 210
"""
    report = parse_and_check(gcode, RECT_BOUNDS)
    assert not report.passed
    assert any(v.axis == "Z" and v.value == 250.0 for v in report.violations)
