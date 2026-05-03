"""Integration tests for ``GET /api/health/services``.

Validates the FastAPI endpoint shape, auth, and that probe results flow
through the serialiser unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent.parent / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


fastapi = pytest.importorskip("fastapi")
starlette_testclient = pytest.importorskip("starlette.testclient")
TestClient = starlette_testclient.TestClient

from hermes3d.api import health as health_module  # noqa: E402
from hermes3d.api.server import create_app  # noqa: E402
from hermes3d.core.health.probe import ProbeResult, ServiceSpec, Status  # noqa: E402

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _stub_results() -> list[ProbeResult]:
    return [
        ProbeResult(
            spec=ServiceSpec("LM Studio", "127.0.0.1", 1234, "llm"),
            status=Status.ONLINE,
            detail="TCP 127.0.0.1:1234 accepted",
            latency_ms=4.2,
            probed_at="2026-05-03T12:00:00+00:00",
        ),
        ProbeResult(
            spec=ServiceSpec("Ollama", "127.0.0.1", 11434, "llm"),
            status=Status.OFFLINE,
            detail="TCP 127.0.0.1:11434 refused (errno=10061)",
            latency_ms=12.8,
            probed_at="2026-05-03T12:00:00+00:00",
        ),
        ProbeResult(
            spec=ServiceSpec("HermesProof MCP", "127.0.0.1", 0, "mcp", enabled=False),
            status=Status.DISABLED,
            detail="service disabled by config",
            latency_ms=0.0,
            probed_at="2026-05-03T12:00:00+00:00",
        ),
    ]


@pytest.fixture
def client_open(monkeypatch, tmp_path):
    """TestClient against an open-mode (no-auth) FastAPI app."""

    def _fake_probe_all(extra=()):  # noqa: ARG001 — match real signature
        return _stub_results()

    def _fake_specs():
        return ()

    monkeypatch.setattr(health_module, "probe_all", _fake_probe_all)
    monkeypatch.setattr(health_module, "moonraker_specs_from_config", _fake_specs)

    app = create_app(
        api_token="",  # open mode
        queue_path=str(tmp_path / "queue.json"),
        spools_path=str(tmp_path / "spools.json"),
        history_path=str(tmp_path / "history.jsonl"),
    )
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_authed(monkeypatch, tmp_path):
    """TestClient against a token-protected FastAPI app."""

    def _fake_probe_all(extra=()):  # noqa: ARG001
        return _stub_results()

    def _fake_specs():
        return ()

    monkeypatch.setattr(health_module, "probe_all", _fake_probe_all)
    monkeypatch.setattr(health_module, "moonraker_specs_from_config", _fake_specs)

    app = create_app(
        api_token="secret-token",
        queue_path=str(tmp_path / "queue.json"),
        spools_path=str(tmp_path / "spools.json"),
        history_path=str(tmp_path / "history.jsonl"),
    )
    with TestClient(app) as c:
        yield c


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


def test_health_endpoint_returns_expected_shape(client_open):
    res = client_open.get("/api/health/services")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "results" in body and isinstance(body["results"], list)
    assert len(body["results"]) == 3

    first = body["results"][0]
    for key in ("name", "category", "host", "port", "status", "detail", "latency_ms", "probed_at"):
        assert key in first, f"missing key {key!r}"
    assert first["status"] == "online"
    assert first["latency_ms"] == 4.2


def test_health_endpoint_serialises_disabled_service(client_open):
    res = client_open.get("/api/health/services")
    body = res.json()
    disabled = next(r for r in body["results"] if r["name"] == "HermesProof MCP")
    assert disabled["status"] == "disabled"
    assert disabled["latency_ms"] == 0.0


def test_health_endpoint_requires_token_when_configured(client_authed):
    no_token = client_authed.get("/api/health/services")
    assert no_token.status_code == 401, no_token.text

    bad_token = client_authed.get("/api/health/services", headers={"Authorization": "Bearer wrong"})
    assert bad_token.status_code == 403, bad_token.text

    good_token = client_authed.get(
        "/api/health/services", headers={"Authorization": "Bearer secret-token"}
    )
    assert good_token.status_code == 200, good_token.text
