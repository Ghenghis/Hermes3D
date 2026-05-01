"""Phase 3.2-C deterministic planner tests."""

from __future__ import annotations

from pathlib import Path

from hermes3d.agents import planner
from hermes3d.agents.planner import PlannerAgent
from hermes3d.orchestration import Err, OfflineSupervisor, Ok, PlanRequest


def _request(prompt: str = "calibration cube") -> PlanRequest:
    return PlanRequest(
        run_id="run-plan",
        agent_id="planner-a",
        prompt=prompt,
    )


def test_planner_source_does_not_import_forbidden_provider_clients():
    source = Path(planner.__file__).read_text(encoding="utf-8")

    assert "openai" not in source
    assert "anthropic" not in source
    assert "requests" not in source


def test_planner_outputs_deterministic_fixture_dag():
    supervisor = OfflineSupervisor()
    agent = PlannerAgent(supervisor=supervisor)
    first_token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))
    second_token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))

    first = agent.plan(_request(), token=first_token)
    second = agent.plan(_request(), token=second_token)

    assert isinstance(first.result, Ok)
    assert isinstance(second.result, Ok)
    assert first.result.value.dag_id == second.result.value.dag_id
    assert first.result.value.nodes[0].tool == "gen3d.generate"
    assert first.result.value.nodes[0].inputs["seed"] == 3201


def test_planner_refuses_write_class_fixture_prompt():
    supervisor = OfflineSupervisor()
    agent = PlannerAgent(supervisor=supervisor)
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))

    result = agent.plan(_request("slice and print"), token=token)

    assert isinstance(result.result, Err)
    assert result.result.code == "write_tool_refused"


def test_planner_refuses_unknown_fixture_prompt():
    supervisor = OfflineSupervisor()
    agent = PlannerAgent(supervisor=supervisor)
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))

    result = agent.plan(_request("unlisted prompt"), token=token)

    assert isinstance(result.result, Err)
    assert result.result.code == "fixture_prompt_unknown"


def test_planner_refuses_unregistered_fixture_tool():
    supervisor = OfflineSupervisor(registered_tools=frozenset({"planner.plan"}))
    agent = PlannerAgent(supervisor=supervisor, registered_tools=frozenset({"planner.plan"}))
    token = supervisor.issue_token(agent_id="planner-a", tools=frozenset({"planner.plan"}))

    result = agent.plan(_request(), token=token)

    assert isinstance(result.result, Err)
    assert result.result.code == "tool_unregistered"
