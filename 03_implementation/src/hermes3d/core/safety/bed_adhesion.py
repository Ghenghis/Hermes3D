"""Bed-adhesion precondition gate.

Status: runnable
Gate ID: ``safety.bed_adhesion_precondition``

Checks the two pre-homing conditions most likely to cause first-layer
failure:

* first-layer Z offset must be within +/-0.05 mm of the profile target.
* bed temperature must be at least 97% of the profile target.

The module is pure-data and performs no printer I/O. Production callers
provide the live bed temperature and calibrated first-layer offset from
their printer/profile surface before starting homing or upload.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BedAdhesionCheckResult:
    """Result of checking first-layer and bed-temperature readiness."""

    passed: bool
    first_layer_z_offset_mm: float
    target_first_layer_z_offset_mm: float
    z_tolerance_mm: float
    bed_actual_c: float
    bed_target_c: float
    min_bed_fraction: float
    homed: bool | None = None
    reasons: list[str] = field(default_factory=list)

    @property
    def bed_min_c(self) -> float:
        return self.bed_target_c * self.min_bed_fraction

    @property
    def z_delta_mm(self) -> float:
        return self.first_layer_z_offset_mm - self.target_first_layer_z_offset_mm

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "first_layer_z_offset_mm": self.first_layer_z_offset_mm,
            "target_first_layer_z_offset_mm": self.target_first_layer_z_offset_mm,
            "z_delta_mm": self.z_delta_mm,
            "z_tolerance_mm": self.z_tolerance_mm,
            "bed_actual_c": self.bed_actual_c,
            "bed_target_c": self.bed_target_c,
            "bed_min_c": self.bed_min_c,
            "min_bed_fraction": self.min_bed_fraction,
            "homed": self.homed,
            "reasons": list(self.reasons),
        }


def check_bed_adhesion_precondition(
    *,
    first_layer_z_offset_mm: float,
    target_first_layer_z_offset_mm: float,
    bed_actual_c: float,
    bed_target_c: float,
    z_tolerance_mm: float = 0.05,
    min_bed_fraction: float = 0.97,
    homed: bool | None = None,
) -> BedAdhesionCheckResult:
    """Validate bed-adhesion preconditions before homing or upload."""
    reasons: list[str] = []

    if z_tolerance_mm < 0:
        raise ValueError("z_tolerance_mm must be non-negative")
    if not (0 < min_bed_fraction <= 1):
        raise ValueError("min_bed_fraction must be in (0, 1]")

    inputs = {
        "first_layer_z_offset_mm": first_layer_z_offset_mm,
        "target_first_layer_z_offset_mm": target_first_layer_z_offset_mm,
        "bed_actual_c": bed_actual_c,
        "bed_target_c": bed_target_c,
    }
    for label, value in inputs.items():
        if not math.isfinite(value):
            reasons.append(f"{label} must be finite")

    if homed is True:
        reasons.append("bed adhesion precondition must run before homing")

    if math.isfinite(bed_target_c) and bed_target_c <= 0:
        reasons.append(f"bed target {bed_target_c:.1f}C must be positive")

    z_delta = first_layer_z_offset_mm - target_first_layer_z_offset_mm
    if math.isfinite(z_delta) and abs(z_delta) - z_tolerance_mm > 1e-9:
        reasons.append(
            f"first-layer Z offset delta {z_delta:+.3f}mm exceeds +/-{z_tolerance_mm:.3f}mm"
        )

    bed_min_c = bed_target_c * min_bed_fraction
    if math.isfinite(bed_actual_c) and math.isfinite(bed_min_c) and bed_actual_c < bed_min_c:
        reasons.append(
            f"bed {bed_actual_c:.1f}C below {min_bed_fraction:.0%} of target "
            f"{bed_target_c:.1f}C ({bed_min_c:.1f}C)"
        )

    return BedAdhesionCheckResult(
        passed=not reasons,
        first_layer_z_offset_mm=float(first_layer_z_offset_mm),
        target_first_layer_z_offset_mm=float(target_first_layer_z_offset_mm),
        z_tolerance_mm=float(z_tolerance_mm),
        bed_actual_c=float(bed_actual_c),
        bed_target_c=float(bed_target_c),
        min_bed_fraction=float(min_bed_fraction),
        homed=homed,
        reasons=reasons,
    )


def build_violation_payload(
    *,
    job_id: str,
    printer_id: str,
    result: BedAdhesionCheckResult,
) -> dict[str, Any]:
    """Build the ``safety.violation`` payload for a failed adhesion check."""
    return {
        "kind": "safety.violation",
        "gate": "safety.bed_adhesion_precondition",
        "job_id": job_id,
        "printer_id": printer_id,
        "result": result.to_dict(),
    }


__all__ = [
    "BedAdhesionCheckResult",
    "build_violation_payload",
    "check_bed_adhesion_precondition",
]
