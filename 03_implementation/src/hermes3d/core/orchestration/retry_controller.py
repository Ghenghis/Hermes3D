"""Retry budget controller — bounded self-correction for workflow nodes.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §30 (Orchestration Brain)

Pure-stdlib retry decorator that gives each workflow node a finite "budget"
of attempts before escalating to the Repair agent. Failures inside the
budget retry with linear or exponential backoff. Failures past the budget
raise a ``RepairEscalation`` carrying enough context for a repair attempt.

Why a custom controller (vs ``tenacity``):
  - Hermes3D-OS Lite is local-first. Pure stdlib means zero new deps.
  - Escalation-on-exhaustion is a first-class outcome, not an afterthought.
  - The decorator preserves wrapped function metadata so existing tests
    keep working.
"""
from __future__ import annotations

import functools
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

log = logging.getLogger(__name__)


@dataclass
class RetryBudget:
    """Bounded retry policy for a single node."""

    max_retries: int = 3
    backoff: Literal["linear", "exponential"] = "exponential"
    initial_delay: float = 1.0

    def delay_for(self, attempt: int) -> float:
        """Delay (seconds) BEFORE attempt number ``attempt`` (1-indexed).

        Attempt 1 has zero delay; subsequent attempts back off.
        """
        if attempt <= 1:
            return 0.0
        if self.backoff == "linear":
            return float(self.initial_delay) * (attempt - 1)
        # exponential
        return float(self.initial_delay) * (2 ** (attempt - 2))


class RepairEscalation(Exception):
    """Raised when a node exhausts its retry budget.

    Carries the failure context the Repair agent needs to suggest a fix.
    """

    def __init__(self, *, cause: BaseException, attempts: int,
                 context: dict[str, Any]) -> None:
        self.cause = cause
        self.attempts = attempts
        self.context = context
        super().__init__(
            f"retry budget exhausted after {attempts} attempts "
            f"(node={context.get('node_name')!r}): {cause!r}"
        )


def with_retry(budget: RetryBudget | None = None,
               on_failure: Callable[[BaseException, int], None] | None = None
               ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that retries a function within a ``RetryBudget``.

    On terminal failure (budget exhausted) raises ``RepairEscalation``.

    Args:
        budget: retry policy; defaults to ``RetryBudget()``.
        on_failure: optional callback ``(exc, attempt)`` invoked after every
            failed attempt (including the terminal one) — useful for
            telemetry/logging without coupling to the retry machinery.
    """
    b = budget or RetryBudget()

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            last_good_state: Any = None
            # Allow the first arg (typical: WorkflowState) to act as the
            # last_good_state snapshot for diagnostics.
            if args:
                last_good_state = args[0]
            total_attempts = b.max_retries + 1
            for attempt in range(1, total_attempts + 1):
                delay = b.delay_for(attempt)
                if delay > 0:
                    time.sleep(delay)
                try:
                    return fn(*args, **kwargs)
                except RepairEscalation:
                    # Already escalated downstream — propagate untouched.
                    raise
                except BaseException as exc:  # noqa: BLE001
                    last_exc = exc
                    if on_failure is not None:
                        try:
                            on_failure(exc, attempt)
                        except Exception:  # noqa: BLE001
                            log.exception("on_failure callback raised")
                    log.warning(
                        "with_retry: %s attempt %d/%d failed: %r",
                        getattr(fn, "__name__", "fn"),
                        attempt, total_attempts, exc,
                    )
            # Budget exhausted
            assert last_exc is not None
            raise RepairEscalation(
                cause=last_exc,
                attempts=total_attempts,
                context={
                    "node_name": getattr(fn, "__name__", "fn"),
                    "last_good_state": last_good_state,
                    "args_repr": repr(args)[:500],
                    "kwargs_repr": repr(kwargs)[:500],
                },
            )

        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        return wrapper

    return decorator


__all__ = [
    "RepairEscalation",
    "RetryBudget",
    "with_retry",
]
