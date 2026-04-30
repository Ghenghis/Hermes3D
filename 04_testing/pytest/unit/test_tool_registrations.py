"""
Tests for built-in tool registrations.

Verifies that every shim in ``tool_registrations.py`` actually invokes its
underlying core module successfully (no API mismatches, no missing imports).
We use ``tmp_path`` and a fresh ``ToolRegistry`` for isolation, and override
the storage paths via ``HERMES3D_QUEUE/SPOOLS/SKILLS`` env vars where
relevant.
"""

from __future__ import annotations

import json
import os
import struct
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_minimal_stl(path: Path) -> None:
    """Write a binary STL file describing a unit cube (12 triangles)."""
    # 8 vertices of a 10x10x10 cube
    v = [
        (0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0),  # bottom
        (0, 0, 10), (10, 0, 10), (10, 10, 10), (0, 10, 10),  # top
    ]
    # 12 triangles (2 per face), normals approximate
    faces = [
        # bottom (z=0, normal -z)
        ((0, 0, -1), v[0], v[2], v[1]),
        ((0, 0, -1), v[0], v[3], v[2]),
        # top (z=10, normal +z)
        ((0, 0, 1), v[4], v[5], v[6]),
        ((0, 0, 1), v[4], v[6], v[7]),
        # front (y=0, normal -y)
        ((0, -1, 0), v[0], v[1], v[5]),
        ((0, -1, 0), v[0], v[5], v[4]),
        # back (y=10, normal +y)
        ((0, 1, 0), v[2], v[3], v[7]),
        ((0, 1, 0), v[2], v[7], v[6]),
        # left (x=0, normal -x)
        ((-1, 0, 0), v[0], v[4], v[7]),
        ((-1, 0, 0), v[0], v[7], v[3]),
        # right (x=10, normal +x)
        ((1, 0, 0), v[1], v[2], v[6]),
        ((1, 0, 0), v[1], v[6], v[5]),
    ]
    with path.open("wb") as fh:
        fh.write(b"\x00" * 80)              # header
        fh.write(struct.pack("<I", len(faces)))
        for normal, a, b, c in faces:
            fh.write(struct.pack("<3f", *normal))
            fh.write(struct.pack("<3f", *a))
            fh.write(struct.pack("<3f", *b))
            fh.write(struct.pack("<3f", *c))
            fh.write(struct.pack("<H", 0))


@pytest.fixture
def isolated_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point queue/spool/skill storage at a temp directory."""
    var = tmp_path / "var"
    var.mkdir()
    monkeypatch.setenv("HERMES3D_QUEUE", str(var / "queue.json"))
    monkeypatch.setenv("HERMES3D_SPOOLS", str(var / "spools.json"))
    monkeypatch.setenv("HERMES3D_SKILLS", str(var / "skills.json"))
    monkeypatch.setenv(
        "HERMES3D_PRINT_HISTORY", str(var / "print_history.json")
    )
    return var


@pytest.fixture
def fresh_registry():
    """Fresh ToolRegistry instance for isolation between tests."""
    from hermes3d.core.agents.tool_registry import ToolRegistry

    return ToolRegistry()


# ---------------------------------------------------------------------------
# Registration mechanics
# ---------------------------------------------------------------------------


def test_register_builtin_tools_registers_eleven(fresh_registry):
    from hermes3d.core.agents.tool_registrations import (
        builtin_names,
        register_builtin_tools,
    )

    names = register_builtin_tools(fresh_registry)
    assert len(names) == 11
    assert set(names) == set(builtin_names())
    # idempotent
    second = register_builtin_tools(fresh_registry)
    assert second == []
    assert len(fresh_registry) == 11


def test_help_returns_full_manifest(fresh_registry):
    from hermes3d.core.agents.tool_registrations import (
        _tool_help,
        register_builtin_tools,
    )
    from hermes3d.core.agents import tool_registry as tr_module

    # _tool_help() reads from the module-level singleton, so register there.
    # Snapshot existing tools so we don't pollute other tests.
    before = {t.name for t in tr_module.tool_registry.all()}
    try:
        register_builtin_tools(tr_module.tool_registry)
        manifest = _tool_help()
        assert manifest["tool_count"] >= 11
        names = {t["name"] for t in manifest["tools"]}
        for expected in (
            "fleet_status",
            "dispatch",
            "queue_add",
            "queue_status",
            "spool_list",
            "estimate_cost",
            "calibration_macro",
            "mesh_analyze",
            "failure_forecast",
            "skill_lookup",
            "help",
        ):
            assert expected in names
        assert "agentic" in manifest["categories"]
    finally:
        # Restore — only remove tools we added.
        for spec in list(tr_module.tool_registry.all()):
            if spec.name not in before:
                tr_module.tool_registry.unregister(spec.name)


def test_is_builtin_recognises_known_names():
    from hermes3d.core.agents.tool_registrations import builtin_names, is_builtin

    for name in builtin_names():
        assert is_builtin(name)
    assert not is_builtin("not_a_real_tool_xyz")


# ---------------------------------------------------------------------------
# dispatch (pure-compute, no IO)
# ---------------------------------------------------------------------------


def test_dispatch_pla_auto_returns_real_decision():
    from hermes3d.core.agents.tool_registrations import _tool_dispatch

    result = _tool_dispatch(
        stl_x_mm=120, stl_y_mm=80, stl_z_mm=50, material="PLA", strategy="auto"
    )
    assert result["selected_printer_id"] is not None
    assert len(result["candidates"]) == 12  # full fleet considered
    assert result["strategy_used"] == "auto"
    # PLA-friendly auto pick — should be a real printer ID we know about
    fleet_ids = {c["printer_id"] for c in result["candidates"]}
    assert result["selected_printer_id"] in fleet_ids


def test_dispatch_oversize_part_finds_no_winner():
    from hermes3d.core.agents.tool_registrations import _tool_dispatch

    # Larger than every bed in the fleet
    result = _tool_dispatch(
        stl_x_mm=600, stl_y_mm=600, stl_z_mm=600, material="PLA", strategy="auto"
    )
    assert result["selected_printer_id"] is None
    # Every candidate must be marked as "doesn't fit"
    assert all(not c["fits"] for c in result["candidates"])


def test_dispatch_invalid_strategy_raises():
    from hermes3d.core.agents.tool_registrations import _tool_dispatch

    with pytest.raises(ValueError, match="unknown strategy"):
        _tool_dispatch(
            stl_x_mm=10, stl_y_mm=10, stl_z_mm=10,
            material="PLA", strategy="not_a_real_strategy",
        )


# ---------------------------------------------------------------------------
# queue (filesystem-backed)
# ---------------------------------------------------------------------------


def test_queue_add_with_real_file_and_status(tmp_path, isolated_paths):
    from hermes3d.core.agents.tool_registrations import (
        _tool_queue_add,
        _tool_queue_status,
    )

    stl = tmp_path / "cube.stl"
    _write_minimal_stl(stl)

    add_result = _tool_queue_add(
        mesh_path=str(stl), material="PETG", quality_level="normal"
    )
    assert add_result["ok"] is True
    assert add_result["state"] == "queued"
    assert len(add_result["mesh_sha256"]) == 64  # full SHA256 hex
    assert add_result["material"] == "PETG"

    # File exists at the right env-overridden path
    assert Path(os.environ["HERMES3D_QUEUE"]).exists()

    status = _tool_queue_status()
    assert status["total"] == 1
    assert status["by_state"] == {"queued": 1}
    assert status["jobs"][0]["material"] == "PETG"


def test_queue_add_refuses_missing_file_without_explicit_sha(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_queue_add

    result = _tool_queue_add(
        mesh_path="/does/not/exist/at/all.stl", material="PLA"
    )
    assert result["ok"] is False
    assert "does not exist" in result["error"]


def test_queue_add_accepts_explicit_sha_for_remote_mesh(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_queue_add

    result = _tool_queue_add(
        mesh_path="s3://parts/widget.stl",
        material="PLA",
        mesh_sha256="a" * 64,
    )
    assert result["ok"] is True
    assert result["mesh_sha256"] == "a" * 64


def test_queue_status_invalid_state_raises(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_queue_status

    with pytest.raises(ValueError, match="unknown state"):
        _tool_queue_status(state="not_a_real_state")


# ---------------------------------------------------------------------------
# spool
# ---------------------------------------------------------------------------


def test_spool_list_empty_then_populated(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_spool_list
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    # Empty - SpoolTracker happily creates an empty store
    result = _tool_spool_list()
    assert result["count"] == 0
    assert result["spools"] == []

    # Populate via the real SpoolTracker, then read back through the shim
    tracker = SpoolTracker(os.environ["HERMES3D_SPOOLS"])
    tracker.add(
        material="PLA", color="matte black", color_hex="#1a1a1a",
        vendor="Polymaker", initial_grams=1000.0, diameter_mm=1.75,
    )
    tracker.add(
        material="PETG", color="translucent blue", color_hex="#3344aa",
        vendor="eSun", initial_grams=750.0, diameter_mm=1.75,
    )

    result = _tool_spool_list()
    assert result["count"] == 2
    materials = {s["material"] for s in result["spools"]}
    assert materials == {"PLA", "PETG"}

    # Filter by material
    result_pla = _tool_spool_list(material="PLA")
    assert result_pla["count"] == 1
    assert result_pla["spools"][0]["vendor"] == "Polymaker"


# ---------------------------------------------------------------------------
# estimate_cost
# ---------------------------------------------------------------------------


def test_estimate_cost_basic_pla():
    from hermes3d.core.agents.tool_registrations import _tool_estimate_cost

    result = _tool_estimate_cost(
        printer_id="prusa_mk3s",
        material="PLA",
        filament_g=125.0,
        duration_hours=4.5,
    )
    assert result["printer_id"] == "prusa_mk3s"
    assert result["filament_cost_usd"] > 0
    assert result["energy_cost_usd"] > 0
    assert result["total_cost_usd"] == pytest.approx(
        result["filament_cost_usd"] + result["energy_cost_usd"], abs=0.01
    )
    assert result["typical_wattage"] > 0


def test_estimate_cost_unknown_material_uses_fallback():
    from hermes3d.core.agents.tool_registrations import _tool_estimate_cost

    result = _tool_estimate_cost(
        printer_id="flsun_s1",
        material="UNOBTAINIUM",
        filament_g=50.0,
        duration_hours=2.0,
    )
    # Should not raise; should fall back to default $25/kg with a note
    assert result["filament_cost_usd"] == pytest.approx(50 / 1000 * 25, abs=0.01)
    assert any("unknown material" in n for n in result["notes"])


# ---------------------------------------------------------------------------
# calibration_macro
# ---------------------------------------------------------------------------


def test_calibration_macro_known_kinds():
    from hermes3d.core.agents.tool_registrations import _tool_calibration_macro

    for kind in (
        "input_shaper",
        "pressure_advance",
        "flow_ratio",
        "shaper_autocalibrate",
        "bed_mesh",
    ):
        result = _tool_calibration_macro(kind=kind)
        assert result["kind"] == kind
        assert result["macro"]


def test_calibration_macro_unknown_kind_raises():
    from hermes3d.core.agents.tool_registrations import _tool_calibration_macro

    with pytest.raises(ValueError, match="unknown calibration kind"):
        _tool_calibration_macro(kind="not_a_real_kind")


# ---------------------------------------------------------------------------
# mesh_analyze
# ---------------------------------------------------------------------------


def test_mesh_analyze_real_stl(tmp_path):
    from hermes3d.core.agents.tool_registrations import _tool_mesh_analyze

    stl = tmp_path / "cube.stl"
    _write_minimal_stl(stl)

    result = _tool_mesh_analyze(mesh_path=str(stl))
    # 10mm cube
    assert result["bbox_mm"] == [10.0, 10.0, 10.0]
    assert result["triangle_count"] == 12
    assert result["volume_mm3"] == pytest.approx(1000.0, rel=0.01)
    assert result["is_watertight"] is True
    assert isinstance(result["risk_flags"], list)


# ---------------------------------------------------------------------------
# failure_forecast
# ---------------------------------------------------------------------------


def test_failure_forecast_no_history_no_skills_baseline(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_failure_forecast

    result = _tool_failure_forecast(printer_id="prusa_mk3s", material="PLA")
    assert 0.0 <= result["failure_probability"] <= 1.0
    assert result["confidence"] in {"low", "medium", "high"}
    # No history + no skills file => citations should be empty or only about baseline
    assert isinstance(result["citations"], list)


# ---------------------------------------------------------------------------
# skill_lookup
# ---------------------------------------------------------------------------


def test_skill_lookup_no_store(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_skill_lookup

    # No file at HERMES3D_SKILLS path yet
    result = _tool_skill_lookup(kind="failure_pattern")
    assert result["count"] == 0
    assert "no skill store" in result.get("note", "")


def test_skill_lookup_with_real_skills(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_skill_lookup
    from hermes3d.core.memory.skill_store import (
        SkillKind,
        SkillScope,
        SkillStore,
    )

    store = SkillStore(os.environ["HERMES3D_SKILLS"])
    store.add(
        skill_kind=SkillKind.FAILURE_PATTERN,
        name="petg_glass_no_glue_lifts",
        scope=SkillScope(printer_id="prusa_mk3s", material="PETG"),
        body={"observed_failure_rate": 0.45},
        confidence=0.78,
    )
    store.add(
        skill_kind=SkillKind.PRINTER_QUIRK,
        name="d01_pro_z_wobble_above_180",
        scope=SkillScope(printer_id="tronxy_d01_pro"),
        body={"observation": "Z-wobble at >180mm prints"},
        confidence=0.65,
    )

    result = _tool_skill_lookup(
        kind="failure_pattern", printer_id="prusa_mk3s", material="PETG"
    )
    assert result["count"] == 1
    assert result["skills"][0]["name"] == "petg_glass_no_glue_lifts"

    # Different scope shouldn't match
    miss = _tool_skill_lookup(
        kind="failure_pattern", printer_id="flsun_s1", material="ASA"
    )
    assert miss["count"] == 0


def test_skill_lookup_invalid_kind_raises(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_skill_lookup

    with pytest.raises(ValueError, match="unknown skill kind"):
        _tool_skill_lookup(kind="not_a_real_kind")


# ---------------------------------------------------------------------------
# fleet_status (real probe — printers offline in this sandbox)
# ---------------------------------------------------------------------------


def test_fleet_status_runs_against_offline_fleet(isolated_paths):
    """We don't have real Moonraker hosts in this test environment, so every
    printer should come back unreachable. The shim must still successfully
    enumerate all 12 of them with profile metadata intact."""
    from hermes3d.core.agents.tool_registrations import _tool_fleet_status

    result = _tool_fleet_status(include_offline=True, timeout_s=0.2)
    assert result["count"] == 12
    by_id = {p["printer_id"]: p for p in result["printers"]}
    # All 12 known printers
    for expected in (
        "flsun_qqs_pro",
        "flsun_t1_a",
        "flsun_t1_b",
        "flsun_super_racer",
        "flsun_s1",
        "flsun_v400",
        "creality_cr10s",
        "creality_cr6_max",
        "prusa_mk3s",
        "sovol_sv01",
        "tronxy_d01_pro",
        "tronxy_x5sa_pro",
    ):
        assert expected in by_id, f"missing {expected}"
        assert by_id[expected]["bed"]
        assert by_id[expected]["kinematics"]


def test_fleet_status_filter_offline(isolated_paths):
    from hermes3d.core.agents.tool_registrations import _tool_fleet_status

    # In sandbox every printer is unreachable — include_offline=False => empty
    result = _tool_fleet_status(include_offline=False, timeout_s=0.2)
    assert result["count"] == 0


# ---------------------------------------------------------------------------
# Registry round-trip via .call()
# ---------------------------------------------------------------------------


def test_call_via_registry_filters_unknown_kwargs(fresh_registry, tmp_path):
    """tool_registry.call() must drop unknown kwargs (its existing contract)."""
    from hermes3d.core.agents.tool_registrations import register_builtin_tools

    register_builtin_tools(fresh_registry)
    result = fresh_registry.call(
        "calibration_macro",
        kind="input_shaper",
        ignored_extra_kwarg="should not crash",
    )
    assert result["kind"] == "input_shaper"


def test_call_via_registry_dispatch_returns_dict(fresh_registry):
    from hermes3d.core.agents.tool_registrations import register_builtin_tools

    register_builtin_tools(fresh_registry)
    result = fresh_registry.call(
        "dispatch",
        stl_x_mm=50.0, stl_y_mm=50.0, stl_z_mm=50.0,
        material="PLA", strategy="fastest",
    )
    assert isinstance(result, dict)
    assert "selected_printer_id" in result
    assert "candidates" in result
