from __future__ import annotations

import hashlib
import ipaddress
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import as_json, execute, new_id, row
from hermes3d.api.safety import check_s1_lock, is_s1_target
from hermes3d.core.printability_truth_gate import GATE_DEFINITIONS
from hermes3d.core.printers import get_profile
from hermes3d.core.printers.moonraker_client import MoonrakerClient, MoonrakerError
from hermes3d.core.safety.gcode_bounds import check_gcode_file, resolve_bounds
from hermes3d.services.local_state import (
    assert_build_plate_clear,
    canonical_printer_id,
    local_printer,
    local_printers,
    save_onboarded_printer,
    set_printer_status,
    set_printer_url,
)

router = APIRouter()
BASE_WRITE_ALLOWED_PRINTERS = {"flsun_t1_a", "flsun_t1_b", "flsun_v400"}
IDLE_PRINT_STATES = {"standby", "complete", "ready"}
REMOTE_SUBDIR_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
ONBOARD_ID_RE = re.compile(r"^[A-Za-z0-9._-]{2,64}$")


class UrlUpdate(BaseModel):
    url: str


class StatusUpdate(BaseModel):
    status: str
    actor: str = "local-operator"


class GcodeUploadRequest(BaseModel):
    gcode_path: str
    start: bool = False
    job_id: str | None = None
    remote_subdir: str = "hermes3d"
    actor: str = "hermes-agent"


class PrinterOnboardRequest(BaseModel):
    name: str
    moonraker_url: str
    id: str | None = None
    model: str = "Generic"
    camera_url: str | None = None
    actor: str = "hermes-agent"
    write_enabled: bool = False


def _printer(printer_id: str) -> dict[str, Any]:
    printer = local_printer(printer_id)
    if not printer:
        raise HTTPException(status_code=404, detail="printer not found")
    return printer


@router.get("/api/printers")
def list_printers() -> list[dict[str, Any]]:
    return local_printers()


@router.post("/api/printers/onboard", status_code=201)
def onboard_printer(body: PrinterOnboardRequest) -> dict[str, Any]:
    moonraker_url, host = _validate_onboard_moonraker_url(body.moonraker_url)
    camera_url = _validated_onboard_camera_url(body.camera_url, host)
    printer_id = _validated_onboard_printer_id(body.id, body.name, host)
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Printer name is required.")
    model = _validated_onboard_model(body.model)
    _assert_onboarding_does_not_overwrite_static_printer(printer_id, host)
    probe_summary = _probe_onboarded_printer(moonraker_url, camera_url, write_enabled=body.write_enabled)
    safety_policy = "write_enabled" if body.write_enabled else "read_only"
    printer = save_onboarded_printer(
        printer_id=printer_id,
        name=name,
        model=model,
        ip=host,
        moonraker_url=moonraker_url,
        camera_url=camera_url,
        status="active",
        safety_policy=safety_policy,
        created_by=body.actor,
        probe_summary=probe_summary,
        source_refs={
            "safety": "Moonraker endpoint onboarded by Hermes3D after live /server/info and /printer/objects/query probes.",
        },
    )
    if printer is None:
        raise HTTPException(status_code=500, detail="Printer was saved but could not be loaded back from the local database.")
    proof_event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (
            proof_event_id,
            "printers.onboarded",
            body.actor,
            as_json(
                {
                    "printer_id": printer["id"],
                    "name": printer["name"],
                    "moonraker_url": moonraker_url,
                    "camera_url": camera_url,
                    "write_enabled": bool(printer.get("write_enabled")),
                    "probe_summary": probe_summary,
                }
            ),
        ),
    )
    return {
        "created": True,
        "printer": printer,
        "probe_summary": probe_summary,
        "proof_event_id": proof_event_id,
    }


@router.get("/api/printers/{printer_id}/status")
def printer_status(printer_id: str) -> dict[str, Any]:
    printer = _printer(printer_id)
    return {"printer_id": printer["id"], "status": printer["status"], "locked": is_s1_target(printer_id)}


@router.put("/api/printers/{printer_id}/status")
def update_printer_status(printer_id: str, body: StatusUpdate) -> dict[str, Any]:
    if body.status not in {"online", "printing", "paused", "maintenance", "offline", "error", "active"}:
        raise HTTPException(status_code=400, detail="invalid printer status")
    canonical = canonical_printer_id(printer_id)
    if not is_s1_target(canonical or printer_id):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "LIVE_STATUS_NOT_OPERATOR_WRITABLE",
                "printer_id": canonical or printer_id,
                "reason": "Live Moonraker printer status is read-only; use the health probe or printer actions instead.",
            },
        )
    allowed_s1_statuses = {"online", "active", "offline", "maintenance", "error"}
    if body.status not in allowed_s1_statuses:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "S1_POLICY_STATUS_RESTRICTED",
                "printer_id": canonical or printer_id,
                "allowed": sorted(allowed_s1_statuses),
                "reason": "S1 can be marked online/offline for operator visibility while movement, upload, and print tests remain locked.",
            },
        )
    printer = set_printer_status(printer_id, body.status, body.actor)
    if not printer:
        raise HTTPException(status_code=404, detail="printer not found")
    return {
        "printer_id": printer["id"],
        "status": printer["status"],
        "actor": body.actor,
        "locked": is_s1_target(printer["id"]),
    }


@router.get("/api/printers/{printer_id}/lock")
def printer_lock(printer_id: str) -> dict[str, Any]:
    locked = is_s1_target(printer_id)
    printer = local_printer(printer_id)
    return {
        "printer_id": printer["id"] if printer else printer_id,
        "locked": locked,
        "reason": "Maintenance lock: do not test or move. Movement may damage the hotend." if locked else None,
        "locked_by": "backend-safety-policy" if locked else None,
        "ip": "192.168.0.12" if locked else None,
    }


@router.get("/api/printers/{printer_id}/test")
def test_printer(printer_id: str) -> dict[str, Any]:
    check_s1_lock(printer_id)
    printer = _printer(printer_id)
    moonraker_url = str(printer.get("moonraker_url") or "")
    started = time.perf_counter()
    ok, message, http_status = _probe_moonraker(moonraker_url)
    return {
        "printer_id": printer["id"],
        "ok": ok,
        "message": message,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "status": "online" if ok else "unreachable",
        "http_status": http_status,
        "setup": {"moonraker_url": moonraker_url, "adapter": "moonraker"},
    }


@router.post("/api/printers/{printer_id}/move")
def move_printer(printer_id: str) -> dict[str, Any]:
    check_s1_lock(printer_id)
    return {"printer_id": printer_id, "accepted": False, "status": "not_configured", "reason": "Movement bridge not configured."}


@router.post("/api/printers/{printer_id}/upload")
def upload_to_printer(printer_id: str) -> dict[str, Any]:
    check_s1_lock(printer_id)
    return {"printer_id": printer_id, "accepted": False, "status": "not_configured", "reason": "Upload bridge not configured."}


@router.post("/api/printers/{printer_id}/upload-gcode")
def upload_gcode_to_printer(printer_id: str, body: GcodeUploadRequest) -> dict[str, Any]:
    check_s1_lock(printer_id)
    printer = _write_enabled_printer(printer_id)
    gcode_path = _validated_gcode_path(body.gcode_path)
    remote_subdir = _validated_remote_subdir(body.remote_subdir)
    bounds, used_fallback_bounds = resolve_bounds(printer_id=printer["id"], fleet_lookup=get_profile)
    bounds_report = check_gcode_file(gcode_path, bounds)
    if not bounds_report.passed:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "GCODE_BOUNDS_FAILED",
                "printer_id": printer["id"],
                "report": bounds_report.to_dict(),
            },
        )
    if body.start:
        _require_print_start_gates(body.job_id)
        assert_build_plate_clear(printer["id"])

    client = MoonrakerClient(str(printer["moonraker_url"]), timeout_s=8.0)
    info, state_before = _fresh_idle_state(client, printer["id"], require_idle=body.start)
    try:
        upload = client.upload_gcode(gcode_path, remote_subdir=remote_subdir, start_print=False)
        start_result: dict[str, Any] | None = None
        if body.start:
            _fresh_idle_state(client, printer["id"], require_idle=True)
            start_result = client.start_print(upload.item_path)
    except (MoonrakerError, OSError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Moonraker upload/start failed: {exc}") from exc

    return {
        "printer_id": printer["id"],
        "printer_name": printer["name"],
        "accepted": True,
        "uploaded": True,
        "started": bool(body.start),
        "job_id": body.job_id,
        "actor": body.actor,
        "moonraker_url": printer["moonraker_url"],
        "item_path": upload.item_path,
        "item_root": upload.item_root,
        "gcode_path": str(gcode_path),
        "gcode_sha256": _sha256(gcode_path),
        "gcode_bytes": gcode_path.stat().st_size,
        "bounds_passed": bounds_report.passed,
        "used_fallback_bounds": used_fallback_bounds,
        "state_before": state_before.raw.get("status", {}),
        "klippy_state": info.klippy_state,
        "start_result": start_result,
    }


def _require_print_start_gates(job_id: str | None) -> None:
    if not job_id:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Starting a print requires job_id with approved PRINT_APPROVAL and passing truth-gate records.",
            },
        )
    approval = row(
        "SELECT id FROM approvals WHERE job_id = ? AND approval_type = 'PRINT_APPROVAL' AND status = 'approved' LIMIT 1",
        (job_id,),
    )
    if not approval:
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Starting a print requires an approved PRINT_APPROVAL record for this job.",
                "job_id": job_id,
            },
        )
    passing = row(
        """
        SELECT COUNT(DISTINCT gate_name) AS count
        FROM truth_gate_results
        WHERE job_id = ? AND status = 'pass'
        """,
        (job_id,),
    )
    passing_count = int(passing["count"]) if passing and passing.get("count") is not None else 0
    if passing_count < len(GATE_DEFINITIONS):
        raise HTTPException(
            status_code=409,
            detail={
                "status": "blocked",
                "reason": "Starting a print requires passing truth-gate records for every configured gate.",
                "job_id": job_id,
                "passing_gates": passing_count,
                "required_gates": len(GATE_DEFINITIONS),
            },
        )


@router.put("/api/printers/{printer_id}/url")
def update_printer_url(printer_id: str, body: UrlUpdate) -> dict[str, Any]:
    _validate_moonraker_url(printer_id, body.url)
    printer = set_printer_url(printer_id, body.url)
    if not printer:
        raise HTTPException(status_code=404, detail="printer not found")
    return {"printer_id": printer["id"], "url": body.url, "saved": True, "locked": is_s1_target(printer["id"])}


def _validate_moonraker_url(printer_id: str, url: str) -> None:
    if not url.strip():
        return
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Moonraker URL must be http(s) with a host")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Moonraker URL must not include credentials")
    canonical = canonical_printer_id(printer_id)
    printer = next((item for item in local_printers() if item["id"] == canonical), None)
    expected_ip = str(printer.get("ip")) if printer and printer.get("ip") else None
    if expected_ip and parsed.hostname != expected_ip:
        raise HTTPException(status_code=400, detail=f"Moonraker URL host must match configured printer IP {expected_ip}")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Moonraker URL host must be a configured printer IP address") from exc
    if address.is_loopback or address.is_multicast or address.is_unspecified or address.is_reserved:
        raise HTTPException(status_code=400, detail="Moonraker URL host is not allowed")


def _validate_onboard_moonraker_url(raw_url: str) -> tuple[str, str]:
    cleaned = raw_url.strip().rstrip("/")
    if not cleaned:
        raise HTTPException(status_code=400, detail="Moonraker URL is required.")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Moonraker URL must be http(s) with a host.")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Moonraker URL must not include credentials.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise HTTPException(status_code=400, detail="Moonraker URL must be the printer API root, not a nested path.")
    host = parsed.hostname
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Moonraker URL host must be a printer IP address.") from exc
    if str(address) == "192.168.0.12" or is_s1_target(str(address)):
        raise HTTPException(
            status_code=423,
            detail={
                "error": "S1_POLICY_LOCKED",
                "printer_id": "flsun_s1",
                "ip": str(address),
                "reason": "FLSUN S1 remains offline/locked/no-test by operator policy; onboarding cannot convert it into a write-enabled printer.",
            },
        )
    if address.is_loopback or address.is_multicast or address.is_unspecified or address.is_reserved:
        raise HTTPException(status_code=400, detail="Moonraker URL host is not allowed.")
    if not (address.is_private or address.is_link_local):
        raise HTTPException(status_code=400, detail="Moonraker URL host must be a local/private printer IP address.")
    return cleaned, str(address)


def _validated_onboard_camera_url(raw_url: str | None, moonraker_host: str) -> str:
    cleaned = raw_url.strip() if raw_url else f"http://{moonraker_host}/webcam/?action=stream"
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=400, detail="Camera URL must be http(s) with a host.")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Camera URL must not include credentials.")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Camera URL host must be a printer or LAN camera IP address.") from exc
    if address.is_loopback or address.is_multicast or address.is_unspecified or address.is_reserved:
        raise HTTPException(status_code=400, detail="Camera URL host is not allowed.")
    if not (address.is_private or address.is_link_local):
        raise HTTPException(status_code=400, detail="Camera URL host must be a local/private IP address.")
    return cleaned


def _validated_onboard_printer_id(raw_id: str | None, name: str, host: str) -> str:
    candidate = (raw_id or f"moonraker_{host.replace('.', '_')}").strip().lower().replace("-", "_")
    candidate = re.sub(r"[^a-z0-9._-]+", "_", candidate).strip("._-")
    if not candidate:
        candidate = re.sub(r"[^a-z0-9._-]+", "_", name.strip().lower()).strip("._-")
    if not ONBOARD_ID_RE.fullmatch(candidate):
        raise HTTPException(status_code=400, detail="Printer ID must be 2-64 chars using letters, numbers, dot, underscore, or dash.")
    if is_s1_target(candidate):
        raise HTTPException(
            status_code=423,
            detail={
                "error": "S1_POLICY_LOCKED",
                "printer_id": "flsun_s1",
                "reason": "S1 aliases stay locked and cannot be onboarded through the generic printer path.",
            },
        )
    return candidate


def _validated_onboard_model(raw_model: str) -> str:
    model = raw_model.strip() or "Generic"
    allowed = {"FLSUN T1", "FLSUN S1", "FLSUN V400", "Generic"}
    if model not in allowed:
        model = "Generic"
    if model == "FLSUN S1":
        raise HTTPException(
            status_code=423,
            detail={
                "error": "S1_POLICY_LOCKED",
                "printer_id": "flsun_s1",
                "reason": "S1 remains managed by the dedicated locked policy path.",
            },
        )
    return model


def _assert_onboarding_does_not_overwrite_static_printer(printer_id: str, host: str) -> None:
    for existing in local_printers():
        existing_id = str(existing["id"])
        existing_ip = str(existing.get("ip") or "")
        if is_s1_target(existing_id) or is_s1_target(existing_ip):
            continue
        if printer_id == existing_id or host == existing_ip:
            if existing_id not in BASE_WRITE_ALLOWED_PRINTERS:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "PRINTER_ALREADY_ONBOARDED",
                        "printer_id": existing_id,
                        "ip": existing_ip,
                        "reason": "A printer with this ID or IP is already onboarded.",
                    },
                )
        if existing_id in BASE_WRITE_ALLOWED_PRINTERS and (printer_id == existing_id or host == existing_ip):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "STATIC_PRINTER_ALREADY_CONFIGURED",
                    "printer_id": existing_id,
                    "ip": existing_ip,
                    "reason": "The operator's fixed T1/V400 fleet is already configured; edit its settings instead of onboarding over it.",
                },
            )


def _probe_onboarded_printer(moonraker_url: str, camera_url: str, *, write_enabled: bool) -> dict[str, Any]:
    probes: list[dict[str, Any]] = []
    client = MoonrakerClient(moonraker_url, timeout_s=4.0)
    try:
        info = client.server_info()
    except (MoonrakerError, OSError, ValueError) as exc:
        _raise_onboard_probe_failed("server_info", exc, probes)
    probes.append(
        {
            "name": "server_info",
            "ok": True,
            "klippy_connected": info.klippy_connected,
            "klippy_state": info.klippy_state,
            "moonraker_version": info.moonraker_version,
            "api_version": info.api_version,
        }
    )
    if not info.klippy_connected or info.klippy_state.lower() != "ready":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PRINTER_NOT_READY",
                "failed_probe": "server_info",
                "klippy_connected": info.klippy_connected,
                "klippy_state": info.klippy_state,
                "reason": "Moonraker responded, but Klipper is not in a ready state.",
                "probes": probes,
            },
        )
    try:
        state = client.printer_state(("print_stats", "virtual_sdcard", "webhooks"))
    except (MoonrakerError, OSError, ValueError) as exc:
        _raise_onboard_probe_failed("printer_objects_query", exc, probes)
    probes.append(
        {
            "name": "printer_objects_query",
            "ok": True,
            "print_state": state.state,
            "filename": state.filename or None,
            "progress": state.progress,
        }
    )
    if write_enabled and state.state.lower() not in IDLE_PRINT_STATES:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PRINTER_NOT_IDLE_FOR_WRITE_ENABLE",
                "failed_probe": "safe_printer_state",
                "print_state": state.state,
                "reason": "Write-enabled onboarding requires the printer to be idle.",
                "probes": probes,
            },
        )
    probes.append(_probe_optional_http(camera_url, "camera_stream"))
    return {
        "ok": True,
        "required_probes": ["server_info", "printer_objects_query"],
        "probes": probes,
    }


def _raise_onboard_probe_failed(probe_name: str, exc: BaseException, probes: list[dict[str, Any]]) -> None:
    detail = {
        "error": "ONBOARDING_PROBE_FAILED",
        "failed_probe": probe_name,
        "reason": str(exc),
        "probes": [*probes, {"name": probe_name, "ok": False, "reason": str(exc)}],
    }
    raise HTTPException(status_code=502, detail=detail) from exc


def _probe_optional_http(url: str, probe_name: str) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, headers={"Accept": "*/*"})
        with urllib.request.urlopen(request, timeout=2.5) as response:
            return {"name": probe_name, "ok": 200 <= int(response.status) < 400, "http_status": int(response.status), "required": False}
    except urllib.error.HTTPError as exc:
        return {"name": probe_name, "ok": False, "http_status": int(exc.code), "required": False, "reason": f"HTTP {exc.code}"}
    except OSError as exc:
        return {"name": probe_name, "ok": False, "http_status": None, "required": False, "reason": str(exc)}


def _probe_moonraker(moonraker_url: str) -> tuple[bool, str, int | None]:
    if not moonraker_url:
        return False, "Moonraker URL is not configured.", None
    for path in ("/server/info", "/printer/info"):
        url = f"{moonraker_url.rstrip('/')}{path}"
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=2.0) as response:
                if 200 <= int(response.status) < 400:
                    return True, f"Moonraker responded at {path}.", int(response.status)
                return False, f"Moonraker returned HTTP {response.status} at {path}.", int(response.status)
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                return False, f"Moonraker requires authentication at {path}.", int(exc.code)
        except OSError:
            continue
    return False, "Moonraker did not respond to /server/info or /printer/info.", None


def _write_enabled_printer(printer_id: str) -> dict[str, Any]:
    canonical = canonical_printer_id(printer_id)
    printer = _printer(canonical or printer_id)
    if canonical not in BASE_WRITE_ALLOWED_PRINTERS and printer.get("write_enabled") is not True:
        raise HTTPException(
            status_code=423 if is_s1_target(printer_id) else 409,
            detail={
                "error": "PRINTER_WRITE_NOT_ALLOWED",
                "printer_id": canonical or printer_id,
                "allowed": sorted(BASE_WRITE_ALLOWED_PRINTERS),
                "reason": "Only the live T1 pair, V400, and explicitly write-enabled onboarded printers are enabled for guarded Moonraker uploads.",
            },
        )
    moonraker_url = printer.get("moonraker_url")
    if not moonraker_url:
        raise HTTPException(status_code=409, detail="Moonraker URL is not configured for this printer.")
    return printer


def _validated_gcode_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if path.suffix.lower() not in {".gcode", ".g"}:
        raise HTTPException(status_code=400, detail="Only .gcode or .g files can be uploaded to a printer.")
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"G-code file not found: {path}")
    if path.stat().st_size <= 0:
        raise HTTPException(status_code=400, detail="G-code file is empty.")
    return path


def _validated_remote_subdir(value: str) -> str:
    cleaned = value.strip().strip("/")
    if not cleaned or ".." in cleaned or "\\" in cleaned or not REMOTE_SUBDIR_RE.match(cleaned):
        raise HTTPException(status_code=400, detail="remote_subdir must be a safe printer-relative path.")
    return cleaned


def _fresh_idle_state(client: MoonrakerClient, printer_id: str, *, require_idle: bool) -> tuple[Any, Any]:
    try:
        info = client.server_info()
        state = client.printer_state(("print_stats", "virtual_sdcard", "toolhead"))
    except MoonrakerError as exc:
        raise HTTPException(status_code=502, detail=f"Moonraker probe failed for {printer_id}: {exc}") from exc
    if not info.klippy_connected or info.klippy_state.lower() != "ready":
        raise HTTPException(
            status_code=409,
            detail=f"Printer {printer_id} is not Klipper-ready: {info.klippy_state}",
        )
    if require_idle and state.state.lower() not in IDLE_PRINT_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Printer {printer_id} is not idle; print_stats.state={state.state}.",
        )
    return info, state


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
