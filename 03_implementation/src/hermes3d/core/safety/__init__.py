"""Hermes3D 3D-printing safety gates.

Public package surface for the four P1 safety gates:

  - :mod:`thermal_runaway`             (gate ``safety.thermal_runaway_detection``)
  - :mod:`emergency_stop`              (gate ``safety.emergency_stop_timing``)
  - :mod:`gcode_bounds`                (gate ``safety.gcode_bounds_precondition``)
  - :mod:`material_window`             (gate ``safety.material_temperature_window``)

Each safety check is meant to run as a pre-flight assertion before
``submit_print_job``. Failures emit ``safety.violation`` events to the
evidence ledger via the existing event-manager bridge in
``hermes3d.core.agents.orchestrator``.

Wiring contract:

    from hermes3d.core.safety import run_all_safety_gates

    bundle = run_all_safety_gates(
        gcode_text=...,
        gcode_bounds_inputs=...,
        material_inputs=...,
        thermal_trace=None,           # live monitoring runs separately
        emergency_stop_transport=...,  # optional; set None to skip timing gate
    )
    if not bundle.passed:
        for violation in bundle.violations:
            event_manager.emit("safety.violation", violation)
        raise PreflightBlocked(bundle)

The module never imports the orchestrator or event_manager directly —
the surface is pure-data so the orchestrator stays the only owner of
side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .emergency_stop import (
    EmergencyStopTransport,
    HaltEvidence,
    HaltOutcome,
    KlipperMockSimulator,
    assert_within_budget,
    measure_m112_round_trip,
)
from .emergency_stop import (
    build_violation_payload as _emergency_stop_payload,
)
from .gcode_bounds import (
    PRUSA_MK3S_DEFAULT_BOUNDS,
    GcodeBoundsReport,
    PrinterBounds,
    parse_and_check,
    resolve_bounds,
)
from .gcode_bounds import (
    build_violation_payload as _gcode_bounds_payload,
)
from .material_window import (
    MaterialCheckResult,
    MaterialDB,
    MaterialWindow,
    check_material_window,
    load_material_db,
)
from .material_window import (
    build_violation_payload as _material_payload,
)
from .thermal_runaway import (
    EmergencyStopEvent,
    TemperatureSample,
    ThermalRunawayDetector,
    TripReason,
    replay_trace,
)
from .thermal_runaway import (
    build_violation_payload as _thermal_payload,
)

# Canonical gate IDs — must match the brief and the gate-runner registry.
GATE_THERMAL_RUNAWAY = "safety.thermal_runaway_detection"
GATE_EMERGENCY_STOP_TIMING = "safety.emergency_stop_timing"
GATE_GCODE_BOUNDS = "safety.gcode_bounds_precondition"
GATE_MATERIAL_WINDOW = "safety.material_temperature_window"

ALL_SAFETY_GATE_IDS = (
    GATE_THERMAL_RUNAWAY,
    GATE_EMERGENCY_STOP_TIMING,
    GATE_GCODE_BOUNDS,
    GATE_MATERIAL_WINDOW,
)


@dataclass
class SafetyBundle:
    """Aggregated result of running all safety gates pre-flight."""

    job_id: str
    printer_id: str
    violations: list[dict[str, Any]] = field(default_factory=list)
    passed_gates: list[str] = field(default_factory=list)
    skipped_gates: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "printer_id": self.printer_id,
            "passed": self.passed,
            "violations": list(self.violations),
            "passed_gates": list(self.passed_gates),
            "skipped_gates": list(self.skipped_gates),
        }


def run_all_safety_gates(
    *,
    job_id: str,
    printer_id: str,
    gcode_text: str | None = None,
    bounds: PrinterBounds | None = None,
    material: str | None = None,
    nozzle_c: float | None = None,
    bed_c: float | None = None,
    material_db: MaterialDB | None = None,
    thermal_samples: list[TemperatureSample] | None = None,
    emergency_stop_transport: EmergencyStopTransport | None = None,
    emergency_stop_budget_ms: float = 200.0,
    env: dict[str, str] | None = None,
) -> SafetyBundle:
    """Run all four safety gates as pre-flight assertions.

    Each gate is independent: missing inputs cause that gate to be
    *skipped* (not failed), so the bundle can be used in dry-run paths
    that exercise only a subset.

    The emergency-stop timing gate is OPTIONAL by default — pass an
    :class:`EmergencyStopTransport` (typically a :class:`KlipperMockSimulator`
    or a Moonraker-backed real client) to enable it.
    """
    bundle = SafetyBundle(job_id=job_id, printer_id=printer_id)

    # 1. gcode bounds
    if gcode_text is not None and bounds is not None:
        report = parse_and_check(gcode_text, bounds)
        if report.passed:
            bundle.passed_gates.append(GATE_GCODE_BOUNDS)
        else:
            bundle.violations.append(
                _gcode_bounds_payload(job_id=job_id, printer_id=printer_id, report=report)
            )
    else:
        bundle.skipped_gates.append(GATE_GCODE_BOUNDS)

    # 2. material window
    if material is not None and nozzle_c is not None and bed_c is not None:
        result = check_material_window(
            material=material,
            nozzle_c=nozzle_c,
            bed_c=bed_c,
            db=material_db,
            env=env,
        )
        if result.passed:
            bundle.passed_gates.append(GATE_MATERIAL_WINDOW)
        else:
            bundle.violations.append(
                _material_payload(job_id=job_id, printer_id=printer_id, result=result)
            )
    else:
        bundle.skipped_gates.append(GATE_MATERIAL_WINDOW)

    # 3. thermal runaway (replay trace if provided; live loop is wired
    #    into the orchestrator's monitoring thread separately).
    if thermal_samples is not None:
        evt, _ = replay_trace(thermal_samples)
        if evt is None:
            bundle.passed_gates.append(GATE_THERMAL_RUNAWAY)
        else:
            t0 = thermal_samples[0].ts if thermal_samples else 0.0
            bundle.violations.append(
                _thermal_payload(
                    job_id=job_id,
                    printer_id=printer_id,
                    event=evt,
                    detection_latency_s=evt.ts - t0,
                )
            )
    else:
        bundle.skipped_gates.append(GATE_THERMAL_RUNAWAY)

    # 4. emergency-stop timing
    if emergency_stop_transport is not None:
        evidence = measure_m112_round_trip(
            emergency_stop_transport,
            timeout_s=emergency_stop_budget_ms / 1000.0,
        )
        if (
            evidence.outcome is HaltOutcome.HALTED
            and evidence.elapsed_ms <= emergency_stop_budget_ms
        ):
            bundle.passed_gates.append(GATE_EMERGENCY_STOP_TIMING)
        else:
            bundle.violations.append(
                _emergency_stop_payload(
                    job_id=job_id,
                    printer_id=printer_id,
                    evidence=evidence,
                    budget_ms=emergency_stop_budget_ms,
                )
            )
    else:
        bundle.skipped_gates.append(GATE_EMERGENCY_STOP_TIMING)

    return bundle


__all__ = [
    "ALL_SAFETY_GATE_IDS",
    "EmergencyStopEvent",
    "EmergencyStopTransport",
    "GATE_EMERGENCY_STOP_TIMING",
    "GATE_GCODE_BOUNDS",
    "GATE_MATERIAL_WINDOW",
    "GATE_THERMAL_RUNAWAY",
    "GcodeBoundsReport",
    "HaltEvidence",
    "HaltOutcome",
    "KlipperMockSimulator",
    "MaterialCheckResult",
    "MaterialDB",
    "MaterialWindow",
    "PRUSA_MK3S_DEFAULT_BOUNDS",
    "PrinterBounds",
    "SafetyBundle",
    "TemperatureSample",
    "ThermalRunawayDetector",
    "TripReason",
    "assert_within_budget",
    "check_material_window",
    "load_material_db",
    "measure_m112_round_trip",
    "parse_and_check",
    "replay_trace",
    "resolve_bounds",
    "run_all_safety_gates",
]
