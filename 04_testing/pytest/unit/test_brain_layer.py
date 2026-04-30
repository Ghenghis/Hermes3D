"""Tests for the agentic brain layer added in v5 expansion phase."""
from __future__ import annotations

import time
from pathlib import Path

import pytest
import trimesh


# =============================================================================
# Orchestration graph
# =============================================================================


def test_workflow_state_serialization_roundtrip():
    from hermes3d.core.orchestration import WorkflowState, NodeOutcome, NodeResult
    s = WorkflowState(workflow_id="wf-test", created_unix=1000.0,
                      data={"a": 1})
    s.history.append(NodeResult(
        node_name="x", outcome=NodeOutcome.PASS,
        started_unix=1000.0, ended_unix=1001.0,
        state_patch={"k": "v"}, notes=["ok"],
    ))
    d = s.to_dict()
    s2 = WorkflowState.from_dict(d)
    assert s2.workflow_id == "wf-test"
    assert s2.history[0].outcome == NodeOutcome.PASS
    assert s2.data == {"a": 1}


def test_print_workflow_dry_run_completes(tmp_path: Path):
    from hermes3d.core.orchestration import build_print_workflow, new_state
    mesh = trimesh.creation.box(extents=(60, 40, 25))
    stl = tmp_path / "t.stl"
    mesh.export(stl)
    graph = build_print_workflow(checkpoint_dir=tmp_path / "cp")
    state = new_state(initial={
        "mesh_path": str(stl),
        "material": "PLA",
        "strategy": "auto",
        "queue_path": str(tmp_path / "queue.json"),
        "dry_run": True,
        "auto_orient_enabled": False,
    })
    final = graph.run(state)
    assert not final.aborted
    # Required nodes that ran successfully
    pass_nodes = {h.node_name for h in final.history
                  if h.outcome.value == "pass"}
    assert "enqueue" in pass_nodes
    assert "truth_gate" in pass_nodes
    assert "dispatch" in pass_nodes
    assert "preflight" in pass_nodes
    # Dispatcher selected a printer
    assert final.data["selected_printer_id"] is not None


def test_print_workflow_repair_path(tmp_path: Path):
    """A non-watertight mesh should trigger the repair node and recover."""
    import numpy as np
    from hermes3d.core.orchestration import build_print_workflow, new_state
    mesh = trimesh.creation.box(extents=(50, 40, 30))
    # Drop one face -> non-watertight
    mask = np.ones(len(mesh.faces), dtype=bool)
    mask[-1] = False
    mesh.update_faces(mask)
    stl = tmp_path / "broken.stl"
    mesh.export(stl)
    assert not trimesh.load_mesh(stl).is_watertight

    graph = build_print_workflow()
    state = new_state(initial={
        "mesh_path": str(stl),
        "material": "PLA",
        "queue_path": str(tmp_path / "q.json"),
        "dry_run": True,
        "auto_orient_enabled": False,
    })
    final = graph.run(state)
    repair_history = [h for h in final.history if h.node_name == "repair_if_needed"]
    assert repair_history, "repair node should have run"
    assert repair_history[0].outcome.value == "pass"
    # Mesh path was updated to repaired version
    assert "repaired" in final.data["mesh_path"] or "oriented" in final.data["mesh_path"]


def test_print_workflow_checkpoint_resume(tmp_path: Path):
    from hermes3d.core.orchestration import build_print_workflow, new_state
    mesh = trimesh.creation.box(extents=(40, 30, 20))
    stl = tmp_path / "x.stl"
    mesh.export(stl)
    graph = build_print_workflow(checkpoint_dir=tmp_path / "cp")
    state = new_state(initial={
        "mesh_path": str(stl),
        "material": "PLA",
        "queue_path": str(tmp_path / "q.json"),
        "dry_run": True,
        "auto_orient_enabled": False,
    })
    final = graph.run(state)
    # Reload the same workflow
    cp = graph.load_checkpoint(state.workflow_id)
    assert cp is not None
    assert cp.workflow_id == state.workflow_id
    assert len(cp.history) == len(final.history)


# =============================================================================
# Skill memory
# =============================================================================


def test_skill_store_add_lookup_persist(tmp_path: Path):
    from hermes3d.core.memory import SkillStore, SkillKind, SkillScope
    store = SkillStore(tmp_path / "sk.json")
    s = store.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="asa_d01_chamber",
        scope=SkillScope(printer_id="tronxy_d01_pro", material="ASA"),
        body={"chamber_temperature": 50},
        confidence=0.8,
    )
    found = store.lookup(kind=SkillKind.PARAMETER_OVERRIDE,
                         printer_id="tronxy_d01_pro", material="ASA")
    assert len(found) == 1
    assert found[0].skill_id == s.skill_id

    # Reload
    store2 = SkillStore(tmp_path / "sk.json")
    assert len(store2.list()) == 1


def test_skill_store_specificity_ordering(tmp_path: Path):
    from hermes3d.core.memory import SkillStore, SkillKind, SkillScope
    store = SkillStore(tmp_path / "sk.json")
    # Generic skill (matches anything)
    store.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE, name="generic",
        scope=SkillScope(),
        body={"x": 1}, confidence=0.9,
    )
    # Specific skill (matches printer + material)
    store.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE, name="specific",
        scope=SkillScope(printer_id="flsun_t1_a", material="PLA"),
        body={"x": 2}, confidence=0.5,
    )
    matches = store.lookup(kind=SkillKind.PARAMETER_OVERRIDE,
                            printer_id="flsun_t1_a", material="PLA")
    # Specific must come first, even though confidence is lower
    assert matches[0].name == "specific"
    assert matches[1].name == "generic"


def test_skill_store_reinforce_caps_at_one(tmp_path: Path):
    from hermes3d.core.memory import SkillStore, SkillKind, SkillScope
    store = SkillStore(tmp_path / "sk.json")
    s = store.add(skill_kind=SkillKind.USER_PREFERENCE, name="x",
                   scope=SkillScope(), body={}, confidence=0.95)
    for _ in range(10):
        store.reinforce(s.skill_id, confidence_delta=0.1)
    assert store.get(s.skill_id).confidence == 1.0


def test_skill_scope_specificity_count():
    from hermes3d.core.memory import SkillScope
    assert SkillScope().specificity() == 0
    assert SkillScope(printer_id="x").specificity() == 1
    assert SkillScope(printer_id="x", material="PLA").specificity() == 2
    assert SkillScope(printer_id="x", material="PLA",
                      quality_level="fine", hour_of_day=14).specificity() == 4


# =============================================================================
# Ollama client
# =============================================================================


def test_ollama_unavailable_does_not_crash():
    from hermes3d.core.llm import OllamaClient
    c = OllamaClient(base_url="http://localhost:1", timeout_s=0.5)
    assert c.available() is False


def test_ollama_extract_json_raw():
    from hermes3d.core.llm.ollama_client import _extract_json
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_ollama_extract_json_fenced():
    from hermes3d.core.llm.ollama_client import _extract_json
    assert _extract_json('```json\n{"x": [1,2]}\n```') == {"x": [1, 2]}


def test_ollama_extract_json_with_preamble():
    from hermes3d.core.llm.ollama_client import _extract_json
    txt = "Sure, here is the JSON:\n{\"selected\": \"flsun_t1_a\"}"
    assert _extract_json(txt) == {"selected": "flsun_t1_a"}


# =============================================================================
# Multi-agent
# =============================================================================


def test_multi_agent_clean_approval():
    from hermes3d.core.agents.dispatcher import (
        DispatchRequest, DispatchStrategy,
    )
    from hermes3d.core.agents.multi_agent import run_multi_agent
    result = run_multi_agent(
        request=DispatchRequest(
            mesh_extents_mm=(180, 100, 55), mesh_xy_radius_mm=90.0,
            material="PLA", strategy=DispatchStrategy.AUTO,
        ),
    )
    assert result.approved
    assert len(result.rounds) == 1


def test_multi_agent_history_drives_revision(tmp_path: Path):
    from hermes3d.core.agents.dispatcher import (
        DispatchRequest, DispatchStrategy,
    )
    from hermes3d.core.agents.multi_agent import run_multi_agent
    from hermes3d.core.farm.print_history import PrintHistory

    h = PrintHistory(tmp_path / "h.jsonl")
    # 10 prints on prusa_mk3s, 70% failure rate
    for i in range(10):
        h.append(job_id=f"j{i}", printer_id="prusa_mk3s", material="PLA",
                 started_unix=time.time() - 3600 * (i + 1),
                 ended_unix=time.time() - 3600 * i,
                 success=(i >= 7))
    result = run_multi_agent(
        request=DispatchRequest(
            mesh_extents_mm=(180, 100, 55), mesh_xy_radius_mm=90.0,
            material="PLA",
        ),
        history=h,
    )
    # Must have gone through at least 2 rounds
    assert len(result.rounds) >= 2
    # First round verdict was REVISE
    assert result.rounds[0]["verdict"] == "revise"
    # Final selection is NOT prusa_mk3s
    assert result.final_decision.selected_printer_id != "prusa_mk3s"


def test_multi_agent_skill_attaches_param_overrides(tmp_path: Path):
    from hermes3d.core.agents.dispatcher import (
        DispatchRequest, DispatchStrategy,
    )
    from hermes3d.core.agents.multi_agent import run_multi_agent
    from hermes3d.core.memory import SkillStore, SkillKind, SkillScope

    sk = SkillStore(tmp_path / "sk.json")
    sk.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="asa_d01_chamber",
        scope=SkillScope(printer_id="tronxy_d01_pro", material="ASA"),
        body={"chamber_temperature": 50},
        confidence=0.8,
    )
    result = run_multi_agent(
        request=DispatchRequest(
            mesh_extents_mm=(80, 80, 40), mesh_xy_radius_mm=56.6,
            material="ASA",
        ),
        skills=sk,
    )
    assert result.approved
    overrides = result.rounds[0]["suggestions"].get("parameter_overrides", [])
    assert len(overrides) == 1
    assert overrides[0]["name"] == "asa_d01_chamber"


# =============================================================================
# Failure predictor
# =============================================================================


def test_failure_predict_baseline_no_data():
    from hermes3d.core.intelligence import predict_failure
    f = predict_failure(printer_id="flsun_t1_a", material="PLA")
    assert f.failure_probability == pytest.approx(0.10, abs=0.01)
    assert f.confidence == "low"


def test_failure_predict_high_confidence_with_history(tmp_path: Path):
    from hermes3d.core.farm.print_history import PrintHistory
    from hermes3d.core.intelligence import predict_failure
    h = PrintHistory(tmp_path / "h.jsonl")
    for i in range(10):
        h.append(job_id=f"j{i}", printer_id="flsun_t1_a", material="PLA",
                 started_unix=time.time() - 3600 * (i + 1),
                 ended_unix=time.time() - 3600 * i,
                 success=(i >= 2))
    f = predict_failure(printer_id="flsun_t1_a", material="PLA", history=h)
    # 10 prints, 2 failures = 20% printer-history failure rate
    # Combined with material baseline (also 80% success) -> medium-high
    assert f.confidence in {"medium", "high"}
    assert f.failure_probability < 0.30


def test_failure_predict_skill_dominates(tmp_path: Path):
    from hermes3d.core.intelligence import predict_failure
    from hermes3d.core.memory import SkillStore, SkillKind, SkillScope
    sk = SkillStore(tmp_path / "sk.json")
    sk.add(skill_kind=SkillKind.FAILURE_PATTERN,
           name="bad_combo",
           scope=SkillScope(printer_id="creality_cr10s", material="PETG"),
           body={"observed_failure_rate": 0.50},
           confidence=0.8)
    f = predict_failure(printer_id="creality_cr10s", material="PETG",
                          skills=sk)
    # 50% skill-rate weighted at 0.5 + 10% baseline weighted at 0.5 = 0.30
    assert f.failure_probability == pytest.approx(0.30, abs=0.05)
    assert "skill" in f.components


# =============================================================================
# Integrations
# =============================================================================


def test_octoprint_client_unreachable_returns_falsy_state():
    from hermes3d.core.integrations import OctoPrintClient
    c = OctoPrintClient(base_url="http://localhost:1", timeout_s=0.5)
    assert c.reachable() is False
    state = c.printer_state()
    assert state["reachable"] is False
    assert "error" in state


def test_obico_client_status_action_thresholds():
    from hermes3d.core.integrations import (
        ObicoClient, ObicoAction, DEFAULT_FAILURE_THRESHOLD,
    )
    # Build by hand with threshold knobs
    c = ObicoClient(base_url="http://localhost:1", timeout_s=0.1,
                     failure_threshold=0.45, heads_up_threshold=0.20)
    assert c.failure_threshold == 0.45
    assert c.heads_up_threshold == 0.20


def test_obico_status_to_dict_serializes_action():
    from hermes3d.core.integrations import ObicoStatus, ObicoAction
    s = ObicoStatus(printer_id="x", is_printing=True,
                     failure_probability=0.5,
                     recommended_action=ObicoAction.PAUSE)
    d = s.to_dict()
    assert d["recommended_action"] == "pause"
