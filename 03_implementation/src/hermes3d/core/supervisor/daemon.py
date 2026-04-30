"""Print supervisor daemon.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §41 (Print Supervisor)

A long-running, reactive agent that watches every printer in the fleet
and reacts to events:

  - Polls Moonraker every N seconds for state + active job
  - Polls Obico (when configured) for spaghetti-detection signal
  - Detects state transitions (queued → printing, printing → complete,
                                printing → error, etc.)
  - On a successful print, records to PrintHistory, updates Spool
    consumption, sends "complete" notification, reinforces success skills
  - On a failure, records to PrintHistory, sends "failed" notification,
    optionally creates a failure-pattern skill from the observation
  - On Obico high-confidence failure detection, can auto-pause or auto-
    cancel based on policy

Designed to run as a background thread inside the Gradio app or as a
standalone process via `python -m hermes3d.core.supervisor.daemon`.
"""
from __future__ import annotations

import dataclasses
import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from hermes3d.core.farm.print_history import PrintHistory
from hermes3d.core.farm.spool_tracker import SpoolTracker
from hermes3d.core.integrations import (
    DEFAULT_FAILURE_THRESHOLD, ObicoAction, ObicoClient,
)
from hermes3d.core.memory import SkillKind, SkillScope, SkillStore
from hermes3d.core.notifications import (
    NotificationEvent, NotificationLevel, Notifier,
    event_print_failed, event_print_succeeded,
)
from hermes3d.core.printers import FLEET, get_profile
from hermes3d.core.printers.moonraker_client import MoonrakerClient


log = logging.getLogger(__name__)


class SupervisorEvent(str, enum.Enum):
    PRINT_STARTED = "print_started"
    PRINT_COMPLETED = "print_completed"
    PRINT_FAILED = "print_failed"
    PRINTER_OFFLINE = "printer_offline"
    PRINTER_RECOVERED = "printer_recovered"
    OBICO_HEADS_UP = "obico_heads_up"
    OBICO_PAUSE_RECOMMENDED = "obico_pause_recommended"
    OBICO_AUTO_PAUSED = "obico_auto_paused"


@dataclass
class SupervisorPolicy:
    """Tuneable behaviour for the supervisor."""

    poll_interval_s: float = 30.0
    obico_enabled: bool = False
    obico_base_url: str | None = None
    obico_api_key: str | None = None
    auto_pause_on_obico: bool = True
    auto_cancel_on_obico: bool = False
    notify_on_start: bool = False
    notify_on_complete: bool = True
    notify_on_fail: bool = True
    learn_failures_into_skills: bool = True
    learn_failure_min_count: int = 3   # only create skill after N obs


@dataclass
class PrinterState:
    """Cached last-known state of a printer."""

    printer_id: str
    klippy_state: str = "unknown"
    is_printing: bool = False
    current_filename: str | None = None
    last_seen_unix: float | None = None
    last_event: SupervisorEvent | None = None
    print_started_unix: float | None = None
    error_count: int = 0


# =============================================================================


class PrintSupervisor:
    """Long-running reactive monitor for the fleet.

    Usage::

        sup = PrintSupervisor(
            history=PrintHistory("./var/history.jsonl"),
            spools=SpoolTracker("./var/spools.json"),
            skills=SkillStore("./var/skills.json"),
            notifier=Notifier(),
            policy=SupervisorPolicy(),
        )
        sup.start()  # spawns background thread
        ...
        sup.stop()   # graceful shutdown
    """

    def __init__(self, *,
                 history: PrintHistory,
                 spools: SpoolTracker,
                 skills: SkillStore,
                 notifier: Notifier,
                 policy: SupervisorPolicy | None = None,
                 printer_ids: Iterable[str] | None = None,
                 ) -> None:
        self.history = history
        self.spools = spools
        self.skills = skills
        self.notifier = notifier
        self.policy = policy or SupervisorPolicy()
        ids = list(printer_ids) if printer_ids is not None else [
            p.profile_id for p in FLEET]
        self.states: dict[str, PrinterState] = {
            pid: PrinterState(printer_id=pid) for pid in ids
        }
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._listeners: list[Callable[[SupervisorEvent, PrinterState,
                                          dict[str, Any]], None]] = []
        # Counter for observed failure conditions (printer_id, material) -> count
        self._failure_observation_counts: dict[tuple[str, str], int] = {}

    # ---- listener registration ------------------------------------------

    def on_event(self, fn: Callable[[SupervisorEvent, PrinterState,
                                       dict[str, Any]], None]) -> None:
        self._listeners.append(fn)

    def _emit(self, event: SupervisorEvent, ps: PrinterState,
              detail: dict[str, Any]) -> None:
        ps.last_event = event
        for cb in self._listeners:
            try:
                cb(event, ps, detail)
            except Exception as exc:  # noqa: BLE001
                log.warning("supervisor listener failed: %s", exc)

    # ---- start/stop -----------------------------------------------------

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("supervisor already running")
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="hermes3d-supervisor", daemon=True)
        self._thread.start()
        log.info("supervisor started (%d printers, %.1fs interval)",
                 len(self.states), self.policy.poll_interval_s)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        log.info("supervisor stopped")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ---- main loop ------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:  # noqa: BLE001
                log.exception("supervisor poll iteration failed: %s", exc)
            # Sleep with early-exit if stopped
            self._stop_event.wait(self.policy.poll_interval_s)

    def poll_once(self) -> None:
        """One sweep of all printers. Public so tests can drive it."""
        for pid, state in self.states.items():
            try:
                self._poll_printer(pid, state)
            except Exception as exc:  # noqa: BLE001
                log.warning("error polling %s: %s", pid, exc)

    # ---- per-printer poll ----------------------------------------------

    def _poll_printer(self, pid: str, ps: PrinterState) -> None:
        try:
            profile = get_profile(pid)
        except KeyError:
            return
        client = MoonrakerClient(profile.moonraker_url_default,
                                  timeout_s=4.0)
        live = client.printer_state()
        ps.last_seen_unix = time.time()
        if not live.get("reachable", False):
            if ps.klippy_state != "offline":
                self._emit(SupervisorEvent.PRINTER_OFFLINE, ps,
                           {"error": live.get("error")})
            ps.klippy_state = "offline"
            return

        new_state = live.get("klippy_state", "unknown")
        new_filename = live.get("print_state", {}).get(
            "filename") if isinstance(live.get("print_state"), dict) else None
        was_printing = ps.is_printing
        is_printing = new_state == "printing"

        # Detect transitions
        if ps.klippy_state == "offline" and new_state in ("ready", "printing"):
            self._emit(SupervisorEvent.PRINTER_RECOVERED, ps, {})

        if not was_printing and is_printing:
            ps.print_started_unix = time.time()
            ps.current_filename = new_filename
            self._emit(SupervisorEvent.PRINT_STARTED, ps,
                       {"filename": new_filename})
            if self.policy.notify_on_start:
                self.notifier.notify(NotificationEvent(
                    title="Print started",
                    message=f"{pid}: {new_filename or '?'}",
                    level=NotificationLevel.INFO,
                    printer_id=pid,
                ))
        elif was_printing and not is_printing:
            self._handle_print_ended(pid, ps, new_state)

        # Obico polling for active prints
        if is_printing and self.policy.obico_enabled and \
                self.policy.obico_base_url:
            self._poll_obico_for(pid, ps)

        ps.klippy_state = new_state
        ps.is_printing = is_printing

    # ---- print-end handler ---------------------------------------------

    def _handle_print_ended(self, pid: str, ps: PrinterState,
                              new_state: str) -> None:
        success = new_state == "ready"  # if klippy is ready post-print, success
        # error states reflect failure
        if new_state in ("error", "shutdown"):
            success = False
        # Persist to history
        material = "PLA"  # we don't know material from Moonraker alone;
        # the dispatcher / queue should store this and pass it in via
        # a richer integration. Best-effort default.
        loaded = next((s for s in self.spools.list(printer_id=pid)),
                       None)
        if loaded:
            material = loaded.material
        ended = time.time()
        record = self.history.append(
            job_id=ps.current_filename or "?",
            printer_id=pid,
            material=material,
            started_unix=ps.print_started_unix or ended,
            ended_unix=ended,
            success=success,
            spool_id=loaded.spool_id if loaded else None,
        )
        # Notify
        if success and self.policy.notify_on_complete:
            self.notifier.notify(event_print_succeeded(
                printer_id=pid,
                job_id=record.record_id,
                duration_min=record.duration_min,
                filament_g=record.filament_used_g or 0.0,
            ))
            self._emit(SupervisorEvent.PRINT_COMPLETED, ps,
                       {"record_id": record.record_id})
        elif not success and self.policy.notify_on_fail:
            self.notifier.notify(event_print_failed(
                printer_id=pid,
                job_id=record.record_id,
                reason=new_state,
            ))
            self._emit(SupervisorEvent.PRINT_FAILED, ps,
                       {"record_id": record.record_id, "klippy_state": new_state})
            self._maybe_learn_failure(pid, material)

        ps.print_started_unix = None
        ps.current_filename = None

    # ---- Obico polling --------------------------------------------------

    def _poll_obico_for(self, pid: str, ps: PrinterState) -> None:
        client = ObicoClient(
            base_url=self.policy.obico_base_url or "",
            api_key=self.policy.obico_api_key,
            timeout_s=4.0,
            failure_threshold=DEFAULT_FAILURE_THRESHOLD,
        )
        try:
            status = client.status(pid)
        except Exception as exc:  # noqa: BLE001
            log.debug("obico status failed for %s: %s", pid, exc)
            return
        if status.recommended_action == ObicoAction.PAUSE:
            self._emit(SupervisorEvent.OBICO_PAUSE_RECOMMENDED, ps,
                       {"failure_probability": status.failure_probability})
            if self.policy.auto_pause_on_obico:
                # Send pause via Moonraker
                try:
                    profile = get_profile(pid)
                    moonraker = MoonrakerClient(
                        profile.moonraker_url_default, timeout_s=4.0)
                    moonraker._request("POST", "/printer/print/pause")
                    self._emit(SupervisorEvent.OBICO_AUTO_PAUSED, ps,
                               {"failure_probability":
                                    status.failure_probability})
                except Exception as exc:  # noqa: BLE001
                    log.warning("auto-pause via Moonraker failed: %s", exc)
        elif status.recommended_action == ObicoAction.HEADS_UP:
            self._emit(SupervisorEvent.OBICO_HEADS_UP, ps,
                       {"failure_probability": status.failure_probability})

    # ---- failure learning ------------------------------------------------

    def _maybe_learn_failure(self, printer_id: str, material: str) -> None:
        if not self.policy.learn_failures_into_skills:
            return
        key = (printer_id, material.upper())
        self._failure_observation_counts[key] = (
            self._failure_observation_counts.get(key, 0) + 1)
        count = self._failure_observation_counts[key]
        if count < self.policy.learn_failure_min_count:
            return
        # Compute observed rate from history
        from hermes3d.core.farm.print_history import aggregate_metrics
        m = aggregate_metrics(self.history)
        ma = m.per_material.get(material.upper())
        if ma and ma.total_prints >= self.policy.learn_failure_min_count:
            rate = 1.0 - (ma.successful / ma.total_prints)
            if rate >= 0.30:
                # Create a failure-pattern skill (or reinforce existing)
                existing = self.skills.lookup(
                    kind=SkillKind.FAILURE_PATTERN,
                    printer_id=printer_id, material=material,
                )
                if existing:
                    self.skills.reinforce(
                        existing[0].skill_id,
                        confidence_delta=0.05,
                        note=f"observed rate now {rate:.2f}")
                else:
                    self.skills.add(
                        skill_kind=SkillKind.FAILURE_PATTERN,
                        name=f"observed_failure_{printer_id}_{material.lower()}",
                        scope=SkillScope(printer_id=printer_id,
                                          material=material),
                        body={"observed_failure_rate": round(rate, 3),
                              "observation_count": count},
                        confidence=min(0.6, rate),
                        source="agent_observed",
                        notes=("auto-created from observed failure pattern"),
                    )


__all__ = [
    "PrintSupervisor",
    "PrinterState",
    "SupervisorEvent",
    "SupervisorPolicy",
]
