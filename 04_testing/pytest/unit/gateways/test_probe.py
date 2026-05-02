"""Provider probe gateway unit tests for Phase 3.4-B."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hermes3d.gateways.budget import fresh_budget_state
from hermes3d.gateways.probe import ProbeOutcome, ProviderProbeGateway
from hermes3d.orchestration.ledger import OrchestrationLedger
from hermes3d.orchestration.supervisor import OfflineSupervisor
from hermes3d.orchestration.types import BudgetState, CapabilityToken, Err, Ok, ProviderConfig


def _setup(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)
    minimax_config = ProviderConfig(
        base_url="https://api.minimax.io/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="HERMES3D_MINIMAX_API_KEY",
        cost_cap_usd_per_run=Decimal("0.05"),
        cost_cap_usd_per_day=Decimal("1.00"),
    )
    gateway = ProviderProbeGateway(ledger=ledger, providers={"minimax": minimax_config})
    return ledger, supervisor, gateway, minimax_config


def _probe_token(supervisor: OfflineSupervisor, *, run_id: str = "probe-test") -> CapabilityToken:
    token = supervisor.issue_token(
        agent_id="probe-tester",
        tools=frozenset({"provider.probe"}),
        scopes=frozenset({run_id}),
    )
    assert not isinstance(token, Err)
    return token


def _fake_caller(
    http_status: int = 200,
    body: str = '{"data":[{"id":"abab6.5"}]}',
    latency_ms: int = 42,
):
    def _caller(_config: ProviderConfig) -> ProbeOutcome:
        return ProbeOutcome(http_status=http_status, latency_ms=latency_ms, body=body)

    return _caller


def _count(ledger: OrchestrationLedger, tool: str) -> int:
    return sum(1 for event in ledger.events() if event.tool == tool)


def test_no_token_refusal(tmp_path) -> None:
    _ledger, _supervisor, gateway, _config = _setup(tmp_path)
    result = gateway.probe(
        "minimax",
        token=None,
        budget=fresh_budget_state(),
        probe_caller=_fake_caller(),
    )

    assert isinstance(result, Err)
    assert result.code == "no_token"


def test_expired_token_refusal(tmp_path) -> None:
    _ledger, supervisor, gateway, _config = _setup(tmp_path)
    token = supervisor.issue_token(
        agent_id="probe-tester",
        tools=frozenset({"provider.probe"}),
        scopes=frozenset({"expired-probe"}),
        ttl_seconds=-1,
    )
    assert not isinstance(token, Err)

    result = gateway.probe(
        "minimax",
        token=token,
        budget=fresh_budget_state(),
        probe_caller=_fake_caller(),
    )

    assert isinstance(result, Err)
    assert result.code == "token_expired"


def test_unauthorized_tool_refusal(tmp_path) -> None:
    _ledger, supervisor, gateway, _config = _setup(tmp_path)
    token = supervisor.issue_token(
        agent_id="probe-tester",
        tools=frozenset({"planner.plan"}),
        scopes=frozenset({"wrong-tool"}),
    )
    assert not isinstance(token, Err)

    result = gateway.probe(
        "minimax",
        token=token,
        budget=fresh_budget_state(),
        probe_caller=_fake_caller(),
    )

    assert isinstance(result, Err)
    assert result.code == "tool_not_authorized"


def test_phase_violation_refusal(tmp_path) -> None:
    _ledger, supervisor, gateway, _config = _setup(tmp_path)
    token = supervisor.issue_token(
        agent_id="probe-tester",
        tools=frozenset({"provider.probe"}),
        scopes=frozenset({"phase-4"}),
        phase=4,
    )
    assert not isinstance(token, Err)

    result = gateway.probe(
        "minimax",
        token=token,
        budget=fresh_budget_state(),
        probe_caller=_fake_caller(),
    )

    assert isinstance(result, Err)
    assert result.code == "phase_violation"


def test_provider_not_in_allowlist_refusal(tmp_path) -> None:
    _ledger, supervisor, gateway, _config = _setup(tmp_path)
    result = gateway.probe(
        "deepseek",
        token=_probe_token(supervisor),
        budget=fresh_budget_state(),
        probe_caller=_fake_caller(),
    )

    assert isinstance(result, Err)
    assert result.code == "provider_not_in_allowlist"


def test_missing_probe_caller_refusal(tmp_path) -> None:
    _ledger, supervisor, gateway, _config = _setup(tmp_path)
    result = gateway.probe(
        "minimax",
        token=_probe_token(supervisor),
        budget=fresh_budget_state(),
    )

    assert isinstance(result, Err)
    assert result.code == "probe_caller_missing"


def test_budget_exceeded_writes_budget_row(tmp_path) -> None:
    ledger, supervisor, gateway, _config = _setup(tmp_path)
    budget = BudgetState(
        spent_usd_run=Decimal("0.10"),
        spent_usd_day=Decimal("0"),
        day_started_utc=fresh_budget_state().day_started_utc,
    )
    result = gateway.probe(
        "minimax",
        token=_probe_token(supervisor),
        budget=budget,
        probe_caller=_fake_caller(),
    )

    assert isinstance(result, Err)
    assert result.code == "probe_budget_exceeded"
    assert _count(ledger, "budget.exceeded") == 1
    event = ledger.events()[0]
    assert "tool=provider.probe" in event.message
    assert "per_run" in event.message


def test_happy_probe_writes_redacted_row_rate_caps_and_rejects_replay(tmp_path) -> None:
    ledger, supervisor, gateway, _config = _setup(tmp_path)
    now = datetime.now(UTC)
    body = '{"data":[{"id":"abab6.5"}],"Authorization":"Bearer abcdefghijklmnop"}'
    token = _probe_token(supervisor)

    first = gateway.probe(
        "minimax",
        token=token,
        budget=fresh_budget_state(now_utc=now),
        probe_caller=_fake_caller(body=body),
        now_utc=now,
    )
    replay = gateway.probe(
        "minimax",
        token=token,
        budget=fresh_budget_state(now_utc=now),
        probe_caller=_fake_caller(),
        now_utc=now,
    )
    rate_limited = gateway.probe(
        "minimax",
        token=_probe_token(supervisor, run_id="probe-test-2"),
        budget=fresh_budget_state(now_utc=now),
        probe_caller=_fake_caller(),
        now_utc=now + timedelta(seconds=30),
    )

    assert isinstance(first, Ok)
    assert first.value.success is True
    assert first.value.latency_ms == 42
    assert "abcdefghijklmnop" not in first.value.redacted_excerpt
    assert isinstance(replay, Err)
    assert replay.code == "token_unknown"
    assert isinstance(rate_limited, Err)
    assert rate_limited.code == "rate_cap_exceeded"
    assert _count(ledger, "provider.probe") == 1
    event = ledger.events()[0]
    assert event.tool == "provider.probe"
    assert event.verdict == "pass"
    assert "abcdefghijklmnop" not in event.message
