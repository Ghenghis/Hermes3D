"""Phase 3.2-C offline prompt to DAG to simulated artifact round trip."""

from __future__ import annotations

from hermes3d.agents.gen3d_executor import SimulatedGen3DExecutor
from hermes3d.agents.planner import PlannerAgent
from hermes3d.orchestration import (
    Gen3DRequest,
    OfflineSupervisor,
    Ok,
    OrchestrationLedger,
    PlanRequest,
)


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
