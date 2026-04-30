"""Tests for the agentic + automation modules added in v5."""

from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import pytest
import trimesh


# =============================================================================
# Mesh repair
# =============================================================================


def test_repair_heals_cube_with_missing_face():
    from hermes3d.core.agents.mesh_repair import repair_mesh

    m = trimesh.creation.box(extents=(20, 20, 20))
    assert m.is_watertight
    # Drop the last face
    mask = np.ones(len(m.faces), dtype=bool)
    mask[-1] = False
    m.update_faces(mask)
    assert not m.is_watertight

    fixed, report = repair_mesh(m)
    assert fixed.is_watertight
    assert report.succeeded
    assert report.initial_watertight is False
    assert report.final_watertight is True
    # Face count restored
    assert len(fixed.faces) >= 12


def test_repair_does_not_mutate_input():
    from hermes3d.core.agents.mesh_repair import repair_mesh

    m = trimesh.creation.box(extents=(10, 10, 10))
    initial_faces = len(m.faces)
    repair_mesh(m)
    assert len(m.faces) == initial_faces  # original unchanged


def test_repair_handles_already_clean_mesh():
    from hermes3d.core.agents.mesh_repair import repair_mesh

    m = trimesh.creation.box(extents=(10, 10, 10))
    fixed, report = repair_mesh(m)
    assert report.final_watertight is True
    assert report.initial_watertight is True


# =============================================================================
# Auto-orient
# =============================================================================


def test_auto_orient_returns_chosen_and_candidates():
    from hermes3d.core.agents.auto_orient import auto_orient

    cone = trimesh.creation.cone(radius=10, height=20)
    decision = auto_orient(cone)
    assert decision.chosen is not None
    assert len(decision.candidates) == 6
    # Sorted descending by score
    scores = [c.score for c in decision.candidates]
    assert scores == sorted(scores, reverse=True)


def test_auto_orient_chooses_base_down_for_pyramid():
    from hermes3d.core.agents.auto_orient import auto_orient

    cone = trimesh.creation.cone(radius=20, height=40)
    # tip up = base down at Z=0 (this is "identity")
    decision = auto_orient(cone)
    # Identity should win (or rotX180 — both put a flat circle on bed)
    assert decision.chosen.candidate_name in {"identity", "rotX180"}
    assert decision.chosen.bed_contact_area_mm2 > 0


# =============================================================================
# Print history
# =============================================================================


def test_print_history_append_and_iter(tmp_path: Path):
    from hermes3d.core.farm.print_history import PrintHistory

    h = PrintHistory(tmp_path / "history.jsonl")
    h.append(
        job_id="a",
        printer_id="flsun_t1_a",
        material="PLA",
        started_unix=1000.0,
        ended_unix=4600.0,
        success=True,
        filament_used_g=42,
    )
    h.append(
        job_id="b",
        printer_id="prusa_mk3s",
        material="PETG",
        started_unix=5000.0,
        ended_unix=11000.0,
        success=False,
        error="thermal runaway",
    )
    records = h.list()
    assert len(records) == 2
    assert records[0].duration_min == pytest.approx(60.0)
    assert records[1].success is False
    assert records[1].error == "thermal runaway"


def test_print_history_aggregate_metrics(tmp_path: Path):
    from hermes3d.core.farm.print_history import PrintHistory, aggregate_metrics

    h = PrintHistory(tmp_path / "h.jsonl")
    for i in range(5):
        h.append(
            job_id=f"j{i}",
            printer_id="flsun_t1_a",
            material="PLA",
            started_unix=1000.0 + i,
            ended_unix=4600.0 + i,
            success=(i != 2),
            filament_used_g=20,
        )
    metrics = aggregate_metrics(h)
    assert metrics.total_prints == 5
    pa = metrics.per_printer["flsun_t1_a"]
    assert pa.successful == 4
    assert pa.failed == 1
    assert pa.success_rate == pytest.approx(0.8)
    assert metrics.per_material["PLA"].total_filament_grams == pytest.approx(100.0)


# =============================================================================
# Cost estimator
# =============================================================================


def test_cost_estimate_pla_short_print():
    from hermes3d.core.farm.cost_estimator import estimate_cost

    e = estimate_cost(printer_id="flsun_t1_a", material="PLA", filament_g=110, duration_hours=6.0)
    assert e.filament_cost_usd == pytest.approx(2.20, abs=0.01)
    assert e.energy_kwh == pytest.approx(1.5, abs=0.01)
    assert e.energy_cost_usd > 0


def test_cost_estimate_unknown_material_uses_fallback():
    from hermes3d.core.farm.cost_estimator import estimate_cost

    e = estimate_cost(
        printer_id="prusa_mk3s", material="UNOBTAINIUM", filament_g=100, duration_hours=2
    )
    assert e.filament_cost_usd == pytest.approx(2.50, abs=0.01)
    assert any("unknown material" in n for n in e.notes)


def test_cost_estimate_negative_inputs_raise():
    from hermes3d.core.farm.cost_estimator import estimate_cost

    with pytest.raises(ValueError):
        estimate_cost(printer_id="prusa_mk3s", material="PLA", filament_g=-1, duration_hours=1)
    with pytest.raises(ValueError):
        estimate_cost(printer_id="prusa_mk3s", material="PLA", filament_g=10, duration_hours=-1)


# =============================================================================
# Equivalence groups
# =============================================================================


def test_equivalence_group_includes_t1_pool():
    from hermes3d.core.agents.equivalence import DEFAULT_GROUPS

    pool = next(g for g in DEFAULT_GROUPS if g.group_id == "flsun_t1_pool")
    assert "flsun_t1_a" in pool.members
    assert "flsun_t1_b" in pool.members


def test_equivalence_least_busy_prefers_ready():
    from hermes3d.core.agents.equivalence import (
        DEFAULT_GROUPS,
        least_busy_member,
    )

    pool = DEFAULT_GROUPS[0]
    live = {
        "flsun_t1_a": {"reachable": True, "klippy_state": "ready"},
        "flsun_t1_b": {"reachable": True, "klippy_state": "printing"},
    }
    assert least_busy_member(pool, live) == "flsun_t1_a"


def test_equivalence_expand_pool_request():
    from hermes3d.core.agents.equivalence import expand_pool_request

    live = {
        "flsun_t1_a": {"reachable": True, "klippy_state": "printing"},
        "flsun_t1_b": {"reachable": True, "klippy_state": "ready"},
    }
    # Group ID -> resolved to the ready member
    assert expand_pool_request("flsun_t1_pool", live) == "flsun_t1_b"
    # Real ID -> unchanged
    assert expand_pool_request("prusa_mk3s", live) == "prusa_mk3s"


# =============================================================================
# Scheduler
# =============================================================================


def test_scheduler_short_print_at_3pm_allowed():
    from hermes3d.core.agents.scheduler import schedule_window, SchedulerPolicy

    now = dt.datetime(2026, 4, 29, 15, 0)
    d = schedule_window(duration_minutes=120, policy=SchedulerPolicy(), now=now)
    assert d.allowed
    assert "17:00" in d.estimated_finish_local


def test_scheduler_quiet_hours_blocks_start():
    from hermes3d.core.agents.scheduler import schedule_window, SchedulerPolicy

    now = dt.datetime(2026, 4, 29, 23, 30)
    d = schedule_window(duration_minutes=240, policy=SchedulerPolicy(), now=now)
    assert not d.allowed
    assert any("quiet hours" in r for r in d.reasons)
    assert d.suggested_start_local is not None


def test_scheduler_duration_cap():
    from hermes3d.core.agents.scheduler import schedule_window, SchedulerPolicy

    now = dt.datetime(2026, 4, 29, 9, 0)
    p = SchedulerPolicy(max_print_duration_minutes=120)
    d = schedule_window(duration_minutes=300, policy=p, now=now)
    assert not d.allowed
    assert any("exceeds policy cap" in r for r in d.reasons)


# =============================================================================
# Job queue
# =============================================================================


def test_queue_enqueue_dispatch_slice_succeed_flow(tmp_path: Path):
    from hermes3d.core.agents.job_queue import JobQueue, JobState

    q = JobQueue(tmp_path / "q.json")
    j = q.enqueue(mesh_path="/x.stl", mesh_sha256="abc", material="PLA")
    assert j.state == JobState.QUEUED

    q.transition_job(j.job_id, JobState.DISPATCHED, target_printer_id="flsun_t1_a")
    q.transition_job(j.job_id, JobState.VALIDATED)
    q.transition_job(j.job_id, JobState.SLICED, sliced_gcode_path="/x.gcode")
    q.transition_job(j.job_id, JobState.UPLOADED)
    q.transition_job(j.job_id, JobState.PRINTING)
    final = q.transition_job(j.job_id, JobState.SUCCEEDED)
    assert final.state == JobState.SUCCEEDED
    # All 7 transitions in history (1 enqueue + 6 advances)
    assert len(final.history) == 7


def test_queue_illegal_transition_raises(tmp_path: Path):
    from hermes3d.core.agents.job_queue import JobQueue, JobState

    q = JobQueue(tmp_path / "q.json")
    j = q.enqueue(mesh_path="/x.stl", mesh_sha256="a", material="PLA")
    # QUEUED can't jump straight to PRINTING
    with pytest.raises(ValueError):
        q.transition_job(j.job_id, JobState.PRINTING)


def test_queue_persists_across_reload(tmp_path: Path):
    from hermes3d.core.agents.job_queue import JobQueue, JobState

    qpath = tmp_path / "q.json"
    q1 = JobQueue(qpath)
    j = q1.enqueue(mesh_path="/x.stl", mesh_sha256="a", material="PLA")
    q1.transition_job(j.job_id, JobState.DISPATCHED, target_printer_id="prusa_mk3s")
    # Reload from disk
    q2 = JobQueue(qpath)
    j2 = q2.get(j.job_id)
    assert j2.state == JobState.DISPATCHED
    assert j2.target_printer_id == "prusa_mk3s"


# =============================================================================
# Spool tracker
# =============================================================================


def test_spool_tracker_add_load_consume(tmp_path: Path):
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    st = SpoolTracker(tmp_path / "sp.json")
    s = st.add(
        material="PLA", color="black", color_hex="#000", vendor="Polymaker", initial_grams=1000
    )
    st.load_on_printer(s.spool_id, "flsun_t1_a")
    st.consume(s.spool_id, 14.0, job_id="job-1")
    s2 = st.get(s.spool_id)
    assert s2.remaining_grams == pytest.approx(986.0)
    assert s2.loaded_on_printer == "flsun_t1_a"
    assert s2.percent_remaining == pytest.approx(98.6, abs=0.1)


def test_spool_tracker_loading_unloads_previous(tmp_path: Path):
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    st = SpoolTracker(tmp_path / "sp.json")
    s1 = st.add(material="PLA", color="A", color_hex="#A", vendor="V", initial_grams=500)
    s2 = st.add(material="PLA", color="B", color_hex="#B", vendor="V", initial_grams=500)
    st.load_on_printer(s1.spool_id, "flsun_t1_a")
    assert st.get(s1.spool_id).loaded_on_printer == "flsun_t1_a"
    st.load_on_printer(s2.spool_id, "flsun_t1_a")
    # s1 must be unloaded automatically
    assert st.get(s1.spool_id).loaded_on_printer is None
    assert st.get(s2.spool_id).loaded_on_printer == "flsun_t1_a"


def test_spool_tracker_consume_negative_raises(tmp_path: Path):
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    st = SpoolTracker(tmp_path / "sp.json")
    s = st.add(material="PLA", color="A", color_hex="#A", vendor="V", initial_grams=500)
    with pytest.raises(ValueError):
        st.consume(s.spool_id, -1.0)


# =============================================================================
# G-code analyzer
# =============================================================================


@pytest.fixture
def synthetic_gcode(tmp_path):
    p = tmp_path / "s.gcode"
    p.write_text(
        "; generated by PrusaSlicer 2.7.0+ on 2026-04-29\n"
        "; layer_height = 0.2\n"
        "; total layer count = 87\n"
        "; nozzle_temperature = 215\n"
        "; bed_temperature = 60\n"
        "; fill_density = 20%\n"
        "; support_material = 0\n"
        "G28\nG29\n"
        ";LAYER:0\nG1 X0 Y0 F3000\nG1 X10 Y10 E0.5 F600\n"
        "G1 E-2.0 F1800\n"
        ";LAYER:1\nG1 X10 Y10 E2.0 F600\n"
        "; filament used [mm] = 4523.42\n"
        "; filament used [g] = 13.6\n"
        "; estimated printing time (normal mode) = 1h 23m 15s\n",
        encoding="utf-8",
    )
    return p


def test_gcode_analyzer_extracts_metadata(synthetic_gcode):
    from hermes3d.core.slicer.gcode_analyzer import analyze_gcode

    a = analyze_gcode(synthetic_gcode)
    assert a.slicer_name == "PrusaSlicer"
    assert a.layer_count == 87
    assert a.layer_height_mm == 0.2
    assert a.estimated_print_time_min == pytest.approx(83.25, abs=0.1)
    assert a.filament_used_g == pytest.approx(13.6)
    assert a.nozzle_temp_c == 215.0
    assert a.bed_temp_c == 60.0


def test_gcode_analyzer_missing_file_raises():
    from hermes3d.core.slicer.gcode_analyzer import analyze_gcode

    with pytest.raises(FileNotFoundError):
        analyze_gcode("/no/such/file.gcode")


# =============================================================================
# Notifier
# =============================================================================


def test_notifier_no_channels_returns_empty():
    """With no env vars set, the Notifier reports no channels."""
    from hermes3d.core.notifications import Notifier, NotificationEvent

    n = Notifier(discord_url=None, slack_url=None, generic_url=None)
    assert n.configured_channels == ()
    assert n.notify(NotificationEvent(title="t", message="m")) == []


def test_notifier_payload_shapes():
    """Verify the payload shapes are correct (offline)."""
    from hermes3d.core.notifications.notifier import (
        discord_payload,
        slack_payload,
        NotificationEvent,
        NotificationLevel,
    )

    e = NotificationEvent(
        title="Print done",
        message="OK",
        level=NotificationLevel.SUCCESS,
        printer_id="flsun_t1_a",
        job_id="abc12345",
    )
    d = discord_payload(e)
    assert "embeds" in d and len(d["embeds"]) == 1
    assert d["embeds"][0]["title"] == "Print done"
    assert d["embeds"][0]["color"] == 0x2ECC71  # green for success
    s = slack_payload(e)
    assert "attachments" in s and s["attachments"][0]["color"] == "#2ECC71"


# =============================================================================
# Preflight
# =============================================================================


def test_preflight_passes_clean_scenario():
    from hermes3d.core.agents.preflight import run_preflight
    from hermes3d.core.agents.scheduler import schedule_window, SchedulerPolicy
    from hermes3d.core.farm.cost_estimator import estimate_cost
    from hermes3d.core.farm.spool_tracker import Spool

    class FakeTG:
        passed = True

    class FakeAnalysis:
        risk_flags = []

    spool = Spool(
        spool_id="s",
        material="PLA",
        color="black",
        color_hex="#000",
        vendor="V",
        diameter_mm=1.75,
        initial_grams=1000,
        remaining_grams=900,
        loaded_on_printer="flsun_t1_a",
    )
    cost = estimate_cost(
        printer_id="flsun_t1_a", material="PLA", filament_g=110, duration_hours=6.0
    )
    schd = schedule_window(
        duration_minutes=360, policy=SchedulerPolicy(), now=dt.datetime(2026, 4, 29, 10, 0)
    )
    r = run_preflight(
        printer_id="flsun_t1_a",
        truth_gate_report=FakeTG(),
        live_state={"reachable": True, "klippy_state": "ready"},
        spool=spool,
        required_grams=110,
        required_material="PLA",
        schedule_decision=schd,
        cost_estimate=cost,
        budget_usd=50.0,
        gcode_analysis=FakeAnalysis(),
    )
    assert r.passed
    assert not r.has_warnings


def test_preflight_fails_when_spool_too_low():
    from hermes3d.core.agents.preflight import run_preflight
    from hermes3d.core.farm.spool_tracker import Spool

    spool = Spool(
        spool_id="s",
        material="PLA",
        color="black",
        color_hex="#000",
        vendor="V",
        diameter_mm=1.75,
        initial_grams=1000,
        remaining_grams=50,
    )
    r = run_preflight(
        printer_id="flsun_t1_a",
        spool=spool,
        required_grams=200,
        required_material="PLA",
    )
    assert not r.passed


def test_preflight_fails_on_wrong_material():
    from hermes3d.core.agents.preflight import run_preflight
    from hermes3d.core.farm.spool_tracker import Spool

    spool = Spool(
        spool_id="s",
        material="PETG",
        color="x",
        color_hex="#x",
        vendor="V",
        diameter_mm=1.75,
        initial_grams=1000,
        remaining_grams=900,
    )
    r = run_preflight(
        printer_id="flsun_t1_a",
        spool=spool,
        required_grams=100,
        required_material="PLA",
    )
    assert not r.passed


# =============================================================================
# Backup
# =============================================================================


def test_backup_restore_roundtrip(tmp_path: Path):
    from hermes3d.core.agents.job_queue import JobQueue
    from hermes3d.core.farm.backup import create_backup, restore_backup
    from hermes3d.core.farm.spool_tracker import SpoolTracker

    state = tmp_path / "var"
    state.mkdir()
    q = JobQueue(state / "queue.json")
    q.enqueue(mesh_path="/x.stl", mesh_sha256="a", material="PLA")
    st = SpoolTracker(state / "spools.json")
    st.add(material="PLA", color="x", color_hex="#x", vendor="V", initial_grams=500)

    out = tmp_path / "backups"
    bundle = create_backup(state_dir=state, out_dir=out)
    assert bundle.exists()

    restored = tmp_path / "restored"
    manifest = restore_backup(bundle, target_dir=restored)
    assert (restored / "queue.json").exists()
    assert (restored / "spools.json").exists()
    assert len(manifest.files) >= 2


def test_backup_refuses_overwrite_by_default(tmp_path: Path):
    from hermes3d.core.agents.job_queue import JobQueue
    from hermes3d.core.farm.backup import create_backup, restore_backup

    state = tmp_path / "v"
    state.mkdir()
    JobQueue(state / "queue.json").enqueue(mesh_path="/x", mesh_sha256="a", material="PLA")
    bundle = create_backup(state_dir=state, out_dir=tmp_path / "b")
    target = tmp_path / "t"
    target.mkdir()
    (target / "junk.txt").write_text("preexisting")
    with pytest.raises(FileExistsError):
        restore_backup(bundle, target_dir=target)


# =============================================================================
# REST API
# =============================================================================


@pytest.fixture
def api_client(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from hermes3d.api.server import create_app

    app = create_app(
        api_token="",
        queue_path=str(tmp_path / "q.json"),
        spools_path=str(tmp_path / "s.json"),
        history_path=str(tmp_path / "h.jsonl"),
    )
    return TestClient(app)


def test_api_health(api_client):
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["fleet_size"] == 12


def test_api_fleet_lists_all_printers(api_client):
    r = api_client.get("/fleet")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 12
    ids = [p["profile_id"] for p in data]
    assert "flsun_t1_a" in ids
    assert "prusa_mk3s" in ids


def test_api_dispatch_returns_selection(api_client):
    r = api_client.post(
        "/dispatch",
        json={
            "mesh_extents_mm": [180, 100, 55],
            "mesh_xy_radius_mm": 90.0,
            "material": "PLA",
            "strategy": "auto",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["selected_printer_id"] is not None
    assert len(body["candidates"]) <= 12


def test_api_queue_lifecycle(api_client):
    r = api_client.post(
        "/queue/jobs",
        json={
            "mesh_path": "/tmp/x.stl",
            "mesh_sha256": "abc",
            "material": "PLA",
        },
    )
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    r = api_client.get("/queue/jobs")
    assert r.status_code == 200
    assert any(j["job_id"] == job_id for j in r.json())
    r = api_client.post(f"/queue/jobs/{job_id}/cancel")
    assert r.status_code == 200
    assert r.json()["state"] == "cancelled"


def test_api_spool_lifecycle(api_client):
    r = api_client.post(
        "/spools",
        json={
            "material": "PLA",
            "color": "black",
            "color_hex": "#000",
            "vendor": "Polymaker",
            "initial_grams": 1000,
        },
    )
    assert r.status_code == 200
    spool_id = r.json()["spool_id"]
    r = api_client.post(f"/spools/{spool_id}/load", json={"printer_id": "flsun_t1_a"})
    assert r.status_code == 200
    r = api_client.post(f"/spools/{spool_id}/consume", json={"grams": 50.0})
    assert r.status_code == 200
    assert r.json()["remaining_grams"] == pytest.approx(950.0)


def test_api_metrics_prometheus_format(api_client):
    r = api_client.get("/metrics/prometheus")
    assert r.status_code == 200
    text = r.text
    assert "# HELP hermes3d_total_prints" in text
    assert "# TYPE hermes3d_total_prints counter" in text


def test_api_auth_required_when_token_set(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from hermes3d.api.server import create_app

    app = create_app(
        api_token="secret",
        queue_path=str(tmp_path / "q.json"),
        spools_path=str(tmp_path / "s.json"),
        history_path=str(tmp_path / "h.jsonl"),
    )
    c = TestClient(app)
    r = c.get("/fleet/flsun_t1_a/state")
    assert r.status_code == 401
    r = c.get("/fleet/flsun_t1_a/state", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 403


# =============================================================================
# MCP server
# =============================================================================


def test_mcp_tool_catalog_size():
    from hermes3d.api.mcp_server import TOOLS

    # The catalog is allowed to grow as we add tools; assert it has the
    # original ten plus all the brain-layer additions.
    assert len(TOOLS) >= 10
    names = {t["name"] for t in TOOLS}
    assert "hermes3d.dispatch" in names
    assert "hermes3d.fleet_status" in names
    assert "hermes3d.proof_verify" in names


def test_mcp_dispatch_handler_returns_selection():
    from hermes3d.api.mcp_server import get_handler

    handler = get_handler("hermes3d.dispatch")
    result = handler(
        {
            "mesh_extents_mm": [180, 100, 55],
            "mesh_xy_radius_mm": 90.0,
            "material": "PLA",
        }
    )
    assert result["selected_printer_id"] is not None
    assert "candidates" in result


def test_mcp_list_materials_handler():
    from hermes3d.api.mcp_server import get_handler

    result = get_handler("hermes3d.list_materials")({})
    materials = {m["material"] for m in result["materials"]}
    for required in {"PLA", "PETG", "ABS", "ASA", "TPU"}:
        assert required in materials


def test_mcp_unknown_tool_raises():
    from hermes3d.api.mcp_server import get_handler

    with pytest.raises(KeyError):
        get_handler("hermes3d.does_not_exist")
