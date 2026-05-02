"""Offline budget helpers for the Phase 3.3 LLM gateway."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from hermes3d.orchestration.types import BudgetState


@dataclass(frozen=True)
class BudgetCaps:
    cost_cap_usd_per_run: Decimal
    cost_cap_usd_per_day: Decimal


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reason: str = ""
    cap: str = ""
    attempted_usd: Decimal = Decimal("0")
    current_usd: Decimal = Decimal("0")
    cap_usd: Decimal = Decimal("0")


class BudgetStore:
    """Tiny JSON-backed budget state store for offline unit tests."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def load(self, *, now_utc: datetime | None = None) -> BudgetState:
        if not self.path.exists():
            return fresh_budget_state(now_utc=now_utc)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return BudgetState(
            spent_usd_run=Decimal(str(payload["spent_usd_run"])),
            spent_usd_day=Decimal(str(payload["spent_usd_day"])),
            day_started_utc=str(payload["day_started_utc"]),
        )

    def save(self, state: BudgetState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            key: str(value) if isinstance(value, Decimal) else value
            for key, value in asdict(state).items()
        }
        self.path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


def fresh_budget_state(*, now_utc: datetime | None = None) -> BudgetState:
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    day_started = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return BudgetState(
        spent_usd_run=Decimal("0"),
        spent_usd_day=Decimal("0"),
        day_started_utc=day_started.isoformat().replace("+00:00", "Z"),
    )


def estimate_cost_usd(
    *,
    tokens_in: int,
    tokens_out: int,
    input_usd_per_token: Decimal,
    output_usd_per_token: Decimal,
) -> Decimal:
    return _money(
        Decimal(tokens_in) * input_usd_per_token + Decimal(tokens_out) * output_usd_per_token
    )


def check_budget(
    budget: BudgetState,
    *,
    caps: BudgetCaps,
    estimated_usd: Decimal,
    now_utc: datetime | None = None,
) -> BudgetDecision:
    current = _rollover_if_needed(budget, now_utc=now_utc)
    estimate = _money(estimated_usd)
    if current.spent_usd_run + estimate > caps.cost_cap_usd_per_run:
        return BudgetDecision(
            allowed=False,
            reason="budget_exceeded",
            cap="per_run",
            attempted_usd=estimate,
            current_usd=current.spent_usd_run,
            cap_usd=caps.cost_cap_usd_per_run,
        )
    if current.spent_usd_day + estimate > caps.cost_cap_usd_per_day:
        return BudgetDecision(
            allowed=False,
            reason="budget_exceeded",
            cap="per_day",
            attempted_usd=estimate,
            current_usd=current.spent_usd_day,
            cap_usd=caps.cost_cap_usd_per_day,
        )
    return BudgetDecision(allowed=True, attempted_usd=estimate)


def record_actual(
    budget: BudgetState,
    *,
    actual_usd: Decimal,
    store: BudgetStore | None = None,
    now_utc: datetime | None = None,
) -> BudgetState:
    current = _rollover_if_needed(budget, now_utc=now_utc)
    actual = _money(actual_usd)
    updated = BudgetState(
        spent_usd_run=current.spent_usd_run + actual,
        spent_usd_day=current.spent_usd_day + actual,
        day_started_utc=current.day_started_utc,
    )
    if store is not None:
        store.save(updated)
    return updated


def _rollover_if_needed(budget: BudgetState, *, now_utc: datetime | None) -> BudgetState:
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)
    day_started = datetime.fromisoformat(budget.day_started_utc.replace("Z", "+00:00"))
    if now.date() == day_started.date():
        return budget
    return fresh_budget_state(now_utc=now)


def _money(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))
