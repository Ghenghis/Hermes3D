"""Auto-recovery agent.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §28 (Auto-Recovery)

When a printer reports `klippy_state: 'error'` or 'shutdown', this agent
attempts a recovery sequence with exponential backoff:

  1. Wait 5 seconds
  2. POST /printer/restart      — soft Klipper restart
  3. Re-probe — if ready, success
  4. Wait 30 seconds
  5. POST /printer/firmware_restart  — full MCU restart
  6. Re-probe — if ready, success
  7. Give up — return RecoveryFailed; user intervention required

The agent never powers anything off. It only invokes Moonraker endpoints
that are safe to call when no print is active. Callers MUST verify there
is no active print before invoking — the agent itself does this check.
"""

from __future__ import annotations

import dataclasses
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from hermes3d.core.printers import get_profile
from hermes3d.core.printers.moonraker_client import MoonrakerClient

log = logging.getLogger(__name__)


class RecoveryOutcome(str, enum.Enum):
    NOT_NEEDED = "not_needed"
    RECOVERED_SOFT = "recovered_soft"
    RECOVERED_FIRMWARE = "recovered_firmware"
    GAVE_UP = "gave_up"
    BLOCKED = "blocked"  # cannot recover — print active


@dataclass
class RecoveryAttempt:
    step: str
    sent_unix: float
    outcome: str
    detail: str = ""


@dataclass
class RecoveryResult:
    printer_id: str
    outcome: RecoveryOutcome
    attempts: list[RecoveryAttempt] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["outcome"] = self.outcome.value
        return d


def auto_recover(
    printer_id: str,
    *,
    api_key: str | None = None,
    initial_wait_s: float = 5.0,
    firmware_restart_wait_s: float = 30.0,
    poll_interval_s: float = 2.0,
    max_total_s: float = 90.0,
) -> RecoveryResult:
    """Attempt to recover a printer in error/shutdown state.

    Returns a RecoveryResult with the outcome and full audit trail.
    """
    profile = get_profile(printer_id)
    client = MoonrakerClient(profile.moonraker_url_default, api_key=api_key, timeout_s=5.0)
    started = time.time()
    result = RecoveryResult(printer_id=printer_id, outcome=RecoveryOutcome.GAVE_UP)

    # Initial state probe
    try:
        state = client.printer_state()
    except Exception as exc:
        result.attempts.append(
            RecoveryAttempt(
                step="initial_probe",
                sent_unix=time.time(),
                outcome="error",
                detail=f"unreachable: {exc}",
            )
        )
        result.final_state = {"reachable": False, "error": str(exc)}
        result.duration_seconds = time.time() - started
        return result

    klippy_state = state.get("klippy_state", "unknown")
    if klippy_state == "ready":
        result.outcome = RecoveryOutcome.NOT_NEEDED
        result.final_state = state
        result.duration_seconds = time.time() - started
        return result
    if klippy_state in ("printing", "paused"):
        result.outcome = RecoveryOutcome.BLOCKED
        result.attempts.append(
            RecoveryAttempt(
                step="block_check",
                sent_unix=time.time(),
                outcome="blocked",
                detail=f"klippy_state={klippy_state} — refusing to restart during active print",
            )
        )
        result.final_state = state
        result.duration_seconds = time.time() - started
        return result

    log.info("Recovery starting for %s (klippy_state=%s)", printer_id, klippy_state)

    # ---- Step 1: soft restart ----
    time.sleep(initial_wait_s)
    try:
        client._request("POST", "/printer/restart")
        result.attempts.append(
            RecoveryAttempt(
                step="soft_restart",
                sent_unix=time.time(),
                outcome="sent",
                detail="POST /printer/restart issued",
            )
        )
    except Exception as exc:
        result.attempts.append(
            RecoveryAttempt(
                step="soft_restart",
                sent_unix=time.time(),
                outcome="error",
                detail=str(exc),
            )
        )

    # Poll for ready
    soft_deadline = time.time() + 20.0
    while time.time() < soft_deadline and time.time() - started < max_total_s:
        time.sleep(poll_interval_s)
        try:
            state = client.printer_state()
            if state.get("klippy_state") == "ready":
                result.outcome = RecoveryOutcome.RECOVERED_SOFT
                result.final_state = state
                result.duration_seconds = time.time() - started
                log.info("Recovered %s via soft restart", printer_id)
                return result
        except Exception as exc:  # noqa: BLE001 -- Wave Agent 7: log recovery-poll failure
            log.debug(
                "auto_recovery.printer_state_poll_soft fallback: %s: %s",
                type(exc).__name__,
                exc,
            )

    # ---- Step 2: firmware restart ----
    time.sleep(min(firmware_restart_wait_s, max(0.0, max_total_s - (time.time() - started))))
    if time.time() - started >= max_total_s:
        result.outcome = RecoveryOutcome.GAVE_UP
        result.duration_seconds = time.time() - started
        return result
    try:
        client._request("POST", "/printer/firmware_restart")
        result.attempts.append(
            RecoveryAttempt(
                step="firmware_restart",
                sent_unix=time.time(),
                outcome="sent",
                detail="POST /printer/firmware_restart issued",
            )
        )
    except Exception as exc:
        result.attempts.append(
            RecoveryAttempt(
                step="firmware_restart",
                sent_unix=time.time(),
                outcome="error",
                detail=str(exc),
            )
        )

    fw_deadline = time.time() + 30.0
    while time.time() < fw_deadline and time.time() - started < max_total_s:
        time.sleep(poll_interval_s)
        try:
            state = client.printer_state()
            if state.get("klippy_state") == "ready":
                result.outcome = RecoveryOutcome.RECOVERED_FIRMWARE
                result.final_state = state
                result.duration_seconds = time.time() - started
                log.info("Recovered %s via firmware restart", printer_id)
                return result
        except Exception as exc:  # noqa: BLE001 -- Wave Agent 7: log firmware-recovery-poll failure
            log.debug(
                "auto_recovery.firmware_restart fallback: %s: %s",
                type(exc).__name__,
                exc,
            )

    result.outcome = RecoveryOutcome.GAVE_UP
    result.final_state = state if "state" in locals() else {}
    result.duration_seconds = time.time() - started
    return result


__all__ = [
    "RecoveryAttempt",
    "RecoveryOutcome",
    "RecoveryResult",
    "auto_recover",
]
