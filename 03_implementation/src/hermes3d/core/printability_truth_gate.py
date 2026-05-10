"""GUI-facing printability truth gate definitions.

This module wraps the existing geometry gate with the 11 GUI contract gates in
their required display and API order.
"""

from __future__ import annotations

from typing import Any

from hermes3d.core.validation.truth_gate import TruthGateConfig, TruthGateReport, run_truth_gate

GATE_IDS = [
    "watertight_mesh",
    "manifold_mesh",
    "fixed_normals",
    "repaired_holes",
    "real_world_scale",
    "minimum_wall_thickness",
    "bed_size_fit",
    "overhang_support_estimate",
    "slicer_dry_run_success",
    "material_printer_compatibility",
    "moonraker_ready_upload_package",
]

GATE_DEFINITIONS: list[dict[str, Any]] = [
    {"id": gate_id, "order": index + 1, "required": True}
    for index, gate_id in enumerate(GATE_IDS)
]


def run_core_truth_gate(mesh_path: str, config: TruthGateConfig | None = None) -> TruthGateReport:
    return run_truth_gate(mesh_path, config)


__all__ = ["GATE_DEFINITIONS", "GATE_IDS", "run_core_truth_gate"]
