"""Tests for hermes3d.core.safety.thermal_runaway."""

from __future__ import annotations

from hermes3d.core.safety.thermal_runaway import (
    TemperatureSample,
    ThermalRunawayDetector,
    TripReason,
    build_violation_payload,
    replay_trace,
)


def _ramp_up_trace(
    *,
    target_c: float = 200.0,
    samples_below: int = 3,
    samples_above: int = 7,
    overshoot_c: float = 16.0,
    period_s: float = 1.0,
) -> list[TemperatureSample]:
    """Build a trace that climbs past target+15 for `samples_above` ticks."""
    trace: list[TemperatureSample] = []
    t = 0.0
    for _ in range(samples_below):
        trace.append(TemperatureSample(ts=t, temperature_c=target_c, target_c=target_c))
        t += period_s
    # Each sample at temp = target + overshoot_c (above the +15 threshold).
    for _ in range(samples_above):
        trace.append(
            TemperatureSample(
                ts=t, temperature_c=target_c + overshoot_c, target_c=target_c
            )
        )
        t += period_s
    return trace


def test_brief_spike_does_not_trip() -> None:
    target = 200.0
    samples = [
        TemperatureSample(ts=0.0, temperature_c=200.0, target_c=target),
        TemperatureSample(ts=1.0, temperature_c=216.0, target_c=target),  # over
        TemperatureSample(ts=2.0, temperature_c=210.0, target_c=target),  # back below
        TemperatureSample(ts=3.0, temperature_c=200.0, target_c=target),
    ]
    evt, _ = replay_trace(samples)
    assert evt is None


def test_persistent_overheat_trips_after_window() -> None:
    """6 seconds at target+16C -> trip on the sample crossing 5s threshold."""
    samples = _ramp_up_trace(
        target_c=200.0, samples_below=2, samples_above=7, overshoot_c=16.0, period_s=1.0
    )
    evt, _ = replay_trace(samples)
    assert evt is not None
    assert evt.reason is TripReason.OVER_TARGET_PERSISTENT
    assert evt.detail["temperature_c"] == 216.0
    assert evt.detail["target_c"] == 200.0
    assert evt.detail["excursion_s"] > 5.0


def test_thermistor_error_trips_immediately() -> None:
    samples = [
        TemperatureSample(ts=0.0, temperature_c=205.0, target_c=200.0),
        TemperatureSample(
            ts=1.0,
            temperature_c=0.0,
            target_c=200.0,
            thermistor_error="MINTEMP",
        ),
    ]
    evt, _ = replay_trace(samples)
    assert evt is not None
    assert evt.reason is TripReason.THERMISTOR_ERROR
    assert evt.detail["error_code"] == "MINTEMP"


def test_excursion_resets_when_temp_drops_below_threshold() -> None:
    """A 4-second over-target stretch followed by a recovery should NOT trip,
    even if a *later* over-target stretch begins immediately."""
    target = 200.0
    samples = [
        TemperatureSample(ts=0.0, temperature_c=216.0, target_c=target),  # start
        TemperatureSample(ts=1.0, temperature_c=216.0, target_c=target),
        TemperatureSample(ts=2.0, temperature_c=216.0, target_c=target),
        TemperatureSample(ts=3.0, temperature_c=216.0, target_c=target),
        TemperatureSample(ts=4.0, temperature_c=210.0, target_c=target),  # recover
        TemperatureSample(ts=5.0, temperature_c=216.0, target_c=target),  # restart
        TemperatureSample(ts=6.0, temperature_c=216.0, target_c=target),
    ]
    evt, _ = replay_trace(samples)
    assert evt is None


def test_detection_latency_within_two_second_budget() -> None:
    """The brief mandates ``EmergencyStop`` fires within 2 s of the
    detection moment. With 1-Hz cadence, the trip lands on the first
    sample after the 5 s window — i.e. <= 1 s after it crosses, well
    under 2 s.
    """
    samples = _ramp_up_trace(
        target_c=200.0, samples_below=0, samples_above=7, overshoot_c=16.0, period_s=1.0
    )
    evt, _ = replay_trace(samples)
    assert evt is not None
    # First over-target sample is at ts=0.0; trip must fire by ts<=7.0 (5s window + 2s budget).
    assert evt.ts <= 7.0


def test_high_resolution_trace_detects_within_budget() -> None:
    """50 ms cadence — trip should fire within window + 0.5 s easily."""
    target = 200.0
    samples: list[TemperatureSample] = []
    t = 0.0
    while t <= 6.0:
        samples.append(
            TemperatureSample(ts=t, temperature_c=216.0, target_c=target)
        )
        t += 0.05
    evt, _ = replay_trace(samples)
    assert evt is not None
    assert evt.ts <= 5.1  # well within 5s window + 2s budget


def test_violation_payload_shape() -> None:
    samples = _ramp_up_trace()
    evt, _ = replay_trace(samples)
    assert evt is not None
    payload = build_violation_payload(
        job_id="job-1",
        printer_id="flsun_qqs_pro",
        event=evt,
        detection_latency_s=0.7,
    )
    assert payload["kind"] == "safety.violation"
    assert payload["gate"] == "safety.thermal_runaway_detection"
    assert payload["job_id"] == "job-1"
    assert payload["printer_id"] == "flsun_qqs_pro"
    assert payload["event"]["reason"] == TripReason.OVER_TARGET_PERSISTENT.value
    assert payload["detection_latency_s"] == 0.7


def test_detector_reset_clears_excursion() -> None:
    target = 200.0
    det = ThermalRunawayDetector()
    det.feed(TemperatureSample(ts=0.0, temperature_c=216.0, target_c=target))
    det.feed(TemperatureSample(ts=1.0, temperature_c=216.0, target_c=target))
    det.reset()
    # Now feed 2 more over-target samples — no trip because the excursion was reset.
    evt = det.feed(TemperatureSample(ts=2.0, temperature_c=216.0, target_c=target))
    assert evt is None
    evt = det.feed(TemperatureSample(ts=3.0, temperature_c=216.0, target_c=target))
    assert evt is None
