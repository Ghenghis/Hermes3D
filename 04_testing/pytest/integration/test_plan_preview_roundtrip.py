"""Phase 3.2-C offline prompt to DAG to simulated artifact round trip."""

from __future__ import annotations

from fastapi.testclient import TestClient
from hermes3d.agents.gen3d_executor import SimulatedGen3DExecutor
from hermes3d.agents.planner import PlannerAgent
from hermes3d.orchestration import (
    Gen3DRequest,
    OfflineSupervisor,
    Ok,
    OrchestrationLedger,
    PlanRequest,
)
from hermes3d.orchestration.bridge import BridgeState, create_bridge_app


def test_prompt_to_dag_to_simulated_artifact_records_ledger_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)
    planner = PlannerAgent(supervisor=supervisor)
    executor = SimulatedGen3DExecutor(supervisor=supervisor)

    plan_token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))
    plan = planner.plan(
        PlanRequest(
            run_id="roundtrip-3-2",
            agent_id="planner-a",
            prompt="calibration cube",
        ),
        token=plan_token,
    )

    assert isinstance(plan.result, Ok)
    node = plan.result.value.nodes[0]

    gen3d_token = supervisor.issue_token(
        agent_id="gen3d-a",
        tools=frozenset({"gen3d.generate"}),
    )
    artifact = executor.generate(
        Gen3DRequest(
            run_id="roundtrip-3-2",
            agent_id="gen3d-a",
            node_id=node.node_id,
            prompt=str(node.inputs["prompt"]),
            seed=int(node.inputs["seed"]),
        ),
        token=gen3d_token,
    )

    assert isinstance(artifact.result, Ok)
    assert artifact.result.value.sha256
    assert [event.tool for event in ledger.events("roundtrip-3-2")] == [
        "planner.plan",
        "gen3d.generate",
    ]


def test_bridge_plan_preview_returns_dag_without_gen3d_execution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ledger = OrchestrationLedger(tmp_path / "preview.sqlite3")
    state = BridgeState(ledger=ledger)
    client = TestClient(create_bridge_app(state), client=("127.0.0.1", 50000))

    response = client.post("/api/plan/preview", json={"prompt": "calibration cube"})

    assert response.status_code == 200
    dag = response.json()
    assert dag["nodes"][0]["tool"] == "gen3d.generate"
    assert dag["run_id"].startswith("plan-preview-")
    events = ledger.events(dag["run_id"])
    assert [event.tool for event in events] == ["planner.plan"]
    assert sum(1 for event in events if event.tool == "gen3d.generate") == 0
    assert not (tmp_path / "var" / "orchestration" / "artifacts").exists()


def test_bridge_run_summary_is_ledger_derived_and_unknown_run_404(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "preview.sqlite3")
    state = BridgeState(ledger=ledger)
    client = TestClient(create_bridge_app(state), client=("127.0.0.1", 50000))
    preview = client.post("/api/plan/preview", json={"prompt": "calibration cube"}).json()

    summary = client.get(f"/api/runs/{preview['run_id']}")
    missing = client.get("/api/runs/not-a-run")

    assert summary.status_code == 200
    assert summary.json()["tools"] == {"planner.plan": 1}
    assert summary.json()["event_count"] == 1
    assert missing.status_code == 404


def test_bridge_preview_routes_refuse_non_localhost_clients(tmp_path):
    state = BridgeState(ledger=OrchestrationLedger(tmp_path / "preview.sqlite3"))
    remote_client = TestClient(create_bridge_app(state), client=("203.0.113.10", 50000))

    preview = remote_client.post("/api/plan/preview", json={"prompt": "calibration cube"})
    summary = remote_client.get("/api/runs/plan-preview-test")

    assert preview.status_code == 403
    assert summary.status_code == 403
