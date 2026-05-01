"""Phase 3.2-C simulated Gen3D executor tests."""

from __future__ import annotations

import json

from hermes3d.agents.gen3d_executor import SimulatedGen3DExecutor
from hermes3d.orchestration import Err, Gen3DRequest, OfflineSupervisor, Ok, OrchestrationLedger
from hermes3d.orchestration.supervisor import stable_sha


def _request(tool: str = "gen3d.generate") -> Gen3DRequest:
    return Gen3DRequest(
        run_id="run-gen3d",
        agent_id="gen3d-a",
        node_id="gen3d-simulated",
        prompt="calibration cube",
        seed=3201,
        tool=tool,
    )


def test_simulated_gen3d_writes_deterministic_artifact_under_var(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    executor = SimulatedGen3DExecutor(supervisor=supervisor)
    first_token = supervisor.issue_token(agent_id="gen3d-a", tools=frozenset({"gen3d.generate"}))
    second_token = supervisor.issue_token(agent_id="gen3d-a", tools=frozenset({"gen3d.generate"}))

    first = executor.generate(_request(), token=first_token)
    second = executor.generate(_request(), token=second_token)

    expected_sha = stable_sha({"prompt": "calibration cube", "seed": 3201})
    artifact_file = tmp_path / "var" / "orchestration" / "artifacts" / f"{expected_sha}.json"

    assert isinstance(first.result, Ok)
    assert isinstance(second.result, Ok)
    assert first.result.value.sha256 == expected_sha
    assert second.result.value.sha256 == expected_sha
    assert artifact_file.exists()
    assert artifact_file.resolve().is_relative_to(
        (tmp_path / "var" / "orchestration" / "artifacts").resolve()
    )
    assert json.loads(artifact_file.read_text(encoding="utf-8"))["sha256"] == expected_sha


def test_simulated_gen3d_refuses_non_gen3d_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    supervisor = OfflineSupervisor()
    executor = SimulatedGen3DExecutor(supervisor=supervisor)
    token = supervisor.issue_token(agent_id="gen3d-a", tools=frozenset({"printer.write"}))

    result = executor.generate(_request(tool="printer.write"), token=token)

    assert isinstance(result.result, Err)
    assert result.result.code == "method_not_allowed"
    assert not (tmp_path / "var" / "orchestration" / "artifacts").exists()


def test_simulated_gen3d_requires_capability_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    executor = SimulatedGen3DExecutor(supervisor=supervisor)

    result = executor.generate(_request(), token=None)

    assert isinstance(result.result, Err)
    assert result.result.code == "no_token"
    assert supervisor.ledger is not None
    assert supervisor.ledger.events()[0].tool == "gen3d.generate"
