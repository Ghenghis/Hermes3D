"""Provider probe R9/R10 integration tests."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from hermes3d.gateways.budget import fresh_budget_state
from hermes3d.gateways.llm import LLMGateway, LLMPolicy
from hermes3d.gateways.probe import ProbeOutcome, ProviderProbeGateway
from hermes3d.orchestration import Err, OfflineSupervisor, Ok
from hermes3d.orchestration.ledger import OrchestrationLedger
from hermes3d.orchestration.types import BudgetState, LLMRequest, LLMResponse
from starlette.testclient import TestClient

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"
if str(FIXTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(FIXTURE_ROOT))

from llm import create_app as create_llm_app  # noqa: E402
from providers.server import create_app as create_provider_app  # noqa: E402


def _llm_policy() -> LLMPolicy:
    return LLMPolicy(
        default_mode="llm",
        provider_allowlist=("openai-fixture",),
        cost_cap_usd_per_run=Decimal("0.05"),
        cost_cap_usd_per_day=Decimal("1.00"),
        timeout_seconds=30,
        prompt_max_bytes=4096,
        retry_max=1,
        rate_per_second=1,
        input_usd_per_token=Decimal("0.000001"),
        output_usd_per_token=Decimal("0.000001"),
        max_completion_tokens=128,
        fallback_mode="template",
    )


def _setup(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)
    minimax_config = _minimax_config()
    probe_gateway = ProviderProbeGateway(
        ledger=ledger,
        providers={"minimax": minimax_config},
    )
    llm_gateway = LLMGateway(ledger=ledger, policy=_llm_policy())
    return ledger, supervisor, probe_gateway, llm_gateway, minimax_config


def _minimax_config():
    from hermes3d.orchestration.types import ProviderConfig

    return ProviderConfig(
        base_url="https://api.minimax.io/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="HERMES3D_MINIMAX_API_KEY",
        cost_cap_usd_per_run=Decimal("0.05"),
        cost_cap_usd_per_day=Decimal("1.00"),
    )


def _fixture_probe_caller(provider_id: str, mode: str):
    client = TestClient(create_provider_app(provider_id=provider_id, mode=mode))

    def caller(_config) -> ProbeOutcome:
        response = client.get("/v1/models")
        return ProbeOutcome(
            http_status=response.status_code,
            latency_ms=9,
            body=response.text,
        )

    return caller


def _fixture_llm_caller(mode: str):
    client = TestClient(create_llm_app(mode=mode))

    def caller(request: LLMRequest) -> LLMResponse:
        response = client.post(
            "/v1/completions",
            json={"prompt": request.prompt, "max_tokens": request.max_completion_tokens},
        )
        response.raise_for_status()
        payload = response.json()
        return LLMResponse(
            redacted_text=str(payload["text"]),
            tokens_in=int(payload.get("tokens_in", 4)),
            tokens_out=int(payload.get("tokens_out", 4)),
            cost_usd_estimate=Decimal("0.000008"),
        )

    return caller


def _probe_token(supervisor: OfflineSupervisor, *, run_id: str = "provider-roundtrip"):
    token = supervisor.issue_token(
        agent_id="probe-test",
        tools=frozenset({"provider.probe"}),
        scopes=frozenset({run_id}),
    )
    assert not isinstance(token, Err)
    return token


def _llm_token(supervisor: OfflineSupervisor, *, run_id: str = "provider-roundtrip"):
    token = supervisor.issue_token(
        agent_id="planner-a",
        tools=frozenset({"llm.complete"}),
        scopes=frozenset({run_id}),
    )
    assert not isinstance(token, Err)
    return token


def _count(ledger: OrchestrationLedger, tool: str) -> int:
    return sum(1 for event in ledger.events() if event.tool == tool)


def test_probe_then_completion_succeeds_with_real_provider_id(tmp_path) -> None:
    ledger, supervisor, probe_gateway, llm_gateway, _config = _setup(tmp_path)
    now = datetime.now(UTC)

    probe_result = probe_gateway.probe(
        "minimax",
        token=_probe_token(supervisor),
        budget=fresh_budget_state(now_utc=now),
        probe_caller=_fixture_probe_caller("minimax", "happy"),
        now_utc=now,
    )
    result = llm_gateway.complete(
        "calibration cube",
        token=_llm_token(supervisor),
        budget=fresh_budget_state(now_utc=now),
        caller=_fixture_llm_caller("happy"),
        provider_id="minimax",
        now_utc=now,
    )

    assert isinstance(probe_result, Ok)
    assert isinstance(result, Ok)
    assert _count(ledger, "provider.probe") == 1
    assert _count(ledger, "llm.complete") == 1


def test_completion_refused_when_no_prior_probe(tmp_path) -> None:
    _ledger, supervisor, _probe_gateway, llm_gateway, _config = _setup(tmp_path)
    token = _llm_token(supervisor)

    result = llm_gateway.complete(
        "calibration cube",
        token=token,
        budget=fresh_budget_state(),
        caller=_fixture_llm_caller("happy"),
        provider_id="minimax",
    )
    replay = llm_gateway.complete(
        "calibration cube",
        token=token,
        budget=fresh_budget_state(),
        caller=_fixture_llm_caller("happy"),
        provider_id="minimax",
    )

    assert isinstance(result, Err)
    assert result.code == "provider_not_probed"
    assert result.message == "minimax"
    assert isinstance(replay, Err)
    assert replay.code == "token_unknown"


def test_completion_refused_when_probe_is_stale(tmp_path) -> None:
    _ledger, supervisor, probe_gateway, llm_gateway, _config = _setup(tmp_path)
    stale = datetime.now(UTC) - timedelta(minutes=30)
    now = datetime.now(UTC)

    probe_result = probe_gateway.probe(
        "minimax",
        token=_probe_token(supervisor),
        budget=fresh_budget_state(now_utc=stale),
        probe_caller=_fixture_probe_caller("minimax", "happy"),
        now_utc=stale,
    )
    result = llm_gateway.complete(
        "calibration cube",
        token=_llm_token(supervisor),
        budget=fresh_budget_state(now_utc=now),
        caller=_fixture_llm_caller("happy"),
        provider_id="minimax",
        now_utc=now,
    )

    assert isinstance(probe_result, Ok)
    assert isinstance(result, Err)
    assert result.code == "provider_not_probed"
    assert result.message == "minimax"


def test_fixture_provider_exempt_from_freshness_check(tmp_path) -> None:
    ledger, supervisor, _probe_gateway, llm_gateway, _config = _setup(tmp_path)

    result = llm_gateway.complete(
        "calibration cube",
        token=_llm_token(supervisor),
        budget=fresh_budget_state(),
        caller=_fixture_llm_caller("happy"),
        provider_id="openai-fixture",
    )

    assert isinstance(result, Ok)
    assert _count(ledger, "provider.probe") == 0
    assert _count(ledger, "llm.complete") == 1


def test_supervisor_refuses_probe_token_when_budget_exhausted(tmp_path) -> None:
    ledger, supervisor, _probe_gateway, _llm_gateway, _config = _setup(tmp_path)
    budget = BudgetState(
        spent_usd_run=Decimal("0"),
        spent_usd_day=Decimal("0.10"),
        day_started_utc=fresh_budget_state().day_started_utc,
    )

    token_or_err = supervisor.issue_token(
        agent_id="probe-test",
        tools=frozenset({"provider.probe"}),
        scopes=frozenset({"r10-test"}),
        budget=budget,
    )

    assert isinstance(token_or_err, Err)
    assert token_or_err.code == "budget_exceeded"
    assert _count(ledger, "budget.exceeded") == 1
    event = ledger.events()[0]
    assert event.tool == "budget.exceeded"
    assert "provider.probe" in event.message
