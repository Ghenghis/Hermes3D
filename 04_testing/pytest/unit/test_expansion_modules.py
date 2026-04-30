"""Tests for the second-wave expansion modules."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest
import trimesh

# =============================================================================
# Mesh analyzer
# =============================================================================


def test_mesh_analyzer_simple_cube_no_overhangs():
    from hermes3d.core.agents.mesh_analyzer import analyze_mesh

    cube = trimesh.creation.box(extents=(40, 30, 20))
    a = analyze_mesh(cube)
    assert a.triangle_count == 12
    assert a.is_watertight
    assert a.overhang_pct == 0.0
    assert a.first_layer_area_mm2 == pytest.approx(1200.0)
    # No risk flags for a simple cube
    assert not a.risk_flags


def test_mesh_analyzer_tip_down_cone_flags_low_bed():
    import trimesh.transformations as tt
    from hermes3d.core.agents.mesh_analyzer import analyze_mesh

    cone = trimesh.creation.cone(radius=20, height=40)
    cone.apply_transform(tt.rotation_matrix(np.pi, (1, 0, 0)))
    a = analyze_mesh(cone)
    # bed area should be near zero (tip touches bed)
    assert a.first_layer_area_mm2 < 50
    assert any("low-bed-contact" in f for f in a.risk_flags)


def test_mesh_analyzer_tall_thin_rod_flags_aspect():
    from hermes3d.core.agents.mesh_analyzer import analyze_mesh

    rod = trimesh.creation.cylinder(radius=5, height=80)
    a = analyze_mesh(rod)
    assert a.height_to_min_xy_aspect == pytest.approx(8.0, abs=0.1)
    assert any("tall-thin" in f for f in a.risk_flags)


def test_mesh_analyzer_with_real_overhangs():
    """A box with a downward overhanging surface should flag overhangs."""
    from hermes3d.core.agents.mesh_analyzer import analyze_mesh

    # Two stacked boxes forming a T-shape (top bar hangs over the stem)
    top = trimesh.creation.box(extents=(40, 10, 5))
    top.apply_translation((0, 0, 30))
    stem = trimesh.creation.box(extents=(10, 10, 30))
    t = trimesh.util.concatenate([top, stem])
    a = analyze_mesh(t)
    assert a.overhang_area_mm2 > 0
    # Overhang flags present (either moderate or high)
    overhang_flags = [f for f in a.risk_flags if "overhang" in f or "bridge" in f]
    assert len(overhang_flags) > 0


def test_mesh_analyzer_volume_metric():
    from hermes3d.core.agents.mesh_analyzer import analyze_mesh

    cube = trimesh.creation.box(extents=(10, 10, 10))
    a = analyze_mesh(cube)
    assert a.volume_mm3 == pytest.approx(1000.0)
    assert a.surface_area_mm2 == pytest.approx(600.0)


# =============================================================================
# Parallel planner
# =============================================================================


def test_parallel_planner_assigns_distinct_printers():
    from hermes3d.core.agents.parallel_planner import (
        PartRequest,
        plan_parallel_print,
    )

    parts = [
        PartRequest("a", (180, 100, 30), 90, "PLA", "normal", 240),
        PartRequest("b", (160, 100, 5), 92, "PLA", "normal", 90),
        PartRequest("c", (50, 50, 30), 35, "ABS", "fine", 180),
    ]
    plan = plan_parallel_print(parts)
    selected = [item.selected_printer_id for item in plan.items]
    # All should be assigned (3 parts, plenty of printers)
    assert all(s is not None for s in selected)
    # All distinct
    assert len(set(selected)) == 3
    assert plan.parallel_count == 3


def test_parallel_planner_respects_max_parallel():
    from hermes3d.core.agents.parallel_planner import (
        PartRequest,
        plan_parallel_print,
    )

    parts = [PartRequest(f"p{i}", (50, 50, 30), 35, "PLA") for i in range(8)]
    plan = plan_parallel_print(parts, max_parallel_printers=3)
    assert plan.parallel_count == 3
    assert len(plan.unscheduled) == 5


def test_parallel_planner_excluded_printers_respected():
    from hermes3d.core.agents.parallel_planner import (
        PartRequest,
        plan_parallel_print,
    )

    parts = [PartRequest("only_one", (180, 100, 55), 90, "PLA")]
    plan = plan_parallel_print(parts, excluded_printers=("prusa_mk3s", "flsun_t1_a"))
    selected = plan.items[0].selected_printer_id
    assert selected not in ("prusa_mk3s", "flsun_t1_a")


# =============================================================================
# Profile generator
# =============================================================================


def test_generate_profile_pla_normal_basic():
    from hermes3d.core.slicer.profile_generator import generate_profile

    p = generate_profile(printer_id="flsun_t1_a", material="PLA", quality_level="normal")
    assert "bed_shape" in p.settings
    assert p.settings["layer_height"] == "0.2"
    # PLA wants 100% fan
    assert p.settings["max_fan_speed"] == "100"
    # Delta defaults to 80mm/s perimeter speed
    assert p.settings["perimeter_speed"] == "80"


def test_generate_profile_quality_levels_differ():
    from hermes3d.core.slicer.profile_generator import generate_profile

    draft = generate_profile(printer_id="prusa_mk3s", material="PLA", quality_level="draft")
    fine = generate_profile(printer_id="prusa_mk3s", material="PLA", quality_level="fine")
    assert float(draft.settings["layer_height"]) > float(fine.settings["layer_height"])
    assert int(draft.settings["perimeters"]) < int(fine.settings["perimeters"])


def test_generate_profile_skill_overrides_applied(tmp_path: Path):
    from hermes3d.core.memory import SkillKind, SkillScope, SkillStore
    from hermes3d.core.slicer.profile_generator import generate_profile

    sk = SkillStore(tmp_path / "sk.json")
    sk.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="test_override",
        scope=SkillScope(printer_id="flsun_t1_a", material="PLA"),
        body={"first_layer_temperature": "220", "fill_density": "30%"},
        confidence=0.8,
    )
    p = generate_profile(printer_id="flsun_t1_a", material="PLA", skills=sk)
    assert p.settings["first_layer_temperature"] == "220"
    assert p.settings["fill_density"] == "30%"
    assert any("test_override" in s for s in p.applied_skills)


def test_generate_profile_writes_ini(tmp_path: Path):
    from hermes3d.core.slicer.profile_generator import generate_profile

    p = generate_profile(printer_id="prusa_mk3s", material="PETG")
    out = p.write(tmp_path / "out.ini")
    text = out.read_text(encoding="utf-8")
    assert "layer_height" in text
    assert "bed_shape" in text
    assert "# Auto-generated" in text


def test_generate_profile_delta_uses_octagonal_bed():
    from hermes3d.core.slicer.profile_generator import generate_profile

    p = generate_profile(printer_id="flsun_t1_a", material="PLA")
    # 8-point polygon for delta circular bed
    points = p.settings["bed_shape"].split(",")
    assert len(points) == 8


def test_generate_profile_cartesian_uses_rectangular_bed():
    from hermes3d.core.slicer.profile_generator import generate_profile

    p = generate_profile(printer_id="prusa_mk3s", material="PLA")
    # 4 corners for rectangular bed
    points = p.settings["bed_shape"].split(",")
    assert len(points) == 4


# =============================================================================
# Skill packs
# =============================================================================


def test_skill_pack_export_then_import(tmp_path: Path):
    from hermes3d.core.memory import SkillKind, SkillScope, SkillStore
    from hermes3d.core.memory.skill_pack import (
        ImportMode,
        export_pack,
        import_pack,
        read_pack,
        write_pack,
    )

    src = SkillStore(tmp_path / "src.json")
    src.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="a",
        scope=SkillScope(material="ASA"),
        body={"k": "v"},
        confidence=0.7,
    )
    src.add(
        skill_kind=SkillKind.MATERIAL_QUIRK,
        name="b",
        scope=SkillScope(material="PETG"),
        body={"observation": "stringes"},
        confidence=0.6,
    )
    pack = export_pack(src, pack_name="t", author="test")
    pack_path = write_pack(pack, tmp_path / "p.json")
    re_pack = read_pack(pack_path)
    assert re_pack.manifest.skill_count == 2
    assert re_pack.manifest.sha256 is not None

    target = SkillStore(tmp_path / "tgt.json")
    report = import_pack(target, re_pack, mode=ImportMode.MERGE)
    assert len(report.added_skill_ids) == 2
    assert len(report.skipped_skill_names) == 0


def test_skill_pack_merge_skips_duplicates(tmp_path: Path):
    from hermes3d.core.memory import SkillKind, SkillScope, SkillStore
    from hermes3d.core.memory.skill_pack import (
        ImportMode,
        export_pack,
        import_pack,
        read_pack,
        write_pack,
    )

    src = SkillStore(tmp_path / "src.json")
    src.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="dup",
        scope=SkillScope(),
        body={"x": 1},
        confidence=0.5,
    )
    pack = export_pack(src, pack_name="t")
    pack_path = write_pack(pack, tmp_path / "p.json")
    re_pack = read_pack(pack_path)
    target = SkillStore(tmp_path / "tgt.json")
    target.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="dup",
        scope=SkillScope(),
        body={"x": 99},
        confidence=0.5,
    )
    report = import_pack(target, re_pack, mode=ImportMode.MERGE)
    assert len(report.skipped_skill_names) == 1
    assert "dup" in report.skipped_skill_names


def test_skill_pack_corrupt_hash_rejected(tmp_path: Path):
    import json

    from hermes3d.core.memory import SkillKind, SkillScope, SkillStore
    from hermes3d.core.memory.skill_pack import (
        export_pack,
        read_pack,
        write_pack,
    )

    src = SkillStore(tmp_path / "src.json")
    src.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="x",
        scope=SkillScope(),
        body={"y": 1},
        confidence=0.5,
    )
    pack = export_pack(src, pack_name="t")
    pack_path = write_pack(pack, tmp_path / "p.json")
    # Corrupt the body
    data = json.loads(pack_path.read_text())
    data["skills"][0]["body"]["y"] = 999
    pack_path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="content-hash mismatch"):
        read_pack(pack_path)


# =============================================================================
# Supervisor (smoke test — does not actually poll Moonraker)
# =============================================================================


def test_supervisor_constructs_and_starts(tmp_path: Path):
    from hermes3d.core.farm.print_history import PrintHistory
    from hermes3d.core.farm.spool_tracker import SpoolTracker
    from hermes3d.core.memory import SkillStore
    from hermes3d.core.notifications import Notifier
    from hermes3d.core.supervisor import (
        PrintSupervisor,
        SupervisorPolicy,
    )

    sup = PrintSupervisor(
        history=PrintHistory(tmp_path / "h.jsonl"),
        spools=SpoolTracker(tmp_path / "s.json"),
        skills=SkillStore(tmp_path / "sk.json"),
        notifier=Notifier(discord_url=None, slack_url=None, generic_url=None),
        policy=SupervisorPolicy(poll_interval_s=0.05),
    )
    assert not sup.is_running()
    sup.start()
    assert sup.is_running()
    time.sleep(0.1)  # let one poll iteration happen (printers will be unreachable)
    sup.stop(timeout=2.0)
    assert not sup.is_running()


def test_supervisor_event_listeners_fire(tmp_path: Path):
    """Manually drive an event and verify listeners receive it."""
    from hermes3d.core.farm.print_history import PrintHistory
    from hermes3d.core.farm.spool_tracker import SpoolTracker
    from hermes3d.core.memory import SkillStore
    from hermes3d.core.notifications import Notifier
    from hermes3d.core.supervisor import (
        PrinterState,
        PrintSupervisor,
        SupervisorEvent,
    )

    sup = PrintSupervisor(
        history=PrintHistory(tmp_path / "h.jsonl"),
        spools=SpoolTracker(tmp_path / "s.json"),
        skills=SkillStore(tmp_path / "sk.json"),
        notifier=Notifier(discord_url=None, slack_url=None, generic_url=None),
    )
    captured = []
    sup.on_event(lambda evt, ps, det: captured.append((evt, ps.printer_id)))
    ps = PrinterState(printer_id="flsun_t1_a")
    sup._emit(SupervisorEvent.PRINT_STARTED, ps, {})
    assert captured == [(SupervisorEvent.PRINT_STARTED, "flsun_t1_a")]


# =============================================================================
# Expanded MCP tools
# =============================================================================


def test_mcp_catalog_includes_new_tools():
    from hermes3d.api.mcp_server import TOOLS

    names = {t["name"] for t in TOOLS}
    expected = {
        "hermes3d.skill_list",
        "hermes3d.skill_lookup",
        "hermes3d.predict_failure",
        "hermes3d.analyze_mesh",
        "hermes3d.generate_profile",
        "hermes3d.parallel_plan",
    }
    assert expected.issubset(names)


def test_mcp_predict_failure_baseline():
    from hermes3d.api.mcp_server import get_handler

    result = get_handler("hermes3d.predict_failure")(
        {
            "printer_id": "flsun_t1_a",
            "material": "PLA",
        }
    )
    assert "failure_probability" in result
    assert result["failure_probability"] == pytest.approx(0.10, abs=0.01)


def test_mcp_analyze_mesh(tmp_path: Path):
    from hermes3d.api.mcp_server import get_handler

    stl = tmp_path / "x.stl"
    trimesh.creation.box(extents=(40, 30, 20)).export(stl)
    result = get_handler("hermes3d.analyze_mesh")(
        {
            "mesh_path": str(stl),
        }
    )
    assert result["triangle_count"] == 12
    assert result["overhang_pct"] == 0.0


def test_mcp_parallel_plan():
    from hermes3d.api.mcp_server import get_handler

    result = get_handler("hermes3d.parallel_plan")(
        {
            "parts": [
                {
                    "part_id": "a",
                    "mesh_extents_mm": [50, 50, 30],
                    "mesh_xy_radius_mm": 35,
                    "material": "PLA",
                },
                {
                    "part_id": "b",
                    "mesh_extents_mm": [80, 80, 40],
                    "mesh_xy_radius_mm": 56.6,
                    "material": "PETG",
                },
            ],
        }
    )
    assert "items" in result
    assert len(result["items"]) == 2
    assert result["parallel_count"] >= 2


def test_mcp_generate_profile():
    from hermes3d.api.mcp_server import get_handler

    result = get_handler("hermes3d.generate_profile")(
        {
            "printer_id": "flsun_t1_a",
            "material": "PLA",
            "quality_level": "normal",
        }
    )
    assert "settings" in result
    assert result["settings"]["layer_height"] == "0.2"
    assert "ini_text" in result
    assert "# Auto-generated" in result["ini_text"]
