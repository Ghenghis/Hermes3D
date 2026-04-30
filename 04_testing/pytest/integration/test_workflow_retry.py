"""Integration: print_workflow uses the retry budget for transient failures.

We monkeypatch the slicer node so it fails twice with a transient error
then succeeds. With ``RetryBudget(max_retries=3)`` the workflow should
complete and the slice node should record success.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _has_matplotlib() -> bool:
    try:
        importlib.import_module("matplotlib")
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(
    not _has_matplotlib(), reason="matplotlib missing — full pipeline cannot render"
)
def test_workflow_retries_transient_slice_failure(monkeypatch, tmp_path):
    from hermes3d.core.design.desk_organizer import OrganizerSpec, build_organizer
    from hermes3d.core.orchestration.agent_graph import new_state
    from hermes3d.core.orchestration import print_workflow
    from hermes3d.core.orchestration.agent_graph import NodeOutcome, NodeResult

    # Make backoff instantaneous.
    monkeypatch.setattr(
        "hermes3d.core.orchestration.retry_controller.time.sleep",
        lambda _s: None,
    )

    mesh = build_organizer(OrganizerSpec())
    stl = tmp_path / "organizer.stl"
    mesh.export(stl)

    calls = {"n": 0}
    real_slice = print_workflow._node_slice

    def flaky_slice(state):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError(f"transient slicer hiccup {calls['n']}")
        # On the 3rd attempt, return a SKIP outcome (slicer not installed)
        # so downstream nodes degrade gracefully.
        return NodeResult(
            node_name="slice",
            outcome=NodeOutcome.SKIP,
            started_unix=0.0,
            ended_unix=0.0,
            notes=["test stub: slice succeeded on retry"],
        )

    monkeypatch.setattr(print_workflow, "_node_slice", flaky_slice)

    graph = print_workflow.build_print_workflow(checkpoint_dir=str(tmp_path / "wf"))
    state = new_state(
        initial={
            "mesh_path": str(stl),
            "material": "PLA",
            "strategy": "auto",
            "dry_run": True,
            "queue_path": str(tmp_path / "queue.json"),
            "preferred_printer_id": "prusa_mk3s",
        }
    )
    final = graph.run(state)

    assert calls["n"] == 3, "slicer should have been retried twice"
    # The slice node entry in history should not be a hard failure.
    slice_entries = [r for r in final.history if r.node_name == "slice"]
    assert slice_entries, "slice node should have run"
    assert slice_entries[-1].outcome != NodeOutcome.FAIL
