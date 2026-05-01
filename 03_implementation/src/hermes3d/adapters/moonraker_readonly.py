"""Read-only Moonraker adapter for Phase 3.1 fixture polling."""

from __future__ import annotations

import ipaddress
import json
from collections.abc import Callable, Mapping
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

from hermes3d.orchestration.types import Err, Ok, PrinterMirror, Result

ALLOWED_ENDPOINTS = frozenset(
    {
        "/printer/info",
        "/printer/objects/query",
        "/server/info",
    }
)
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost"})
ALLOWED_NETWORKS = (ipaddress.ip_network("192.168.0.0/24"),)
DEFAULT_TIMEOUT_SECONDS = 2.0
RESPONSE_CAP_BYTES = 256 * 1024

BytesGetter = Callable[[str, float, int], bytes]


class MoonrakerReadonlyError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MoonrakerReadonlyAdapter:
    """GET-only Moonraker client for the Phase 3.1 offline fixture path."""

    def __init__(
        self,
        base_url: str,
        *,
        get_bytes: BytesGetter | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        response_cap_bytes: int = RESPONSE_CAP_BYTES,
    ) -> None:
        self.base_url = _normalize_base_url(base_url)
        self.timeout_seconds = timeout_seconds
        self.response_cap_bytes = response_cap_bytes
        self._get_bytes = get_bytes or _default_get_bytes

    @property
    def allowed_endpoints(self) -> frozenset[str]:
        return ALLOWED_ENDPOINTS

    def get_printer_info(self) -> Result[Mapping[str, object]]:
        return self.get_endpoint("/printer/info")

    def get_objects_query(self) -> Result[Mapping[str, object]]:
        return self.get_endpoint("/printer/objects/query")

    def get_server_info(self) -> Result[Mapping[str, object]]:
        return self.get_endpoint("/server/info")

    def get_endpoint(self, endpoint: str) -> Result[Mapping[str, object]]:
        if endpoint not in ALLOWED_ENDPOINTS:
            return Err("endpoint_not_allowed", f"Moonraker endpoint is not allowed: {endpoint}")

        url = f"{self.base_url}{endpoint}"
        try:
            raw = self._get_bytes(url, self.timeout_seconds, self.response_cap_bytes)
        except MoonrakerReadonlyError as exc:
            return Err(exc.code, exc.message)
        except TimeoutError:
            return Err("timeout", "Moonraker read timed out")
        except (OSError, urlerror.URLError) as exc:
            return Err("request_failed", f"Moonraker read failed: {exc}")

        if len(raw) > self.response_cap_bytes:
            return Err("response_too_large", "Moonraker response exceeded 256 KiB")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Err("invalid_json", "Moonraker response was not valid JSON")

        if not isinstance(payload, Mapping):
            return Err("invalid_payload", "Moonraker response payload must be an object")

        result = payload.get("result", payload)
        if not isinstance(result, Mapping):
            return Err("invalid_payload", "Moonraker result payload must be an object")

        return Ok(result)

    def poll_printer(self, printer_id: str) -> Result[PrinterMirror]:
        printer_info = self.get_printer_info()
        if isinstance(printer_info, Err):
            return printer_info

        server_info = self.get_server_info()
        if isinstance(server_info, Err):
            return server_info

        objects_query = self.get_objects_query()
        if isinstance(objects_query, Err):
            return objects_query

        return Ok(
            _to_printer_mirror(
                printer_id=printer_id,
                printer_info=printer_info.value,
                server_info=server_info.value,
                objects_query=objects_query.value,
            ),
            "Moonraker read-only poll completed",
        )


def _default_get_bytes(url: str, timeout_seconds: float, response_cap_bytes: int) -> bytes:
    req = urlrequest.Request(url, method="GET")
    with urlrequest.urlopen(req, timeout=timeout_seconds) as response:
        return response.read(response_cap_bytes + 1)


def _normalize_base_url(base_url: str) -> str:
    parsed = urlparse.urlparse(base_url)
    host = parsed.hostname
    if parsed.scheme not in {"http", "https"} or host is None or parsed.netloc == "":
        raise MoonrakerReadonlyError("invalid_base_url", "Moonraker base URL must be HTTP(S)")
    if parsed.username or parsed.password:
        raise MoonrakerReadonlyError(
            "invalid_base_url", "Moonraker base URL cannot include userinfo"
        )
    if parsed.path not in {"", "/"}:
        raise MoonrakerReadonlyError("invalid_base_url", "Moonraker base URL cannot include a path")
    if not _host_allowed(host):
        raise MoonrakerReadonlyError(
            "host_not_allowed", f"Moonraker host is not allowlisted: {host}"
        )
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _host_allowed(host: str) -> bool:
    normalized = host.lower().rstrip(".")
    if normalized in ALLOWED_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return any(ip in network for network in ALLOWED_NETWORKS)


def _to_printer_mirror(
    *,
    printer_id: str,
    printer_info: Mapping[str, object],
    server_info: Mapping[str, object],
    objects_query: Mapping[str, object],
) -> PrinterMirror:
    status = _mapping(objects_query.get("status"))
    print_stats = _mapping(status.get("print_stats"))
    virtual_sdcard = _mapping(status.get("virtual_sdcard"))
    extruder = _mapping(status.get("extruder"))
    heater_bed = _mapping(status.get("heater_bed"))

    printer_state = _string_value(
        print_stats.get("state"),
        printer_info.get("state"),
        server_info.get("klippy_state"),
        default="unknown",
    )
    return PrinterMirror(
        printer_id=printer_id,
        name=_string_value(
            printer_info.get("hostname"), server_info.get("hostname"), default=printer_id
        ),
        status=printer_state,
        state=printer_state,
        progress=_float_value(virtual_sdcard.get("progress")),
        temperatures={
            "extruder": _float_value(extruder.get("temperature")),
            "bed": _float_value(heater_bed.get("temperature")),
        },
        metadata={
            "moonraker_version": server_info.get("moonraker_version"),
            "klippy_state": server_info.get("klippy_state"),
            "state_message": printer_info.get("state_message"),
        },
    )


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return value
    return {}


def _string_value(*values: object, default: str) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return default


def _float_value(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    return 0.0
