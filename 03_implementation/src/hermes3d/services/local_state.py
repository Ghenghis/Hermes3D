from __future__ import annotations

import json
import os
import socket
import tomllib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from hermes3d.api.routes._common import execute, new_id, row, rows
from hermes3d.core.printers.moonraker_client import MoonrakerClient, MoonrakerError
from hermes3d.core.slicer.flsun_profiles import printer_source_refs

REPO_ROOT = Path(__file__).resolve().parents[4]
IMPLEMENTATION_ROOT = REPO_ROOT / "03_implementation"
CONFIG_DIR = IMPLEMENTATION_ROOT / "config"

LOCAL_FLEET_IDS = ("flsun_t1_a", "flsun_t1_b", "flsun_s1", "flsun_v400")
S1_IDS = {"flsun_s1", "flsun-s1", "s1", "192.168.0.12"}
PLATE_NEEDS_CLEARANCE_STATES = {"needs_clearance", "unknown"}

DEFAULT_LOCAL_OVERRIDES: dict[str, dict[str, str]] = {
    "flsun_t1_a": {"name": "T1 #1", "moonraker_url": "http://192.168.0.10", "status": "active"},
    "flsun_t1_b": {"name": "T1 #2", "moonraker_url": "http://192.168.0.11", "status": "active"},
    "flsun_s1": {"name": "FLSUN S1", "moonraker_url": "http://192.168.0.12", "status": "offline"},
    "flsun_v400": {
        "name": "FLSUN V400",
        "moonraker_url": "http://192.168.0.34",
        "status": "active",
    },
}

DEFAULT_CAMERA_VIEW: dict[str, Any] = {
    "rotate_deg": 0,
    "mirror_x": False,
    "mirror_y": False,
    "zoom": 1.0,
    "focus_x": 50,
    "focus_y": 50,
    "brightness": 100,
    "contrast": 100,
    "saturation": 100,
    "fit": "cover",
    "feed_mode": "stream",
    "card_size": "standard",
    "review_overlay": "none",
}

STATUS_MAP = {
    "active": "online",
    "ready": "online",
    "online": "online",
    "printing": "printing",
    "paused": "paused",
    "maintenance": "maintenance",
    "offline": "offline",
    "disabled": "offline",
    "error": "error",
}


def implementation_path(*parts: str) -> Path:
    return IMPLEMENTATION_ROOT.joinpath(*parts)


def load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _printer_config() -> dict[str, dict[str, Any]]:
    stock = load_toml(CONFIG_DIR / "printers.toml").get("printers", {})
    user = load_toml(CONFIG_DIR / "printers.user.toml").get("printers", {})
    merged: dict[str, dict[str, Any]] = {}
    for printer_id in LOCAL_FLEET_IDS:
        base = dict(stock.get(printer_id, {}))
        base.update(DEFAULT_LOCAL_OVERRIDES.get(printer_id, {}))
        base.update(user.get(printer_id, {}))
        merged[printer_id] = base
    for item in onboarded_printer_rows():
        printer_id = str(item["id"])
        if printer_id in merged:
            continue
        source_refs: dict[str, Any] = {}
        raw_source_refs = item.get("source_refs")
        if isinstance(raw_source_refs, str) and raw_source_refs.strip():
            try:
                parsed_refs = json.loads(raw_source_refs)
            except json.JSONDecodeError:
                parsed_refs = {}
            if isinstance(parsed_refs, dict):
                source_refs = parsed_refs
        merged[printer_id] = {
            "name": str(item.get("name") or printer_id),
            "model": str(item.get("model") or "Generic"),
            "moonraker_url": str(item.get("moonraker_url") or ""),
            "camera_url": item.get("camera_url"),
            "status": str(item.get("status") or "active"),
            "adapter": str(item.get("adapter") or "moonraker"),
            "safety_policy": str(item.get("safety_policy") or "read_only"),
            "source_refs": source_refs,
            "onboarded": True,
        }
    return merged


def onboarded_printer_rows() -> list[dict[str, Any]]:
    return rows("SELECT * FROM onboarded_printers ORDER BY created_at, id")


def save_onboarded_printer(
    *,
    printer_id: str,
    name: str,
    model: str,
    ip: str,
    moonraker_url: str,
    camera_url: str | None,
    status: str,
    safety_policy: str,
    created_by: str,
    probe_summary: dict[str, Any],
    source_refs: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    execute(
        """
        INSERT INTO onboarded_printers
            (id, name, model, adapter, ip, moonraker_url, camera_url, status,
             safety_policy, source_refs, probe_summary, created_by, updated_at)
        VALUES (?, ?, ?, 'moonraker', ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            model = excluded.model,
            ip = excluded.ip,
            moonraker_url = excluded.moonraker_url,
            camera_url = excluded.camera_url,
            status = excluded.status,
            safety_policy = excluded.safety_policy,
            source_refs = excluded.source_refs,
            probe_summary = excluded.probe_summary,
            created_by = excluded.created_by,
            updated_at = datetime('now')
        """,
        (
            printer_id,
            name,
            model,
            ip,
            moonraker_url,
            camera_url,
            status,
            safety_policy,
            json.dumps(source_refs or {}, sort_keys=True),
            json.dumps(probe_summary, sort_keys=True),
            created_by,
        ),
    )
    return local_printer(printer_id)


def _setting(key: str) -> str | None:
    item = row("SELECT value FROM settings WHERE key = ?", (key,))
    return str(item["value"]) if item else None


def _persist_setting(key: str, value: str) -> None:
    execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, value),
    )


def canonical_printer_id(printer_id: str | None) -> str | None:
    if not printer_id:
        return None
    normalized = printer_id.lower().replace("-", "_")
    aliases = {
        "t1_1": "flsun_t1_a",
        "t1_a": "flsun_t1_a",
        "flsun_t1_1": "flsun_t1_a",
        "192.168.0.10": "flsun_t1_a",
        "t1_2": "flsun_t1_b",
        "t1_b": "flsun_t1_b",
        "flsun_t1_2": "flsun_t1_b",
        "192.168.0.11": "flsun_t1_b",
        "s1": "flsun_s1",
        "flsun_s1": "flsun_s1",
        "192.168.0.12": "flsun_s1",
        "v400": "flsun_v400",
        "flsun_v400": "flsun_v400",
        "192.168.0.34": "flsun_v400",
    }
    alias = aliases.get(normalized)
    if alias:
        return alias
    config = _printer_config()
    if normalized in config:
        return normalized
    for candidate_id, item in config.items():
        candidate_key = candidate_id.lower().replace("-", "_")
        name_key = str(item.get("name") or "").lower().replace("-", "_").replace(" ", "_")
        ip_key = printer_ip(str(item.get("moonraker_url") or "")) or ""
        if normalized in {candidate_key, name_key, ip_key.lower()}:
            return candidate_id
    return normalized


def is_s1_printer(printer_id: str | None) -> bool:
    return canonical_printer_id(printer_id) == "flsun_s1" or bool(
        printer_id and printer_id.lower() in S1_IDS
    )


def printer_ip(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    return parsed.hostname or None


def printer_camera_url(printer_id: str, ip: str | None) -> str | None:
    explicit = _setting(f"printer.{printer_id}.camera_url")
    if explicit is not None:
        return explicit or None
    configured = _printer_config().get(printer_id, {})
    configured_camera = configured.get("camera_url")
    if isinstance(configured_camera, str) and configured_camera.strip():
        return configured_camera
    if not ip:
        return None
    return f"http://{ip}/webcam/?action=stream"


def camera_view_settings(printer_id: str) -> dict[str, Any]:
    canonical = canonical_printer_id(printer_id) or printer_id
    defaults = dict(DEFAULT_CAMERA_VIEW)
    if canonical == "flsun_s1":
        defaults["rotate_deg"] = 90
        defaults["fit"] = "cover"
        defaults["card_size"] = "wide"
        defaults["zoom"] = 1.5
        defaults["review_overlay"] = "plate_frame"
    stored = _setting(f"printer.{canonical}.camera_view")
    if stored:
        try:
            parsed = json.loads(stored)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            defaults.update(_clean_camera_view(parsed))
    if canonical == "flsun_s1" and not stored:
        defaults["rotate_deg"] = 90
        defaults["fit"] = "cover"
        defaults["card_size"] = "wide"
        defaults["zoom"] = 1.5
        defaults["review_overlay"] = "plate_frame"
    return defaults


def set_camera_view_settings(printer_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    canonical = canonical_printer_id(printer_id)
    if canonical is None or canonical not in _printer_config():
        return None
    merged = camera_view_settings(canonical)
    merged.update(_clean_camera_view(updates))
    _persist_setting(f"printer.{canonical}.camera_view", json.dumps(merged, sort_keys=True))
    return merged


def _clean_camera_view(value: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    rotate = value.get("rotate_deg")
    if isinstance(rotate, (int, float)):
        cleaned["rotate_deg"] = int(round(float(rotate) / 90) * 90) % 360
    for key in ("mirror_x", "mirror_y"):
        if isinstance(value.get(key), bool):
            cleaned[key] = value[key]
    ranges = {
        "zoom": (0.5, 4.0),
        "focus_x": (0.0, 100.0),
        "focus_y": (0.0, 100.0),
        "brightness": (40.0, 180.0),
        "contrast": (40.0, 200.0),
        "saturation": (0.0, 220.0),
    }
    for key, bounds in ranges.items():
        raw = value.get(key)
        if isinstance(raw, (int, float)):
            cleaned[key] = round(min(bounds[1], max(bounds[0], float(raw))), 2)
    if value.get("fit") in {"cover", "contain"}:
        cleaned["fit"] = value["fit"]
    if value.get("feed_mode") in {"stream", "snapshot"}:
        cleaned["feed_mode"] = value["feed_mode"]
    if value.get("card_size") in {"compact", "standard", "wide", "large", "full"}:
        cleaned["card_size"] = value["card_size"]
    if value.get("review_overlay") in {"none", "crosshair", "grid", "plate_frame"}:
        cleaned["review_overlay"] = value["review_overlay"]
    return cleaned


def _moonraker_snapshot(url: str | None, *, locked: bool) -> dict[str, Any]:
    if locked or not url:
        return {}
    printer_info_state = _moonraker_printer_info_state(url)
    if printer_info_state is None:
        return {"data_source": "error", "status": "offline"}

    base_status = "online" if str(printer_info_state).lower() == "ready" else "offline"
    try:
        client = MoonrakerClient(url, timeout_s=1.5)
        state = client.printer_state(("print_stats", "virtual_sdcard", "extruder", "heater_bed"))
    except (MoonrakerError, OSError, ValueError):
        if base_status == "online":
            return {
                "data_source": "degraded",
                "status": base_status,
                "temp_hot": None,
                "temp_bed": None,
                "progress": None,
                "current_job": None,
            }
        return {
            "data_source": "live" if base_status == "online" else "error",
            "status": base_status,
            "temp_hot": None,
            "temp_bed": None,
            "progress": None,
            "current_job": None,
        }

    raw_status = state.raw.get("status", {}) if isinstance(state.raw, dict) else {}
    extruder = (
        raw_status.get("extruder", {}) if isinstance(raw_status.get("extruder"), dict) else {}
    )
    bed = raw_status.get("heater_bed", {}) if isinstance(raw_status.get("heater_bed"), dict) else {}
    print_state = state.state.lower()
    if str(printer_info_state).lower() != "ready":
        status = "offline"
    elif print_state == "printing":
        status = "printing"
    elif print_state == "paused":
        status = "paused"
    elif print_state == "error":
        status = "error"
    else:
        status = "online"
    return {
        "data_source": "live",
        "status": status,
        "temp_hot": _rounded_number(extruder.get("temperature")),
        "temp_bed": _rounded_number(bed.get("temperature")),
        "progress": round(state.progress * 100, 1) if state.progress is not None else None,
        "current_job": state.filename or None,
    }


def _moonraker_printer_info_state(url: str, timeout_s: float = 1.5) -> str | None:
    try:
        request = urllib.request.Request(
            f"{url.rstrip('/')}/printer/info", headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ):
        return None
    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, dict):
        state = result.get("state")
        return str(state) if state is not None else None
    return None


def _moonraker_snapshots(config: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    requests: list[tuple[str, str | None, bool]] = []
    for printer_id, item in config.items():
        url = _setting(f"printer.{printer_id}.moonraker_url") or str(
            item.get("moonraker_url") or ""
        )
        requests.append((printer_id, url or None, printer_id == "flsun_s1"))
    if not requests:
        return {}
    snapshots: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(requests))) as pool:
        futures = {
            pool.submit(_moonraker_snapshot, url, locked=locked): printer_id
            for printer_id, url, locked in requests
        }
        for future in as_completed(futures):
            printer_id = futures[future]
            try:
                snapshots[printer_id] = future.result()
            except Exception:
                snapshots[printer_id] = {"data_source": "error", "status": "offline"}
    return snapshots


def _rounded_number(value: Any) -> float | None:
    return round(float(value), 1) if isinstance(value, int | float) else None


def local_printers(*, live: bool = True) -> list[dict[str, Any]]:
    config = _printer_config()
    live_snapshots = _moonraker_snapshots(config) if live else {}
    result: list[dict[str, Any]] = []
    for printer_id, item in config.items():
        url = _setting(f"printer.{printer_id}.moonraker_url") or str(
            item.get("moonraker_url") or ""
        )
        configured_status = _setting(f"printer.{printer_id}.status") or str(
            item.get("status") or "offline"
        )
        status = STATUS_MAP.get(configured_status.lower(), "offline")
        ip = printer_ip(url)
        locked = printer_id == "flsun_s1"
        live_snapshot = live_snapshots.get(printer_id, {}) if live else {}
        model = str(item.get("model") or "Generic")
        if model == "T1":
            model = "FLSUN T1"
        elif model == "S1":
            model = "FLSUN S1"
        elif model == "V400":
            model = "FLSUN V400"
        live_source = str(live_snapshot.get("data_source") or "")
        effective_status = str(live_snapshot.get("status") or status)
        effective_data_source = str(
            live_snapshot.get("data_source") or ("policy" if locked else "config")
        )
        effective_status_source = (
            live_source
            if live_source
            else "settings"
            if _setting(f"printer.{printer_id}.status")
            else "local_config"
        )
        if live and live_source == "error" and status in {"online", "active"}:
            effective_status = "online"
            effective_data_source = "degraded"
            effective_status_source = "telemetry_timeout_fallback_to_operator_status"
        source_refs = item.get("source_refs")
        if not isinstance(source_refs, dict):
            source_refs = printer_source_refs(printer_id)
        result.append(
            {
                "id": printer_id,
                "name": str(
                    item.get("name") or f"{item.get('manufacturer', '')} {item.get('model', '')}"
                ).strip(),
                "model": model if model in {"FLSUN T1", "FLSUN S1", "FLSUN V400"} else "Generic",
                "ip": ip,
                "status": effective_status,
                "adapter": str(item.get("adapter") or "moonraker"),
                "data_source": effective_data_source,
                "temp_hot": live_snapshot.get("temp_hot"),
                "temp_bed": live_snapshot.get("temp_bed"),
                "progress": live_snapshot.get("progress"),
                "current_job": live_snapshot.get("current_job"),
                "maintenance_flag": locked or status == "maintenance",
                "camera_url": printer_camera_url(printer_id, ip),
                "moonraker_url": url or None,
                "source_refs": source_refs,
                "status_source": effective_status_source,
                "safety_policy": "locked"
                if locked
                else str(item.get("safety_policy") or "write_enabled"),
                "write_enabled": (not locked)
                and str(item.get("safety_policy") or "write_enabled") == "write_enabled",
                "onboarded": bool(item.get("onboarded")),
            }
        )
    return result


def local_printer(printer_id: str, *, live: bool = True) -> dict[str, Any] | None:
    canonical = canonical_printer_id(printer_id)
    return next(
        (printer for printer in local_printers(live=live) if printer["id"] == canonical), None
    )


def build_plate_clearance_rows(
    printers: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    printers = printers or local_printers()
    existing = {item["printer_id"]: item for item in rows("SELECT * FROM build_plate_clearance")}
    result: list[dict[str, Any]] = []
    for printer in printers:
        current_job = printer.get("current_job")
        progress = printer.get("progress")
        existing_row = existing.get(str(printer["id"]))
        completed_job = (
            isinstance(current_job, str)
            and current_job != ""
            and isinstance(progress, int | float)
            and float(progress) >= 99.5
        )
        if completed_job:
            if (
                not existing_row
                or existing_row.get("last_job_filename") != current_job
                or existing_row.get("state") != "clear"
            ):
                existing_row = _upsert_build_plate_clearance(
                    str(printer["id"]),
                    "needs_clearance",
                    current_job,
                    "live_telemetry",
                    "Completed print detected; build plate must be checked before the next print starts.",
                    None,
                )
                _ensure_plate_notification(printer, existing_row)
        elif not existing_row:
            existing_row = _upsert_build_plate_clearance(
                str(printer["id"]),
                "clear" if not is_s1_printer(str(printer["id"])) else "locked",
                current_job if isinstance(current_job, str) else None,
                "live_telemetry",
                "No completed active print is currently reported by live telemetry.",
                None,
            )
        result.append(_plate_row_with_printer(existing_row, printer))
    return result


def build_plate_clearance(printer_id: str) -> dict[str, Any] | None:
    canonical = canonical_printer_id(printer_id)
    if not canonical:
        return None
    return next(
        (item for item in build_plate_clearance_rows() if item["printer_id"] == canonical), None
    )


def mark_build_plate_clear(
    printer_id: str, actor: str, reason: str | None = None
) -> dict[str, Any] | None:
    printer = local_printer(printer_id)
    if not printer:
        return None
    current_job = printer.get("current_job")
    updated = _upsert_build_plate_clearance(
        str(printer["id"]),
        "clear",
        current_job if isinstance(current_job, str) else None,
        "operator_or_agent_visual_check",
        reason or "Build plate visually confirmed clear.",
        actor,
    )
    execute(
        """
        UPDATE notifications
        SET read_at = COALESCE(read_at, datetime('now')),
            dismissed_at = COALESCE(dismissed_at, datetime('now'))
        WHERE type = 'ACTION_REQUIRED'
          AND source_tab = 'observe'
          AND action_url = ?
          AND dismissed_at IS NULL
        """,
        (f"#observe?plate={printer['id']}",),
    )
    return _plate_row_with_printer(updated, printer)


def assert_build_plate_clear(printer_id: str) -> None:
    plate = build_plate_clearance(printer_id)
    if plate and plate["state"] in PLATE_NEEDS_CLEARANCE_STATES:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=409,
            detail={
                "error": "BUILD_PLATE_NOT_CLEARED",
                "printer_id": plate["printer_id"],
                "state": plate["state"],
                "last_job_filename": plate.get("last_job_filename"),
                "reason": plate.get("reason")
                or "Build plate must be checked before starting another print.",
            },
        )


def _upsert_build_plate_clearance(
    printer_id: str,
    state: str,
    last_job_filename: str | None,
    source: str,
    reason: str,
    actor: str | None,
) -> dict[str, Any]:
    execute(
        """
        INSERT INTO build_plate_clearance
            (printer_id, state, last_job_filename, source, reason, confirmed_by, confirmed_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? IS NULL THEN NULL ELSE datetime('now') END, datetime('now'))
        ON CONFLICT(printer_id) DO UPDATE SET
            state = excluded.state,
            last_job_filename = excluded.last_job_filename,
            source = excluded.source,
            reason = excluded.reason,
            confirmed_by = excluded.confirmed_by,
            confirmed_at = excluded.confirmed_at,
            updated_at = datetime('now')
        """,
        (printer_id, state, last_job_filename, source, reason, actor, actor),
    )
    return row("SELECT * FROM build_plate_clearance WHERE printer_id = ?", (printer_id,)) or {
        "printer_id": printer_id,
        "state": state,
        "last_job_filename": last_job_filename,
        "source": source,
        "reason": reason,
        "confirmed_by": actor,
    }


def _plate_row_with_printer(plate: dict[str, Any], printer: dict[str, Any]) -> dict[str, Any]:
    return {
        **plate,
        "printer_name": printer["name"],
        "camera_url": printer.get("camera_url"),
        "printer_locked": is_s1_printer(str(printer["id"])),
    }


def _ensure_plate_notification(printer: dict[str, Any], plate: dict[str, Any]) -> None:
    action_url = f"#observe?plate={printer['id']}"
    existing = row(
        """
        SELECT id FROM notifications
        WHERE type = 'ACTION_REQUIRED'
          AND source_tab = 'observe'
          AND action_url = ?
          AND read_at IS NULL
          AND dismissed_at IS NULL
        """,
        (action_url,),
    )
    if existing:
        return
    execute(
        """
        INSERT INTO notifications
            (id, type, priority, title, body, source_agent_id, source_tab, action_url, action_label)
        VALUES (?, 'ACTION_REQUIRED', 'high', ?, ?, 'print-safety-agent', 'observe', ?, 'Check plate')
        """,
        (
            new_id(),
            f"{printer['name']} build plate needs clearance",
            f"Completed print {plate.get('last_job_filename') or ''} reached 100%. Confirm the part is removed before starting the next print.",
            action_url,
        ),
    )


def set_printer_status(printer_id: str, status: str, actor: str) -> dict[str, Any] | None:
    printer = local_printer(printer_id)
    if printer is None:
        return None
    _persist_setting(f"printer.{printer['id']}.status", status)
    _persist_setting(f"printer.{printer['id']}.status_actor", actor)
    return local_printer(printer["id"])


def set_printer_url(printer_id: str, url: str) -> dict[str, Any] | None:
    printer = local_printer(printer_id)
    if printer is None:
        return None
    _persist_setting(f"printer.{printer['id']}.moonraker_url", url)
    return local_printer(printer["id"])


def source_modules() -> list[dict[str, Any]]:
    result = rows("SELECT * FROM modules ORDER BY section, display_name")
    if result:
        return result
    from hermes3d.db.load_modules import load_modules

    load_modules()
    return rows("SELECT * FROM modules ORDER BY section, display_name")


def service_url(service_id: str) -> str | None:
    return _setting(f"service.{service_id}.url")


def set_service_url(service_id: str, url: str) -> None:
    _persist_setting(f"service.{service_id}.url", url)


def port_reachable(url: str | None, timeout_s: float = 0.35) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def env_configured(*names: str) -> bool:
    return any(bool(os.environ.get(name)) for name in names)
