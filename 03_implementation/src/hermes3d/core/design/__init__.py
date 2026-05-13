"""Parametric design generators."""

from hermes3d.core.design.desk_organizer import (
    OrganizerSpec,
    acceptance_variants,
    build_organizer,
    export_organizer,
)
from hermes3d.core.design.primitives import (
    CalibrationCubeSpec,
    SimpleBoxSpec,
    build_calibration_cube,
    build_simple_box,
)

__all__ = [
    "CalibrationCubeSpec",
    "OrganizerSpec",
    "SimpleBoxSpec",
    "acceptance_variants",
    "build_calibration_cube",
    "build_organizer",
    "build_simple_box",
    "export_organizer",
]
