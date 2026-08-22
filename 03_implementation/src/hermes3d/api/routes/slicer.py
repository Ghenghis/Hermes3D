"""Slicer HTTP route — W18-A12 wire-up.

Status: runnable
Verdict gate: GUI_SLICER_GREEN

Exposes:
    POST /api/slice            — start a slice job (background thread).
    GET  /api/slice/{job_id}   — poll job status + final artifact details.

STRICT operator freeze (2026-05-11):
    The slicer produces G-code as a FILE on disk. This route NEVER uploads,
    dispatches, or transmits that G-code to a printer (no Moonraker /
    Klipper / OctoPrint / /api/printers writes). The deliverable is the
    file path + sha256 + analyzer metadata returned by GET.

Storage layout:
    var/slicer/{job_id}/
        ├── {stl_basename}.gcode       (real slicer output)
        └── proof.json                 (proof envelope: argv, sha256, etc.)

Persistence:
    * A row in ``jobs`` with ``job_type='slice'`` and ``dry_run=1``
      (the slicer never touches a printer, so dry_run is the honest flag).
    * Step + event rows + a ``slice_completed`` / ``slice_failed`` proof
      event in ``proof_events``.
    * Two ``artifacts`` rows on success (gcode + proof.json), so the
      existing /api/artifacts surface picks the files up automatically.

Backgrounding:
    Slicing takes a few seconds for a 10 mm cube but can grow to minutes
    for a large desk-organizer mesh, so the POST handler returns
    ``202 Accepted`` immediately and the work runs in a Python thread.
    SQLite is the rendezvous point — GET reads job + step + artifact rows.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hermes3d.api.routes._common import as_json, execute, new_id, row, rows
from hermes3d.services.local_state import implementation_path
from hermes3d.services.source_tool_support import source_support_record, source_support_records
from hermes3d.services.window_capture import (
    capture_window_jpeg,
    capture_window_png,
    click_window,
    find_desktop_window,
    focus_window,
    list_matching_windows,
    press_window_key,
    wheel_window,
    windows_available,
)

LOG = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request body
# ---------------------------------------------------------------------------


class SliceRequest(BaseModel):
    """Body of POST /api/slice."""

    stl_path: str = Field(..., description="Absolute or repo-relative path to the input STL.")
    printer_profile: str | None = Field(
        default=None,
        description=(
            "Slicer .ini profile path or profile id. Optional — when omitted the "
            "slicer falls back to its bundled defaults."
        ),
    )
    options: dict[str, Any] = Field(default_factory=dict, description="Future-use options.")


class SlicerAppPathRequest(BaseModel):
    """Body of PUT /api/slicer/apps/{app_id}/path."""

    path: str = Field(..., description="Absolute path to a local slicer executable.")


class WindowClickRequest(BaseModel):
    x_ratio: float = Field(..., ge=0, le=1)
    y_ratio: float = Field(..., ge=0, le=1)
    button: str = "left"
    double: bool = False


class WindowWheelRequest(BaseModel):
    x_ratio: float = Field(..., ge=0, le=1)
    y_ratio: float = Field(..., ge=0, le=1)
    delta_y: float


class WindowKeyRequest(BaseModel):
    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False


SLICER_DESKTOP_APPS: dict[str, dict[str, Any]] = {
    "prusaslicer": {
        "label": "PrusaSlicer",
        "module_id": "prusaslicer",
        "kind": "desktop_slicer",
        "default_path": "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer.exe",
        "candidates": [
            "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer.exe",
            "C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe",
            "C:/Program Files (x86)/Prusa3D/PrusaSlicer/prusa-slicer.exe",
        ],
        "path_commands": ["prusa-slicer", "PrusaSlicer", "prusa-slicer-console"],
        "window_process_names": ["prusa-slicer", "PrusaSlicer"],
        "window_title_contains": ["PrusaSlicer"],
    },
    "flsun_slicer": {
        "label": "FLSUN Slicer",
        "module_id": "flsun_slicer",
        "kind": "desktop_slicer",
        "default_path": "C:/FlsunSlicer2.0/FlsunSlicer.exe",
        "candidates": [
            "C:/FlsunSlicer2.0/FlsunSlicer.exe",
            "C:/Program Files/FlsunSlicer/FlsunSlicer.exe",
        ],
        "path_commands": ["FlsunSlicer", "flsun-slicer", "flusn-slicer"],
        "window_process_names": ["FlsunSlicer"],
        "window_title_contains": ["FlsunSlicer"],
    },
    "orcaslicer": {
        "label": "OrcaSlicer",
        "module_id": "orcaslicer",
        "kind": "desktop_slicer",
        "default_path": "C:/Program Files/OrcaSlicer/orca-slicer.exe",
        "candidates": [
            "C:/Program Files/OrcaSlicer/orca-slicer.exe",
            "C:/Program Files/OrcaSlicer/OrcaSlicer.exe",
            "C:/Program Files (x86)/OrcaSlicer/orca-slicer.exe",
        ],
        "path_commands": ["orca-slicer", "OrcaSlicer", "orcaslicer"],
        "window_process_names": ["orca-slicer", "OrcaSlicer"],
        "window_title_contains": ["OrcaSlicer"],
    },
}


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def _slicer_root() -> Path:
    """Return ``<repo>/var/slicer`` and ensure it exists."""

    root = implementation_path("var", "slicer")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _job_dir(job_id: str) -> Path:
    out = _slicer_root() / job_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _resolve_stl(raw_path: str) -> Path:
    """Resolve the user-supplied path against common repo roots."""

    candidates: list[Path] = []
    raw = Path(raw_path)
    candidates.append(raw)
    if not raw.is_absolute():
        candidates.append(implementation_path(raw_path))
        candidates.append(implementation_path("..", raw_path))
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved
    raise HTTPException(
        status_code=404,
        detail={
            "status": "blocked",
            "reason": f"STL not found: {raw_path}",
            "searched": [str(c) for c in candidates],
        },
    )


def _record_proof_event(event_type: str, payload: dict[str, Any]) -> str:
    """Insert a row in ``proof_events`` and return the new event_id."""

    event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, 'slicer-executor', ?)",
        (event_id, event_type, as_json(payload)),
    )
    return event_id


def _slicer_app_or_404(app_id: str) -> dict[str, Any]:
    app = SLICER_DESKTOP_APPS.get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Unknown slicer app: {app_id}")
    return app


def _slicer_app_settings_key(app_id: str) -> str:
    return f"slicer.desktop_app.{app_id}.path"


def _setting_value(key: str) -> str | None:
    item = row("SELECT value FROM settings WHERE key = ?", (key,))
    value = str(item["value"]).strip() if item and item.get("value") else ""
    return value or None


def _save_setting(key: str, value: str) -> None:
    execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value),
    )


def _normalise_executable_path(raw_path: str) -> Path:
    stripped = raw_path.strip().strip("\"'")
    if not stripped:
        raise HTTPException(status_code=400, detail="Executable path is required.")
    path = Path(stripped)
    if not path.is_absolute():
        raise HTTPException(status_code=400, detail="Use an absolute executable path.")
    if path.suffix.lower() != ".exe":
        raise HTTPException(status_code=400, detail="Slicer app path must point to a .exe file.")
    try:
        resolved = path.resolve(strict=False)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid executable path: {exc}") from exc
    return resolved


def _slicer_app_candidates(app_id: str, app: dict[str, Any]) -> list[dict[str, Any]]:
    override = _setting_value(_slicer_app_settings_key(app_id))
    raw_candidates: list[tuple[str, str]] = []
    if override:
        raw_candidates.append(("user", override))
    raw_candidates.extend(("known", str(path)) for path in app.get("candidates") or [])
    for command in app.get("path_commands") or []:
        found = shutil.which(str(command))
        raw_candidates.append(("path", found or f"PATH:{command}"))

    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    for source, raw_path in raw_candidates:
        if raw_path in seen:
            continue
        seen.add(raw_path)
        if raw_path.startswith("PATH:"):
            records.append(
                {
                    "source": source,
                    "path": raw_path,
                    "exists": False,
                    "is_executable": False,
                }
            )
            continue
        path = Path(raw_path)
        exists = path.is_file()
        records.append(
            {
                "source": source,
                "path": str(path),
                "exists": exists,
                "is_executable": exists and path.suffix.lower() == ".exe",
            }
        )
    return records


def _slicer_app_record(app_id: str) -> dict[str, Any]:
    app = _slicer_app_or_404(app_id)
    candidates = _slicer_app_candidates(app_id, app)
    selected = next((item for item in candidates if item["is_executable"]), None)
    override = _setting_value(_slicer_app_settings_key(app_id))
    window = _slicer_app_window_record(app_id, app, str(selected["path"]) if selected else None)
    return {
        "id": app_id,
        "module_id": app["module_id"],
        "label": app["label"],
        "kind": app["kind"],
        "status": "ready" if selected else "missing",
        "detected": bool(selected),
        "path": selected["path"] if selected else override or app["default_path"],
        "path_source": selected["source"] if selected else "user" if override else "default",
        "user_path": override,
        "default_path": app["default_path"],
        "candidates": candidates,
        "launch_supported": bool(selected),
        "window": window,
        "window_available": bool(window.get("available")),
        "window_preview_url": f"/api/slicer/apps/{app_id}/window/screenshot.png",
        "window_stream_url": f"/api/slicer/apps/{app_id}/window/stream.mjpeg",
        "source_support": source_support_record(app_id),
        "proof_gate_version": "desktop-slicer-launcher-v1",
        "safety": "Launches the local slicer desktop program only. It does not upload, start, stop, home, heat, or otherwise command printer hardware.",
    }


def _slicer_app_window(app_id: str, app: dict[str, Any] | None = None, executable_path: str | None = None):
    app = app or _slicer_app_or_404(app_id)
    return find_desktop_window(
        process_names=app.get("window_process_names") or (),
        title_contains=app.get("window_title_contains") or (),
        executable_path=executable_path,
    )


def _slicer_app_window_record(app_id: str, app: dict[str, Any] | None = None, executable_path: str | None = None) -> dict[str, Any]:
    if not windows_available():
        return {
            "available": False,
            "status": "desktop_capture_unavailable",
            "reason": "Windows desktop capture libraries are unavailable in this runtime.",
        }
    window = _slicer_app_window(app_id, app, executable_path)
    matching_windows = list_matching_windows(
        process_names=app.get("window_process_names") or (),
        title_contains=app.get("window_title_contains") or (),
        executable_path=executable_path,
    )
    if not window:
        if matching_windows:
            best = matching_windows[0]
            return {
                "available": False,
                "status": "running_needs_focus",
                "reason": "The desktop slicer process has a window, but it is minimized or parked offscreen. Use Focus Window.",
                "hwnd": best.hwnd,
                "title": best.title,
                "process_id": best.process_id,
                "process_name": best.process_name,
                "process_path": best.process_path,
            }
        return {
            "available": False,
            "status": "not_running",
            "reason": "The desktop slicer window is not open.",
        }
    left, top, right, bottom = window.rect
    return {
        "available": True,
        "status": "running",
        "hwnd": window.hwnd,
        "title": window.title,
        "process_id": window.process_id,
        "process_name": window.process_name,
        "process_path": window.process_path,
        "rect": {"left": left, "top": top, "right": right, "bottom": bottom},
        "preview_url": f"/api/slicer/apps/{app_id}/window/screenshot.png",
        "stream_url": f"/api/slicer/apps/{app_id}/window/stream.mjpeg",
    }


@router.get("/api/slicer/apps")
def list_slicer_apps() -> dict[str, Any]:
    """Return detected local desktop slicer applications.

    This is an app-launch surface, not a CLI proof surface. It reports the
    executable that a user can open manually from the dashboard and keeps
    printer hardware completely untouched.
    """

    app_ids = ["flsun_slicer", "prusaslicer", "orcaslicer"]
    return {
        "status": "ready",
        "count": len(app_ids),
        "apps": [_slicer_app_record(app_id) for app_id in app_ids],
        "source_supported": source_support_records(app_ids),
    }


@router.get("/api/slicer/apps/{app_id}")
def get_slicer_app(app_id: str) -> dict[str, Any]:
    return _slicer_app_record(app_id)


@router.get("/api/slicer/apps/{app_id}/window")
def get_slicer_app_window(app_id: str) -> dict[str, Any]:
    app = _slicer_app_or_404(app_id)
    record = _slicer_app_record(app_id)
    return {
        "app_id": app_id,
        "label": app["label"],
        "window": _slicer_app_window_record(app_id, app, str(record.get("path") or "")),
    }


@router.get("/api/slicer/apps/{app_id}/window/screenshot.png")
def get_slicer_app_window_screenshot(app_id: str) -> Response:
    app = _slicer_app_or_404(app_id)
    record = _slicer_app_record(app_id)
    window = _slicer_app_window(app_id, app, str(record.get("path") or ""))
    if not window:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "not_running",
                "reason": f"{app['label']} is not open, so no desktop GUI screenshot can be captured.",
            },
        )
    try:
        png = capture_window_png(window)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "desktop_capture_unavailable",
                "reason": str(exc),
            },
        ) from exc
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.get("/api/slicer/apps/{app_id}/window/stream.mjpeg")
def stream_slicer_app_window(app_id: str, fps: float = 8.0) -> StreamingResponse:
    app = _slicer_app_or_404(app_id)
    record = _slicer_app_record(app_id)
    executable_path = str(record.get("path") or "")
    if not _slicer_app_window(app_id, app, executable_path):
        raise HTTPException(
            status_code=404,
            detail={
                "status": "not_running",
                "reason": f"{app['label']} is not open, so no live desktop GUI stream can be captured.",
            },
        )
    return StreamingResponse(
        _slicer_mjpeg_frames(app_id, app, executable_path, fps=fps),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/slicer/apps/{app_id}/window/focus")
def focus_slicer_app_window(app_id: str) -> dict[str, Any]:
    app = _slicer_app_or_404(app_id)
    record = _slicer_app_record(app_id)
    window = _slicer_app_window(app_id, app, str(record.get("path") or ""))
    if not window:
        matching_windows = list_matching_windows(
            process_names=app.get("window_process_names") or (),
            title_contains=app.get("window_title_contains") or (),
            executable_path=str(record.get("path") or ""),
        )
        if not matching_windows:
            return {
                "accepted": False,
                "status": "not_running",
                "reason": f"{app['label']} is not open.",
            }
        window = matching_windows[0]
    try:
        focus_window(window)
    except Exception as exc:  # pragma: no cover - desktop focus can be OS-policy blocked
        return {
            "accepted": False,
            "status": "focus_blocked",
            "reason": str(exc),
            "window": _slicer_app_window_record(app_id, app, str(record.get("path") or "")),
        }
    return {
        "accepted": True,
        "status": "focused",
        "window": _slicer_app_window_record(app_id, app, str(record.get("path") or "")),
    }


@router.post("/api/slicer/apps/{app_id}/window/click")
def click_slicer_app_window(app_id: str, body: WindowClickRequest) -> dict[str, Any]:
    app = _slicer_app_or_404(app_id)
    record = _slicer_app_record(app_id)
    window = _slicer_app_window(app_id, app, str(record.get("path") or ""))
    if not window:
        return {"accepted": False, "status": "not_running", "reason": f"{app['label']} is not open."}
    try:
        click_window(
            window,
            x_ratio=body.x_ratio,
            y_ratio=body.y_ratio,
            button=body.button,
            double=body.double,
        )
    except Exception as exc:
        return {"accepted": False, "status": "input_blocked", "reason": str(exc)}
    return {
        "accepted": True,
        "status": "clicked",
        "window": _slicer_app_window_record(app_id, app, str(record.get("path") or "")),
        "safety": "Local desktop input only; no Hermes3D printer API call was made.",
    }


@router.post("/api/slicer/apps/{app_id}/window/wheel")
def wheel_slicer_app_window(app_id: str, body: WindowWheelRequest) -> dict[str, Any]:
    app = _slicer_app_or_404(app_id)
    record = _slicer_app_record(app_id)
    window = _slicer_app_window(app_id, app, str(record.get("path") or ""))
    if not window:
        return {"accepted": False, "status": "not_running", "reason": f"{app['label']} is not open."}
    try:
        wheel_window(window, x_ratio=body.x_ratio, y_ratio=body.y_ratio, delta_y=body.delta_y)
    except Exception as exc:
        return {"accepted": False, "status": "input_blocked", "reason": str(exc)}
    return {
        "accepted": True,
        "status": "wheeled",
        "window": _slicer_app_window_record(app_id, app, str(record.get("path") or "")),
        "safety": "Local desktop input only; no Hermes3D printer API call was made.",
    }


@router.post("/api/slicer/apps/{app_id}/window/key")
def key_slicer_app_window(app_id: str, body: WindowKeyRequest) -> dict[str, Any]:
    app = _slicer_app_or_404(app_id)
    record = _slicer_app_record(app_id)
    window = _slicer_app_window(app_id, app, str(record.get("path") or ""))
    if not window:
        return {"accepted": False, "status": "not_running", "reason": f"{app['label']} is not open."}
    try:
        press_window_key(window, key=body.key, ctrl=body.ctrl, alt=body.alt, shift=body.shift)
    except Exception as exc:
        return {"accepted": False, "status": "input_blocked", "reason": str(exc)}
    return {
        "accepted": True,
        "status": "key_sent",
        "window": _slicer_app_window_record(app_id, app, str(record.get("path") or "")),
        "safety": "Local desktop input only; no Hermes3D printer API call was made.",
    }


def _slicer_mjpeg_frames(
    app_id: str,
    app: dict[str, Any],
    executable_path: str,
    *,
    fps: float,
) -> Iterator[bytes]:
    interval = 1.0 / max(1.0, min(12.0, float(fps or 8.0)))
    while True:
        started = time.monotonic()
        window = _slicer_app_window(app_id, app, executable_path)
        if window:
            try:
                frame = capture_window_jpeg(window, quality=72, max_width=1600)
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                    + frame
                    + b"\r\n"
                )
            except Exception:
                # Window capture can fail while the native app is resizing or
                # switching GPU surfaces; retry on the next frame.
                pass
        elapsed = time.monotonic() - started
        time.sleep(max(0.01, interval - elapsed))


@router.put("/api/slicer/apps/{app_id}/path")
def set_slicer_app_path(app_id: str, body: SlicerAppPathRequest) -> dict[str, Any]:
    _slicer_app_or_404(app_id)
    path = _normalise_executable_path(body.path)
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail={
                "status": "blocked",
                "reason": f"Executable not found: {path}",
                "path": str(path),
            },
        )
    _save_setting(_slicer_app_settings_key(app_id), str(path))
    record = _slicer_app_record(app_id)
    proof_event_id = _record_proof_event(
        "slicer_app_path_saved",
        {
            "app_id": app_id,
            "label": record["label"],
            "path": str(path),
            "safety": record["safety"],
        },
    )
    return {
        "accepted": True,
        "status": "saved",
        "app": record,
        "proof_event_id": proof_event_id,
    }


@router.post("/api/slicer/apps/{app_id}/launch")
def launch_slicer_app(app_id: str) -> dict[str, Any]:
    record = _slicer_app_record(app_id)
    app = _slicer_app_or_404(app_id)
    existing_window = _slicer_app_window(app_id, app, str(record.get("path") or ""))
    if existing_window:
        try:
            focus_window(existing_window)
        except Exception:
            pass
        return {
            "accepted": True,
            "status": "focused_existing",
            "app": _slicer_app_record(app_id),
            "pid": existing_window.process_id,
        }
    if not record["detected"]:
        return {
            "accepted": False,
            "status": "missing",
            "app": record,
            "reason": f"{record['label']} executable was not found. Set a local .exe path first.",
        }
    path = Path(str(record["path"]))
    if not path.is_file():
        return {
            "accepted": False,
            "status": "missing",
            "app": record,
            "reason": f"{record['label']} executable no longer exists at {path}.",
        }
    try:
        proc = subprocess.Popen(  # noqa: S603 -- fixed local executable path, shell disabled.
            [str(path)],
            cwd=str(path.parent),
            shell=False,
        )
    except OSError as exc:
        return {
            "accepted": False,
            "status": "launch_failed",
            "app": record,
            "reason": f"Launch failed: {exc}",
        }
    proof_event_id = _record_proof_event(
        "slicer_app_launched",
        {
            "app_id": app_id,
            "label": record["label"],
            "path": str(path),
            "pid": proc.pid,
            "safety": record["safety"],
            "no_printer_hardware": True,
        },
    )
    return {
        "accepted": True,
        "status": "launched",
        "app": record,
        "pid": proc.pid,
        "proof_event_id": proof_event_id,
    }


def _write_proof_envelope(
    *,
    job_dir: Path,
    job_id: str,
    request_body: SliceRequest,
    slice_result_dict: dict[str, Any],
    analyzer_dict: dict[str, Any],
    gcode_sha256: str,
    gcode_size_bytes: int,
    proof_event_id: str,
) -> Path:
    """Write the slicer proof envelope JSON beside the G-code."""

    proof_path = job_dir / "proof.json"
    envelope = {
        "schema": "hermes3d.slicer.proof.v1",
        "job_id": job_id,
        "request": request_body.model_dump(),
        "slicer": slice_result_dict,
        "analyzer": analyzer_dict,
        "gcode": {
            "path": slice_result_dict.get("gcode_path"),
            "size_bytes": gcode_size_bytes,
            "sha256": gcode_sha256,
        },
        "proof_event_id": proof_event_id,
        "freeze_assertions": {
            "no_printer_writes": True,
            "no_moonraker_upload": True,
            "no_klipper_dispatch": True,
            "no_octoprint_upload": True,
        },
    }
    proof_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    return proof_path


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------


def _run_slice_job(job_id: str, body: SliceRequest, stl_path: Path) -> None:
    """Run slice_mesh in a thread; persist outcome rows."""

    job_dir = _job_dir(job_id)
    try:
        from hermes3d.core.slicer.gcode_analyzer import analyze_gcode
        from hermes3d.core.slicer.slicer_runner import (
            SlicerError,
            SlicerNotFound,
            slice_mesh,
        )

        try:
            result = slice_mesh(
                stl_path,
                profile=body.printer_profile,
                output_dir=job_dir,
                timeout_seconds=int(body.options.get("timeout_seconds", 600)),
            )
        except SlicerNotFound as exc:
            _finalize_failure(
                job_id=job_id,
                reason=f"slicer_not_found: {exc}",
                stage="slicer.binary_lookup",
            )
            return
        except SlicerError as exc:
            _finalize_failure(
                job_id=job_id,
                reason=f"slicer_error: {exc}",
                stage="slicer.exec",
            )
            return
        except Exception as exc:  # noqa: BLE001 — capture any unexpected failure
            _finalize_failure(
                job_id=job_id,
                reason=f"unexpected_error: {exc}",
                stage="slicer.exec",
            )
            return

        gcode_path = Path(result.gcode_path)
        if not gcode_path.is_file():
            _finalize_failure(
                job_id=job_id,
                reason=f"slicer reported success but gcode missing at {gcode_path}",
                stage="slicer.output_check",
            )
            return
        size_bytes = gcode_path.stat().st_size
        if size_bytes <= 0:
            _finalize_failure(
                job_id=job_id,
                reason=f"slicer wrote a zero-byte gcode at {gcode_path}",
                stage="slicer.output_check",
            )
            return

        gcode_sha = _file_sha256(gcode_path)
        try:
            analyzer = analyze_gcode(gcode_path)
            analyzer_dict = analyzer.to_dict()
        except Exception as exc:  # noqa: BLE001 — analyzer must not nuke a real slice
            LOG.warning("analyze_gcode failed for %s: %s", gcode_path, exc)
            analyzer_dict = {
                "error": f"analyzer_failed: {exc}",
                "layer_count": None,
                "motion_lines": 0,
            }

        result_dict = result.to_dict()
        proof_event_id = _record_proof_event(
            "slice_completed",
            {
                "job_id": job_id,
                "stl_path": str(stl_path),
                "gcode_path": str(gcode_path),
                "gcode_size_bytes": size_bytes,
                "gcode_sha256": gcode_sha,
                "layer_count": analyzer_dict.get("layer_count"),
                "motion_lines": analyzer_dict.get("motion_lines"),
                "estimated_print_time_min": analyzer_dict.get("estimated_print_time_min"),
                "slicer_binary": result_dict.get("slicer_binary"),
                "duration_seconds": result_dict.get("duration_seconds"),
            },
        )
        proof_path = _write_proof_envelope(
            job_dir=job_dir,
            job_id=job_id,
            request_body=body,
            slice_result_dict=result_dict,
            analyzer_dict=analyzer_dict,
            gcode_sha256=gcode_sha,
            gcode_size_bytes=size_bytes,
            proof_event_id=proof_event_id,
        )

        # Persist artifacts rows so /api/artifacts and the GUI artifact list
        # pick them up. We attach two artifacts: the gcode + the proof envelope.
        gcode_artifact_id = new_id()
        proof_artifact_id = new_id()
        gcode_notes = {
            "sha256": gcode_sha,
            "size_bytes": size_bytes,
            "layer_count": analyzer_dict.get("layer_count"),
            "motion_lines": analyzer_dict.get("motion_lines"),
            "estimated_print_time_min": analyzer_dict.get("estimated_print_time_min"),
            "estimated_filament_g": analyzer_dict.get("filament_used_g"),
            "proof_artifact_id": proof_artifact_id,
            "proof_event_id": proof_event_id,
            "slicer_binary": result_dict.get("slicer_binary"),
        }
        execute(
            """
            INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
            VALUES (?, ?, 'gcode', 'slicer-executor', 'SLICING', 'SLICER_OUTPUT', ?, ?, ?, ?)
            """,
            (
                gcode_artifact_id,
                job_id,
                gcode_path.name,
                str(gcode_path),
                size_bytes,
                as_json(gcode_notes),
            ),
        )
        execute(
            """
            INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
            VALUES (?, ?, 'proof_report', 'slicer-executor', 'SLICING', 'SLICER_OUTPUT', ?, ?, ?, ?)
            """,
            (
                proof_artifact_id,
                job_id,
                proof_path.name,
                str(proof_path),
                proof_path.stat().st_size,
                as_json(
                    {
                        "sha256": _file_sha256(proof_path),
                        "gcode_artifact_id": gcode_artifact_id,
                        "proof_event_id": proof_event_id,
                    }
                ),
            ),
        )

        execute(
            """
            INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, duration_s)
            VALUES (?, ?, 2, 'Slice STL via PrusaSlicer CLI', 'done', datetime('now'), datetime('now'), ?),
                   (?, ?, 3, 'Write signed slicer proof envelope', 'done', datetime('now'), datetime('now'), 0)
            """,
            (
                new_id(),
                job_id,
                float(result_dict.get("duration_seconds") or 0.0),
                new_id(),
                job_id,
            ),
        )
        execute(
            "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'slice_completed', 'slicer-executor', ?)",
            (
                new_id(),
                job_id,
                f"Sliced {gcode_path.name} ({size_bytes} bytes, sha256={gcode_sha[:16]}); proof_event_id={proof_event_id}",
            ),
        )
        execute(
            "UPDATE jobs SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
    except Exception as exc:  # noqa: BLE001 — final safety net
        LOG.exception("Slicer background thread crashed for job %s", job_id)
        _finalize_failure(
            job_id=job_id,
            reason=f"background_thread_crash: {exc}",
            stage="slicer.thread",
        )


def _finalize_failure(*, job_id: str, reason: str, stage: str) -> None:
    """Mark the job failed and emit a slice_failed proof event."""

    proof_event_id = _record_proof_event(
        "slice_failed",
        {"job_id": job_id, "reason": reason, "stage": stage},
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at, error)
        VALUES (?, ?, 2, 'Slice STL via PrusaSlicer CLI', 'failed', datetime('now'), datetime('now'), ?)
        """,
        (new_id(), job_id, reason[:1000]),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'slice_failed', 'slicer-executor', ?)",
        (new_id(), job_id, f"{stage}: {reason[:400]}; proof_event_id={proof_event_id}"),
    )
    execute(
        "UPDATE jobs SET status = 'failed', updated_at = datetime('now') WHERE id = ?",
        (job_id,),
    )


# ---------------------------------------------------------------------------
# HTTP handlers
# ---------------------------------------------------------------------------


@router.post("/api/slice", status_code=202)
def post_slice(body: SliceRequest) -> dict[str, Any]:
    """Start a slicer job. Returns 202 with the new job_id immediately.

    The actual ``slice_mesh()`` call runs on a daemon thread and writes its
    outcome rows + artifacts back into SQLite.
    """

    stl_path = _resolve_stl(body.stl_path)
    job_id = new_id()
    execute(
        """
        INSERT INTO jobs (id, name, job_type, status, printer_id, dry_run)
        VALUES (?, ?, 'slice', 'running', NULL, 1)
        """,
        (job_id, f"Slice {stl_path.name}"),
    )
    execute(
        """
        INSERT INTO job_steps (id, job_id, step_number, name, status, started_at, ended_at)
        VALUES (?, ?, 1, 'Slice request received', 'done', datetime('now'), datetime('now'))
        """,
        (new_id(), job_id),
    )
    execute(
        "INSERT INTO job_events (id, job_id, event_type, source_agent, message) VALUES (?, ?, 'slice_requested', 'slicer-executor', ?)",
        (
            new_id(),
            job_id,
            f"POST /api/slice for stl={stl_path}; profile={body.printer_profile or '(default)'}",
        ),
    )

    thread = threading.Thread(
        target=_run_slice_job,
        args=(job_id, body, stl_path),
        name=f"slice-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    return {
        "status": "accepted",
        "accepted": True,
        "job_id": job_id,
        "id": job_id,
        "stl_path": str(stl_path),
        "printer_profile": body.printer_profile,
        "freeze": {
            "no_printer_writes": True,
            "no_dispatch": True,
        },
    }


@router.get("/api/slice/{job_id}")
def get_slice(job_id: str) -> dict[str, Any]:
    """Return the job's current state plus G-code artifact details when terminal."""

    job = row("SELECT * FROM jobs WHERE id = ? AND job_type = 'slice'", (job_id,))
    if not job:
        raise HTTPException(
            status_code=404, detail={"status": "not_found", "reason": "slice job not found"}
        )
    status = str(job.get("status") or "queued").lower()

    job_artifacts = rows(
        "SELECT * FROM artifacts WHERE job_id = ? ORDER BY created_at ASC",
        (job_id,),
    )
    gcode_row = next(
        (a for a in job_artifacts if (a.get("evidence_type") or "").lower() == "gcode"),
        None,
    )
    proof_row = next(
        (a for a in job_artifacts if (a.get("evidence_type") or "").lower() == "proof_report"),
        None,
    )

    events_rows = rows(
        "SELECT id, event_type, source_agent, payload, created_at "
        "FROM proof_events WHERE event_type IN ('slice_completed','slice_failed') "
        "AND payload LIKE ? ORDER BY created_at DESC LIMIT 1",
        (f'%"job_id":"{job_id}"%',),
    )
    proof_event = events_rows[0] if events_rows else None
    proof_event_id = proof_event.get("id") if proof_event else None

    response: dict[str, Any] = {
        "id": job_id,
        "job_id": job_id,
        "status": status,
        "name": job.get("name"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "dry_run": bool(job.get("dry_run")),
        "proof_event_id": proof_event_id,
    }

    if gcode_row:
        notes = _parse_notes(gcode_row.get("notes"))
        response["gcode_path"] = gcode_row.get("file_path")
        response["sha256"] = notes.get("sha256")
        response["size_bytes"] = gcode_row.get("file_size")
        response["layer_count"] = notes.get("layer_count")
        response["motion_lines"] = notes.get("motion_lines")
        response["estimated_print_time_min"] = notes.get("estimated_print_time_min")
        response["estimated_filament_g"] = notes.get("estimated_filament_g")
        response["slicer_binary"] = notes.get("slicer_binary")
        response["gcode_artifact_id"] = gcode_row.get("id")
    if proof_row:
        response["proof_path"] = proof_row.get("file_path")
        response["proof_artifact_id"] = proof_row.get("id")

    if status == "failed":
        # Pull the last failed step's error and the slice_failed payload for
        # better operator messages.
        failed_step = next(
            iter(
                rows(
                    "SELECT * FROM job_steps WHERE job_id = ? AND status = 'failed' ORDER BY step_number DESC LIMIT 1",
                    (job_id,),
                )
            ),
            None,
        )
        if failed_step:
            response["error"] = failed_step.get("error")
        if proof_event:
            try:
                response["failure_payload"] = json.loads(str(proof_event.get("payload") or "{}"))
            except json.JSONDecodeError:
                response["failure_payload"] = None

    return response


def _parse_notes(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


__all__ = ["router"]
