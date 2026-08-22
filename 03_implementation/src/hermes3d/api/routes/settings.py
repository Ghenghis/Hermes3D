from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hermes3d.api.routes._common import execute, rows
from hermes3d.services.local_state import local_printers

router = APIRouter()


class ThemeUpdate(BaseModel):
    theme: str


@router.get("/api/settings")
def get_settings() -> dict[str, Any]:
    flat = {
        item["key"]: item["value"] for item in rows("SELECT key, value FROM settings ORDER BY key")
    }
    ports = {
        key.removeprefix("ports."): int(value)
        for key, value in flat.items()
        if key.startswith("ports.") and str(value).isdigit()
    }
    printer_urls = {
        key.removeprefix("printer.").removesuffix(".moonraker_url"): value
        for key, value in flat.items()
        if key.startswith("printer.") and key.endswith(".moonraker_url")
    }
    camera_urls = {
        key.removeprefix("printer.").removesuffix(".camera_url"): value
        for key, value in flat.items()
        if key.startswith("printer.") and key.endswith(".camera_url")
    }
    printer_statuses = {
        key.removeprefix("printer.").removesuffix(".status"): value
        for key, value in flat.items()
        if key.startswith("printer.") and key.endswith(".status")
    }
    service_urls = {
        key.removeprefix("service.").removesuffix(".url"): value
        for key, value in flat.items()
        if key.startswith("service.") and key.endswith(".url")
    }
    return {
        **flat,
        "theme": flat.get("theme", "midnight"),
        "ports": ports,
        "printerUrls": printer_urls,
        "cameraUrls": camera_urls,
        "printerStatuses": printer_statuses,
        "serviceUrls": service_urls,
    }


@router.put("/api/settings")
def put_settings(body: dict[str, Any]) -> dict[str, Any]:
    updates = body.get("settings", body)
    for key, value in updates.items():
        if key == "ports" and isinstance(value, dict):
            for port_name, port in value.items():
                execute(
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                    (f"ports.{port_name}", str(port)),
                )
            continue
        if key == "printerUrls" and isinstance(value, dict):
            for printer_id, url in value.items():
                _validate_printer_url(str(printer_id), str(url))
                execute(
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                    (f"printer.{printer_id}.moonraker_url", str(url)),
                )
            continue
        if key == "cameraUrls" and isinstance(value, dict):
            for printer_id, url in value.items():
                _validate_camera_url(str(printer_id), str(url))
                execute(
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                    (f"printer.{printer_id}.camera_url", str(url)),
                )
            continue
        if key == "printerStatuses" and isinstance(value, dict):
            for printer_id, status in value.items():
                cleaned_status = str(status).strip().lower()
                _validate_printer_status(str(printer_id), cleaned_status)
                execute(
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                    (f"printer.{printer_id}.status", cleaned_status),
                )
            continue
        if key == "serviceUrls" and isinstance(value, dict):
            for service_id, url in value.items():
                execute(
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                    (f"service.{service_id}.url", str(url)),
                )
            continue
        execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, str(value)),
        )
    return get_settings()


@router.put("/api/settings/theme")
def put_theme(body: ThemeUpdate) -> dict[str, str]:
    if body.theme not in {"midnight", "alloy", "ember", "forest"}:
        raise HTTPException(status_code=400, detail="invalid theme")
    execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('theme', ?, datetime('now'))",
        (body.theme,),
    )
    return get_settings()


def _validate_camera_url(printer_id: str, url: str) -> None:
    _validate_printer_lan_url(printer_id, url, "camera URL")


def _validate_printer_url(printer_id: str, url: str) -> None:
    _validate_printer_lan_url(printer_id, url, "Moonraker URL")


def _validate_printer_status(printer_id: str, status: str) -> None:
    allowed_statuses = {
        "active",
        "online",
        "printing",
        "paused",
        "maintenance",
        "offline",
        "disabled",
        "error",
    }
    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status for {printer_id}: {status}")
    known_ids = {str(printer.get("id")) for printer in local_printers(live=False)}
    if printer_id not in known_ids:
        raise HTTPException(status_code=404, detail=f"Unknown printer id: {printer_id}")


def _validate_printer_lan_url(printer_id: str, url: str, label: str) -> None:
    if not url.strip():
        return
    known_ids = {str(printer.get("id")) for printer in local_printers(live=False)}
    if printer_id not in known_ids:
        raise HTTPException(status_code=404, detail=f"Unknown printer id: {printer_id}")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=400, detail=f"{label} for {printer_id} must be http(s) with a host"
        )
    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=400, detail=f"{label} for {printer_id} must not include credentials"
        )
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"{label} host {parsed.hostname} must be a printer IP address"
        ) from exc
    if (
        address.is_loopback
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
        or not address.is_private
    ):
        raise HTTPException(
            status_code=400, detail=f"{label} host {parsed.hostname} must be a private LAN IP address"
        )
