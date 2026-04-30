"""Parametric design generators (currently: desk_organizer)."""

from hermes3d.core.design.desk_organizer import (
    OrganizerSpec,
    acceptance_variants,
    build_organizer,
    export_organizer,
)

__all__ = [
    "OrganizerSpec",
    "acceptance_variants",
    "build_organizer",
    "export_organizer",
]
