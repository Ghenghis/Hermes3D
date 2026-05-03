"""Thermal-runaway detection — pre-flight + live monitoring loop.

Status: runnable
Gate ID: ``safety.thermal_runaway_detection``
Contract: 03_implementation/.../safety/__init__.py public API.

This module implements the thermal-runaway detection state-machine that
the Hermes3D orchestrator drives over a printer's temperature telemetry.
The detector follows two independent trip conditions, either of which
fires an :class:`EmergencyStopEvent` within 2 seconds of detection:

  1. **Over-temperature persistence.** If ``extruder.temperature``
     exceeds ``target + over_target_c`` (default ``+15°C``) continuously
     for longer than ``window_s`` (default ``5 s``), the runaway trip
     fires.

  2. **Thermistor error event.** If Klipper / Marlin reports a
     thermistor disconnect (e.g. ``MINTEMP``, ``MAXTEMP``,
     ``shutdown:temperature_sensor``), the trip fires immediately on the
     same telemetry tick that surfaces the error.

The detector is a pure state machine: it consumes
:class:`TemperatureSample` instances and emits :class:`EmergencyStopEvent`
only when conditions are met. There is no I/O, no network, no thread.
The orchestrator's monitoring loop owns the cadence (typically 1 Hz);
the test harness drives it with a synthetic trace and asserts the
detection latency is bounded by ``2 × window_period``.

The "safety.violation" event payload is built by
:func:`build_violation_payload` and surfaced to the evidence ledger via
the existing event-manager bridge in
``hermes3d.core.agents.orchestrator``.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class TripReason(str, enum.Enum):
    """Why the detector fired an EmergencyStop trip."""

    OVER_TARGET_PERSISTENT = "over_target_persistent"
    THERMISTOR_ERROR = "thermistor_error"


@dataclass(frozen=True)
class TemperatureSample:
    """A single tick of extruder temperature telemetry.

    ``ts`` is monotonic seconds (e.g. from ``time.monotonic()``); the
    detector only ever subtracts samples, so wall-clock vs monotonic is
    irrelevant as long as it is consistent within one print job.

    ``thermistor_error`` carries an optional firmware error code
    (``"MINTEMP"``, ``"MAXTEMP"``, ``"shutdown:temperature_sensor"``,
    etc.) and trips the detector regardless of the temperature value.
    """

    ts: float
    temperature_c: float
    target_c: float
    thermistor_error: str | None = None


@dataclass(frozen=True)
class EmergencyStopEvent:
    """Trip output. Caller must immediately halt the print and persist
    a ``safety.violation`` event with this payload's ``to_dict()``.
    """

    ts: float
    reason: TripReason
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "reason": self.reason.value,
            "detail": dict(self.detail),
        }


@dataclass
class ThermalRunawayDetector:
    """Stateful runaway detector. One instance per printer per job.

    The detector accumulates the duration of the current "over target"
    excursion. Any sample whose temperature drops back below
    ``target + over_target_c`` resets the excursion to zero — a brief
    spike does not trip the gate, only sustained over-temperature for
    longer than ``window_s`` does.
    """

    over_target_c: float = 15.0
    window_s: float = 5.0
    # internal
    _excursion_start_ts: float | None = None
    _last_ts: float | None = None

    def reset(self) -> None:
        self._excursion_start_ts = None
        self._last_ts = None

    def feed(self, sample: TemperatureSample) -> EmergencyStopEvent | None:
        """Consume one sample. Return an :class:`EmergencyStopEvent` if
        this sample crosses a trip condition, otherwise ``None``.

        The latency between the *physical* event (the moment the
        printer reports a sample whose excursion-duration crosses
        ``window_s``) and the trip is by construction one sample period.
        At a 1 Hz monitoring cadence the worst-case detection latency is
        ``window_s + 1 s = 6 s``; the gate's 2-second budget refers to
        the time between the *detection moment* and the
        :class:`EmergencyStopEvent` being surfaced, not to the entire
        excursion.
        """
        self._last_ts = sample.ts

        # Condition 2: thermistor error trips immediately.
        if sample.thermistor_error:
            self._excursion_start_ts = None
            return EmergencyStopEvent(
                ts=sample.ts,
                reason=TripReason.THERMISTOR_ERROR,
                detail={
                    "error_code": sample.thermistor_error,
                    "temperature_c": sample.temperature_c,
                    "target_c": sample.target_c,
                },
            )

        # Condition 1: persistent over-target.
        threshold = sample.target_c + self.over_target_c
        if sample.temperature_c > threshold:
            if self._excursion_start_ts is None:
                self._excursion_start_ts = sample.ts
            elif (sample.ts - self._excursion_start_ts) > self.window_s:
                event = EmergencyStopEvent(
                    ts=sample.ts,
                    reason=TripReason.OVER_TARGET_PERSISTENT,
                    detail={
                        "temperature_c": sample.temperature_c,
                        "target_c": sample.target_c,
                        "threshold_c": threshold,
                        "excursion_s": sample.ts - self._excursion_start_ts,
                        "window_s": self.window_s,
                    },
                )
                self._excursion_start_ts = None
                return event
        else:
            # Drop back below threshold — clear excursion.
            self._excursion_start_ts = None
        return None


def replay_trace(
    samples: list[TemperatureSample],
    *,
    detector: ThermalRunawayDetector | None = None,
) -> tuple[EmergencyStopEvent | None, ThermalRunawayDetector]:
    """Replay an entire trace. Returns the first trip event (or None)
    and the detector instance for inspection. Used by the gate test.
    """
    det = detector or ThermalRunawayDetector()
    for s in samples:
        evt = det.feed(s)
        if evt is not None:
            return evt, det
    return None, det


def build_violation_payload(
    *,
    job_id: str,
    printer_id: str,
    event: EmergencyStopEvent,
    detection_latency_s: float,
) -> dict[str, Any]:
    """Build the ``safety.violation`` payload for the evidence ledger.

    The payload is intentionally JSON-serialisable with stdlib types so
    the existing event_manager bridge can ship it without touching it.
    """
    return {
        "kind": "safety.violation",
        "gate": "safety.thermal_runaway_detection",
        "job_id": job_id,
        "printer_id": printer_id,
        "event": event.to_dict(),
        "detection_latency_s": detection_latency_s,
    }


__all__ = [
    "EmergencyStopEvent",
    "TemperatureSample",
    "ThermalRunawayDetector",
    "TripReason",
    "build_violation_payload",
    "replay_trace",
]
