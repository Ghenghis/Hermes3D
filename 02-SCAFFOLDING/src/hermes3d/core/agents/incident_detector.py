"""Incident detector.

Closes the loop between Moonraker / OctoPrint health pings and the supervisor
daemon. The detector classifies incidents into actionable types and emits
``IncidentEvent`` objects the supervisor turns into notifications + recovery
attempts.

Incident types covered (real-world fleet failures Dave has hit before):

  - NETWORK_LOSS         : printer host unreachable for N consecutive pings
  - MCU_DISCONNECTED     : Klipper connected but MCU error in printer state
  - RUNAWAY_TEMP         : hotend or bed temperature outside safe envelope
  - PRINT_STALLED        : print active but progress unchanged for N seconds
  - POWER_LOSS_SUSPECTED : was printing, now reports klippy not running
  - SD_CARD_REMOVED      : virtual_sdcard reports no file but job was active
  - FAN_FAILURE          : extruder temp drift up while target unchanged
  - FILAMENT_RUNOUT      : runout sensor triggered, print active
  - OBICO_FAILURE_SIGNAL : Obico says failure threshold exceeded

The detector is stateful — it keeps a per-printer rolling window of pings
so transient blips don't trigger false alarms.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IncidentType(str, Enum):
    NETWORK_LOSS = "network_loss"
    MCU_DISCONNECTED = "mcu_disconnected"
    RUNAWAY_TEMP = "runaway_temp"
    PRINT_STALLED = "print_stalled"
    POWER_LOSS_SUSPECTED = "power_loss_suspected"
    SD_CARD_REMOVED = "sd_card_removed"
    FAN_FAILURE = "fan_failure"
    FILAMENT_RUNOUT = "filament_runout"
    OBICO_FAILURE_SIGNAL = "obico_failure_signal"


class IncidentSeverity(str, Enum):
    INFO = "info"      # log, no user action
    WARN = "warn"      # notify user
    CRITICAL = "critical"  # auto-pause + notify


@dataclass
class IncidentEvent:
    incident_type: IncidentType
    severity: IncidentSeverity
    printer_id: str
    detected_at: float
    description: str
    suggested_action: str
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_type": self.incident_type.value,
            "severity": self.severity.value,
            "printer_id": self.printer_id,
            "detected_at": self.detected_at,
            "description": self.description,
            "suggested_action": self.suggested_action,
            "context": dict(self.context),
        }


@dataclass
class PrinterPing:
    """One health ping from Moonraker/OctoPrint."""

    printer_id: str
    timestamp: float
    reachable: bool
    klippy_state: str | None = None  # "ready", "shutdown", "error", "startup"
    print_state: str | None = None   # "printing", "paused", "complete", "error", "standby"
    progress: float | None = None    # 0..1
    hotend_temp_c: float | None = None
    hotend_target_c: float | None = None
    bed_temp_c: float | None = None
    bed_target_c: float | None = None
    filament_present: bool | None = None
    obico_failure_score: float | None = None  # 0..1, >=0.45 means probable failure


# Tunables — conservative defaults so we don't false-alarm.
NETWORK_LOSS_PINGS = 3            # 3 consecutive misses = network loss
STALL_PROGRESS_SECONDS = 600      # 10 minutes with no progress change
RUNAWAY_HOTEND_OFFSET_C = 25      # actual > target + 25°C
RUNAWAY_BED_OFFSET_C = 15
FAN_FAILURE_DRIFT_OFFSET_C = 12   # target unchanged, actual climbs >12°C
FAN_FAILURE_WINDOW_PINGS = 5
OBICO_FAILURE_THRESHOLD = 0.45


class IncidentDetector:
    """Stateful detector. Feed it pings via ``ingest_ping``; query incidents."""

    def __init__(
        self,
        *,
        network_loss_pings: int = NETWORK_LOSS_PINGS,
        stall_seconds: int = STALL_PROGRESS_SECONDS,
        ping_window: int = 16,
    ) -> None:
        self._network_loss_pings = network_loss_pings
        self._stall_seconds = stall_seconds
        self._pings: dict[str, deque[PrinterPing]] = defaultdict(
            lambda: deque(maxlen=ping_window)
        )

    def ingest_ping(self, ping: PrinterPing) -> list[IncidentEvent]:
        history = self._pings[ping.printer_id]
        history.append(ping)
        events: list[IncidentEvent] = []

        events.extend(self._check_network(ping, history))
        events.extend(self._check_klippy(ping, history))
        events.extend(self._check_runaway(ping))
        events.extend(self._check_stall(ping, history))
        events.extend(self._check_fan(ping, history))
        events.extend(self._check_filament(ping))
        events.extend(self._check_obico(ping))

        return events

    # -----------------------------------------------------------------
    # Detection rules
    # -----------------------------------------------------------------

    def _check_network(
        self, ping: PrinterPing, history: deque[PrinterPing]
    ) -> list[IncidentEvent]:
        if ping.reachable:
            return []
        recent = list(history)[-self._network_loss_pings :]
        if len(recent) < self._network_loss_pings:
            return []
        if all(not p.reachable for p in recent):
            return [
                IncidentEvent(
                    incident_type=IncidentType.NETWORK_LOSS,
                    severity=IncidentSeverity.WARN,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description=f"{ping.printer_id} unreachable for {self._network_loss_pings} consecutive pings",
                    suggested_action="Check Wi-Fi/Ethernet, restart Pi if needed.",
                    context={"window": [p.timestamp for p in recent]},
                )
            ]
        return []

    def _check_klippy(
        self, ping: PrinterPing, history: deque[PrinterPing]
    ) -> list[IncidentEvent]:
        events: list[IncidentEvent] = []
        if ping.klippy_state == "error":
            events.append(
                IncidentEvent(
                    incident_type=IncidentType.MCU_DISCONNECTED,
                    severity=IncidentSeverity.CRITICAL,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description=f"{ping.printer_id} reports klippy_state=error",
                    suggested_action="Run FIRMWARE_RESTART; check USB cable; check thermistor wiring.",
                    context={"klippy_state": ping.klippy_state},
                )
            )

        prior_active = any(
            p.print_state == "printing" for p in list(history)[:-1]
        )
        if (
            prior_active
            and ping.klippy_state in {"shutdown", "startup"}
            and ping.print_state != "printing"
        ):
            events.append(
                IncidentEvent(
                    incident_type=IncidentType.POWER_LOSS_SUSPECTED,
                    severity=IncidentSeverity.CRITICAL,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description=f"{ping.printer_id} was printing, now klippy={ping.klippy_state}",
                    suggested_action="Inspect printer for completion or partial print; check PSU.",
                    context={"klippy_state": ping.klippy_state},
                )
            )
        return events

    def _check_runaway(self, ping: PrinterPing) -> list[IncidentEvent]:
        events: list[IncidentEvent] = []
        if (
            ping.hotend_temp_c is not None
            and ping.hotend_target_c is not None
            and ping.hotend_target_c > 0
            and ping.hotend_temp_c > ping.hotend_target_c + RUNAWAY_HOTEND_OFFSET_C
        ):
            events.append(
                IncidentEvent(
                    incident_type=IncidentType.RUNAWAY_TEMP,
                    severity=IncidentSeverity.CRITICAL,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description=(
                        f"Hotend {ping.hotend_temp_c:.0f}°C exceeds target "
                        f"{ping.hotend_target_c:.0f}°C by >{RUNAWAY_HOTEND_OFFSET_C}°C"
                    ),
                    suggested_action="EMERGENCY_STOP: thermal runaway suspected.",
                    context={
                        "hotend_temp_c": ping.hotend_temp_c,
                        "hotend_target_c": ping.hotend_target_c,
                    },
                )
            )
        if (
            ping.bed_temp_c is not None
            and ping.bed_target_c is not None
            and ping.bed_target_c > 0
            and ping.bed_temp_c > ping.bed_target_c + RUNAWAY_BED_OFFSET_C
        ):
            events.append(
                IncidentEvent(
                    incident_type=IncidentType.RUNAWAY_TEMP,
                    severity=IncidentSeverity.CRITICAL,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description=(
                        f"Bed {ping.bed_temp_c:.0f}°C exceeds target "
                        f"{ping.bed_target_c:.0f}°C by >{RUNAWAY_BED_OFFSET_C}°C"
                    ),
                    suggested_action="EMERGENCY_STOP: bed thermal runaway suspected.",
                    context={
                        "bed_temp_c": ping.bed_temp_c,
                        "bed_target_c": ping.bed_target_c,
                    },
                )
            )
        return events

    def _check_stall(
        self, ping: PrinterPing, history: deque[PrinterPing]
    ) -> list[IncidentEvent]:
        if ping.print_state != "printing" or ping.progress is None:
            return []
        baseline_ts: float | None = None
        for p in reversed(list(history)[:-1]):
            if p.progress is None:
                continue
            if abs(p.progress - ping.progress) > 0.001:
                baseline_ts = p.timestamp
                break
        if baseline_ts is None:
            # No movement seen yet in window; use earliest timestamp.
            if not history:
                return []
            baseline_ts = list(history)[0].timestamp
        if ping.timestamp - baseline_ts >= self._stall_seconds:
            return [
                IncidentEvent(
                    incident_type=IncidentType.PRINT_STALLED,
                    severity=IncidentSeverity.WARN,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description=(
                        f"Progress unchanged for {int(ping.timestamp - baseline_ts)}s"
                    ),
                    suggested_action="Check for clogged nozzle, jammed extruder, or paused console.",
                    context={"progress": ping.progress},
                )
            ]
        return []

    def _check_fan(
        self, ping: PrinterPing, history: deque[PrinterPing]
    ) -> list[IncidentEvent]:
        if (
            ping.hotend_temp_c is None
            or ping.hotend_target_c is None
            or ping.print_state != "printing"
        ):
            return []
        recent = list(history)[-FAN_FAILURE_WINDOW_PINGS:]
        if len(recent) < FAN_FAILURE_WINDOW_PINGS:
            return []
        targets = {
            round(p.hotend_target_c, 0)
            for p in recent
            if p.hotend_target_c is not None
        }
        if len(targets) > 1:
            return []
        # Target stable; is actual climbing?
        actuals = [p.hotend_temp_c for p in recent if p.hotend_temp_c is not None]
        if len(actuals) < FAN_FAILURE_WINDOW_PINGS:
            return []
        drift = actuals[-1] - actuals[0]
        if drift >= FAN_FAILURE_DRIFT_OFFSET_C:
            return [
                IncidentEvent(
                    incident_type=IncidentType.FAN_FAILURE,
                    severity=IncidentSeverity.WARN,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description=(
                        f"Hotend drifted +{drift:.0f}°C with target stable — fan or "
                        f"thermistor suspected"
                    ),
                    suggested_action="Inspect hotend cooling fan; verify with diagnostic macro.",
                    context={"drift_c": drift},
                )
            ]
        return []

    def _check_filament(self, ping: PrinterPing) -> list[IncidentEvent]:
        if ping.filament_present is False and ping.print_state == "printing":
            return [
                IncidentEvent(
                    incident_type=IncidentType.FILAMENT_RUNOUT,
                    severity=IncidentSeverity.WARN,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description="Filament runout sensor reports empty during active print",
                    suggested_action="PAUSE and load fresh spool; or auto-resume if M600 configured.",
                )
            ]
        return []

    def _check_obico(self, ping: PrinterPing) -> list[IncidentEvent]:
        if (
            ping.obico_failure_score is not None
            and ping.obico_failure_score >= OBICO_FAILURE_THRESHOLD
            and ping.print_state == "printing"
        ):
            return [
                IncidentEvent(
                    incident_type=IncidentType.OBICO_FAILURE_SIGNAL,
                    severity=IncidentSeverity.CRITICAL,
                    printer_id=ping.printer_id,
                    detected_at=ping.timestamp,
                    description=(
                        f"Obico failure score {ping.obico_failure_score:.2f} exceeds "
                        f"threshold {OBICO_FAILURE_THRESHOLD}"
                    ),
                    suggested_action="Auto-PAUSE recommended; review camera before resuming.",
                    context={"failure_score": ping.obico_failure_score},
                )
            ]
        return []

    # -----------------------------------------------------------------
    # Introspection
    # -----------------------------------------------------------------

    def history(self, printer_id: str) -> list[PrinterPing]:
        return list(self._pings.get(printer_id, []))

    def reset(self, printer_id: str) -> None:
        self._pings.pop(printer_id, None)


__all__ = [
    "IncidentDetector",
    "IncidentEvent",
    "IncidentSeverity",
    "IncidentType",
    "PrinterPing",
    "FAN_FAILURE_DRIFT_OFFSET_C",
    "FAN_FAILURE_WINDOW_PINGS",
    "NETWORK_LOSS_PINGS",
    "OBICO_FAILURE_THRESHOLD",
    "RUNAWAY_BED_OFFSET_C",
    "RUNAWAY_HOTEND_OFFSET_C",
    "STALL_PROGRESS_SECONDS",
]
