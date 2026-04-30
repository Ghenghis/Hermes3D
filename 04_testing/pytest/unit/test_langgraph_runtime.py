"""Tests for LangGraphOrchestrator runtime + fallback path."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest
import trimesh


def _make_state(tmp_path: Path):
    from hermes3d.core.orchestration import new_state

    mesh = trimesh.creation.box(extents=(40, 30, 20))
    stl = tmp_path / "fixture.stl"
    mesh.export(stl)
    return new_state(
        initial={
            "mesh_path": str(stl),
            "material": "PLA",
            "strategy": "auto",
            "queue_path": str(tmp_path / "queue.json"),
            "dry_run": True,
            "auto_orient_enabled": False,
        }
    )


def _langgraph_installed() -> bool:
    try:
        import langgraph  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _langgraph_installed(), reason="optional 'langgraph' extra not installed")
def test_orchestrator_with_langgraph_completes(tmp_path: Path):
    from hermes3d.core.agents.orchestrator import LangGraphOrchestrator

    state = _make_state(tmp_path)
    orch = LangGraphOrchestrator()
    final = orch.run(state, checkpoint_dir=tmp_path / "cp")
    assert final.terminal is True
    assert isinstance(final.aborted, bool)
    assert final.node_results is final.history
    assert len(final.history) >= 4


def test_orchestrator_fallback_without_langgraph(tmp_path: Path, monkeypatch):
    """Force the import path to fail and assert fallback completes + warns."""
    monkeypatch.setitem(sys.modules, "langgraph", None)

    from hermes3d.core.agents.orchestrator import (
        LangGraphOrchestrator,
        LangGraphUnavailableWarning,
    )

    state = _make_state(tmp_path)
    orch = LangGraphOrchestrator()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        final = orch.run(state, checkpoint_dir=tmp_path / "cp")
    assert final.terminal is True
    assert any(issubclass(w.category, LangGraphUnavailableWarning) for w in caught), (
        "expected LangGraphUnavailableWarning"
    )
    assert not final.aborted
    pass_nodes = {h.node_name for h in final.history if h.outcome.value == "pass"}
    assert "enqueue" in pass_nodes
    assert "dispatch" in pass_nodes


def test_orchestrator_checkpoint_resume(tmp_path: Path):
    """Run partway, persist a checkpoint, then load + resume."""
    from hermes3d.core.agents.orchestrator import LangGraphOrchestrator
    from hermes3d.core.orchestration import build_print_workflow

    state = _make_state(tmp_path)
    orch = LangGraphOrchestrator(force_fallback=True)
    final = orch.run(state, checkpoint_dir=tmp_path / "cp")
    assert final.terminal is True

    graph = build_print_workflow(checkpoint_dir=tmp_path / "cp")
    cp = graph.load_checkpoint(state.workflow_id)
    assert cp is not None
    assert cp.workflow_id == state.workflow_id
    assert len(cp.history) == len(final.history)

    final2 = orch.run(cp, checkpoint_dir=tmp_path / "cp")
    assert final2.terminal is True


def test_orchestrator_repair_conditional_edge(tmp_path: Path):
    """A non-watertight mesh triggers the repair node — conditional path."""
    import numpy as np
    from hermes3d.core.agents.orchestrator import LangGraphOrchestrator
    from hermes3d.core.orchestration import new_state

    mesh = trimesh.creation.box(extents=(50, 40, 30))
    mask = np.ones(len(mesh.faces), dtype=bool)
    mask[-1] = False
    mesh.update_faces(mask)
    stl = tmp_path / "broken.stl"
    mesh.export(stl)

    state = new_state(
        initial={
            "mesh_path": str(stl),
            "material": "PLA",
            "queue_path": str(tmp_path / "q.json"),
            "dry_run": True,
            "auto_orient_enabled": False,
        }
    )
    orch = LangGraphOrchestrator(force_fallback=True)
    final = orch.run(state, checkpoint_dir=tmp_path / "cp")
    repair_history = [h for h in final.history if h.node_name == "repair_if_needed"]
    assert repair_history, "repair node should have run"
    assert repair_history[0].outcome.value == "pass"


def test_run_with_langgraph_entry_point(tmp_path: Path):
    """The print_workflow.run_with_langgraph helper drives the orchestrator."""
    from hermes3d.core.orchestration.print_workflow import run_with_langgraph

    state = _make_state(tmp_path)
    final = run_with_langgraph(state, checkpoint_dir=tmp_path / "cp")
    assert final.terminal is True
