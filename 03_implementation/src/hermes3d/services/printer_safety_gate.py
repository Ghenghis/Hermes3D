"""Printer safety gate (W6-9) — default-deny pre-flight for heat/start commands.

Threat model
------------
A commodity FDM printer with a heated nozzle (~210 C) and bed (~60 C) becomes a
fire-ignition source if it heats up while:

  * the print plate is OBSTRUCTED by a previous print, debris, or a hand;
  * no operator can VISUALLY confirm the situation (camera dead);
  * remote callers can issue ``heat-extruder`` / ``start-print`` blindly.

This module is a **gate**, not a sensor: future camera and vision-classifier
subsystems call ``record_camera_frame`` and ``record_plate_classification``;
this gate decides whether ``is_safe_to_start`` may pass for a given printer.

Three explicit gates (per user W6-9 brief 2026-05-09)
-----------------------------------------------------
1. **Camera-only**     — a recent live frame must exist (freshness window
   ``CAMERA_FRAME_FRESHNESS_SEC``).  Without it, no operator can see the bed
   so we cannot consent to ignition.
2. **Plate clear**     — the most recent classification for the printer's
   camera must be ``"clear"`` with confidence
   >= ``PLATE_CLEAR_MIN_CONFIDENCE`` and no older than
   ``PLATE_CLEAR_FRESHNESS_SEC``.
3. **No heat/start**   — every ``heat-*`` / ``start-print`` route must call
   ``is_safe_to_start`` and refuse on any blocked reason.

Posture is **default-deny**: a freshly initialised gate refuses every
printer because it has never seen a frame or a classification.

Sources
-------
- NIST SP 800-82r3 (Guide to OT Security): default-deny + sensor-driven
  pre-conditions are the only way to bound failure of an ICS actuator.
  https://csrc.nist.gov/publications/detail/sp/800-82/rev-3/final
- OctoPrint safety best practices: never enable heating without operator
  visual confirmation.
  https://docs.octoprint.org/en/master/features/safety.html
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal

# --------------------------------------------------------------------------- #
# Tunable constants — kept module-level so tests/operators can override them
# without touching the gate's logic.
# --------------------------------------------------------------------------- #

CAMERA_FRAME_FRESHNESS_SEC: float = 5.0
"""Most-recent camera frame must be within this window to count as live."""

PLATE_CLEAR_FRESHNESS_SEC: float = 30.0
"""Most-recent plate classification must be within this window to count."""

PLATE_CLEAR_MIN_CONFIDENCE: float = 0.85
"""Minimum classifier confidence for a 'clear' verdict to pass the gate."""


PlateClassification = Literal["clear", "obstructed", "unknown"]


# --------------------------------------------------------------------------- #
# State records
# --------------------------------------------------------------------------- #


@dataclass
class CameraFrameRecord:
    """The latest camera frame seen for a camera_id."""

    camera_id: str
    ts_unix: float


@dataclass
class PlateClassificationRecord:
    """The latest plate-vision classification for a camera_id."""

    camera_id: str
    classification: PlateClassification
    confidence: float
    ts_unix: float


@dataclass
class PrinterGateState:
    """Per-printer view of the gate's belief about safety."""

    printer_id: str
    camera_id: str | None = None
    last_frame: CameraFrameRecord | None = None
    last_classification: PlateClassificationRecord | None = None
    history: list[dict[str, object]] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Gate
# --------------------------------------------------------------------------- #


class PrinterSafetyGate:
    """In-memory default-deny gate for printer heat/start commands.

    State is in-process and protected by an :class:`asyncio.Lock` so that
    concurrent ``is_safe_to_start`` calls never see a half-applied update.
    A future revision may persist state to the truth ledger; the public
    surface is intentionally narrow so that swap is purely additive.
    """

    def __init__(
        self,
        *,
        camera_freshness_sec: float = CAMERA_FRAME_FRESHNESS_SEC,
        plate_freshness_sec: float = PLATE_CLEAR_FRESHNESS_SEC,
        plate_min_confidence: float = PLATE_CLEAR_MIN_CONFIDENCE,
        clock: "callable[[], float] | None" = None,
    ) -> None:
        self._camera_freshness_sec = float(camera_freshness_sec)
        self._plate_freshness_sec = float(plate_freshness_sec)
        self._plate_min_confidence = float(plate_min_confidence)
        # injectable clock for deterministic tests
        self._clock = clock or time.time
        self._lock = asyncio.Lock()
        # printer_id -> state
        self._printers: dict[str, PrinterGateState] = {}
        # camera_id -> set(printer_id) — so a recorded frame/classification
        # can fan out to every printer bound to that camera
        self._camera_to_printers: dict[str, set[str]] = {}

    # ----- registration / binding -------------------------------------------------

    async def bind_camera(self, printer_id: str, camera_id: str) -> None:
        """Bind a printer to a camera_id.

        A printer with no bound camera is permanently blocked because the
        camera-only gate has no source of truth.
        """
        async with self._lock:
            state = self._printers.setdefault(
                printer_id, PrinterGateState(printer_id=printer_id)
            )
            state.camera_id = camera_id
            self._camera_to_printers.setdefault(camera_id, set()).add(printer_id)

    # ----- state ingestion --------------------------------------------------------

    async def record_camera_frame(self, camera_id: str, ts_unix: float) -> None:
        """Record a live camera frame.

        Idempotent: only the most-recent frame per camera_id matters.
        Older timestamps are ignored so that out-of-order ingestion cannot
        regress the freshness clock.
        """
        async with self._lock:
            for printer_id in self._camera_to_printers.get(camera_id, set()):
                state = self._printers.setdefault(
                    printer_id, PrinterGateState(printer_id=printer_id, camera_id=camera_id)
                )
                if state.last_frame is None or ts_unix >= state.last_frame.ts_unix:
                    state.last_frame = CameraFrameRecord(
                        camera_id=camera_id, ts_unix=ts_unix
                    )

    async def record_plate_classification(
        self,
        camera_id: str,
        classification: PlateClassification,
        confidence: float,
        ts_unix: float,
    ) -> None:
        """Record a vision-classifier verdict for a printer's bed.

        The classification is the latest decision per camera_id. As above,
        older-than-current timestamps are ignored.
        """
        if classification not in ("clear", "obstructed", "unknown"):
            raise ValueError(
                f"classification must be one of 'clear','obstructed','unknown'; got {classification!r}"
            )
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1]; got {confidence}")
        async with self._lock:
            for printer_id in self._camera_to_printers.get(camera_id, set()):
                state = self._printers.setdefault(
                    printer_id, PrinterGateState(printer_id=printer_id, camera_id=camera_id)
                )
                prev = state.last_classification
                if prev is None or ts_unix >= prev.ts_unix:
                    state.last_classification = PlateClassificationRecord(
                        camera_id=camera_id,
                        classification=classification,
                        confidence=float(confidence),
                        ts_unix=float(ts_unix),
                    )

    # ----- gate decision ----------------------------------------------------------

    async def is_safe_to_start(self, printer_id: str) -> tuple[bool, list[str]]:
        """Default-deny gate for heat/start commands.

        Returns ``(allow, reasons)``. ``allow`` is True only when EVERY
        gate passes; ``reasons`` enumerates the failures so the route can
        surface them to the operator.
        """
        async with self._lock:
            now = self._clock()
            state = self._printers.get(printer_id)
            reasons: list[str] = []

            if state is None or state.camera_id is None:
                reasons.append("no camera bound to printer")
            # camera freshness gate
            frame = state.last_frame if state else None
            if frame is None:
                reasons.append("no camera frame ever")
            elif (now - frame.ts_unix) > self._camera_freshness_sec:
                reasons.append(
                    f"camera stale: last frame {now - frame.ts_unix:.1f}s ago "
                    f"(freshness window {self._camera_freshness_sec:.1f}s)"
                )
            # plate-clear gate
            cls = state.last_classification if state else None
            if cls is None:
                reasons.append("no plate classification ever")
            else:
                age = now - cls.ts_unix
                if age > self._plate_freshness_sec:
                    reasons.append(
                        f"plate classification stale: {age:.1f}s ago "
                        f"(freshness window {self._plate_freshness_sec:.1f}s)"
                    )
                elif cls.classification == "obstructed":
                    reasons.append(
                        f"plate not clear: classifier says 'obstructed' (confidence {cls.confidence:.2f})"
                    )
                elif cls.classification == "unknown":
                    reasons.append(
                        f"plate not clear: classifier says 'unknown' (confidence {cls.confidence:.2f})"
                    )
                elif cls.confidence < self._plate_min_confidence:
                    reasons.append(
                        f"plate-clear confidence too low: {cls.confidence:.2f} "
                        f"(min {self._plate_min_confidence:.2f})"
                    )

            allow = not reasons
            return allow, reasons

    # ----- introspection ----------------------------------------------------------

    async def safety_state(self, printer_id: str) -> dict[str, object]:
        """Return a JSON-serialisable snapshot of the gate state.

        Used by ``GET /api/printers/{id}/safety-state`` so the GUI can
        render *why* a printer is currently blocked.
        """
        async with self._lock:
            now = self._clock()
            state = self._printers.get(printer_id)
            frame = state.last_frame if state else None
            cls = state.last_classification if state else None
            camera_fresh = bool(
                frame and (now - frame.ts_unix) <= self._camera_freshness_sec
            )

        # release lock before recomputing allow (which re-acquires).
        allow, reasons = await self.is_safe_to_start(printer_id)
        return {
            "printer_id": printer_id,
            "camera_id": state.camera_id if state else None,
            "camera_fresh": camera_fresh,
            "camera_age_sec": (now - frame.ts_unix) if frame else None,
            "plate_classification": cls.classification if cls else None,
            "plate_confidence": cls.confidence if cls else 0.0,
            "plate_age_sec": (now - cls.ts_unix) if cls else None,
            "allow": allow,
            "blocked_by": reasons,
            "thresholds": {
                "camera_freshness_sec": self._camera_freshness_sec,
                "plate_freshness_sec": self._plate_freshness_sec,
                "plate_min_confidence": self._plate_min_confidence,
            },
        }


# --------------------------------------------------------------------------- #
# Process-wide singleton — routes import this; tests construct fresh gates.
# --------------------------------------------------------------------------- #

_default_gate: PrinterSafetyGate | None = None


def get_default_gate() -> PrinterSafetyGate:
    """Return the process-wide gate, creating it on first call."""
    global _default_gate
    if _default_gate is None:
        _default_gate = PrinterSafetyGate()
    return _default_gate


def reset_default_gate() -> None:
    """Reset the singleton — used by tests, never call from production."""
    global _default_gate
    _default_gate = None


__all__ = [
    "CAMERA_FRAME_FRESHNESS_SEC",
    "CameraFrameRecord",
    "PLATE_CLEAR_FRESHNESS_SEC",
    "PLATE_CLEAR_MIN_CONFIDENCE",
    "PlateClassification",
    "PlateClassificationRecord",
    "PrinterGateState",
    "PrinterSafetyGate",
    "get_default_gate",
    "reset_default_gate",
]
