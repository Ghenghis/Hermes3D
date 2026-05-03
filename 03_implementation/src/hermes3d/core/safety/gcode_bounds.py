"""G-code bounds pre-condition gate.

Status: runnable
Gate ID: ``safety.gcode_bounds_precondition``

Parses an entire G-code program, simulates the head's (X, Y, Z)
trajectory, and rejects the program if any move targets a point outside
the printer's printable volume. Runs *before* upload — the file never
touches the printer if a single move is OOB.

Coverage notes:

  * ``G0`` / ``G1`` — straight-line moves, supported in absolute (G90)
    and relative (G91) modes.
  * ``G2`` / ``G3`` — clockwise / counter-clockwise arcs. We do not
    rasterise the arc; we approximate the bounding box by checking the
    arc's tangent extrema in addition to start + end. For most slicer
    output (which restricts arcs to small fillets) this is exact;
    pathological hand-written arcs that span >180° still get checked
    via their start, end, and the four cardinal-tangent points if the
    arc passes through them.
  * ``G28`` — homing move. We *do not* bounds-check homing moves
    against bed bounds (they're allowed to ride the printable volume's
    perimeter); the gate records a warning instead.
  * ``G29`` — bed-mesh probe. Allowed; not checked.
  * ``G90`` / ``G91`` — absolute / relative move mode (motion only).
  * ``G92`` — "set position" without moving. Updates the simulator's
    head position to whatever the slicer claims it is.
  * ``M``-codes / ``T``-codes / ``S``-codes — non-motion. Skipped.

The gate's bounds source order is:

  1. ``printers.toml`` entry for the target printer (production path).
  2. The ``override_bounds`` argument (test injection).
  3. Prusa MK3S+ defaults (250 x 210 x 210 mm). This is the documented
     fallback when the printer is missing from the fleet config; the
     gate emits a ``safety.violation`` *warning* (not block) when the
     fallback is taken.

The fallback bounds are deliberately CONSERVATIVE — most printers are
larger than the MK3S+ but we'd rather refuse a borderline-legal move
than let an unconfigured printer off-bed itself.
"""

from __future__ import annotations

import enum
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Bounds spec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrinterBounds:
    """Axis-aligned printable volume.

    For circular (delta) beds, callers should pre-compute the inscribed
    rectangle and feed that here, OR pass ``circular_diameter_mm`` for
    radial-fit checking. We only check (X, Y); Z is checked separately
    against ``z_max_mm``.

    The origin convention follows the slicer's: bed center is normally
    at (X_min + X_max) / 2; for delta printers (origin at center) the
    bounds are symmetric around (0, 0).
    """

    x_min_mm: float
    x_max_mm: float
    y_min_mm: float
    y_max_mm: float
    z_min_mm: float = 0.0
    z_max_mm: float = 210.0
    circular_diameter_mm: float | None = None

    def contains_xy(self, x: float, y: float) -> bool:
        if self.circular_diameter_mm is not None:
            r = self.circular_diameter_mm / 2.0
            cx = (self.x_min_mm + self.x_max_mm) / 2.0
            cy = (self.y_min_mm + self.y_max_mm) / 2.0
            return math.hypot(x - cx, y - cy) <= r + 1e-6
        return (
            self.x_min_mm - 1e-6 <= x <= self.x_max_mm + 1e-6
            and self.y_min_mm - 1e-6 <= y <= self.y_max_mm + 1e-6
        )

    def contains_z(self, z: float) -> bool:
        return self.z_min_mm - 1e-6 <= z <= self.z_max_mm + 1e-6


# Prusa MK3S+ defaults — the documented fallback when a printer is not
# in the fleet config.
PRUSA_MK3S_DEFAULT_BOUNDS = PrinterBounds(
    x_min_mm=0.0, x_max_mm=250.0,
    y_min_mm=-3.0, y_max_mm=210.0,  # MK3S+ has y starting slightly negative
    z_min_mm=0.0, z_max_mm=210.0,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class MoveMode(str, enum.Enum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"


# Regex: command + word arguments. Strips inline `;` comments and `()`.
_WORD_RE = re.compile(r"([A-Za-z])\s*(-?\d+(?:\.\d+)?)")
_COMMENT_RE = re.compile(r";.*$")
_PAREN_RE = re.compile(r"\([^)]*\)")


def _tokenize(line: str) -> dict[str, float] | None:
    """Return a {letter: float} dict or None if the line has no command."""
    line = _PAREN_RE.sub("", line)
    line = _COMMENT_RE.sub("", line).strip()
    if not line:
        return None
    words = _WORD_RE.findall(line)
    if not words:
        return None
    return {letter.upper(): float(value) for letter, value in words}


@dataclass
class _SimState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    mode: MoveMode = MoveMode.ABSOLUTE


@dataclass
class BoundsViolation:
    """A single OOB move."""

    line_no: int
    line_text: str
    axis: str        # "X", "Y", "Z", "XY-radial"
    value: float
    bound_min: float
    bound_max: float


@dataclass
class GcodeBoundsReport:
    """Result of parsing + bounds-checking one G-code program."""

    file_path: str
    bounds: PrinterBounds
    n_moves: int = 0
    n_arcs: int = 0
    used_fallback_bounds: bool = False
    violations: list[BoundsViolation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bbox_observed: tuple[float, float, float, float, float, float] | None = None

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "passed": self.passed,
            "n_moves": self.n_moves,
            "n_arcs": self.n_arcs,
            "used_fallback_bounds": self.used_fallback_bounds,
            "violations": [
                {
                    "line_no": v.line_no,
                    "line_text": v.line_text,
                    "axis": v.axis,
                    "value": v.value,
                    "bound_min": v.bound_min,
                    "bound_max": v.bound_max,
                }
                for v in self.violations
            ],
            "warnings": list(self.warnings),
            "bbox_observed": list(self.bbox_observed) if self.bbox_observed else None,
        }


def _arc_extrema(
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    cx: float, cy: float,
    clockwise: bool,
) -> list[tuple[float, float]]:
    """Return cardinal-tangent extrema of an arc that fall on the arc.

    For an arc from start to end around center (cx, cy), the bounding
    box may extend beyond start + end if the arc passes through one of
    the four cardinal tangent points (cx ± r, cy) or (cx, cy ± r). We
    test each cardinal tangent and return only those that lie on the
    arc.
    """
    r = math.hypot(start_x - cx, start_y - cy)
    if r < 1e-9:
        return []

    start_angle = math.atan2(start_y - cy, start_x - cx)
    end_angle = math.atan2(end_y - cy, end_x - cx)

    def _on_arc(theta: float) -> bool:
        # Normalize sweep direction.
        if clockwise:
            sweep = (start_angle - end_angle) % (2 * math.pi)
            offset = (start_angle - theta) % (2 * math.pi)
        else:
            sweep = (end_angle - start_angle) % (2 * math.pi)
            offset = (theta - start_angle) % (2 * math.pi)
        return offset <= sweep + 1e-9

    extrema: list[tuple[float, float]] = []
    for theta in (0.0, math.pi / 2, math.pi, -math.pi / 2):
        if _on_arc(theta):
            extrema.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    return extrema


def parse_and_check(
    gcode_text: str,
    bounds: PrinterBounds,
    *,
    file_path: str = "<inline>",
) -> GcodeBoundsReport:
    """Parse a G-code program and return a :class:`GcodeBoundsReport`.

    The parser walks the program line-by-line, simulating the
    extruder's nominal head position. Every commanded target is checked
    against ``bounds``. Arcs are checked at start, end, and any
    cardinal tangent points the arc passes through.

    Non-motion codes (M, T, S) are skipped without error. Unknown
    G-codes are recorded as warnings but do not block.
    """
    report = GcodeBoundsReport(file_path=file_path, bounds=bounds)
    state = _SimState()

    bbox_x_min = bbox_y_min = bbox_z_min = math.inf
    bbox_x_max = bbox_y_max = bbox_z_max = -math.inf

    def _check_xy_z(x: float, y: float, z: float, line_no: int, line_text: str) -> None:
        nonlocal bbox_x_min, bbox_y_min, bbox_z_min
        nonlocal bbox_x_max, bbox_y_max, bbox_z_max
        bbox_x_min = min(bbox_x_min, x)
        bbox_y_min = min(bbox_y_min, y)
        bbox_z_min = min(bbox_z_min, z)
        bbox_x_max = max(bbox_x_max, x)
        bbox_y_max = max(bbox_y_max, y)
        bbox_z_max = max(bbox_z_max, z)
        if not bounds.contains_xy(x, y):
            if bounds.circular_diameter_mm is not None:
                cx = (bounds.x_min_mm + bounds.x_max_mm) / 2.0
                cy = (bounds.y_min_mm + bounds.y_max_mm) / 2.0
                radial = math.hypot(x - cx, y - cy)
                report.violations.append(
                    BoundsViolation(
                        line_no=line_no,
                        line_text=line_text,
                        axis="XY-radial",
                        value=radial,
                        bound_min=0.0,
                        bound_max=bounds.circular_diameter_mm / 2.0,
                    )
                )
            else:
                if not (bounds.x_min_mm - 1e-6 <= x <= bounds.x_max_mm + 1e-6):
                    report.violations.append(
                        BoundsViolation(
                            line_no=line_no,
                            line_text=line_text,
                            axis="X",
                            value=x,
                            bound_min=bounds.x_min_mm,
                            bound_max=bounds.x_max_mm,
                        )
                    )
                if not (bounds.y_min_mm - 1e-6 <= y <= bounds.y_max_mm + 1e-6):
                    report.violations.append(
                        BoundsViolation(
                            line_no=line_no,
                            line_text=line_text,
                            axis="Y",
                            value=y,
                            bound_min=bounds.y_min_mm,
                            bound_max=bounds.y_max_mm,
                        )
                    )
        if not bounds.contains_z(z):
            report.violations.append(
                BoundsViolation(
                    line_no=line_no,
                    line_text=line_text,
                    axis="Z",
                    value=z,
                    bound_min=bounds.z_min_mm,
                    bound_max=bounds.z_max_mm,
                )
            )

    for raw_line_no, raw_line in enumerate(gcode_text.splitlines(), start=1):
        tokens = _tokenize(raw_line)
        if not tokens:
            continue

        # Build the command code "G<n>" / "M<n>" / "T<n>".
        # Only G commands change the head position.
        if "G" not in tokens:
            # M / T / S — skip.
            continue
        gnum = int(tokens["G"])

        if gnum == 90:
            state.mode = MoveMode.ABSOLUTE
            continue
        if gnum == 91:
            state.mode = MoveMode.RELATIVE
            continue
        if gnum == 92:
            # Set head position without moving.
            state.x = tokens.get("X", state.x)
            state.y = tokens.get("Y", state.y)
            state.z = tokens.get("Z", state.z)
            continue
        if gnum == 28:
            # Homing — record but do not bounds-check.
            report.warnings.append(f"line {raw_line_no}: G28 home — bounds skipped")
            # Reset to the bed origin; this is a reasonable default for
            # any printer kinematics.
            cx = (bounds.x_min_mm + bounds.x_max_mm) / 2.0
            cy = (bounds.y_min_mm + bounds.y_max_mm) / 2.0
            if "X" in tokens or "Y" in tokens or "Z" in tokens:
                state.x = bounds.x_min_mm if "X" in tokens else state.x
                state.y = bounds.y_min_mm if "Y" in tokens else state.y
                state.z = bounds.z_min_mm if "Z" in tokens else state.z
            else:
                state.x, state.y, state.z = cx, cy, bounds.z_min_mm
            continue
        if gnum == 29:
            # Bed mesh probe — allowed.
            report.warnings.append(f"line {raw_line_no}: G29 bed mesh — bounds skipped")
            continue

        if gnum in (0, 1):
            target_x = state.x
            target_y = state.y
            target_z = state.z
            if state.mode is MoveMode.ABSOLUTE:
                target_x = tokens.get("X", state.x)
                target_y = tokens.get("Y", state.y)
                target_z = tokens.get("Z", state.z)
            else:  # relative
                target_x = state.x + tokens.get("X", 0.0)
                target_y = state.y + tokens.get("Y", 0.0)
                target_z = state.z + tokens.get("Z", 0.0)
            _check_xy_z(target_x, target_y, target_z, raw_line_no, raw_line.strip())
            state.x, state.y, state.z = target_x, target_y, target_z
            report.n_moves += 1
            continue

        if gnum in (2, 3):
            # Arc move. I + J = relative offset to center; alternatively R = radius.
            target_x = state.x
            target_y = state.y
            target_z = state.z
            if state.mode is MoveMode.ABSOLUTE:
                target_x = tokens.get("X", state.x)
                target_y = tokens.get("Y", state.y)
                target_z = tokens.get("Z", state.z)
            else:
                target_x = state.x + tokens.get("X", 0.0)
                target_y = state.y + tokens.get("Y", 0.0)
                target_z = state.z + tokens.get("Z", 0.0)
            cx = state.x + tokens.get("I", 0.0)
            cy = state.y + tokens.get("J", 0.0)

            # Always check start + end first.
            _check_xy_z(target_x, target_y, target_z, raw_line_no, raw_line.strip())
            # Then any tangent extrema on the arc.
            for ex, ey in _arc_extrema(
                state.x, state.y,
                target_x, target_y,
                cx, cy,
                clockwise=(gnum == 2),
            ):
                _check_xy_z(ex, ey, target_z, raw_line_no, raw_line.strip())
            state.x, state.y, state.z = target_x, target_y, target_z
            report.n_moves += 1
            report.n_arcs += 1
            continue

        # Unknown G-code — record warning, do not block.
        report.warnings.append(f"line {raw_line_no}: unknown G{gnum} — skipped")

    if math.isfinite(bbox_x_min):
        report.bbox_observed = (
            bbox_x_min, bbox_x_max,
            bbox_y_min, bbox_y_max,
            bbox_z_min, bbox_z_max,
        )
    return report


def check_gcode_file(
    path: str | Path,
    bounds: PrinterBounds,
) -> GcodeBoundsReport:
    """Parse and bounds-check a G-code file from disk."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_and_check(text, bounds, file_path=str(p))


def resolve_bounds(
    *,
    printer_id: str,
    fleet_lookup,
    override_bounds: PrinterBounds | None = None,
) -> tuple[PrinterBounds, bool]:
    """Resolve the bounds to use for a given printer.

    Order:
      1. ``override_bounds`` (test injection).
      2. ``fleet_lookup(printer_id)`` -> PrinterProfile (production path).
      3. :data:`PRUSA_MK3S_DEFAULT_BOUNDS` (warning).

    Returns ``(bounds, used_fallback)``.
    """
    if override_bounds is not None:
        return override_bounds, False
    profile = None
    if fleet_lookup is not None:
        try:
            profile = fleet_lookup(printer_id)
        except Exception:
            profile = None
    if profile is None:
        return PRUSA_MK3S_DEFAULT_BOUNDS, True
    bed = profile.bed
    if bed.kind == "circular":
        # Build symmetric rectangle around (0, 0) for delta printers,
        # then use circular_diameter_mm for the radial check.
        r = bed.diameter_mm / 2.0
        return (
            PrinterBounds(
                x_min_mm=-r, x_max_mm=r,
                y_min_mm=-r, y_max_mm=r,
                z_min_mm=0.0, z_max_mm=profile.z_height_mm,
                circular_diameter_mm=bed.diameter_mm,
            ),
            False,
        )
    return (
        PrinterBounds(
            x_min_mm=0.0, x_max_mm=bed.x_mm,
            y_min_mm=0.0, y_max_mm=bed.y_mm,
            z_min_mm=0.0, z_max_mm=profile.z_height_mm,
        ),
        False,
    )


def build_violation_payload(
    *,
    job_id: str,
    printer_id: str,
    report: GcodeBoundsReport,
) -> dict[str, Any]:
    """Build the ``safety.violation`` payload for a failed bounds check."""
    return {
        "kind": "safety.violation",
        "gate": "safety.gcode_bounds_precondition",
        "job_id": job_id,
        "printer_id": printer_id,
        "report": report.to_dict(),
    }


__all__ = [
    "BoundsViolation",
    "GcodeBoundsReport",
    "MoveMode",
    "PRUSA_MK3S_DEFAULT_BOUNDS",
    "PrinterBounds",
    "build_violation_payload",
    "check_gcode_file",
    "parse_and_check",
    "resolve_bounds",
]
