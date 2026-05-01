"""Phase 3.1-C fixture-backed fleet poll round trip."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib import parse as urlparse

from fastapi.testclient import TestClient
from hermes3d.adapters import moonraker_readonly
from hermes3d.adapters.moonraker_readonly import MoonrakerReadonlyAdapter
from hermes3d.agents.printer_executor import POLL_TOOL, PrinterExecutor
from hermes3d.orchestration import Err, OfflineSupervisor, Ok, PollRequest, PrinterMirror
from hermes3d.orchestration.bridge import BridgeState, create_bridge_app

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures"
if str(FIXTURE_ROOT) not in sys.path:
    sys.path.insert(0, str(FIXTURE_ROOT))

from moonraker import create_app  # noqa: E402


def _fixture_getter(client: TestClient):
    def get_bytes(url: str, _timeout_seconds: float, _response_cap_bytes: int) -> bytes:
        parsed = urlparse.urlparse(url)
        response = client.get(parsed.path)
        return response.content

    return get_bytes


def test_fixture_server_poll_returns_valid_printer_dto_without_default_reader(monkeypatch):
    def fail_default_reader(*_args, **_kwargs):
        raise AssertionError("default URL reader must not be used by fixture-backed test")

    monkeypatch.setattr(moonraker_readonly.urlrequest, "urlopen", fail_default_reader)
    client = TestClient(create_app())
    adapter = MoonrakerReadonlyAdapter(
        "http://localhost:7125",
        get_bytes=_fixture_getter(client),
    )
    supervisor = OfflineSupervisor()
    executor = PrinterExecutor(supervisor=supervisor, adapter=adapter)
    request = PollRequest(
        run_id="roundtrip-1",
        agent_id="agent-a",
        printer_id="printer-1",
        tool=POLL_TOOL,
    )
    token = supervisor.issue_token(agent_id="agent-a", tools=frozenset({POLL_TOOL}))

    result = executor.poll(request, token=token)

    assert isinstance(result.result, Ok)
    assert isinstance(result.result.value, PrinterMirror)
    assert result.result.value.name == "fixture-printer-01"
    assert result.result.value.status == "standby"
    assert result.result.value.temperatures["extruder"] == 24.0


def test_fixture_server_has_no_write_endpoints():
    client = TestClient(create_app())

    response = client.post("/printer/print/start")

    assert response.status_code in {404, 405}


def test_executor_requires_capability_token():
    client = TestClient(create_app())
    adapter = MoonrakerReadonlyAdapter("http://localhost:7125", get_bytes=_fixture_getter(client))
    executor = PrinterExecutor(supervisor=OfflineSupervisor(), adapter=adapter)
    request = PollRequest(
        run_id="roundtrip-2",
        agent_id="agent-a",
        printer_id="printer-1",
        tool=POLL_TOOL,
    )

    result = executor.poll(request, token=None)

    assert isinstance(result.result, Err)
    assert result.result.code == "no_token"


def test_executor_refuses_non_poll_methods():
    client = TestClient(create_app())
    adapter = MoonrakerReadonlyAdapter("http://localhost:7125", get_bytes=_fixture_getter(client))
    supervisor = OfflineSupervisor()
    executor = PrinterExecutor(supervisor=supervisor, adapter=adapter)
    request = PollRequest(
        run_id="roundtrip-3",
        agent_id="agent-a",
        printer_id="printer-1",
        tool="printer.write",
    )
    token = supervisor.issue_token(agent_id="agent-a", tools=frozenset({"printer.write"}))

    result = executor.poll(request, token=token)

    assert isinstance(result.result, Err)
    assert result.result.code == "method_not_allowed"


def test_fixture_oversized_response_returns_safe_error():
    client = TestClient(create_app(oversized_server_info=True))
    adapter = MoonrakerReadonlyAdapter("http://localhost:7125", get_bytes=_fixture_getter(client))
    supervisor = OfflineSupervisor()
    executor = PrinterExecutor(supervisor=supervisor, adapter=adapter)
    request = PollRequest(
        run_id="roundtrip-4",
        agent_id="agent-a",
        printer_id="printer-1",
        tool=POLL_TOOL,
    )
    token = supervisor.issue_token(agent_id="agent-a", tools=frozenset({POLL_TOOL}))

    result = executor.poll(request, token=token)

    assert isinstance(result.result, Err)
    assert result.result.code == "response_too_large"


def test_bridge_returns_fixture_snapshot_with_four_live_and_eight_mock_entries():
    client = TestClient(create_bridge_app(), client=("127.0.0.1", 50000))

    response = client.get("/api/printers", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    printers = response.json()
    assert len(printers) == 12
    assert sum(1 for printer in printers if printer["data_source"] == "live") == 4
    assert sum(1 for printer in printers if printer["data_source"] == "mock") == 8


def test_bridge_returns_orchestrator_last_poll_snapshot():
    state = BridgeState()
    state.update_last_poll_snapshot(
        [
            {
                "id": "fixture-only",
                "name": "Fixture Only",
                "model": "Generic",
                "ip": "127.0.0.1",
                "status": "online",
                "adapter": "moonraker",
                "data_source": "live",
                "temp_hot": 21,
                "temp_bed": 20,
                "progress": None,
                "current_job": None,
                "maintenance_flag": False,
                "camera_url": None,
            }
        ]
    )
    client = TestClient(create_bridge_app(state), client=("127.0.0.1", 50000))

    response = client.get("/api/printers")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "fixture-only"


def test_bridge_refuses_non_localhost_clients_and_has_no_write_route():
    remote_client = TestClient(create_bridge_app(), client=("203.0.113.10", 50000))
    local_client = TestClient(create_bridge_app(), client=("127.0.0.1", 50000))

    assert remote_client.get("/api/printers").status_code == 403
    assert local_client.post("/api/printers").status_code == 405
    assert local_client.get("/openapi.json").status_code == 404


def test_bridge_omits_cors_header_for_non_localhost_origins():
    client = TestClient(create_bridge_app(), client=("127.0.0.1", 50000))

    response = client.get("/api/printers", headers={"Origin": "http://example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
