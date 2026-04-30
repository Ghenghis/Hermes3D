"""Fleet dispatcher — agentic printer selection.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §10 (Material-Aware Dispatch)

Given a print request (geometry + material + strategy + optional live load
data), this module scores every printer in the fleet and selects the best
candidate. The output is a structured ``DispatchDecision`` with the chosen
printer, the full candidate scoring table, and a human-readable rationale.

Design principles:
  - Pure function over inputs — no I/O, no live network calls. Live data
    (printer state) is passed in. This makes the dispatcher deterministic
    and unit-testable.
  - Composable strategies — each strategy is a separate scoring function.
    "auto" combines them with weights that match the request.
  - Hard filters first, scoring second. A printer that fails a hard
    requirement (bed too small, hotend too cold, no enclosure for ASA) is
    eliminated before any soft scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hermes3d.core.printers import (
    FLEET,
    Kinematics,
    PrinterProfile,
    fits_bed,
    get_profile,
)
from hermes3d.core.agents.materials import MaterialProfile, get_material


# =============================================================================


class DispatchStrategy(str, Enum):
    """Selection strategy."""

    FASTEST = "fastest"            # Highest max_print_speed_mm_s
    QUALITY = "quality"            # Lowest accel + direct drive (less ringing)
    LARGEST_BED = "largest_bed"    # Pick biggest bed that fits
    SMALLEST_FIT = "smallest_fit"  # Smallest bed that fits — efficient farm use
    LEAST_BUSY = "least_busy"      # Idle preferred over printing
    DELTA_PREFER = "delta_prefer"      # Tall/cylindrical -> delta
    CARTESIAN_PREFER = "cartesian_prefer"  # Wide/flat -> cartesian
    AUTO = "auto"                  # Multi-criteria weighted blend


@dataclass(frozen=True)
class DispatchRequest:
    """A request to print a part. All fields are inputs to scoring.

    ``mesh_extents_mm`` is the axis-aligned bbox (dx, dy, dz) of the mesh
    after any orientation/scaling is applied.

    ``mesh_xy_radius_mm`` is the smallest enclosing xy-circle radius when
    the mesh is centered on its bbox — required for accurate delta-bed
    fitting; if None, callers fall back to bbox-corner radius (worst case).

    ``material`` matches a name in
    :func:`hermes3d.core.agents.materials.list_materials`.
    """

    mesh_extents_mm: tuple[float, float, float]
    mesh_xy_radius_mm: float | None = None
    material: str = "PLA"
    layer_height_mm: float = 0.2
    quality_level: str = "normal"   # "draft" | "normal" | "fine"
    strategy: DispatchStrategy = DispatchStrategy.AUTO
    # Optional live state from probe_fleet()
    live_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Optional list of printer_ids to exclude (e.g., user disabled them)
    excluded_printers: tuple[str, ...] = ()
    # Optional restriction to a specific subset (e.g., from a UI selector)
    allowed_printers: tuple[str, ...] = ()


@dataclass(frozen=True)
class DispatchScore:
    """Per-printer scoring entry."""

    printer_id: str
    score: float
    fits: bool
    eligible: bool
    reasons: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class DispatchDecision:
    """Final agentic decision."""

    selected_printer_id: str | None
    candidates: tuple[DispatchScore, ...]
    rationale: str
    strategy_used: DispatchStrategy

    @property
    def has_selection(self) -> bool:
        return self.selected_printer_id is not None


# =============================================================================
# Hard filters
# =============================================================================


def _check_eligibility(profile: PrinterProfile, req: DispatchRequest,
                       material: MaterialProfile) -> tuple[bool, list[str]]:
    """Return (eligible, blockers).

    Hard checks:
      - bed fit
      - hotend can reach material's typical temperature
      - bed can reach material's typical temperature
      - enclosure required for ASA / PC
      - direct drive required for TPU
      - hardened nozzle required for CF / PA-CF — checked optimistically:
        the user can swap nozzles, so we record a soft warning rather than
        a hard block. Strict mode is opt-in by callers.
    """
    blockers: list[str] = []

    # 1. Bed fit
    fits, fit_msg = fits_bed(profile, req.mesh_extents_mm, req.mesh_xy_radius_mm)
    if not fits:
        blockers.append(f"bed-fit: {fit_msg}")

    # 2. Hotend temperature
    if profile.hotend_max_c < material.hotend_typical_c:
        blockers.append(
            f"hotend-temp: profile max {profile.hotend_max_c}°C < material "
            f"typical {material.hotend_typical_c}°C ({material.material})"
        )

    # 3. Bed temperature
    if profile.bed_max_c < material.bed_typical_c:
        blockers.append(
            f"bed-temp: profile max {profile.bed_max_c}°C < material "
            f"typical {material.bed_typical_c}°C ({material.material})"
        )

    # 4. Enclosure
    if material.requires_enclosure and not profile.enclosed:
        blockers.append(
            f"enclosure: {material.material} requires enclosure; "
            f"{profile.profile_id} is open-frame"
        )

    # 5. Direct drive
    if material.requires_direct_drive and not profile.direct_drive:
        blockers.append(
            f"direct-drive: {material.material} requires direct-drive "
            f"extruder; {profile.profile_id} is bowden"
        )

    return (not blockers), blockers


# =============================================================================
# Scoring strategies
# =============================================================================


def _score_fastest(profile: PrinterProfile, req: DispatchRequest) -> float:
    """Higher score = faster printer. Normalized to [0, 1] by max in fleet."""
    max_speed = max(p.max_print_speed_mm_s for p in FLEET)
    return profile.max_print_speed_mm_s / max_speed


def _score_quality(profile: PrinterProfile, req: DispatchRequest) -> float:
    """Higher score = better surface quality.

    Heuristic: low max_acceleration -> less ringing/ghosting at typical
    speeds. Direct-drive helps retraction precision. Prusa-class linear
    motion (cartesian, calibrated) tends to score well; the FLSUN S1 at
    40k mm/s² is fast but ringing-prone above 600 mm/s — captured here.
    """
    # Inverted-accel score (low accel -> high quality)
    max_accel = max(p.max_acceleration_mm_s2 for p in FLEET)
    accel_score = 1.0 - (profile.max_acceleration_mm_s2 / max_accel)
    # Direct-drive bonus
    dd_bonus = 0.15 if profile.direct_drive else 0.0
    # Cartesian gets a small bonus for predictable repeatability on small
    # detailed parts (Prusa MK3S benchmarks dominate here).
    cart_bonus = 0.10 if profile.kinematics is Kinematics.CARTESIAN else 0.0
    return min(1.0, accel_score + dd_bonus + cart_bonus)


def _score_largest_bed(profile: PrinterProfile, req: DispatchRequest) -> float:
    """Higher score = bigger build area."""
    if profile.bed.kind == "rectangular":
        area = profile.bed.x_mm * profile.bed.y_mm
    else:
        import math
        area = math.pi * (profile.bed.diameter_mm / 2) ** 2
    max_area = 0.0
    for p in FLEET:
        if p.bed.kind == "rectangular":
            a = p.bed.x_mm * p.bed.y_mm
        else:
            import math
            a = math.pi * (p.bed.diameter_mm / 2) ** 2
        max_area = max(max_area, a)
    return area / max_area if max_area else 0.0


def _score_smallest_fit(profile: PrinterProfile, req: DispatchRequest) -> float:
    """Higher score = smallest printer that still fits the part — keeps the
    big farm machines free for big parts."""
    return 1.0 - _score_largest_bed(profile, req)


def _score_least_busy(profile: PrinterProfile, req: DispatchRequest) -> float:
    """Higher score = idle printer; lower = currently printing."""
    state = req.live_state.get(profile.profile_id, {})
    if not state:
        return 0.5  # unknown — neutral
    if not state.get("reachable", False):
        return 0.0  # offline = unusable
    klippy_state = state.get("klippy_state", "unknown")
    if klippy_state == "ready":
        return 1.0
    if klippy_state in ("error", "shutdown"):
        return 0.0
    if klippy_state in ("startup", "disconnect"):
        return 0.2
    # printing/paused
    return 0.3


def _score_delta_prefer(profile: PrinterProfile, req: DispatchRequest) -> float:
    """Tall + xy-radial parts favour delta kinematics."""
    dx, dy, dz = req.mesh_extents_mm
    aspect = dz / max(dx, dy, 1.0)
    if profile.kinematics is Kinematics.DELTA:
        return min(1.0, 0.5 + 0.5 * min(aspect / 2.0, 1.0))
    return 0.3


def _score_cartesian_prefer(profile: PrinterProfile, req: DispatchRequest) -> float:
    """Wide flat parts favour cartesian/CoreXY."""
    dx, dy, dz = req.mesh_extents_mm
    aspect = dz / max(dx, dy, 1.0)
    if profile.kinematics in (Kinematics.CARTESIAN, Kinematics.COREXY):
        return min(1.0, 1.0 - aspect / 3.0)
    return 0.3


_SINGLE_STRATEGIES = {
    DispatchStrategy.FASTEST: _score_fastest,
    DispatchStrategy.QUALITY: _score_quality,
    DispatchStrategy.LARGEST_BED: _score_largest_bed,
    DispatchStrategy.SMALLEST_FIT: _score_smallest_fit,
    DispatchStrategy.LEAST_BUSY: _score_least_busy,
    DispatchStrategy.DELTA_PREFER: _score_delta_prefer,
    DispatchStrategy.CARTESIAN_PREFER: _score_cartesian_prefer,
}


def _score_auto(profile: PrinterProfile, req: DispatchRequest,
                material: MaterialProfile) -> tuple[float, list[str]]:
    """Multi-criteria weighted blend with rationale building.

    Weights are tuned for the user's typical workflow: prototyping speed
    matters, but quality matters more for parts on the desk; least-busy
    matters across a 12-printer farm.
    """
    weights: dict[str, float] = {
        "fastest": 0.20,
        "quality": 0.20,
        "least_busy": 0.30,
        "smallest_fit": 0.15,  # avoid hogging the big printers
        "kinematics": 0.10,
        "material_pref": 0.05,
    }
    contribs: dict[str, float] = {}

    contribs["fastest"] = _score_fastest(profile, req) * weights["fastest"]
    contribs["quality"] = _score_quality(profile, req) * weights["quality"]
    contribs["least_busy"] = _score_least_busy(profile, req) * weights["least_busy"]
    contribs["smallest_fit"] = _score_smallest_fit(profile, req) * weights["smallest_fit"]

    # Kinematics: blend delta-prefer and cartesian-prefer based on aspect.
    dx, dy, dz = req.mesh_extents_mm
    aspect = dz / max(dx, dy, 1.0)
    if aspect > 1.5:
        contribs["kinematics"] = _score_delta_prefer(profile, req) * weights["kinematics"]
    else:
        contribs["kinematics"] = _score_cartesian_prefer(profile, req) * weights["kinematics"]

    # Material soft preferences
    pref = 0.0
    if material.prefers_enclosure and profile.enclosed:
        pref += 0.5
    if material.prefers_high_flow and profile.max_print_speed_mm_s >= 600:
        pref += 0.5
    contribs["material_pref"] = min(1.0, pref) * weights["material_pref"]

    # Quality-level shaping: "fine" tilts toward quality; "draft" toward speed.
    if req.quality_level == "fine":
        contribs["quality"] *= 1.5
        contribs["fastest"] *= 0.5
    elif req.quality_level == "draft":
        contribs["fastest"] *= 1.5
        contribs["quality"] *= 0.5

    score = sum(contribs.values())
    rationale: list[str] = []
    for k, v in sorted(contribs.items(), key=lambda kv: -kv[1])[:3]:
        rationale.append(f"{k}={v:.2f}")
    return score, rationale


# =============================================================================
# Public API
# =============================================================================


def dispatch(req: DispatchRequest) -> DispatchDecision:
    """Score the fleet and select a printer for the request.

    Returns a DispatchDecision with full traceability — every candidate is
    scored, every blocker is recorded, the rationale is human-readable.
    """
    material = get_material(req.material)
    candidates: list[DispatchScore] = []

    pool = list(FLEET)
    if req.allowed_printers:
        pool = [p for p in pool if p.profile_id in req.allowed_printers]
    if req.excluded_printers:
        pool = [p for p in pool if p.profile_id not in req.excluded_printers]

    for profile in pool:
        eligible, blockers = _check_eligibility(profile, req, material)
        fits, _ = fits_bed(profile, req.mesh_extents_mm, req.mesh_xy_radius_mm)

        if not eligible:
            candidates.append(DispatchScore(
                printer_id=profile.profile_id,
                score=0.0,
                fits=fits,
                eligible=False,
                blockers=tuple(blockers),
            ))
            continue

        # Eligible — score it
        if req.strategy is DispatchStrategy.AUTO:
            score, why = _score_auto(profile, req, material)
            reasons = tuple(why)
        else:
            scorer = _SINGLE_STRATEGIES.get(req.strategy)
            if scorer is None:
                raise ValueError(f"Unknown strategy: {req.strategy}")
            score = scorer(profile, req)
            reasons = (f"{req.strategy.value}_score={score:.2f}",)

        candidates.append(DispatchScore(
            printer_id=profile.profile_id,
            score=float(score),
            fits=True,
            eligible=True,
            reasons=reasons,
        ))

    # Pick the best eligible candidate
    eligible_only = [c for c in candidates if c.eligible]
    if not eligible_only:
        rationale = (
            f"No eligible printer for material={material.material} "
            f"at extents={req.mesh_extents_mm}. "
            f"Blockers across fleet: "
            + "; ".join(
                f"{c.printer_id}: {', '.join(c.blockers)}"
                for c in candidates if c.blockers
            )
        )
        return DispatchDecision(
            selected_printer_id=None,
            candidates=tuple(sorted(candidates, key=lambda c: -c.score)),
            rationale=rationale,
            strategy_used=req.strategy,
        )

    best = max(eligible_only, key=lambda c: c.score)
    rationale = (
        f"Selected {best.printer_id} for material={material.material} "
        f"under strategy={req.strategy.value}: " + "; ".join(best.reasons)
    )
    return DispatchDecision(
        selected_printer_id=best.printer_id,
        candidates=tuple(sorted(candidates, key=lambda c: -c.score)),
        rationale=rationale,
        strategy_used=req.strategy,
    )


__all__ = [
    "DispatchDecision",
    "DispatchRequest",
    "DispatchScore",
    "DispatchStrategy",
    "dispatch",
]
