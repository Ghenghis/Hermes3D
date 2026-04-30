"""Slicer integration: PrusaSlicer / OrcaSlicer CLI wrapper.

The slicer binary itself is NOT bundled (correctly delegated to the
installer per the contract). Use ``find_slicer()`` to detect availability.
"""

from hermes3d.core.slicer.slicer_runner import (
    SliceResult,
    SlicerError,
    SlicerNotFound,
    find_slicer,
    parse_gcode_metadata,
    slice_mesh,
)

__all__ = [
    "SliceResult",
    "SlicerError",
    "SlicerNotFound",
    "find_slicer",
    "parse_gcode_metadata",
    "slice_mesh",
]
