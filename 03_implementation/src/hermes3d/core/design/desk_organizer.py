"""
Hermes3D-OS — Parametric Desk Organizer.

Status: runnable
Contract: 04_testing/acceptance/DESIGN_BRIEF.md

This is the kit's official acceptance test design. It is a real,
customisable, useful object — not a toy primitive. It tests every
non-trivial part of the Truth Gate at once:

  - thin walls (must be >= 1.2 mm by default)
  - large overall envelope (must fit the bed)
  - multiple internal compartments (real CSG with boolean differences)
  - circular pen holders (curved surfaces, sampled normals)
  - phone slot (angled face)
  - cable pass-through (open notch — must remain manifold despite holes)

Implementation:
  Pure trimesh + manifold3d boolean ops. No CadQuery, no OpenSCAD, no
  Blender. Runs everywhere Python + numpy + trimesh + manifold3d run,
  which is both Dave's Windows box and a CI runner.

Parameters are validated and clamped; the generator either produces a
mesh that the Truth Gate will pass with the default config, or it raises
a clear error explaining why the parameters are infeasible.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh

# Engine selection — manifold3d is required for clean boolean ops.
trimesh.util.attach_to_log()
_ENGINE = "manifold"


@dataclass(frozen=True)
class OrganizerSpec:
    """Customisable parameters for the desk organizer.

    All units mm. The defaults produce a real, sensible organizer that
    the Truth Gate accepts on the default config.
    """

    # Outer envelope
    width_mm: float = 180.0  # X
    depth_mm: float = 100.0  # Y
    height_mm: float = 55.0  # Z (low body) — phone dock rises above
    wall_mm: float = 2.0  # all walls and dividers
    floor_mm: float = 2.0

    # Tray compartments (along X)
    tray_count: int = 3
    tray_depth_fraction: float = 0.55  # fraction of total depth used by tray

    # Pen holders — array of cylindrical holes drilled into the back band
    pen_count: int = 4
    pen_diameter_mm: float = 12.0
    pen_depth_mm: float = 40.0

    # Phone dock — a slot at the back-right
    phone_slot: bool = True
    phone_slot_width_mm: float = 12.0
    phone_slot_length_mm: float = 80.0
    phone_slot_height_mm: float = 35.0
    phone_slot_angle_deg: float = 8.0  # forward lean

    # Cable pass-through (a notch in the back wall)
    cable_passthrough: bool = True
    cable_notch_width_mm: float = 14.0
    cable_notch_height_mm: float = 8.0

    # Fillet on top edges (very small for printability)
    chamfer_mm: float = 0.6

    def validated(self) -> OrganizerSpec:
        """Return self if valid, else raise ValueError."""
        errors: list[str] = []
        if self.wall_mm < 1.2:
            errors.append(f"wall_mm {self.wall_mm} < 1.2 (Truth Gate min wall).")
        if self.floor_mm < 1.2:
            errors.append(f"floor_mm {self.floor_mm} < 1.2.")
        if self.tray_count < 1:
            errors.append("tray_count must be >= 1.")
        if self.pen_count < 0:
            errors.append("pen_count must be >= 0.")
        if self.pen_diameter_mm <= 0 and self.pen_count > 0:
            errors.append("pen_diameter_mm must be > 0 when pen_count > 0.")
        if self.width_mm <= 0 or self.depth_mm <= 0 or self.height_mm <= 0:
            errors.append("All envelope dimensions must be > 0.")
        # Pen holders must fit in the back band
        back_band_depth = self.depth_mm * (1 - self.tray_depth_fraction)
        if self.pen_count > 0 and back_band_depth < self.pen_diameter_mm + 2 * self.wall_mm:
            errors.append(
                f"Back band depth {back_band_depth:.1f}mm too small for pen "
                f"diameter {self.pen_diameter_mm}mm + walls."
            )
        if self.phone_slot and self.phone_slot_height_mm + self.height_mm > 200:
            errors.append("phone slot makes object exceed reasonable height.")
        if errors:
            raise ValueError("Invalid OrganizerSpec:\n  - " + "\n  - ".join(errors))
        return self

    def signature(self) -> str:
        """Deterministic short hash of the parameters — for output naming."""
        import hashlib
        import json

        payload = json.dumps(self.__dict__, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:10]


# ---------------------------------------------------------------------------
# Geometry helpers — every operation is a real CSG operation.
# ---------------------------------------------------------------------------


def _box(
    size: tuple[float, float, float], translate: tuple[float, float, float]
) -> trimesh.Trimesh:
    m = trimesh.creation.box(extents=size)
    m.apply_translation(translate)
    return m


def _cylinder(
    radius: float, height: float, translate: tuple[float, float, float], sections: int = 64
) -> trimesh.Trimesh:
    m = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    m.apply_translation(translate)
    return m


def _difference(base: trimesh.Trimesh, cuts: Iterable[trimesh.Trimesh]) -> trimesh.Trimesh:
    cuts = list(cuts)
    if not cuts:
        return base
    return trimesh.boolean.difference([base, *cuts], engine=_ENGINE)


def _union(parts: Iterable[trimesh.Trimesh]) -> trimesh.Trimesh:
    parts = list(parts)
    if not parts:
        raise ValueError("Cannot union empty parts list.")
    if len(parts) == 1:
        return parts[0]
    return trimesh.boolean.union(parts, engine=_ENGINE)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------


def build_organizer(spec: OrganizerSpec | None = None) -> trimesh.Trimesh:
    """Build the parametric desk organizer mesh.

    Returns a single watertight, manifold trimesh.Trimesh. Raises ValueError
    if the spec is infeasible. Raises RuntimeError if CSG fails to produce
    a watertight result.

    Strategy:
        Build the entire outer envelope (including the raised phone-dock
        block) as a single union of two boxes, then perform ONE big
        difference with all cavities/holes/slots. Avoiding a late-stage
        union of two carved bodies prevents thin-sliver seams that the
        Truth Gate (correctly) flags.
    """
    s = (spec or OrganizerSpec()).validated()

    W, D, H = s.width_mm, s.depth_mm, s.height_mm

    # --- 1. Outer envelope: body + (optional) raised dock corner --------
    parts: list[trimesh.Trimesh] = [_box((W, D, H), (0, 0, H / 2))]

    dock_present = s.phone_slot
    if dock_present:
        # Compute extra Y-depth the dock needs to keep `wall_mm` thickness
        # at the slot top after the tilt rotates the slot toward the front
        # (-Y). Without this, a non-zero phone_slot_angle_deg would slice
        # through the front wall — Truth Gate caught this.
        tilt_rad = math.radians(abs(s.phone_slot_angle_deg))
        tilt_displacement = math.tan(tilt_rad) * s.phone_slot_height_mm
        dock_w = s.phone_slot_length_mm + 2 * s.wall_mm
        dock_d = s.phone_slot_width_mm + 2 * s.wall_mm + tilt_displacement
        dock_h = s.phone_slot_height_mm
        # Extend the dock toward -Y by the tilt displacement so the front
        # wall stays >= wall_mm at every Z.
        dock_x = W / 2 - dock_w / 2 - s.wall_mm
        dock_y = D / 2 - dock_d / 2 - s.wall_mm
        # Overlap the body by 0.5 mm so the union is numerically robust.
        overlap = 0.5
        dock_z_size = dock_h + overlap
        dock_z_center = H + dock_h / 2 - overlap / 2
        parts.append(_box((dock_w, dock_d, dock_z_size), (dock_x, dock_y, dock_z_center)))

    outer = _union(parts)

    # --- 2. Tray compartments (front portion) ---------------------------
    tray_y_extent = D * s.tray_depth_fraction
    tray_y_center = (-D / 2) + (tray_y_extent / 2) + s.wall_mm / 2
    tray_inner_y = tray_y_extent - 2 * s.wall_mm
    tray_inner_z = H - s.floor_mm
    tray_z_center = s.floor_mm + tray_inner_z / 2

    inner_w = W - 2 * s.wall_mm
    if s.tray_count == 1:
        compartment_w = inner_w
    else:
        compartment_w = (inner_w - (s.tray_count - 1) * s.wall_mm) / s.tray_count
    if compartment_w <= 0:
        raise ValueError(f"tray_count={s.tray_count} too high for width={W} with wall={s.wall_mm}.")

    cuts: list[trimesh.Trimesh] = []
    for i in range(s.tray_count):
        x_start = -W / 2 + s.wall_mm + i * (compartment_w + s.wall_mm)
        x_center = x_start + compartment_w / 2
        cuts.append(
            _box(
                (compartment_w, tray_inner_y, tray_inner_z),
                (x_center, tray_y_center, tray_z_center),
            )
        )

    # --- 3. Pen holes (back band, top-down cylinders) -------------------
    if s.pen_count > 0:
        back_band_y_center = (D / 2) - (D - tray_y_extent) / 2
        margin = s.wall_mm + s.pen_diameter_mm / 2
        if s.pen_count == 1:
            xs = [0.0]
        else:
            xs = list(np.linspace(-W / 2 + margin, W / 2 - margin, s.pen_count))
        # Skip pens that would collide with the phone dock footprint.
        if dock_present:
            dock_x = W / 2 - (s.phone_slot_length_mm + 2 * s.wall_mm) / 2 - s.wall_mm
            dock_x_min = dock_x - (s.phone_slot_length_mm + 2 * s.wall_mm) / 2
            dock_x_max = dock_x + (s.phone_slot_length_mm + 2 * s.wall_mm) / 2
            xs = [
                x
                for x in xs
                if not (
                    dock_x_min - s.pen_diameter_mm / 2 <= x <= dock_x_max + s.pen_diameter_mm / 2
                )
            ]
        pen_z_center = H - s.pen_depth_mm / 2 + 0.005  # slight overshoot at top
        for x in xs:
            cuts.append(
                _cylinder(
                    radius=s.pen_diameter_mm / 2,
                    height=s.pen_depth_mm + 0.02,
                    translate=(x, back_band_y_center, pen_z_center),
                    sections=64,
                )
            )

    # --- 4. Cable passthrough (notch in back wall) -----------------------
    if s.cable_passthrough:
        cuts.append(
            _box(
                size=(s.cable_notch_width_mm, s.wall_mm * 4, s.cable_notch_height_mm),
                translate=(
                    0.0,
                    D / 2,
                    s.cable_notch_height_mm / 2 + s.floor_mm,
                ),
            )
        )

    # --- 5. Phone slot cut (inside the raised dock area) -----------------
    if dock_present:
        tilt_rad = math.radians(abs(s.phone_slot_angle_deg))
        tilt_displacement = math.tan(tilt_rad) * s.phone_slot_height_mm
        dock_w = s.phone_slot_length_mm + 2 * s.wall_mm
        dock_d = s.phone_slot_width_mm + 2 * s.wall_mm + tilt_displacement
        dock_h = s.phone_slot_height_mm
        dock_x = W / 2 - dock_w / 2 - s.wall_mm
        dock_y = D / 2 - dock_d / 2 - s.wall_mm
        # The cutter must FULLY exit the dock at top and bottom even after
        # the tilt, otherwise the cutter's tilted top/bottom face leaves a
        # thin sliver against the dock's flat top/bottom face. The required
        # extension is (slot_width/2)*sin(angle) at each end. We add 1 mm
        # safety on top of that.
        z_overshoot = (s.phone_slot_width_mm / 2) * math.sin(tilt_rad) + 1.0
        slot_h = dock_h + 2 * z_overshoot
        slot_y_center = dock_y + tilt_displacement / 2
        slot_z_center = H + dock_h / 2
        slot_cut = _box(
            (s.phone_slot_length_mm, s.phone_slot_width_mm, slot_h),
            (dock_x, slot_y_center, slot_z_center),
        )
        if abs(s.phone_slot_angle_deg) > 1e-3:
            angle = math.radians(s.phone_slot_angle_deg)
            R = trimesh.transformations.rotation_matrix(
                angle=angle,
                direction=[1, 0, 0],
                point=[dock_x, slot_y_center, H],
            )
            slot_cut.apply_transform(R)
        cuts.append(slot_cut)

    # --- 6. ONE big difference -------------------------------------------
    body = _difference(outer, cuts)

    # --- 7. Sanity / healing --------------------------------------------
    body.process(validate=True)
    if not (body.is_watertight and body.is_winding_consistent):
        body.fill_holes()
        body.fix_normals()
        body.process(validate=True)
    if not (body.is_watertight and body.is_winding_consistent):
        raise RuntimeError(
            f"CSG produced a non-manifold body (bug in generator or backend); spec={s!r}"
        )

    return body


def export_organizer(
    spec: OrganizerSpec | None,
    output_path: str | Path,
    file_format: str = "stl",
) -> Path:
    """Build and export to the given path.

    Returns the resolved Path. Raises on any geometry or IO failure.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh = build_organizer(spec)
    mesh.export(output_path, file_type=file_format)
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Export produced empty file: {output_path}")
    return output_path.resolve()


# ---------------------------------------------------------------------------
# Variants for the acceptance suite. Every variant must independently pass
# the Truth Gate; this is asserted in tests/conformance/test_acceptance.py.
# ---------------------------------------------------------------------------


def acceptance_variants() -> list[tuple[str, OrganizerSpec]]:
    """The canonical set of variants used by the acceptance run."""
    return [
        ("default", OrganizerSpec()),
        (
            "compact",
            OrganizerSpec(
                width_mm=120,
                depth_mm=80,
                height_mm=45,
                tray_count=2,
                pen_count=2,
                phone_slot=False,
                cable_passthrough=True,
            ),
        ),
        (
            "wide_pens",
            OrganizerSpec(
                width_mm=210,
                depth_mm=110,
                height_mm=55,
                tray_count=4,
                pen_count=6,
                pen_diameter_mm=12,
                pen_depth_mm=40,
            ),
        ),
        (
            "no_pens_no_phone",
            OrganizerSpec(
                width_mm=160,
                depth_mm=90,
                height_mm=50,
                tray_count=3,
                pen_count=0,
                phone_slot=False,
                cable_passthrough=False,
            ),
        ),
    ]


__all__ = [
    "OrganizerSpec",
    "acceptance_variants",
    "build_organizer",
    "export_organizer",
]
