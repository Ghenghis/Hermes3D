from __future__ import annotations

import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from hermes3d.api.routes._common import execute, new_id, row, rows
from hermes3d.api.safety import is_s1_target
from hermes3d.db.init import DB_PATH
from hermes3d.services.local_state import local_printer, local_printers
from hermes3d.services.local_state import (
    build_plate_clearance_rows,
    camera_view_settings,
    mark_build_plate_clear,
    set_camera_view_settings,
)

router = APIRouter()


class AnomalyCreate(BaseModel):
    confidence: int
    description: str
    snapshot_id: str | None = None


class PlateClearanceUpdate(BaseModel):
    actor: str = "hermes-agent"
    reason: str | None = None


class CameraViewUpdate(BaseModel):
    rotate_deg: int | None = None
    mirror_x: bool | None = None
    mirror_y: bool | None = None
    zoom: float | None = None
    focus_x: float | None = None
    focus_y: float | None = None
    brightness: float | None = None
    contrast: float | None = None
    saturation: float | None = None
    fit: str | None = None
    feed_mode: str | None = None
    card_size: str | None = None
    review_overlay: str | None = None


@router.get("/api/observe/cameras")
def cameras() -> list[dict]:
    printers = local_printers(live=False)
    plates = {plate["printer_id"]: plate for plate in build_plate_clearance_rows(printers)}
    return [
        {
            "printer_id": printer["id"],
            "printer_name": printer["name"],
            "camera_url": printer["camera_url"],
            "health": _configured_camera_state(printer),
            "is_locked": _camera_is_locked(printer),
            "printer_locked": is_s1_target(printer["id"]),
            "camera_kind": _camera_kind(printer),
            "camera_note": _camera_note(printer),
            "stream_url": f"/api/observe/cameras/{printer['id']}/stream",
            "snapshot_url": f"/api/observe/cameras/{printer['id']}/snapshot",
            "view_settings": camera_view_settings(str(printer["id"])),
            "plate_clearance": plates.get(str(printer["id"])),
        }
        for printer in printers
    ]


@router.get("/api/observe/build-plate-clearance")
def build_plate_clearance() -> list[dict]:
    return build_plate_clearance_rows()


@router.post("/api/observe/build-plate-clearance/{printer_id}/clear")
def clear_build_plate(printer_id: str, body: PlateClearanceUpdate) -> dict:
    updated = mark_build_plate_clear(printer_id, body.actor, body.reason)
    if not updated:
        raise HTTPException(status_code=404, detail="printer not found")
    return updated


@router.put("/api/observe/cameras/{printer_id}/view")
def update_camera_view(printer_id: str, body: CameraViewUpdate) -> dict:
    payload = body.model_dump(exclude_none=True) if hasattr(body, "model_dump") else body.dict(exclude_none=True)
    updated = set_camera_view_settings(printer_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="printer not found")
    return updated


@router.get("/api/observe/cameras/{printer_id}/stream")
def stream(printer_id: str) -> RedirectResponse:
    printer = local_printer(printer_id, live=False)
    if not printer:
        raise HTTPException(status_code=404, detail="camera not found")
    camera_url = printer.get("camera_url")
    if not camera_url:
        raise HTTPException(status_code=404, detail=_camera_note(printer))
    return RedirectResponse(str(camera_url), status_code=307)


@router.get("/api/observe/cameras/{printer_id}/snapshot")
def snapshot(printer_id: str) -> RedirectResponse:
    printer = local_printer(printer_id, live=False)
    if not printer:
        raise HTTPException(status_code=404, detail="camera not found")
    camera_url = printer.get("camera_url")
    if not camera_url:
        raise HTTPException(status_code=404, detail=_camera_note(printer))
    return RedirectResponse(_snapshot_url(str(camera_url)), status_code=307)


@router.post("/api/observe/cameras/{printer_id}/capture-evidence")
def capture_evidence(printer_id: str) -> dict:
    printer = local_printer(printer_id, live=False)
    if not printer:
        raise HTTPException(status_code=404, detail="camera not found")
    camera_url = printer.get("camera_url")
    if not camera_url:
        raise HTTPException(status_code=409, detail=_camera_note(printer))
    artifact_id = new_id()
    artifact_dir = DB_PATH.parent / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = artifact_dir / f"{artifact_id}.jpg"
    try:
        request = urllib.request.Request(_snapshot_url(str(camera_url)), headers={"Accept": "image/*"})
        with urllib.request.urlopen(request, timeout=5.0) as response, snapshot_path.open("wb") as handle:
            handle.write(response.read())
    except (urllib.error.URLError, OSError) as exc:
        raise HTTPException(status_code=502, detail=f"camera snapshot capture failed: {type(exc).__name__}") from exc
    execute(
        """
        INSERT INTO artifacts
            (id, evidence_type, stage, label, file_path, file_size, notes)
        VALUES (?, 'photo', 'PRINT_RUN', ?, ?, ?, ?)
        """,
        (
            artifact_id,
            f"Camera capture {printer['name']}",
            str(snapshot_path),
            snapshot_path.stat().st_size,
            f"Captured from real camera endpoint for {printer['id']}",
        ),
    )
    return row("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)) or {"artifact_id": artifact_id, "snapshot_path": str(snapshot_path)}


@router.get("/api/observe/cameras/{printer_id}/health")
def camera_health(printer_id: str) -> dict:
    camera = next((c for c in cameras() if c["printer_id"] == (local_printer(printer_id) or {}).get("id", printer_id)), None)
    if not camera:
        raise HTTPException(status_code=404, detail="camera not found")
    health, http_status = _probe_camera(camera["camera_url"])
    return {
        "printer_id": camera["printer_id"],
        "health": health,
        "http_status": http_status,
        "is_locked": camera["printer_locked"],
        "printer_locked": camera["printer_locked"],
    }


@router.post("/api/observe/anomaly/{printer_id}", status_code=201)
def create_anomaly(printer_id: str, body: AnomalyCreate) -> dict:
    anomaly_id = new_id()
    execute(
        """
        INSERT INTO anomaly_reports
            (id, printer_id, confidence, description, snapshot_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (anomaly_id, printer_id, body.confidence, body.description, body.snapshot_id),
    )
    return row("SELECT * FROM anomaly_reports WHERE id = ?", (anomaly_id,)) or {}


@router.get("/api/observe/anomalies")
def anomalies(status: str | None = None) -> list[dict]:
    return rows(
        "SELECT * FROM anomaly_reports WHERE (? IS NULL OR status = ?) ORDER BY created_at DESC",
        (status, status),
    )


@router.patch("/api/observe/anomaly/{anomaly_id}/dismiss")
def dismiss_anomaly(anomaly_id: str) -> dict:
    execute("UPDATE anomaly_reports SET status = 'dismissed' WHERE id = ?", (anomaly_id,))
    anomaly = row("SELECT * FROM anomaly_reports WHERE id = ?", (anomaly_id,))
    if not anomaly:
        raise HTTPException(status_code=404, detail="anomaly not found")
    return anomaly


def _configured_camera_state(printer: dict) -> str:
    return "configured" if printer.get("camera_url") else "not_configured"


def _camera_is_locked(printer: dict) -> bool:
    return is_s1_target(printer["id"]) and not printer.get("camera_url")


def _camera_kind(printer: dict) -> str:
    printer_id = str(printer.get("id") or "")
    if printer_id in {"flsun_t1_a", "flsun_t1_b"}:
        return "integrated"
    if printer_id == "flsun_v400":
        return "usb_webcam"
    if printer_id == "flsun_s1":
        return "integrated"
    return "external"


def _camera_note(printer: dict) -> str:
    printer_id = str(printer.get("id") or "")
    if printer_id == "flsun_s1":
        return "S1 is locked for movement, upload, and print tests; the read-only camera feed is allowed."
    if printer_id == "flsun_v400" and not printer.get("camera_url"):
        return "V400 uses a USB webcam; configure printer.flsun_v400.camera_url before Observe can show a feed."
    if not printer.get("camera_url"):
        return "Camera URL is not configured for this printer."
    return "Camera feed configured."


def _snapshot_url(camera_url: str) -> str:
    if "action=stream" in camera_url:
        return camera_url.replace("action=stream", "action=snapshot")
    separator = "&" if "?" in camera_url else "?"
    return f"{camera_url}{separator}action=snapshot"


def _probe_camera(camera_url: str | None) -> tuple[str, int | None]:
    if not camera_url:
        return "not_configured", None
    try:
        request = urllib.request.Request(camera_url, headers={"Accept": "image/*,*/*"})
        with urllib.request.urlopen(request, timeout=1.5) as response:
            status = int(response.status)
            return ("reachable" if 200 <= status < 400 else "unreachable", status)
    except urllib.error.HTTPError as exc:
        return "unreachable", int(exc.code)
    except OSError:
        return "unreachable", None
