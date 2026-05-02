"""Phase 3.3-C planner LLM fixture round trip."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from hermes3d.agents.planner import PlannerAgent
from hermes3d.gateways.budget import fresh_budget_state
from hermes3d.gateways.llm import LLMGateway, LLMPolicy
from hermes3d.orchestration import Err, OfflineSupervisor, Ok, PlanRequest
from hermes3d.orchestration.ledger import OrchestrationLedger
from hermes3d.orchestration.types import BudgetState, CapabilityToken, LLMRequest, LLMResponse
from starlette.testclient import TestClient

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"
if str(FIXTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(FIXTURE_ROOT))

from llm import create_app  # noqa: E402


def _policy() -> LLMPolicy:
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


def _request(run_id: str = "llm-roundtrip") -> PlanRequest:
    return PlanRequest(run_id=run_id, agent_id="planner-a", prompt="calibration cube")


def _plan_token(supervisor: OfflineSupervisor, *, run_id: str = "llm-roundtrip") -> CapabilityToken:
    token = supervisor.issue_token(
        agent_id="planner-a",
        tools=frozenset({"planner.plan"}),
        scopes=frozenset({run_id}),
    )
    assert not isinstance(token, Err)
    return token


def _llm_token(supervisor: OfflineSupervisor, *, run_id: str = "llm-roundtrip") -> CapabilityToken:
    token = supervisor.issue_token(
        agent_id="planner-a",
        tools=frozenset({"llm.complete"}),
        scopes=frozenset({run_id}),
    )
    assert not isinstance(token, Err)
    return token


def _fixture_caller(mode: str):
    client = TestClient(create_app(mode=mode))

    def caller(request: LLMRequest) -> LLMResponse:
        response = client.post(
            "/v1/completions",
            json={"prompt": request.prompt, "max_tokens": request.max_completion_tokens},
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = response.json()
            text = str(payload["text"])
            tokens_in = int(payload.get("tokens_in", 4))
            tokens_out = int(payload.get("tokens_out", 4))
        else:
            text = response.text
            tokens_in = 4
            tokens_out = 4
        return LLMResponse(
            redacted_text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd_estimate=Decimal("0.000008"),
        )

    return caller


def _setup(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)
    gateway = LLMGateway(ledger=ledger, policy=_policy())
    planner = PlannerAgent(supervisor=supervisor, ledger=ledger)
    return ledger, supervisor, gateway, planner


def _count(ledger: OrchestrationLedger, tool: str) -> int:
    return sum(1 for event in ledger.events() if event.tool == tool)


def test_llm_happy_path_records_llm_complete_without_fallback(tmp_path) -> None:
    ledger, supervisor, gateway, planner = _setup(tmp_path)

    result = planner.plan(
        _request(),
        token=_plan_token(supervisor),
        llm_token=_llm_token(supervisor),
        budget=fresh_budget_state(),
        gateway=gateway,
        caller=_fixture_caller("happy"),
    )

    assert isinstance(result.result, Ok)
    assert result.result.value.metadata["planner_mode"] == "llm"
    assert _count(ledger, "llm.complete") == 1
    assert _count(ledger, "planner.fallback") == 0


def test_malformed_llm_response_falls_back_and_records_reason(tmp_path) -> None:
    ledger, supervisor, gateway, planner = _setup(tmp_path)

    result = planner.plan(
        _request(),
        token=_plan_token(supervisor),
        llm_token=_llm_token(supervisor),
        budget=fresh_budget_state(),
        gateway=gateway,
        caller=_fixture_caller("malformed"),
    )

    assert isinstance(result.result, Ok)
    assert result.result.value.metadata["planner_mode"] == "template"
    fallback_events = [event for event in ledger.events() if event.tool == "planner.fallback"]
    assert len(fallback_events) == 1
    assert "unknown_template" in fallback_events[0].message


def test_budget_exhaustion_refuses_llm_token_and_records_fallback(tmp_path) -> None:
    ledger, supervisor, gateway, planner = _setup(tmp_path)
    budget = BudgetState(
        spent_usd_run=Decimal("0.05"),
        spent_usd_day=Decimal("0"),
        day_started_utc=fresh_budget_state().day_started_utc,
    )
    llm_refusal = supervisor.issue_token(
        agent_id="planner-a",
        tools=frozenset({"llm.complete"}),
        scopes=frozenset({"llm-budget"}),
        budget=budget,
    )

    assert isinstance(llm_refusal, Err)
    assert llm_refusal.code == "budget_exceeded"

    result = planner.plan(
        _request("llm-budget"),
        token=_plan_token(supervisor, run_id="llm-budget"),
        llm_token=None,
        budget=budget,
        gateway=gateway,
        caller=_fixture_caller("happy"),
    )

    assert isinstance(result.result, Ok)
    assert result.result.value.metadata["planner_mode"] == "template"
    assert _count(ledger, "budget.exceeded") >= 1
    assert _count(ledger, "planner.fallback") == 1


def test_unknown_fixture_tool_falls_back_and_records_planner_fallback(tmp_path) -> None:
    ledger, supervisor, gateway, planner = _setup(tmp_path)

    result = planner.plan(
        _request(),
        token=_plan_token(supervisor),
        llm_token=_llm_token(supervisor),
        budget=fresh_budget_state(),
        gateway=gateway,
        caller=_fixture_caller("unknown"),
    )

    assert isinstance(result.result, Ok)
    assert result.result.value.metadata["planner_mode"] == "template"
    assert _count(ledger, "planner.fallback") == 1
