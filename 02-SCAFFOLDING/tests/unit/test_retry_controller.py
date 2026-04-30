"""Tests for retry_controller — RetryBudget + with_retry decorator."""
from __future__ import annotations

import pytest

from hermes3d.core.orchestration.retry_controller import (
    RepairEscalation,
    RetryBudget,
    with_retry,
)


def test_retry_succeeds_after_two_failures(monkeypatch):
    """Function raises twice, then succeeds — wrapper returns the value."""
    monkeypatch.setattr(
        "hermes3d.core.orchestration.retry_controller.time.sleep",
        lambda _s: None,
    )
    calls = {"n": 0}

    @with_retry(RetryBudget(max_retries=3, initial_delay=0.0))
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_retry_exhaustion_raises_repair_escalation(monkeypatch):
    """Function always raises -> RepairEscalation, attempts == max_retries+1."""
    monkeypatch.setattr(
        "hermes3d.core.orchestration.retry_controller.time.sleep",
        lambda _s: None,
    )
    calls = {"n": 0}

    @with_retry(RetryBudget(max_retries=3, initial_delay=0.0))
    def always_fails():
        calls["n"] += 1
        raise ValueError("boom")

    with pytest.raises(RepairEscalation) as exc_info:
        always_fails()
    esc = exc_info.value
    assert esc.attempts == 4  # max_retries (3) + 1
    assert calls["n"] == 4
    assert isinstance(esc.cause, ValueError)
    assert esc.context["node_name"] == "always_fails"


def test_exponential_backoff_increasing_delays(monkeypatch):
    """Exponential backoff yields strictly increasing sleep durations."""
    seen: list[float] = []
    monkeypatch.setattr(
        "hermes3d.core.orchestration.retry_controller.time.sleep",
        lambda s: seen.append(s),
    )

    budget = RetryBudget(max_retries=4, backoff="exponential",
                          initial_delay=1.0)

    @with_retry(budget)
    def always_fails():
        raise RuntimeError("nope")

    with pytest.raises(RepairEscalation):
        always_fails()
    # Attempt 1 has 0 delay (no sleep call). Attempts 2..5 should be
    # 1, 2, 4, 8.
    nonzero = [s for s in seen if s > 0]
    assert nonzero == [1.0, 2.0, 4.0, 8.0]
    # Strictly increasing
    assert all(b > a for a, b in zip(nonzero, nonzero[1:]))


def test_with_retry_preserves_metadata_and_return_type(monkeypatch):
    monkeypatch.setattr(
        "hermes3d.core.orchestration.retry_controller.time.sleep",
        lambda _s: None,
    )

    @with_retry(RetryBudget(max_retries=1, initial_delay=0.0))
    def my_node(x: int) -> dict:
        """Original docstring."""
        return {"value": x * 2}

    assert my_node.__name__ == "my_node"
    assert "Original docstring" in (my_node.__doc__ or "")
    out = my_node(7)
    assert isinstance(out, dict)
    assert out == {"value": 14}
