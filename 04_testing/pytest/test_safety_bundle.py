"""End-to-end-ish test for hermes3d.core.safety.run_all_safety_gates.

Exercises the public ``run_all_safety_gates`` entry point and the
``ALL_SAFETY_GATE_IDS`` registry. The orchestrator wiring (event_manager
emission) is tested separately in the integration layer; this file
verifies the pre-flight bundle's pass/fail/skip semantics.
"""

from __future__ import annotations

from hermes3d.core.safety import (
    ALL_SAFETY_GATE_IDS,
    GATE_EMERGENCY_STOP_TIMING,
    GATE_GCODE_BOUNDS,
    GATE_MATERIAL_WINDOW,
    GATE_THERMAL_RUNAWAY,
    KlipperMockSimulator,
    PrinterBounds,
    SafetyBundle,
    TemperatureSample,
    run_all_safety_gates,
)

CLEAN_GCODE = """\
G28
G90
G1 X10 Y10 Z0.2 F1500
G1 X100 Y100
"""

OOB_GCODE = """\
G90
G1 X1000 Y10
"""


def _bounds() -> PrinterBounds:
    return PrinterBounds(
        x_min_mm=0.0,
        x_max_mm=250.0,
        y_min_mm=0.0,
        y_max_mm=210.0,
        z_max_mm=210.0,
    )


def test_all_gate_ids_registered() -> None:
    assert GATE_THERMAL_RUNAWAY in ALL_SAFETY_GATE_IDS
    assert GATE_EMERGENCY_STOP_TIMING in ALL_SAFETY_GATE_IDS
    assert GATE_GCODE_BOUNDS in ALL_SAFETY_GATE_IDS
    assert GATE_MATERIAL_WINDOW in ALL_SAFETY_GATE_IDS
    assert len(ALL_SAFETY_GATE_IDS) == 4


def test_all_pass_when_inputs_clean() -> None:
    sim = KlipperMockSimulator(response_delay_s=0.040)
    samples = [TemperatureSample(ts=t, temperature_c=200.0, target_c=200.0) for t in range(0, 6)]
    bundle: SafetyBundle = run_all_safety_gates(
        job_id="j",
        printer_id="p",
        gcode_text=CLEAN_GCODE,
        bounds=_bounds(),
        material="PLA",
        nozzle_c=205.0,
        bed_c=60.0,
        thermal_samples=samples,
        emergency_stop_transport=sim,
    )
    assert bundle.passed
    assert sorted(bundle.passed_gates) == sorted(ALL_SAFETY_GATE_IDS)
    assert bundle.skipped_gates == []


def test_oob_gcode_violates() -> None:
    bundle = run_all_safety_gates(
        job_id="j",
        printer_id="p",
        gcode_text=OOB_GCODE,
        bounds=_bounds(),
    )
    assert not bundle.passed
    assert any(v["gate"] == GATE_GCODE_BOUNDS for v in bundle.violations)


def test_unknown_material_violates() -> None:
    bundle = run_all_safety_gates(
        job_id="j",
        printer_id="p",
        material="Unobtanium",
        nozzle_c=200.0,
        bed_c=60.0,
    )
    assert not bundle.passed
    assert any(v["gate"] == GATE_MATERIAL_WINDOW for v in bundle.violations)


def test_skips_record_correctly() -> None:
    bundle = run_all_safety_gates(job_id="j", printer_id="p")
    assert bundle.passed  # nothing failed because nothing ran
    assert sorted(bundle.skipped_gates) == sorted(ALL_SAFETY_GATE_IDS)


def test_thermal_runaway_violation_recorded_in_bundle() -> None:
    samples = [
        TemperatureSample(ts=float(i), temperature_c=216.0, target_c=200.0) for i in range(7)
    ]
    bundle = run_all_safety_gates(
        job_id="j",
        printer_id="p",
        thermal_samples=samples,
    )
    assert not bundle.passed
    assert any(v["gate"] == GATE_THERMAL_RUNAWAY for v in bundle.violations)


def test_emergency_stop_timing_failure_recorded_in_bundle() -> None:
    sim = KlipperMockSimulator(fail_to_respond=True)
    bundle = run_all_safety_gates(
        job_id="j",
        printer_id="p",
        emergency_stop_transport=sim,
        emergency_stop_budget_ms=200.0,
    )
    assert not bundle.passed
    assert any(v["gate"] == GATE_EMERGENCY_STOP_TIMING for v in bundle.violations)
