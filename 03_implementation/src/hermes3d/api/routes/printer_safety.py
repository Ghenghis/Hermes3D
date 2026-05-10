"""Printer safety E2E gate routes (W6-9).

These routes are a *separate, additive* default-deny layer that any future
camera-driven start/heat workflow MUST go through.  They are intentionally
lightweight (no Moonraker calls, no Klipper dependency) so the gate can
refuse heat/start before any printer-specific code runs.

See :mod:`hermes3d.services.printer_safety_gate` for the threat model and
the three explicit gates this module enforces.

Routes
------

- ``POST /api/printers/{id}/start-print``         — gated start
- ``POST /api/printers/{id}/heat-extruder``       — gated extruder heat
- ``POST /api/printers/{id}/heat-bed``            — gated bed heat
- ``GET  /api/printers/{id}/safety-state``        — JSON status for the GUI

Two ingestion routes live alongside so the future camera and vision
classifier can push proof events without grabbing a service handle:

- ``POST /api/printers/{id}/safety-events/camera-frame``
- ``POST /api/printers/{id}/safety-events/plate-classification``

All four "command" routes are 403 by default until the gate has seen a
recent camera frame AND a recent ``plate=clear`` classification.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hermes3d.services.printer_safety_gate import (
    PlateClassification,
    PrinterSafetyGate,
    get_default_gate,
)

router = APIRouter()


def _gate() -> PrinterSafetyGate:
    """Indirection so tests can swap the gate via dependency_overrides."""
    return get_default_gate()


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #


class CameraFrameEvent(BaseModel):
    camera_id: str = Field(..., min_length=1)
    ts_unix: float


class PlateClassificationEvent(BaseModel):
    camera_id: str = Field(..., min_length=1)
    classification: PlateClassification
    confidence: float = Field(..., ge=0.0, le=1.0)
    ts_unix: float


class BindCameraRequest(BaseModel):
    camera_id: str = Field(..., min_length=1)


# --------------------------------------------------------------------------- #
# Gated commands — every one of these must pass is_safe_to_start()
# --------------------------------------------------------------------------- #


async def _enforce_safe_to_start(printer_id: str) -> None:
    allow, reasons = await _gate().is_safe_to_start(printer_id)
    if not allow:
        raise HTTPException(
            status_code=403,
            detail={
                "ok": False,
                "printer_id": printer_id,
                "blocked_by": reasons,
                "reason": "Printer safety gate refused: camera-only and plate-clear gates must both pass before heat or start.",
            },
        )


@router.post("/api/printers/{printer_id}/start-print")
async def start_print(printer_id: str) -> dict[str, Any]:
    await _enforce_safe_to_start(printer_id)
    return {"ok": True, "printer_id": printer_id, "action": "start-print", "gated": True}


@router.post("/api/printers/{printer_id}/heat-extruder")
async def heat_extruder(printer_id: str) -> dict[str, Any]:
    await _enforce_safe_to_start(printer_id)
    return {"ok": True, "printer_id": printer_id, "action": "heat-extruder", "gated": True}


@router.post("/api/printers/{printer_id}/heat-bed")
async def heat_bed(printer_id: str) -> dict[str, Any]:
    await _enforce_safe_to_start(printer_id)
    return {"ok": True, "printer_id": printer_id, "action": "heat-bed", "gated": True}


# --------------------------------------------------------------------------- #
# Read-only safety state — for the operator dashboard
# --------------------------------------------------------------------------- #


@router.get("/api/printers/{printer_id}/safety-state")
async def safety_state(printer_id: str) -> dict[str, Any]:
    return await _gate().safety_state(printer_id)


# --------------------------------------------------------------------------- #
# Ingestion — future camera feed and vision classifier post into these
# --------------------------------------------------------------------------- #


@router.post("/api/printers/{printer_id}/safety-events/camera-frame")
async def post_camera_frame(printer_id: str, event: CameraFrameEvent) -> dict[str, Any]:
    # Bind the printer to the camera_id on first frame so the gate
    # knows which printer benefits from this event.
    await _gate().bind_camera(printer_id, event.camera_id)
    await _gate().record_camera_frame(event.camera_id, event.ts_unix)
    state = await _gate().safety_state(printer_id)
    return {"ok": True, "printer_id": printer_id, "state": state}


@router.post("/api/printers/{printer_id}/safety-events/plate-classification")
async def post_plate_classification(
    printer_id: str, event: PlateClassificationEvent
) -> dict[str, Any]:
    await _gate().bind_camera(printer_id, event.camera_id)
    await _gate().record_plate_classification(
        event.camera_id, event.classification, event.confidence, event.ts_unix
    )
    state = await _gate().safety_state(printer_id)
    return {"ok": True, "printer_id": printer_id, "state": state}


@router.post("/api/printers/{printer_id}/safety-events/bind-camera")
async def post_bind_camera(printer_id: str, body: BindCameraRequest) -> dict[str, Any]:
    await _gate().bind_camera(printer_id, body.camera_id)
    return {"ok": True, "printer_id": printer_id, "camera_id": body.camera_id}


__all__ = ["router"]
