"""Tests for hermes3d.core.safety.emergency_stop."""

from __future__ import annotations

import pytest
from hermes3d.core.safety.emergency_stop import (
    HaltOutcome,
    KlipperMockSimulator,
    assert_within_budget,
    build_violation_payload,
    measure_m112_round_trip,
)


def test_fast_response_within_budget() -> None:
    sim = KlipperMockSimulator(response_delay_s=0.05)
    evidence = measure_m112_round_trip(sim, timeout_s=0.200)
    assert evidence.outcome is HaltOutcome.HALTED
    assert evidence.elapsed_ms < 200.0
    assert "motors_disabled" in evidence.response_token


def test_slow_response_times_out() -> None:
    """Mock response delay > timeout -> TimeoutError -> TIMEOUT outcome."""
    sim = KlipperMockSimulator(response_delay_s=0.250)
    evidence = measure_m112_round_trip(sim, timeout_s=0.200)
    assert evidence.outcome is HaltOutcome.TIMEOUT
    assert "timeout" in evidence.detail["error"].lower()


def test_assert_within_budget_passes_for_fast_halt() -> None:
    sim = KlipperMockSimulator(response_delay_s=0.030)
    evidence = measure_m112_round_trip(sim, timeout_s=0.200)
    assert_within_budget(evidence, budget_ms=200.0)


def test_assert_within_budget_raises_on_timeout() -> None:
    sim = KlipperMockSimulator(fail_to_respond=True)
    evidence = measure_m112_round_trip(sim, timeout_s=0.200)
    with pytest.raises(AssertionError, match="outcome=timeout"):
        assert_within_budget(evidence, budget_ms=200.0)


def test_violation_payload_shape_for_timeout() -> None:
    sim = KlipperMockSimulator(fail_to_respond=True)
    evidence = measure_m112_round_trip(sim, timeout_s=0.200)
    payload = build_violation_payload(
        job_id="job-7",
        printer_id="prusa_mk3s",
        evidence=evidence,
        budget_ms=200.0,
    )
    assert payload["kind"] == "safety.violation"
    assert payload["gate"] == "safety.emergency_stop_timing"
    assert payload["evidence"]["outcome"] == "timeout"


def test_real_sleep_path_observably_within_budget() -> None:
    """When ``actually_sleep=True`` the simulator inserts a real sleep —
    confirms the wall-clock measurement path also reports under budget.
    """
    sim = KlipperMockSimulator(response_delay_s=0.020, actually_sleep=True)
    evidence = measure_m112_round_trip(sim, timeout_s=0.200)
    assert evidence.outcome is HaltOutcome.HALTED
    assert evidence.elapsed_ms < 200.0
    assert evidence.elapsed_ms >= 15.0  # Some wall time should pass
