"""In-memory Phase 3.3 LLM budget accounting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal


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


@dataclass(frozen=True)
class BudgetUsage:
    run_usd: Decimal
    day_usd: Decimal


@dataclass
class LLMBudgetTracker:
    """Track per-run and per-day spend without persistence or external I/O."""

    caps: BudgetCaps
    day: date = field(default_factory=lambda: datetime.now(UTC).date())
    _run_spend: dict[str, Decimal] = field(default_factory=dict)
    _day_spend: Decimal = Decimal("0")

    def would_exceed(
        self,
        *,
        run_id: str,
        estimated_usd: Decimal,
        now_utc: datetime | None = None,
    ) -> BudgetDecision:
        self._roll_day(now_utc)
        estimate = _money(estimated_usd)
        run_current = self._run_spend.get(run_id, Decimal("0"))
        if run_current + estimate > self.caps.cost_cap_usd_per_run:
            return BudgetDecision(
                allowed=False,
                reason="budget_exceeded",
                cap="per_run",
                attempted_usd=estimate,
                current_usd=run_current,
                cap_usd=self.caps.cost_cap_usd_per_run,
            )
        if self._day_spend + estimate > self.caps.cost_cap_usd_per_day:
            return BudgetDecision(
                allowed=False,
                reason="budget_exceeded",
                cap="per_day",
                attempted_usd=estimate,
                current_usd=self._day_spend,
                cap_usd=self.caps.cost_cap_usd_per_day,
            )
        return BudgetDecision(allowed=True, attempted_usd=estimate)

    def consume(
        self,
        *,
        run_id: str,
        actual_usd: Decimal,
        now_utc: datetime | None = None,
    ) -> BudgetUsage:
        self._roll_day(now_utc)
        actual = _money(actual_usd)
        self._run_spend[run_id] = self._run_spend.get(run_id, Decimal("0")) + actual
        self._day_spend += actual
        return BudgetUsage(run_usd=self._run_spend[run_id], day_usd=self._day_spend)

    def usage(self, *, run_id: str) -> BudgetUsage:
        return BudgetUsage(
            run_usd=self._run_spend.get(run_id, Decimal("0")),
            day_usd=self._day_spend,
        )

    def _roll_day(self, now_utc: datetime | None) -> None:
        current_day = (now_utc or datetime.now(UTC)).astimezone(UTC).date()
        if current_day != self.day:
            self.day = current_day
            self._run_spend.clear()
            self._day_spend = Decimal("0")


def _money(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))
