"""Moonraker HTTP client.

Status: runnable
Contract: 00_overview/contract/MASTER_CONTRACT.md §9 (Printer Fleet Connectivity)

A small, dependency-light wrapper around the public Moonraker REST API:

    https://moonraker.readthedocs.io/en/latest/web_api/

Supports:
  - server.info        -> connectivity probe / version
  - printer.info       -> hostname + state
  - printer.objects.query  -> live state (idle/printing/paused/error)
  - server.files.upload    -> upload sliced .gcode to virtual_sdcard
  - printer.print.start    -> begin printing an uploaded file
  - printer.print.cancel   -> stop the current print

Every call returns a typed dataclass; errors raise ``MoonrakerError`` with
the HTTP status and Moonraker's error envelope so callers can act on it.

This is the bridge between the Hermes3D pipeline and the user's physical
printers (FLSUN T1/T1/V400/S1/SR/QQ-S Pro, Tronxy, Creality, Prusa, Sovol).
A printer must be reachable via Moonraker's HTTP server (default port 7125
or 80 via Mainsail/Fluidd's bundled nginx) for these calls to succeed.

Stack assumed: Klipper + Moonraker + (Fluidd or Mainsail) — the firmware
combination Dave runs on the fleet.
"""

from __future__ import annotations

import ipaddress
import json
import os
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse

# Default request timeout in seconds. Long uploads override per-call.
DEFAULT_TIMEOUT_S = 15.0


class MoonrakerError(RuntimeError):
    """Raised when Moonraker returns an error envelope or HTTP non-2xx."""

    def __init__(
        self, message: str, *, status: int | None = None, url: str | None = None, body: Any = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.url = url
        self.body = body


@dataclass(frozen=True)
class MoonrakerInfo:
    """Result of ``server.info``."""

    klippy_connected: bool
    klippy_state: str
    moonraker_version: str
    api_version: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PrinterState:
    """Snapshot of ``printer.objects.query``."""

    state: str  # "ready" | "printing" | "paused" | "error" | ...
    state_message: str
    progress: float  # 0.0 - 1.0
    filename: str  # currently printing file ("" if idle)
    print_duration_s: float
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UploadResult:
    """Result of ``server.files.upload``."""

    item_path: str  # path within virtual_sdcard, e.g. "hermes3d/desk_organizer.gcode"
    item_root: str  # always "gcodes" for prints
    print_started: bool
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------


class MoonrakerClient:
    """Stateless HTTP client for one Moonraker instance.

    ``base_url`` should be the root URL of the Moonraker host, with NO
    trailing slash and NO API path:
        http://flsun-s1.local
        http://192.168.1.42:7125

    The client transparently handles:
      - authentication via API key (X-Api-Key header) when provided.
      - JSON-RPC (the ``/server/jsonrpc`` POST style) is NOT used here in
        favour of Moonraker's REST endpoints, which are stable and simpler.
    """

    def __init__(
        self, base_url: str, *, api_key: str | None = None, timeout_s: float = DEFAULT_TIMEOUT_S
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("MOONRAKER_API_KEY") or None
        _validate_base_url(self.base_url, api_key_present=bool(self.api_key))
        self.timeout_s = float(timeout_s)

    # -- low-level helpers --------------------------------------------------

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.api_key:
            h["X-Api-Key"] = self.api_key
        if extra:
            h.update(extra)
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: bytes | None = None,
        content_type: str | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        url = self.base_url + path
        if query:
            qs = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in query.items())
            url = f"{url}?{qs}"
        headers = self._headers()
        if content_type and body is not None:
            headers["Content-Type"] = content_type
        req = urlrequest.Request(url=url, method=method.upper(), headers=headers, data=body)
        try:
            with urlrequest.urlopen(req, timeout=timeout_s or self.timeout_s) as resp:
                raw = resp.read()
                if not raw:
                    return {}
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    raise MoonrakerError(
                        f"Non-JSON response from {url}: {exc}",
                        status=resp.status,
                        url=url,
                        body=raw[:200],
                    ) from exc
        except HTTPError as exc:
            payload: Any = None
            try:
                payload = json.loads(exc.read().decode("utf-8"))
            except Exception:
                payload = None
            err_msg = (
                payload.get("error", {}).get("message") if isinstance(payload, dict) else None
            ) or str(exc)
            raise MoonrakerError(
                f"HTTP {exc.code} on {url}: {err_msg}",
                status=exc.code,
                url=url,
                body=payload,
            ) from exc
        except (TimeoutError, URLError) as exc:
            raise MoonrakerError(
                f"Network error on {url}: {exc}",
                url=url,
            ) from exc

    # -- public API ---------------------------------------------------------

    def server_info(self) -> MoonrakerInfo:
        """Probe connectivity and gather basic version info."""
        data = self._request("GET", "/server/info")
        result = data.get("result", {}) if isinstance(data, dict) else {}
        return MoonrakerInfo(
            klippy_connected=bool(result.get("klippy_connected", False)),
            klippy_state=str(result.get("klippy_state", "unknown")),
            moonraker_version=str(result.get("moonraker_version", "")),
            api_version=str(result.get("api_version", "")),
            raw=result,
        )

    def printer_state(
        self,
        objects: Iterable[str] = ("print_stats", "virtual_sdcard"),
    ) -> PrinterState:
        """Query live print_stats + virtual_sdcard via printer.objects.query."""
        # Moonraker query string: ?print_stats&virtual_sdcard
        qs_path = "/printer/objects/query?" + "&".join(quote(o, safe="") for o in objects)
        data = self._request("GET", qs_path)
        result = data.get("result", {}) if isinstance(data, dict) else {}
        status = result.get("status", {})
        ps = status.get("print_stats", {}) or {}
        vs = status.get("virtual_sdcard", {}) or {}
        filename_value = ps.get("filename") or vs.get("file_path") or ""
        return PrinterState(
            state=str(ps.get("state", "unknown")),
            state_message=str(ps.get("message", "")),
            progress=float(vs.get("progress", 0.0)),
            filename=str(filename_value),
            print_duration_s=float(ps.get("print_duration", 0.0)),
            raw=result,
        )

    def upload_gcode(
        self,
        gcode_path: str | Path,
        *,
        remote_subdir: str = "hermes3d",
        start_print: bool = False,
        timeout_s: float = 300.0,
    ) -> UploadResult:
        """Upload a sliced .gcode file to Moonraker's `gcodes` root.

        Args:
            gcode_path: local path to the .gcode file.
            remote_subdir: subdirectory inside the printer's gcodes/ root
                (auto-created by Moonraker if missing).
            start_print: when True, ask Moonraker to start the print
                immediately after the upload completes.
            timeout_s: upload-only timeout (large prints can be many MB).
        """
        gcode_path = Path(gcode_path)
        if not gcode_path.exists():
            raise FileNotFoundError(f"GCode not found: {gcode_path}")
        if gcode_path.suffix.lower() not in (".gcode", ".g"):
            raise ValueError(f"Expected .gcode file, got {gcode_path.suffix}")

        boundary = f"----HermesBoundary{int(time.time() * 1000)}"
        crlf = b"\r\n"
        parts: list[bytes] = []

        def add_field(name: str, value: str) -> None:
            parts.append(f"--{boundary}".encode())
            parts.append(crlf)
            parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
            parts.append(crlf + crlf)
            parts.append(value.encode())
            parts.append(crlf)

        add_field("root", "gcodes")
        add_field("path", remote_subdir)
        if start_print:
            add_field("print", "true")

        # File field
        parts.append(f"--{boundary}".encode())
        parts.append(crlf)
        parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{gcode_path.name}"'.encode()
        )
        parts.append(crlf)
        parts.append(b"Content-Type: application/octet-stream")
        parts.append(crlf + crlf)
        parts.append(gcode_path.read_bytes())
        parts.append(crlf)
        parts.append(f"--{boundary}--".encode())
        parts.append(crlf)

        body = b"".join(parts)
        result = self._request(
            "POST",
            "/server/files/upload",
            body=body,
            content_type=f"multipart/form-data; boundary={boundary}",
            timeout_s=timeout_s,
        )
        # Moonraker may return either:
        # {"result": {"item": {"path": "...", "root": "gcodes"}, "print_started": false}}
        # or an empty body after a successful upload on some FLSUN builds.
        r = (result.get("result") or {}) if isinstance(result, dict) else {}
        item = r.get("item") or {}
        fallback_path = (
            f"{remote_subdir.strip('/')}/{gcode_path.name}"
            if remote_subdir.strip("/")
            else gcode_path.name
        )
        return UploadResult(
            item_path=str(item.get("path") or fallback_path),
            item_root=str(item.get("root", "gcodes")),
            print_started=bool(r.get("print_started", False)),
            raw=r,
        )

    def start_print(self, filename: str) -> dict[str, Any]:
        """Start printing a file already present on the printer."""
        return self._request("POST", "/printer/print/start", query={"filename": filename})

    def cancel_print(self) -> dict[str, Any]:
        return self._request("POST", "/printer/print/cancel")


# ---------------------------------------------------------------------------
# Fleet-wide helper (no I/O until called)
# ---------------------------------------------------------------------------


def probe_fleet(timeout_s: float = 5.0) -> list[dict[str, Any]]:
    """Try to reach every printer in the fleet and return a status table.

    This is what ``scripts/doctor.ps1 -CheckFleet`` calls. Returns a list of
    dicts (one per profile) with: profile_id, url, reachable, klippy_state,
    moonraker_version, error.
    """
    from hermes3d.core.printers import FLEET  # local import; small dep

    out: list[dict[str, Any]] = []
    for p in FLEET:
        url = p.moonraker_url_default
        entry: dict[str, Any] = {
            "profile_id": p.profile_id,
            "manufacturer": p.manufacturer,
            "model": p.model,
            "moonraker_url": url,
            "reachable": False,
            "klippy_state": None,
            "moonraker_version": None,
            "error": None,
        }
        try:
            client = MoonrakerClient(url, timeout_s=timeout_s)
            info = client.server_info()
            entry["reachable"] = True
            entry["klippy_state"] = info.klippy_state
            entry["moonraker_version"] = info.moonraker_version
        except MoonrakerError as exc:
            entry["error"] = str(exc)
        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"
        out.append(entry)
    return out


def _validate_base_url(base_url: str, *, api_key_present: bool) -> None:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Moonraker base_url must be http(s) with a host")
    if parsed.username or parsed.password:
        raise ValueError("Moonraker base_url must not include credentials")
    if not api_key_present:
        return
    try:
        host = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise ValueError("Refusing to send MOONRAKER_API_KEY to a non-IP Moonraker host") from exc
    if not (host.is_private or host.is_link_local):
        raise ValueError("Refusing to send MOONRAKER_API_KEY outside the local printer LAN")


__all__ = [
    "DEFAULT_TIMEOUT_S",
    "MoonrakerClient",
    "MoonrakerError",
    "MoonrakerInfo",
    "PrinterState",
    "UploadResult",
    "probe_fleet",
]
