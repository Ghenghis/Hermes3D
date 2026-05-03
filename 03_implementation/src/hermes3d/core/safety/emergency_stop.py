"""Emergency-stop timing harness.

Status: runnable
Gate ID: ``safety.emergency_stop_timing``

Exercises the round-trip:

    M112 issued -> firmware reports motor halt evidence

against a synthetic Klipper / Marlin mock simulator. Asserts that the
end-to-end timer is below 200 ms, which is the budget the
``safety.emergency_stop_timing`` gate enforces.

The harness is structured so the same code path can be pointed at
either:

  * an in-process :class:`KlipperMockSimulator` (test default), or
  * a real client implementing the :class:`EmergencyStopTransport`
    protocol (a thin wrapper around Moonraker's ``machine.shutdown``
    + Klipper's ``shutdown`` event subscription).

No network I/O happens in this module; the production transport lives
in ``hermes3d.core.printers.moonraker_client``. This file is the
*timing assertion* and the *mock* used to pin behavior in tests.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Protocol


class HaltOutcome(str, enum.Enum):
    HALTED = "halted"
    TIMEOUT = "timeout"
    NO_RESPONSE = "no_response"


@dataclass(frozen=True)
class HaltEvidence:
    """Firmware evidence of a successful motor halt.

    ``response_token`` is the firmware string we accept as proof
    (Klipper: ``"klipper:idle: motors_disabled"``, Marlin: ``"echo:M112"``
    followed by ``"//action:disable_steppers"`` — we accept either).
    """

    outcome: HaltOutcome
    response_token: str
    elapsed_ms: float
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "response_token": self.response_token,
            "elapsed_ms": self.elapsed_ms,
            "detail": dict(self.detail),
        }


class EmergencyStopTransport(Protocol):
    """Anything that can ``send_m112`` and return a halt evidence string.

    Implementations:
      * :class:`KlipperMockSimulator` — synthetic, configurable delay.
      * Real Moonraker client (out of scope for this module).
    """

    def send_m112(self, *, timeout_s: float) -> tuple[str, float]:
        """Issue M112 and block until the firmware reports a halt.

        Return ``(response_token, elapsed_seconds)``. Raise
        ``TimeoutError`` if the firmware does not respond within
        ``timeout_s``.
        """
        ...


# ---------------------------------------------------------------------------
# Synthetic mock — used by the gate test.
# ---------------------------------------------------------------------------


@dataclass
class KlipperMockSimulator:
    """In-process mock that responds to M112 after a configurable delay.

    The delay is *deterministic* — the simulator does not actually sleep
    by default, but instead reports the requested delay as the elapsed
    time. Set ``actually_sleep=True`` to insert a real ``time.sleep``
    call (used by the timing-budget integration test to confirm wall
    clock behavior).
    """

    response_delay_s: float = 0.05  # 50 ms default
    response_token: str = "klipper:idle: motors_disabled"
    fail_to_respond: bool = False
    actually_sleep: bool = False

    def send_m112(self, *, timeout_s: float) -> tuple[str, float]:
        if self.fail_to_respond:
            raise TimeoutError(
                f"KlipperMockSimulator configured with fail_to_respond=True "
                f"(timeout={timeout_s:.3f}s)"
            )
        if self.response_delay_s > timeout_s:
            raise TimeoutError(
                f"M112 timeout: response_delay={self.response_delay_s:.3f}s "
                f"exceeds budget {timeout_s:.3f}s"
            )
        if self.actually_sleep:
            time.sleep(self.response_delay_s)
        return self.response_token, self.response_delay_s


# ---------------------------------------------------------------------------
# Timing harness — the gate's runtime assertion.
# ---------------------------------------------------------------------------


def measure_m112_round_trip(
    transport: EmergencyStopTransport,
    *,
    timeout_s: float = 0.200,
) -> HaltEvidence:
    """Issue ``M112`` and time the round trip end-to-end.

    Returns a :class:`HaltEvidence`. The ``elapsed_ms`` field is the
    measured wall-clock delta between just-before-send and the firmware
    response token being observed. This is what the gate compares
    against the 200 ms budget.

    The timing budget itself is enforced by the gate, not by this
    function — we want the function to *measure* even when over-budget
    so tests can record the exact margin.
    """
    started_at = time.monotonic()
    try:
        token, elapsed_s = transport.send_m112(timeout_s=timeout_s)
    except TimeoutError as exc:
        elapsed_ms = (time.monotonic() - started_at) * 1000.0
        return HaltEvidence(
            outcome=HaltOutcome.TIMEOUT,
            response_token="",
            elapsed_ms=elapsed_ms,
            detail={"error": str(exc), "timeout_s": timeout_s},
        )
    # Use the wall-clock delta — this is the number the gate checks.
    elapsed_ms = (time.monotonic() - started_at) * 1000.0
    if elapsed_s is not None and not elapsed_ms:
        elapsed_ms = elapsed_s * 1000.0
    return HaltEvidence(
        outcome=HaltOutcome.HALTED,
        response_token=token,
        elapsed_ms=elapsed_ms,
        detail={"reported_elapsed_s": elapsed_s, "timeout_s": timeout_s},
    )


def assert_within_budget(evidence: HaltEvidence, *, budget_ms: float = 200.0) -> None:
    """Raise ``AssertionError`` if the M112 round trip blew its budget.

    Used by the gate runner; pytest tests call ``measure_m112_round_trip``
    directly and compare ``evidence.elapsed_ms`` themselves.
    """
    if evidence.outcome is not HaltOutcome.HALTED:
        raise AssertionError(
            f"emergency_stop_timing: outcome={evidence.outcome.value} "
            f"(expected HALTED); detail={evidence.detail}"
        )
    if evidence.elapsed_ms > budget_ms:
        raise AssertionError(
            f"emergency_stop_timing: elapsed={evidence.elapsed_ms:.1f}ms "
            f"exceeds budget {budget_ms:.1f}ms"
        )


def build_violation_payload(
    *,
    job_id: str,
    printer_id: str,
    evidence: HaltEvidence,
    budget_ms: float,
) -> dict[str, Any]:
    """Build the ``safety.violation`` payload when M112 timing fails."""
    return {
        "kind": "safety.violation",
        "gate": "safety.emergency_stop_timing",
        "job_id": job_id,
        "printer_id": printer_id,
        "evidence": evidence.to_dict(),
        "budget_ms": budget_ms,
    }


__all__ = [
    "EmergencyStopTransport",
    "HaltEvidence",
    "HaltOutcome",
    "KlipperMockSimulator",
    "assert_within_budget",
    "build_violation_payload",
    "measure_m112_round_trip",
]
