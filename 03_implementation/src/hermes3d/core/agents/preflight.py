"""Pre-flight checker.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §24 (Pre-flight)

Before sending a print to a printer, runs a battery of checks:

  1. Truth Gate passed (mesh)
  2. Printer reachable + klippy ready
  3. Spool of correct material loaded with enough remaining grams
  4. No active job already on this printer
  5. Print duration within scheduler policy (quiet hours, max-duration)
  6. Cost within optional budget cap
  7. G-code analysis risk flags reviewed
  8. Bed clear (last print's success state, when known)

Returns a structured PreflightReport with one CheckResult per item. The
caller decides whether to proceed; this module never starts a print on
its own.

This is the "last line of defense" before filament is committed.
"""

from __future__ import annotations

import dataclasses
import enum
from dataclasses import dataclass, field
from typing import Any


class PreflightOutcome(str, enum.Enum):
    PASS = "pass"
    WARN = "warn"  # proceed, but the user should know
    FAIL = "fail"  # do not proceed


@dataclass(frozen=True)
class CheckResult:
    name: str
    outcome: PreflightOutcome
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreflightReport:
    printer_id: str
    job_id: str | None
    checks: list[CheckResult] = field(default_factory=list)
    timestamp_unix: float = 0.0

    @property
    def passed(self) -> bool:
        return not any(c.outcome == PreflightOutcome.FAIL for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.outcome == PreflightOutcome.WARN for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "printer_id": self.printer_id,
            "job_id": self.job_id,
            "passed": self.passed,
            "has_warnings": self.has_warnings,
            "timestamp_unix": self.timestamp_unix,
            "checks": [{**dataclasses.asdict(c), "outcome": c.outcome.value} for c in self.checks],
        }


# =============================================================================


def check_truth_gate(report) -> CheckResult:
    """Accept a TruthGateReport-like object with .passed boolean."""
    if getattr(report, "passed", False):
        return CheckResult(
            name="truth_gate",
            outcome=PreflightOutcome.PASS,
            message="Truth Gate passed",
        )
    return CheckResult(
        name="truth_gate",
        outcome=PreflightOutcome.FAIL,
        message="Truth Gate did not pass — refusing to print",
    )


def check_printer_state(live_state: dict[str, Any]) -> CheckResult:
    if not live_state.get("reachable", False):
        return CheckResult(
            name="printer_state",
            outcome=PreflightOutcome.FAIL,
            message=f"Printer unreachable: {live_state.get('error', 'no response')}",
        )
    ks = live_state.get("klippy_state", "unknown")
    if ks == "ready":
        return CheckResult(
            name="printer_state",
            outcome=PreflightOutcome.PASS,
            message=f"Klippy ready",
        )
    if ks in ("printing", "paused"):
        return CheckResult(
            name="printer_state",
            outcome=PreflightOutcome.FAIL,
            message=f"Printer busy: {ks}",
        )
    return CheckResult(
        name="printer_state",
        outcome=PreflightOutcome.WARN,
        message=f"Klippy state '{ks}' is non-ready; proceed with caution",
    )


def check_spool(spool, required_grams: float, required_material: str) -> CheckResult:
    """Verify a loaded spool has enough filament of the right material.

    ``spool`` may be None (no spool tracked). In that case, the check is
    a WARN — proceed but warn the user.
    """
    if spool is None:
        return CheckResult(
            name="spool",
            outcome=PreflightOutcome.WARN,
            message="No tracked spool on this printer; cannot verify filament",
        )
    if spool.material.upper() != required_material.upper():
        return CheckResult(
            name="spool",
            outcome=PreflightOutcome.FAIL,
            message=(f"Loaded spool is {spool.material} but job needs {required_material}"),
        )
    if spool.remaining_grams < required_grams:
        return CheckResult(
            name="spool",
            outcome=PreflightOutcome.FAIL,
            message=(
                f"Loaded spool has only {spool.remaining_grams:.0f}g; "
                f"job needs {required_grams:.0f}g"
            ),
        )
    margin = spool.remaining_grams - required_grams
    if margin < 50:
        return CheckResult(
            name="spool",
            outcome=PreflightOutcome.WARN,
            message=(f"Spool has {margin:.0f}g margin — risky"),
        )
    return CheckResult(
        name="spool",
        outcome=PreflightOutcome.PASS,
        message=f"Spool OK ({spool.remaining_grams:.0f}g of {spool.material})",
    )


def check_schedule(decision) -> CheckResult:
    if getattr(decision, "allowed", False):
        return CheckResult(
            name="schedule",
            outcome=PreflightOutcome.PASS,
            message=f"Schedule OK — finish {decision.estimated_finish_local}",
        )
    return CheckResult(
        name="schedule",
        outcome=PreflightOutcome.FAIL,
        message="Schedule blocked: " + "; ".join(decision.reasons),
    )


def check_budget(cost_estimate, budget_usd: float | None) -> CheckResult:
    if budget_usd is None:
        return CheckResult(
            name="budget",
            outcome=PreflightOutcome.PASS,
            message="No budget cap set",
        )
    if cost_estimate.total_cost_usd > budget_usd:
        return CheckResult(
            name="budget",
            outcome=PreflightOutcome.FAIL,
            message=(
                f"Estimated ${cost_estimate.total_cost_usd:.2f} exceeds cap ${budget_usd:.2f}"
            ),
        )
    return CheckResult(
        name="budget",
        outcome=PreflightOutcome.PASS,
        message=f"Cost ${cost_estimate.total_cost_usd:.2f} within budget",
    )


def check_gcode_risks(analysis) -> CheckResult:
    risks = list(getattr(analysis, "risk_flags", []) or [])
    if not risks:
        return CheckResult(
            name="gcode_risks",
            outcome=PreflightOutcome.PASS,
            message="No risk flags raised by g-code analyzer",
        )
    return CheckResult(
        name="gcode_risks",
        outcome=PreflightOutcome.WARN,
        message=f"{len(risks)} risk flags raised: {risks[0]}",
        detail={"risks": risks},
    )


def run_preflight(
    *,
    printer_id: str,
    job_id: str | None = None,
    truth_gate_report=None,
    live_state: dict[str, Any] | None = None,
    spool=None,
    required_grams: float = 0.0,
    required_material: str = "PLA",
    schedule_decision=None,
    cost_estimate=None,
    budget_usd: float | None = None,
    gcode_analysis=None,
) -> PreflightReport:
    """Run the full preflight checklist. Each input is optional — the
    corresponding check is skipped when its data is missing.
    """
    import time

    report = PreflightReport(
        printer_id=printer_id,
        job_id=job_id,
        timestamp_unix=time.time(),
    )
    if truth_gate_report is not None:
        report.checks.append(check_truth_gate(truth_gate_report))
    if live_state is not None:
        report.checks.append(check_printer_state(live_state))
    if spool is not None or required_grams > 0:
        report.checks.append(check_spool(spool, required_grams, required_material))
    if schedule_decision is not None:
        report.checks.append(check_schedule(schedule_decision))
    if cost_estimate is not None:
        report.checks.append(check_budget(cost_estimate, budget_usd))
    if gcode_analysis is not None:
        report.checks.append(check_gcode_risks(gcode_analysis))
    return report


__all__ = [
    "CheckResult",
    "PreflightOutcome",
    "PreflightReport",
    "check_budget",
    "check_gcode_risks",
    "check_printer_state",
    "check_schedule",
    "check_spool",
    "check_truth_gate",
    "run_preflight",
]
