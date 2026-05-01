"""Phase 3.1-C read-only Moonraker adapter contract tests."""

from __future__ import annotations

import json
from urllib import parse as urlparse

import pytest
from hermes3d.adapters.moonraker_readonly import (
    ALLOWED_ENDPOINTS,
    DEFAULT_TIMEOUT_SECONDS,
    RESPONSE_CAP_BYTES,
    MoonrakerReadonlyAdapter,
    MoonrakerReadonlyError,
)
from hermes3d.orchestration import Err, Ok, PrinterMirror


def _payload(path: str) -> bytes:
    responses = {
        "/printer/info": {
            "result": {
                "hostname": "unit-printer",
                "state": "ready",
                "state_message": "ready",
            }
        },
        "/server/info": {
            "result": {
                "hostname": "unit-printer",
                "klippy_state": "ready",
                "moonraker_version": "unit-3.1",
            }
        },
        "/printer/objects/query": {
            "result": {
                "status": {
                    "print_stats": {"state": "standby"},
                    "virtual_sdcard": {"progress": 0.25},
                    "extruder": {"temperature": 25.0},
                    "heater_bed": {"temperature": 26.0},
                }
            }
        },
    }
    return json.dumps(responses[path], sort_keys=True).encode("utf-8")


def test_adapter_uses_only_allowed_get_endpoints_and_returns_printer_dto():
    seen: list[tuple[str, float, int]] = []

    def get_bytes(url: str, timeout_seconds: float, response_cap_bytes: int) -> bytes:
        parsed = urlparse.urlparse(url)
        seen.append((parsed.path, timeout_seconds, response_cap_bytes))
        assert parsed.path in ALLOWED_ENDPOINTS
        return _payload(parsed.path)

    adapter = MoonrakerReadonlyAdapter("http://localhost:7125", get_bytes=get_bytes)
    result = adapter.poll_printer("printer-1")

    assert isinstance(result, Ok)
    assert isinstance(result.value, PrinterMirror)
    assert result.value.printer_id == "printer-1"
    assert result.value.name == "unit-printer"
    assert result.value.status == "standby"
    assert result.value.progress == 0.25
    assert {path for path, _timeout, _cap in seen} == ALLOWED_ENDPOINTS
    assert all(timeout == DEFAULT_TIMEOUT_SECONDS for _path, timeout, _cap in seen)
    assert all(cap == RESPONSE_CAP_BYTES for _path, _timeout, cap in seen)


def test_write_methods_are_absent():
    adapter = MoonrakerReadonlyAdapter("http://127.0.0.1:7125", get_bytes=lambda *_args: b"{}")

    for method_name in (
        "delete",
        "dry_run",
        "execute",
        "post",
        "put",
        "send_gcode",
        "start_print",
    ):
        assert not hasattr(adapter, method_name)


def test_refuses_non_allowlisted_hosts():
    with pytest.raises(MoonrakerReadonlyError, match="not allowlisted"):
        MoonrakerReadonlyAdapter("http://10.0.0.5:7125")


def test_allows_configured_private_printer_subnet():
    adapter = MoonrakerReadonlyAdapter("http://192.168.0.42:7125", get_bytes=lambda *_args: b"{}")

    assert adapter.base_url == "http://192.168.0.42:7125"


def test_disallowed_endpoint_is_refused_without_reader_call():
    called = False

    def get_bytes(_url: str, _timeout_seconds: float, _response_cap_bytes: int) -> bytes:
        nonlocal called
        called = True
        return b"{}"

    adapter = MoonrakerReadonlyAdapter("http://localhost:7125", get_bytes=get_bytes)
    result = adapter.get_endpoint("/printer/gcode/script")

    assert isinstance(result, Err)
    assert result.code == "endpoint_not_allowed"
    assert called is False


def test_oversized_response_returns_safe_error():
    adapter = MoonrakerReadonlyAdapter(
        "http://localhost:7125",
        get_bytes=lambda *_args: b"x" * (RESPONSE_CAP_BYTES + 1),
    )

    result = adapter.get_server_info()

    assert isinstance(result, Err)
    assert result.code == "response_too_large"
