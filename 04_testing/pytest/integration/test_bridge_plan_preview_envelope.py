"""CP3.3-D bridge envelope coverage for planner mode metadata."""

from __future__ import annotations

from hermes3d.agents.planner import PlannerAgent
from hermes3d.orchestration.bridge import BridgeState, create_bridge_app
from hermes3d.orchestration.ledger import OrchestrationLedger
from hermes3d.orchestration.supervisor import OfflineSupervisor
from starlette.testclient import TestClient


def test_bridge_plan_preview_surfaces_planner_mode_template(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)
    planner = PlannerAgent(supervisor=supervisor, ledger=ledger)
    state = BridgeState(ledger=ledger, supervisor=supervisor, planner=planner)
    app = create_bridge_app(state)
    client = TestClient(app, client=("127.0.0.1", 50000))

    r = client.post("/api/plan/preview", json={"prompt": "calibration cube"})

    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["planner_mode"] == "template"
    assert "prompt_sha256" in body["metadata"]
    run_id = body["run_id"]
    r2 = client.get(f"/api/runs/{run_id}")
    assert r2.status_code == 200
    assert any(event["tool"] == "planner.plan" for event in r2.json()["events"])
