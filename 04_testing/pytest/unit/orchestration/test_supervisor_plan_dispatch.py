"""Phase 3.2-C supervisor plan and simulated Gen3D dispatch rules."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from hermes3d.orchestration import (
    Err,
    Gen3DRequest,
    OfflineSupervisor,
    Ok,
    OrchestrationLedger,
    PlanRequest,
    SimulatedModelArtifact,
    TaskDAG,
    TaskNode,
)


def _plan_request() -> PlanRequest:
    return PlanRequest(
        run_id="run-plan",
        agent_id="planner-a",
        prompt="calibration cube",
    )


def _gen3d_request() -> Gen3DRequest:
    return Gen3DRequest(
        run_id="run-plan",
        agent_id="gen3d-a",
        node_id="gen3d-simulated",
        prompt="calibration cube",
        seed=3201,
    )


def _dag(
    tool: str = "gen3d.generate",
    gate_set: frozenset[str] = frozenset(),
) -> TaskDAG:
    return TaskDAG(
        dag_id="dag-1",
        run_id="run-plan",
        nodes=(
            TaskNode(
                node_id="gen3d-simulated",
                tool=tool,
                kind="gen3d.fixture.calibration_cube",
                gate_set=gate_set,
            ),
        ),
    )


def _artifact(_request: Gen3DRequest) -> SimulatedModelArtifact:
    return SimulatedModelArtifact(
        artifact_id="artifact-1",
        sha256="artifact-sha",
        prompt="calibration cube",
        seed=3201,
    )


def _sha(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _plan_outputs_sha(tmp_path, gate_set: frozenset[str]) -> str:
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))

    result = supervisor.dispatch_plan(
        _plan_request(),
        token=token,
        handler=lambda _request: _dag(gate_set=gate_set),
    )

    assert isinstance(result.result, Ok)
    return ledger.events()[0].outputs_sha


def test_dispatch_plan_refuses_tokenless_request_and_writes_ledger(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)

    result = supervisor.dispatch_plan(_plan_request(), handler=lambda _request: _dag())

    assert isinstance(result.result, Err)
    assert result.result.code == "no_token"
    assert result.token_id is None
    assert ledger.events()[0].tool == "planner.plan"
    assert ledger.events()[0].verdict == "fail"


def test_dispatch_plan_refuses_wrong_tool_token(tmp_path):
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"printer.poll"}))

    result = supervisor.dispatch_plan(_plan_request(), token=token, handler=lambda _request: _dag())

    assert isinstance(result.result, Err)
    assert result.result.code == "tool_not_authorized"


def test_dispatch_plan_refuses_replayed_token(tmp_path):
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))

    accepted = supervisor.dispatch_plan(
        _plan_request(),
        token=token,
        handler=lambda _request: _dag(),
    )
    replay = supervisor.dispatch_plan(_plan_request(), token=token, handler=lambda _request: _dag())

    assert isinstance(accepted.result, Ok)
    assert isinstance(replay.result, Err)
    assert replay.result.code == "token_unknown"


def test_dispatch_plan_refuses_expired_token(tmp_path):
    now = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    token = supervisor.issue_token(
        agent_id="planner-a",
        tools=frozenset({"planner.plan"}),
        ttl_seconds=1,
        now_utc=now,
    )

    result = supervisor.dispatch_plan(
        _plan_request(),
        token=token,
        handler=lambda _request: _dag(),
        now_utc=now + timedelta(seconds=2),
    )

    assert isinstance(result.result, Err)
    assert result.result.code == "token_expired"


def test_dispatch_plan_refuses_phase_violation(tmp_path):
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    token = supervisor.issue_token(
        agent_id="planner-a",
        tools=frozenset({"planner.plan"}),
        phase=4,
    )

    result = supervisor.dispatch_plan(_plan_request(), token=token, handler=lambda _request: _dag())

    assert isinstance(result.result, Err)
    assert result.result.code == "phase_violation"


def test_dispatch_plan_refuses_unregistered_plan_tool_before_handler(tmp_path):
    supervisor = OfflineSupervisor(
        ledger=OrchestrationLedger(tmp_path / "events.sqlite3"),
        registered_tools=frozenset({"gen3d.generate"}),
    )
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))
    handler_called = False

    def handler(_request: PlanRequest) -> TaskDAG:
        nonlocal handler_called
        handler_called = True
        return _dag()

    result = supervisor.dispatch_plan(_plan_request(), token=token, handler=handler)

    assert isinstance(result.result, Err)
    assert result.result.code == "tool_unregistered"
    assert handler_called is False
    assert supervisor.ledger is not None
    assert supervisor.ledger.events()[0].tool == "planner.plan"
    assert supervisor.ledger.events()[0].verdict == "fail"


def test_dispatch_plan_enforces_r6_unregistered_tool(tmp_path):
    supervisor = OfflineSupervisor(
        ledger=OrchestrationLedger(tmp_path / "events.sqlite3"),
        registered_tools=frozenset({"planner.plan"}),
    )
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))

    result = supervisor.dispatch_plan(_plan_request(), token=token, handler=lambda _request: _dag())

    assert isinstance(result.result, Err)
    assert result.result.code == "tool_unregistered"


def test_dispatch_plan_accepts_registered_dag_and_reuses_run_mutex(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))

    result = supervisor.dispatch_plan(_plan_request(), token=token, handler=lambda _request: _dag())

    assert isinstance(result.result, Ok)
    assert result.result.value.nodes[0].tool == "gen3d.generate"
    assert ledger.events()[0].tool == "planner.plan"
    assert ledger.events()[0].verdict == "pass"
    assert supervisor.mutex_for_run("run-plan") is supervisor.mutex_for_run("run-plan")


def test_dispatch_plan_outputs_sha_normalizes_frozenset_gate_set(tmp_path):
    outputs_sha = _plan_outputs_sha(
        tmp_path,
        frozenset({"slice.dryrun", "mesh.qa"}),
    )

    assert outputs_sha == _sha(
        {
            "ok": True,
            "value": {
                "dag_id": "dag-1",
                "run_id": "run-plan",
                "nodes": [
                    {
                        "node_id": "gen3d-simulated",
                        "tool": "gen3d.generate",
                        "kind": "gen3d.fixture.calibration_cube",
                        "inputs": {},
                        "retry_budget": 0,
                        "gate_set": ["mesh.qa", "slice.dryrun"],
                        "depends_on": [],
                    }
                ],
                "edges": [],
                "max_depth": 12,
                "max_fanout": 4,
                "metadata": {},
            },
            "message": "offline plan dispatch completed",
        }
    )


def test_dispatch_plan_outputs_sha_repeats_for_equivalent_gate_sets(tmp_path):
    first = _plan_outputs_sha(
        tmp_path / "first",
        frozenset({"slice.dryrun", "mesh.qa"}),
    )
    second = _plan_outputs_sha(
        tmp_path / "second",
        frozenset({"mesh.qa", "slice.dryrun"}),
    )

    assert first == second


def test_dispatch_gen3d_writes_ledger_event(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)
    token = supervisor.issue_token(agent_id="gen3d-a", tools=frozenset({"gen3d.generate"}))

    result = supervisor.dispatch_gen3d(_gen3d_request(), token=token, handler=_artifact)

    assert isinstance(result.result, Ok)
    assert ledger.events()[0].tool == "gen3d.generate"
    assert ledger.events()[0].verdict == "pass"
