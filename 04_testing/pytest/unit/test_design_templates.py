from __future__ import annotations

from pathlib import Path

from hermes3d.api.routes.design import (
    _discover_templates,
    _resolve_supported_design,
    _supported_templates,
)
from hermes3d.core.design.primitives import (
    CalibrationCubeSpec,
    SimpleBoxSpec,
    build_calibration_cube,
    build_simple_box,
)
from hermes3d.core.validation.truth_gate import run_truth_gate
from hermes3d.services.modeling_backend import backend_summary_for_proof


def test_supported_templates_include_day_to_day_primitives() -> None:
    ids = {template["id"] for template in _supported_templates()}

    assert {"desk_organizer", "calibration_cube", "simple_box"} <= ids


def test_template_discovery_reports_primitive_executors_available() -> None:
    templates = {template["id"]: template for template in _discover_templates()}

    assert templates["calibration_cube"]["executor_available"] is True
    assert templates["calibration_cube"]["deps_ok"] is True
    assert templates["simple_box"]["executor_available"] is True
    assert templates["simple_box"]["deps_ok"] is True


def test_resolver_routes_calibration_cube_template() -> None:
    template_id, spec = _resolve_supported_design(
        "make a 25mm calibration cube",
        {"template": "calibration_cube", "size_mm": 25},
    )

    assert template_id == "calibration_cube"
    assert isinstance(spec, CalibrationCubeSpec)
    assert spec.size_mm == 25


def test_resolver_routes_simple_box_template() -> None:
    template_id, spec = _resolve_supported_design(
        "make a small open storage box",
        {
            "template": "simple_box",
            "width_mm": 60,
            "depth_mm": 40,
            "height_mm": 24,
            "wall_mm": 2,
            "floor_mm": 2,
        },
    )

    assert template_id == "simple_box"
    assert isinstance(spec, SimpleBoxSpec)
    assert spec.width_mm == 60
    assert spec.depth_mm == 40
    assert spec.height_mm == 24


def test_primitive_meshes_pass_truth_gate(tmp_path: Path) -> None:
    cases = {
        "calibration_cube": build_calibration_cube(CalibrationCubeSpec(size_mm=20)),
        "simple_box": build_simple_box(
            SimpleBoxSpec(width_mm=70, depth_mm=45, height_mm=28, wall_mm=2, floor_mm=2)
        ),
    }

    for name, mesh in cases.items():
        mesh_path = tmp_path / f"{name}.stl"
        mesh.export(mesh_path, file_type="stl")
        report = run_truth_gate(mesh_path)
        assert report.overall_status.value == "pass"


def test_modeling_backend_knows_primitive_templates() -> None:
    cube = backend_summary_for_proof("calibration_cube")
    box = backend_summary_for_proof("simple_box")

    assert cube["name"] == "trimesh"
    assert "primitive_box_mesh" in cube["capabilities"]
    assert box["name"] == "trimesh"
    assert box["engine"]["name"] == "manifold3d"
