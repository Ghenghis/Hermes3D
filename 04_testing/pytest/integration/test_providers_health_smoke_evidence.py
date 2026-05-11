"""W18-A21 (2026-05-11): /api/providers/health reads smoke evidence.

MiniMax-builders identified the root cause: ``provider_health()`` in
``hermes3d.api.routes.system`` was hardcoding ``status="idle"`` for every
cloud provider with a configured API key, even after a successful live
smoke at ``/api/code-operator/providers/smoke`` wrote a
``code_provider_smoke`` evidence row and a
``var/code-history/provider-smoke-status.json`` record.

These tests pin the new behavior:

1. No smoke evidence on disk -> entries stay honestly ``idle``.
2. Recent ``status="ready"`` smoke -> entry becomes ``green`` and surfaces
   the evidence id / model / base_url_label.
3. Old (>5 min) ``status="ready"`` smoke -> entry returns ``idle`` with
   ``stale=True`` and a "rerun provider smoke" blocked_reason; never
   fabricates a passing green status from a stale proof.
4. Recent ``status="blocked"``/``auth_failed`` smoke -> entry becomes
   ``red`` and surfaces the first blocked_reason.

The endpoint is read-only and free of API key exposure.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _write_smoke(status_file: Path, providers: dict) -> None:
    status_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "updated_at": _iso(datetime.now(timezone.utc)),
        "providers": providers,
    }
    status_file.write_text(json.dumps(payload), encoding="utf-8")


def _ready_record(
    provider: str, *, ts_utc: str, evidence_id: str | None = "ev_w18a21_ready"
) -> dict:
    return {
        "provider_id": provider,
        "accepted": True,
        "status": "ready",
        "ts_utc": ts_utc,
        "blocked_reasons": [],
        "auth_contract": {
            "provider_id": provider,
            "base_url_label": f"api.{provider}.io",
            "chat_path": "/chat/completions",
            "auth_scheme": "Authorization: Bearer <redacted>",
            "api_key_configured": True,
            "api_key_source": f"HERMES3D_{provider.upper()}_API_KEY",
            "accepted_api_key_env": [f"HERMES3D_{provider.upper()}_API_KEY"],
            "model": f"{provider}-builder-default",
            "model_configured": True,
            "model_source": f"HERMES3D_{provider.upper()}_MODEL",
            "base_url_source": "default",
        },
        "content_sha256": "deadbeef" * 8,
        "evidence_id": evidence_id,
    }


def _blocked_record(provider: str, *, ts_utc: str, reason: str) -> dict:
    rec = _ready_record(provider, ts_utc=ts_utc)
    rec["accepted"] = False
    rec["status"] = "blocked"
    rec["blocked_reasons"] = [reason]
    rec["content_sha256"] = None
    return rec


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """Fresh FastAPI client with API keys configured + tmp smoke status file."""
    # Make sure the cloud provider rows are emitted (the endpoint only adds
    # them when the key env var is set in the resolved private env).
    monkeypatch.setenv("HERMES3D_MINIMAX_API_KEY", "test-key-redacted")
    monkeypatch.setenv("HERMES3D_DEEPSEEK_API_KEY", "test-key-redacted")
    monkeypatch.delenv("HERMES3D_LLM_API_KEY", raising=False)

    db_path = tmp_path / "hermes3d.db"
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    # Redirect the smoke status file to a tmp path the test owns.
    status_file = tmp_path / "var" / "code-history" / "provider-smoke-status.json"
    from hermes3d.api.routes import system as system_module

    monkeypatch.setattr(system_module, "PROVIDER_SMOKE_STATUS_FILE", status_file)

    from hermes3d.api.app import create_gui_app

    client = TestClient(create_gui_app())
    client._status_file = status_file  # type: ignore[attr-defined]
    return client


def _get_health(client: TestClient) -> list[dict]:
    response = client.get("/api/providers/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, dict)
    providers = body.get("providers")
    assert isinstance(providers, list)
    return providers


def _provider(providers: list[dict], provider_id: str) -> dict:
    matches = [p for p in providers if p.get("provider_id") == provider_id]
    assert matches, f"provider {provider_id} not present in /api/providers/health"
    return matches[0]


def test_providers_health_honest_idle_when_no_smoke_evidence(client: TestClient) -> None:
    """With no smoke status file present, MiniMax/DeepSeek stay honestly idle."""
    providers = _get_health(client)
    minimax = _provider(providers, "minimax")
    deepseek = _provider(providers, "deepseek")
    for entry in (minimax, deepseek):
        assert entry["status"] == "idle"
        assert entry["stale"] is False
        assert entry["http_status"] is None
        # Honest idle should not fabricate evidence_id.
        assert entry.get("evidence_id") in (None, "")


def test_providers_health_green_for_recent_ready_smoke(client: TestClient) -> None:
    """A recent ready smoke flips MiniMax to green and surfaces evidence."""
    status_file: Path = client._status_file  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc)
    _write_smoke(
        status_file,
        {
            "minimax": _ready_record("minimax", ts_utc=_iso(now)),
            # DeepSeek intentionally absent — should remain idle.
        },
    )
    providers = _get_health(client)
    minimax = _provider(providers, "minimax")
    deepseek = _provider(providers, "deepseek")
    assert minimax["status"] == "green"
    assert minimax["stale"] is False
    assert minimax["http_status"] == 200
    assert minimax["evidence_id"] == "ev_w18a21_ready"
    assert minimax["model"] == "minimax-builder-default"
    assert minimax["base_url_label"] == "api.minimax.io"
    assert minimax.get("blocked_reason") is None
    # DeepSeek with no smoke entry stays honestly idle.
    assert deepseek["status"] == "idle"
    assert deepseek.get("evidence_id") in (None, "")


def test_providers_health_stale_smoke_does_not_fabricate_green(client: TestClient) -> None:
    """A ready smoke older than the staleness window must not stay green."""
    status_file: Path = client._status_file  # type: ignore[attr-defined]
    stale_ts = _iso(datetime.now(timezone.utc) - timedelta(minutes=30))
    _write_smoke(
        status_file,
        {"minimax": _ready_record("minimax", ts_utc=stale_ts)},
    )
    minimax = _provider(_get_health(client), "minimax")
    assert minimax["status"] == "idle"
    assert minimax["stale"] is True
    assert "rerun provider smoke" in (minimax.get("blocked_reason") or "").lower()


def test_providers_health_red_for_recent_blocked_smoke(client: TestClient) -> None:
    """A recent blocked / auth-failed smoke must flip the provider to red."""
    status_file: Path = client._status_file  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc)
    _write_smoke(
        status_file,
        {
            "deepseek": _blocked_record(
                "deepseek",
                ts_utc=_iso(now),
                reason="Provider deepseek returned HTTP 401: authentication failed",
            ),
        },
    )
    deepseek = _provider(_get_health(client), "deepseek")
    assert deepseek["status"] == "red"
    assert deepseek.get("blocked_reason", "").startswith("Provider deepseek returned HTTP 401")


def test_providers_health_response_never_exposes_api_key(client: TestClient) -> None:
    """Even with the env API key set, the response body must not echo it."""
    status_file: Path = client._status_file  # type: ignore[attr-defined]
    _write_smoke(
        status_file,
        {"minimax": _ready_record("minimax", ts_utc=_iso(datetime.now(timezone.utc)))},
    )
    body = client.get("/api/providers/health").text
    assert "test-key-redacted" not in body
