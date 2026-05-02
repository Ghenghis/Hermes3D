"""Phase 3.3 budget accounting tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hermes3d.gateways.budget import (
    BudgetCaps,
    BudgetStore,
    check_budget,
    estimate_cost_usd,
    fresh_budget_state,
    record_actual,
)
from hermes3d.orchestration.types import BudgetState


def test_fresh_state_initializes() -> None:
    state = fresh_budget_state(now_utc=datetime(2026, 5, 2, 12, tzinfo=UTC))

    assert state.spent_usd_run == Decimal("0")
    assert state.spent_usd_day == Decimal("0")
    assert state.day_started_utc == "2026-05-02T00:00:00Z"


def test_estimate_cost_is_deterministic() -> None:
    first = estimate_cost_usd(
        tokens_in=10,
        tokens_out=20,
        input_usd_per_token=Decimal("0.001"),
        output_usd_per_token=Decimal("0.002"),
    )
    second = estimate_cost_usd(
        tokens_in=10,
        tokens_out=20,
        input_usd_per_token=Decimal("0.001"),
        output_usd_per_token=Decimal("0.002"),
    )

    assert first == Decimal("0.050000")
    assert second == first


def test_per_run_cap_exceeded() -> None:
    state = fresh_budget_state()
    caps = BudgetCaps(cost_cap_usd_per_run=Decimal("0.01"), cost_cap_usd_per_day=Decimal("1.00"))

    decision = check_budget(state, caps=caps, estimated_usd=Decimal("0.02"))

    assert decision.allowed is False
    assert decision.cap == "per_run"


def test_per_day_cap_exceeded() -> None:
    state = BudgetState(
        spent_usd_run=Decimal("0.00"),
        spent_usd_day=Decimal("0.90"),
        day_started_utc=fresh_budget_state().day_started_utc,
    )
    caps = BudgetCaps(cost_cap_usd_per_run=Decimal("1.00"), cost_cap_usd_per_day=Decimal("1.00"))

    decision = check_budget(state, caps=caps, estimated_usd=Decimal("0.20"))

    assert decision.allowed is False
    assert decision.cap == "per_day"


def test_day_rollover_resets_day_spend() -> None:
    first_day = datetime(2026, 5, 2, 12, tzinfo=UTC)
    state = record_actual(
        fresh_budget_state(now_utc=first_day),
        actual_usd=Decimal("0.90"),
        now_utc=first_day,
    )
    caps = BudgetCaps(cost_cap_usd_per_run=Decimal("1.00"), cost_cap_usd_per_day=Decimal("1.00"))

    decision = check_budget(
        state,
        caps=caps,
        estimated_usd=Decimal("0.20"),
        now_utc=first_day + timedelta(days=1),
    )

    assert decision.allowed is True


def test_record_actual_persists_and_reloads(tmp_path) -> None:
    store = BudgetStore(tmp_path / "budget.json")
    state = record_actual(
        fresh_budget_state(now_utc=datetime(2026, 5, 2, 12, tzinfo=UTC)),
        actual_usd=Decimal("0.123456"),
        store=store,
    )

    loaded = store.load(now_utc=datetime(2026, 5, 2, 12, tzinfo=UTC))

    assert loaded == state
