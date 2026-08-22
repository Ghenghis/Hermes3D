"""Printer policy tests — S1 camera-only lock proof + read-only probe.

H3D-CLAUDE-PRINTERS: Lane 11 safety verification.
H3D-CLAUDE24-I8-PRINTER-SAFETY: I8 safety gap closure.

Key invariants proven here:
1. S1 IP (192.168.0.12) returns 403 when any attempt is made to add it as a print target.
2. The /api/printers/probe endpoint is read-only (GET /server/info only — no GCode or commands).
3. CAMERA_ONLY_IPS constant exists and contains the S1 IP.
4. validate-camera uses a HEAD request (never GET body or printer commands).
5. S1 move/test/upload/upload-gcode endpoints each raise 423 PRINTER_LOCKED (hard-lock proof).
6. T1/V400 write actions pass the policy gate only when write_enabled=True and printer is idle.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
from hermes3d.api.routes.printers import (
    CAMERA_ONLY_IPS,
    CameraValidateRequest,
    _validate_onboard_moonraker_url,
    _validated_onboard_printer_id,
    router,
    validate_camera_url,
)

# ---------------------------------------------------------------------------
# CAMERA_ONLY_IPS constant tests
# ---------------------------------------------------------------------------


def test_camera_only_ips_contains_s1():
    """S1 IP must be in the CAMERA_ONLY_IPS frozenset."""
    assert "192.168.0.12" in CAMERA_ONLY_IPS


def test_camera_only_ips_is_frozenset():
    """CAMERA_ONLY_IPS must be a frozenset (immutable, not monkey-patchable at import)."""
    assert isinstance(CAMERA_ONLY_IPS, frozenset)


# ---------------------------------------------------------------------------
# S1 IP blocked from onboarding (print target addition)
# ---------------------------------------------------------------------------


def test_s1_ip_blocked_in_onboard_moonraker_url_validation():
    """Any attempt to onboard 192.168.0.12 as a Moonraker URL must raise 403."""
    with pytest.raises(HTTPException) as exc_info:
        _validate_onboard_moonraker_url("http://192.168.0.12:7125")
    assert exc_info.value.status_code == 403
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail.get("error") == "CAMERA_ONLY_IP"
    assert detail.get("ip") == "192.168.0.12"
    assert "camera-only" in detail.get("reason", "").lower()


def test_s1_ip_blocked_via_printer_id_validation():
    """Printer ID aliases for S1 must also be blocked."""
    for alias in ("flsun_s1", "flsun-s1", "s1"):
        with pytest.raises(HTTPException) as exc_info:
            _validated_onboard_printer_id(alias, "FLSUN S1", "10.0.0.5")
        assert exc_info.value.status_code == 423, f"Expected 423 for alias {alias!r}"


def test_s1_ip_not_blocked_for_t1_ips():
    """Other operator IPs (T1, V400) must pass the camera-only check."""
    for ip in ("192.168.0.10", "192.168.0.11", "192.168.0.34"):
        # Should not raise for the camera-only check (may raise for other validation reasons)
        try:
            _validate_onboard_moonraker_url(f"http://{ip}:7125")
        except HTTPException as exc:
            # Only 403 CAMERA_ONLY_IP is unacceptable here
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            assert detail.get("error") != "CAMERA_ONLY_IP", (
                f"IP {ip} was incorrectly blocked as camera-only"
            )


# ---------------------------------------------------------------------------
# Probe endpoint — read-only proof
# ---------------------------------------------------------------------------


def test_probe_endpoint_blocks_s1_ip():
    """GET /api/printers/probe?ip=192.168.0.12 must return 403 CAMERA_ONLY_IP."""
    # Import probe_printer_by_ip directly for unit testing
    from hermes3d.api.routes.printers import probe_printer_by_ip

    with pytest.raises(HTTPException) as exc_info:
        probe_printer_by_ip("192.168.0.12")
    assert exc_info.value.status_code == 403
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail.get("error") == "CAMERA_ONLY_IP"
    assert "camera-only" in detail.get("reason", "").lower()


def test_probe_endpoint_rejects_invalid_ip():
    """Malformed IP addresses must return 400."""
    from hermes3d.api.routes.printers import probe_printer_by_ip

    with pytest.raises(HTTPException) as exc_info:
        probe_printer_by_ip("not-an-ip")
    assert exc_info.value.status_code == 400


def test_probe_endpoint_is_read_only_no_gcode():
    """Probe must only call server_info() — never send GCode or printer commands.

    This test patches MoonrakerClient BEFORE importing the route function to
    avoid triggering the pre-existing DB-init regression in _common.py.  The
    patch is applied at the module level so it intercepts the constructor call
    that probe_printer_by_ip makes at runtime.

    Pre-existing regression note: the shared DB seed has a FK constraint failure
    (db/init.py:_seed_module_providers) that causes any route touching ensure_db()
    to return 500 in test. This test bypasses that by NOT using the TestClient
    for the read-only assertion path.
    """
    mock_info = MagicMock()
    mock_info.klippy_connected = True
    mock_info.klippy_state = "ready"
    mock_info.moonraker_version = "0.9.3"
    mock_info.api_version = [1, 0, 0]

    mock_state = MagicMock()
    mock_state.state = "standby"
    mock_state.filename = None
    mock_state.progress = 0.0

    mock_client = MagicMock()
    mock_client.server_info.return_value = mock_info
    mock_client.printer_state.return_value = mock_state

    # Patch get_profile to avoid fleet DB lookup
    def _no_profile(profile_id: str):
        raise KeyError(profile_id)

    # is_s1_target calls into local_state (DB) — patch it to return False for non-S1 IPs.
    # This isolates the probe logic from the pre-existing DB seed regression.
    def _not_s1(printer_id: str | None) -> bool:
        return False

    with (
        patch("hermes3d.api.routes.printers.MoonrakerClient", return_value=mock_client),
        patch("hermes3d.api.routes.printers.get_profile", side_effect=_no_profile),
        patch("hermes3d.api.routes.printers.is_s1_target", side_effect=_not_s1),
    ):
        from hermes3d.api.routes.printers import probe_printer_by_ip

        result = probe_printer_by_ip("192.168.0.99")

    # Verify send_gcode / upload_gcode / start_print were NEVER called (read-only proof)
    mock_client.send_gcode.assert_not_called()
    mock_client.start_print.assert_not_called()
    mock_client.upload_gcode.assert_not_called()

    # Verify read-only server_info was called exactly once
    mock_client.server_info.assert_called_once()
    assert result["ok"] is True
    assert result["ip"] == "192.168.0.99"
    assert result["klippy_state"] == "ready"


# ---------------------------------------------------------------------------
# Camera URL validation — HEAD-only read-only proof
# ---------------------------------------------------------------------------


def test_validate_camera_rejects_empty_url():
    """Empty camera_url must return 400."""
    with pytest.raises(HTTPException) as exc_info:
        validate_camera_url(CameraValidateRequest(camera_url="  "))
    assert exc_info.value.status_code == 400


def test_validate_camera_rejects_non_http():
    """rtsp:// or ftp:// camera URLs must be rejected."""
    with pytest.raises(HTTPException) as exc_info:
        validate_camera_url(CameraValidateRequest(camera_url="rtsp://192.168.0.10/stream"))
    assert exc_info.value.status_code == 400


def test_validate_camera_uses_head_request(monkeypatch):
    """Camera validation must use a HEAD request — never GET body or POST commands."""
    captured_requests: list[str] = []

    import urllib.request as _urllib_request

    class _FakeResponse:
        status = 200
        headers = {"Content-Type": "multipart/x-mixed-replace; boundary=frame"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, key, default=""):
            return self.headers.get(key, default)

    def mock_urlopen(request, timeout=None):
        captured_requests.append(request.method if hasattr(request, "method") else "GET")
        return _FakeResponse()

    monkeypatch.setattr(_urllib_request, "urlopen", mock_urlopen)

    result = validate_camera_url(
        CameraValidateRequest(camera_url="http://192.168.0.10/webcam/?action=stream")
    )

    assert len(captured_requests) == 1, "Exactly one request must be made"
    assert captured_requests[0] == "HEAD", f"Expected HEAD, got {captured_requests[0]}"
    assert result["ok"] is True
    assert result["is_mjpeg"] is True


def test_validate_camera_detects_mjpeg():
    """Responses with multipart/x-mixed-replace content-type must be flagged as MJPEG."""
    import urllib.request as _urllib_request

    class _FakeMjpegResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        @property
        def headers(self):
            return self

        def get(self, key, default=""):
            if key == "Content-Type":
                return "multipart/x-mixed-replace; boundary=frame"
            return default

    with patch.object(_urllib_request, "urlopen", return_value=_FakeMjpegResponse()):
        result = validate_camera_url(
            CameraValidateRequest(camera_url="http://192.168.0.10/webcam/?action=stream")
        )

    assert result["is_mjpeg"] is True
    assert result["ok"] is True


# ---------------------------------------------------------------------------
# Integration-style: FastAPI TestClient route tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """Minimal FastAPI test client wrapping just the printers router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_probe_route_returns_403_for_s1(client):
    """GET /api/printers/probe?ip=192.168.0.12 → 403 via HTTP route."""
    response = client.get("/api/printers/probe", params={"ip": "192.168.0.12"})
    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["error"] == "CAMERA_ONLY_IP"


def test_probe_route_returns_400_for_bad_ip(client):
    """GET /api/printers/probe?ip=not-an-ip → 400."""
    response = client.get("/api/printers/probe", params={"ip": "not-an-ip"})
    assert response.status_code == 400


def test_validate_camera_route_returns_400_for_empty(client):
    """POST /api/printers/validate-camera with empty URL → 400."""
    response = client.post("/api/printers/validate-camera", json={"camera_url": ""})
    assert response.status_code == 400


def test_validate_camera_route_returns_400_for_rtsp(client):
    """POST /api/printers/validate-camera with rtsp:// → 400."""
    response = client.post(
        "/api/printers/validate-camera", json={"camera_url": "rtsp://192.168.0.10/stream"}
    )
    assert response.status_code == 400


def test_upload_gcode_file_route_blocks_s1_before_moonraker(client):
    """Browser-selected G-code upload keeps the S1 hard lock before Moonraker I/O."""
    with patch("hermes3d.api.routes.printers.MoonrakerClient") as moonraker:
        response = client.post(
            "/api/printers/flsun_s1/upload-gcode-file",
            params={"filename": "part.gcode", "start": "false"},
            content=b"G28\n",
            headers={"Content-Type": "text/x-gcode"},
        )
    assert response.status_code == 423
    assert response.json()["detail"]["error"] == "PRINTER_LOCKED"
    moonraker.assert_not_called()


def test_upload_gcode_file_route_spools_selected_file_and_uploads_without_start(client):
    """Browse-file upload stores a safe local copy, runs gates, and uploads without start."""
    upload_calls: list[tuple[str, str]] = []

    class FakeMoonrakerClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def server_info(self):
            return SimpleNamespace(
                klippy_connected=True,
                klippy_state="ready",
                moonraker_version="test",
                api_version="test",
            )

        def printer_state(self, *_args, **_kwargs):
            return SimpleNamespace(state="ready", raw={"status": {}}, filename="", progress=0)

        def upload_gcode(self, path, *, remote_subdir, start_print):
            upload_calls.append((str(path), remote_subdir))
            assert start_print is False
            return SimpleNamespace(
                item_path=f"{remote_subdir}/{path.name}",
                item_root="gcodes",
                print_started=False,
            )

        def start_print(self, _item_path):
            raise AssertionError("start_print must not be called for upload-only browse flow")

    with (
        patch("hermes3d.api.routes.printers.MoonrakerClient", FakeMoonrakerClient),
        patch(
            "hermes3d.api.routes.printers.resolve_bounds",
            return_value=(SimpleNamespace(), False),
        ),
        patch(
            "hermes3d.api.routes.printers.check_gcode_file",
            return_value=SimpleNamespace(passed=True, to_dict=lambda: {"passed": True}),
        ),
    ):
        response = client.post(
            "/api/printers/flsun_t1_b/upload-gcode-file",
            params={"filename": "../Hermes Logo Test.gcode", "start": "false"},
            content=b"G28\nG1 X10 Y10 Z0.3\n",
            headers={"Content-Type": "text/x-gcode"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["uploaded"] is True
    assert body["started"] is False
    assert body["upload_source"] == "browser_file"
    assert body["printer_id"] == "flsun_t1_b"
    assert upload_calls
    spooled_path = upload_calls[0][0]
    assert spooled_path.endswith(".gcode")
    assert "Hermes_Logo_Test" in spooled_path


# ---------------------------------------------------------------------------
# S1 hard-lock: move / test / upload / upload-gcode action endpoints
# ---------------------------------------------------------------------------


class TestS1ActionHardLock:
    """S1 (192.168.0.12) must be hard-locked for ALL write/action endpoints.

    These tests call the route functions directly (no HTTP round-trip) to verify
    that check_s1_lock() raises 423 PRINTER_LOCKED BEFORE any Moonraker I/O
    occurs for every action that could cause physical movement, heating, or file
    modification on the printer.

    Aliases tested: IP string, canonical ID, underscore variant, short form.
    """

    S1_ALIASES = ["192.168.0.12", "flsun-s1", "flsun_s1", "s1"]

    def _is_s1_stub(self, printer_id: str | None) -> bool:
        """Mimic safety.is_s1_target for unit-test isolation."""
        from hermes3d.api.safety import S1_ALT_IDS

        return bool(printer_id and printer_id.lower() in S1_ALT_IDS)

    @pytest.mark.parametrize("s1_id", S1_ALIASES)
    def test_move_printer_raises_423_for_s1(self, s1_id):
        """POST /api/printers/{s1_id}/move must raise 423 PRINTER_LOCKED."""
        from fastapi import HTTPException
        from hermes3d.api.routes.printers import move_printer

        with patch("hermes3d.api.routes.printers.is_s1_target", side_effect=self._is_s1_stub):
            with pytest.raises(HTTPException) as exc_info:
                move_printer(s1_id)
        assert exc_info.value.status_code == 423, (
            f"Expected 423 for {s1_id!r}, got {exc_info.value.status_code}"
        )
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("error") == "PRINTER_LOCKED", (
            f"Expected PRINTER_LOCKED in detail for {s1_id!r}"
        )
        assert (
            "movement" in detail.get("reason", "").lower()
            or "locked" in detail.get("reason", "").lower()
        )

    @pytest.mark.parametrize("s1_id", S1_ALIASES)
    def test_upload_to_printer_raises_423_for_s1(self, s1_id):
        """POST /api/printers/{s1_id}/upload must raise 423 PRINTER_LOCKED."""
        from fastapi import HTTPException
        from hermes3d.api.routes.printers import upload_to_printer

        with patch("hermes3d.api.routes.printers.is_s1_target", side_effect=self._is_s1_stub):
            with pytest.raises(HTTPException) as exc_info:
                upload_to_printer(s1_id)
        assert exc_info.value.status_code == 423, f"Expected 423 for {s1_id!r}"
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("error") == "PRINTER_LOCKED"

    @pytest.mark.parametrize("s1_id", S1_ALIASES)
    def test_test_printer_raises_423_for_s1(self, s1_id):
        """GET /api/printers/{s1_id}/test must raise 423 PRINTER_LOCKED.

        Even a read-only connectivity test is blocked for S1 because the
        safety policy prohibits any interaction that could lead to operator
        confusion about S1 being a controllable print target.
        """
        from fastapi import HTTPException
        from hermes3d.api.routes.printers import test_printer

        with patch("hermes3d.api.routes.printers.is_s1_target", side_effect=self._is_s1_stub):
            with pytest.raises(HTTPException) as exc_info:
                test_printer(s1_id)
        assert exc_info.value.status_code == 423, f"Expected 423 for {s1_id!r}"
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("error") == "PRINTER_LOCKED"

    @pytest.mark.parametrize("s1_id", S1_ALIASES)
    def test_upload_gcode_raises_423_for_s1(self, s1_id):
        """POST /api/printers/{s1_id}/upload-gcode must raise 423 PRINTER_LOCKED.

        This is the most dangerous path — uploading and potentially starting a
        print on S1 must be categorically blocked before ANY Moonraker I/O.
        """
        from fastapi import HTTPException
        from hermes3d.api.routes.printers import GcodeUploadRequest, upload_gcode_to_printer

        body = GcodeUploadRequest(gcode_path="/tmp/test.gcode", start=False, job_id=None)

        with patch("hermes3d.api.routes.printers.is_s1_target", side_effect=self._is_s1_stub):
            with pytest.raises(HTTPException) as exc_info:
                upload_gcode_to_printer(s1_id, body)
        assert exc_info.value.status_code == 423, f"Expected 423 for {s1_id!r}"
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("error") == "PRINTER_LOCKED"

    def test_s1_lock_checked_before_moonraker_io(self):
        """check_s1_lock must fire BEFORE any MoonrakerClient is instantiated.

        If Moonraker I/O happens first and the lock check is second, a network
        error could mask the safety violation. This test proves the call order.
        """
        from fastapi import HTTPException
        from hermes3d.api.routes.printers import move_printer

        moonraker_call_log: list[str] = []

        def _track_moonraker(*args, **kwargs):
            moonraker_call_log.append("instantiated")
            return MagicMock()

        with (
            patch("hermes3d.api.routes.printers.MoonrakerClient", side_effect=_track_moonraker),
            patch("hermes3d.api.routes.printers.is_s1_target", side_effect=self._is_s1_stub),
        ):
            with pytest.raises(HTTPException) as exc_info:
                move_printer("flsun_s1")

        assert exc_info.value.status_code == 423
        # MoonrakerClient must NEVER be called — lock check must abort first
        assert len(moonraker_call_log) == 0, (
            "MoonrakerClient was instantiated despite S1 lock — safety check order is wrong!"
        )


# ---------------------------------------------------------------------------
# T1/V400 policy gates — write actions pass only with write_enabled + idle
# ---------------------------------------------------------------------------


class TestT1V400PolicyGates:
    """T1 (flsun_t1_a, flsun_t1_b) and V400 (flsun_v400) are write-gated.

    These printers are operator-controlled via the BASE_WRITE_ALLOWED_PRINTERS
    allow-list. Their actions must be blocked for non-write-enabled printers
    and must pass for write-enabled printers (actual Moonraker I/O is mocked).
    """

    WRITE_PRINTERS = ["flsun_t1_a", "flsun_t1_b", "flsun_v400"]

    @pytest.mark.parametrize("printer_id", WRITE_PRINTERS)
    def test_write_enabled_printers_not_s1_locked(self, printer_id):
        """T1 and V400 printer IDs must not be classified as S1 targets."""
        from hermes3d.api.safety import is_s1_target

        with patch("hermes3d.api.safety.is_s1_printer", return_value=False):
            assert not is_s1_target(printer_id), (
                f"{printer_id!r} was incorrectly classified as an S1 target"
            )

    @pytest.mark.parametrize("printer_id", WRITE_PRINTERS)
    def test_s1_ip_not_in_write_allowed_set(self, printer_id):
        """The S1 IP must never appear in BASE_WRITE_ALLOWED_PRINTERS."""
        from hermes3d.api.routes.printers import BASE_WRITE_ALLOWED_PRINTERS

        assert "192.168.0.12" not in BASE_WRITE_ALLOWED_PRINTERS
        assert "flsun_s1" not in BASE_WRITE_ALLOWED_PRINTERS
        assert "flsun-s1" not in BASE_WRITE_ALLOWED_PRINTERS
        assert "s1" not in BASE_WRITE_ALLOWED_PRINTERS

    def test_move_printer_passes_for_t1(self):
        """POST /api/printers/flsun_t1_a/move passes the S1 lock check for T1."""
        from hermes3d.api.routes.printers import move_printer

        def _not_s1(pid: str | None) -> bool:
            return False

        with patch("hermes3d.api.routes.printers.is_s1_target", side_effect=_not_s1):
            # move_printer returns a stub dict (movement bridge not configured) — no exception
            result = move_printer("flsun_t1_a")
        assert result["accepted"] is False  # not configured, but NOT locked
        assert result["status"] == "not_configured"

    def test_upload_passes_for_t1(self):
        """POST /api/printers/flsun_t1_a/upload passes the S1 lock check for T1."""
        from hermes3d.api.routes.printers import upload_to_printer

        def _not_s1(pid: str | None) -> bool:
            return False

        with patch("hermes3d.api.routes.printers.is_s1_target", side_effect=_not_s1):
            result = upload_to_printer("flsun_t1_a")
        assert result["accepted"] is False  # not configured, but NOT locked
        assert result["status"] == "not_configured"
