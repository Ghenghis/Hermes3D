"""Small proof-backed parametric primitives for day-to-day modeling.

These templates intentionally stay simple: they give the Design tab useful
calibration and box-making paths without depending on a cloud modeler or a
running GUI application. Geometry is still real mesh generation and still goes
through the same proof/truth-gate path as the desk organizer.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import trimesh

_ENGINE = "manifold"


def _signature(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:10]


def _box(
    size: tuple[float, float, float], translate: tuple[float, float, float]
) -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(translate)
    return mesh


def _difference(base: trimesh.Trimesh, cut: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.difference([base, cut], engine=_ENGINE)


def _ensure_printable_mesh(mesh: trimesh.Trimesh, *, name: str) -> trimesh.Trimesh:
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    mesh.process(validate=True)
    if not mesh.is_watertight:
        raise RuntimeError(f"{name} generated a non-watertight mesh.")
    if not mesh.is_winding_consistent:
        raise RuntimeError(f"{name} generated inconsistent winding.")
    if float(mesh.volume) <= 0:
        raise RuntimeError(f"{name} generated non-positive mesh volume.")
    return mesh


@dataclass(frozen=True)
class CalibrationCubeSpec:
    """Simple solid cube for dimension and slicer calibration."""

    size_mm: float = 20.0

    def validated(self) -> CalibrationCubeSpec:
        if not (5.0 <= self.size_mm <= 100.0):
            raise ValueError("size_mm must be between 5 and 100 mm.")
        return self

    def signature(self) -> str:
        return _signature({"template": "calibration_cube", **self.__dict__})


def build_calibration_cube(spec: CalibrationCubeSpec | None = None) -> trimesh.Trimesh:
    s = (spec or CalibrationCubeSpec()).validated()
    return _ensure_printable_mesh(
        _box((s.size_mm, s.size_mm, s.size_mm), (0, 0, s.size_mm / 2)),
        name="calibration_cube",
    )


@dataclass(frozen=True)
class SimpleBoxSpec:
    """Open-top storage box with real wall/floor thickness."""

    width_mm: float = 80.0
    depth_mm: float = 50.0
    height_mm: float = 30.0
    wall_mm: float = 2.0
    floor_mm: float = 2.0

    def validated(self) -> SimpleBoxSpec:
        errors: list[str] = []
        if not (10.0 <= self.width_mm <= 220.0):
            errors.append("width_mm must be between 10 and 220 mm.")
        if not (10.0 <= self.depth_mm <= 220.0):
            errors.append("depth_mm must be between 10 and 220 mm.")
        if not (5.0 <= self.height_mm <= 180.0):
            errors.append("height_mm must be between 5 and 180 mm.")
        if self.wall_mm < 1.2:
            errors.append("wall_mm must be at least 1.2 mm.")
        if self.floor_mm < 1.2:
            errors.append("floor_mm must be at least 1.2 mm.")
        if self.width_mm <= 2 * self.wall_mm + 2:
            errors.append("width_mm is too small for the requested wall thickness.")
        if self.depth_mm <= 2 * self.wall_mm + 2:
            errors.append("depth_mm is too small for the requested wall thickness.")
        if self.height_mm <= self.floor_mm + 2:
            errors.append("height_mm is too small for the requested floor thickness.")
        if errors:
            raise ValueError("Invalid SimpleBoxSpec:\n  - " + "\n  - ".join(errors))
        return self

    def signature(self) -> str:
        return _signature({"template": "simple_box", **self.__dict__})


def build_simple_box(spec: SimpleBoxSpec | None = None) -> trimesh.Trimesh:
    s = (spec or SimpleBoxSpec()).validated()
    outer = _box((s.width_mm, s.depth_mm, s.height_mm), (0, 0, s.height_mm / 2))
    inner_height = s.height_mm - s.floor_mm + 1.0
    inner = _box(
        (s.width_mm - 2 * s.wall_mm, s.depth_mm - 2 * s.wall_mm, inner_height),
        (0, 0, s.floor_mm + inner_height / 2),
    )
    return _ensure_printable_mesh(_difference(outer, inner), name="simple_box")


__all__ = [
    "CalibrationCubeSpec",
    "SimpleBoxSpec",
    "build_calibration_cube",
    "build_simple_box",
]
