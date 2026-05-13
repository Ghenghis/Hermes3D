"""Agents provider smoke should update the shared provider health surface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """Fresh app with isolated DB + shared smoke-status file."""
    monkeypatch.setenv("HERMES3D_MINIMAX_API_KEY", "test-minimax-key-redacted")
    monkeypatch.setenv("HERMES3D_MINIMAX_BASE_URL", "https://api.minimax.io/v1")
    monkeypatch.setenv("HERMES3D_MINIMAX_MODEL", "MiniMax-M2.7-highspeed")
    monkeypatch.setenv("HERMES3D_DEEPSEEK_API_KEY", "test-deepseek-key-redacted")
    monkeypatch.setenv("HERMES3D_DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("HERMES3D_DEEPSEEK_MODEL", "deepseek-v4-pro")

    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", tmp_path / "hermes3d.db")
    db_init.reset_initialization_state()

    status_file = tmp_path / "var" / "code-history" / "provider-smoke-status.json"
    from hermes3d.api.routes import system as system_route
    from hermes3d.services import code_history

    monkeypatch.setattr(system_route, "PROVIDER_SMOKE_STATUS_FILE", status_file)
    monkeypatch.setattr(code_history, "PROVIDER_SMOKE_STATUS_FILE", status_file)

    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    api = TestClient(app)
    api._status_file = status_file  # type: ignore[attr-defined]
    return api


def _fake_pass(provider_id: str, **_kwargs: Any) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "status": "PASS_LIVE",
        "http_status": 200,
        "latency_ms": 17 if provider_id == "minimax" else 23,
        "model": "MiniMax-M2.7-highspeed" if provider_id == "minimax" else "deepseek-v4-pro",
        "tokens_in": 1,
        "tokens_out": 1,
        "body_sha256": (provider_id[:1] or "x") * 64,
        "body_size_bytes": 80,
        "error_code": None,
        "key_present": True,
        "completion_text": "redacted by route",
    }


def test_agents_provider_smoke_flips_shared_provider_health_green(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The GUI-facing smoke endpoint must not leave /api/providers/health idle."""
    from hermes3d.api.routes import agents as agents_route

    monkeypatch.setattr(agents_route, "_provider_call", _fake_pass)

    response = client.post(
        "/api/agents/providers/smoke",
        json={"providers": ["minimax", "deepseek"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    minimax_smoke = body["providers"]["minimax"]
    deepseek_smoke = body["providers"]["deepseek"]
    assert minimax_smoke["status"] == "PASS_LIVE"
    assert deepseek_smoke["status"] == "PASS_LIVE"
    assert minimax_smoke["proof_event_id"]
    assert deepseek_smoke["proof_event_id"]
    assert "completion_text" not in json.dumps(body)

    health = client.get("/api/providers/health")
    assert health.status_code == 200, health.text
    providers = {entry["provider_id"]: entry for entry in health.json()["providers"]}
    assert providers["minimax"]["status"] == "green"
    assert providers["minimax"]["evidence_id"] == minimax_smoke["proof_event_id"]
    assert providers["minimax"]["http_status"] == 200
    assert providers["minimax"]["latency_ms"] == 17
    assert providers["deepseek"]["status"] == "green"
    assert providers["deepseek"]["evidence_id"] == deepseek_smoke["proof_event_id"]
    assert providers["deepseek"]["http_status"] == 200
    assert providers["deepseek"]["latency_ms"] == 23

    raw_status = client._status_file.read_text(encoding="utf-8")  # type: ignore[attr-defined]
    assert "test-minimax-key-redacted" not in raw_status
    assert "test-deepseek-key-redacted" not in raw_status


def test_agents_provider_smoke_auth_failure_flips_shared_health_red(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hermes3d.api.routes import agents as agents_route

    def fake_auth_failure(provider_id: str, **_kwargs: Any) -> dict[str, Any]:
        return {
            "provider_id": provider_id,
            "status": "FAIL_AUTH",
            "http_status": 401,
            "latency_ms": 31,
            "model": "deepseek-v4-pro",
            "tokens_in": None,
            "tokens_out": None,
            "body_sha256": "d" * 64,
            "body_size_bytes": 120,
            "error_code": "authentication_error",
            "key_present": True,
        }

    monkeypatch.setattr(agents_route, "_provider_call", fake_auth_failure)

    response = client.post("/api/agents/providers/smoke", json={"providers": ["deepseek"]})
    assert response.status_code == 200, response.text
    proof_event_id = response.json()["providers"]["deepseek"]["proof_event_id"]

    health = client.get("/api/providers/health")
    providers = {entry["provider_id"]: entry for entry in health.json()["providers"]}
    assert providers["deepseek"]["status"] == "red"
    assert providers["deepseek"]["evidence_id"] == proof_event_id
    assert providers["deepseek"]["blocked_reason"].startswith(
        "Provider deepseek smoke failed authentication"
    )
