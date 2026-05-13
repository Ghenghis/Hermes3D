"""Runtime source identity is visible in health surfaces.

The desktop backend can keep running from an old checkout after develop
moves on. These tests make the source root / git fingerprint observable and
allow launchers or smoke checks to fail when an expected checkout is not the
one serving requests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.delenv("HERMES3D_EXPECTED_REPO_ROOT", raising=False)
    monkeypatch.delenv("HERMES3D_EXPECTED_SOURCE_ROOT", raising=False)
    monkeypatch.delenv("HERMES3D_EXPECTED_GIT_BRANCH", raising=False)
    monkeypatch.delenv("HERMES3D_EXPECTED_GIT_SHA", raising=False)
    monkeypatch.delenv("HERMES3D_EXPECTED_COMMIT", raising=False)

    from hermes3d.api.routes import desktop_compat
    from hermes3d.api.routes import system as system_route
    from hermes3d.db import init as db_init

    db_path = tmp_path / "hermes3d.db"
    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    monkeypatch.setattr(system_route, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    monkeypatch.setattr(desktop_compat, "_runtime_url", lambda: "http://127.0.0.1:1234")
    monkeypatch.setattr(
        desktop_compat,
        "runtime_probe",
        lambda: {
            "ready": True,
            "status": "ready",
            "model": "test-model",
            "reason": "stubbed runtime ready",
        },
    )

    from hermes3d.api.app import create_gui_app

    return TestClient(create_gui_app())


def test_health_exposes_runtime_source_identity(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200, response.text
    body = response.json()
    identity = body["runtime_identity"]
    assert identity["repo_root"] == str(REPO_ROOT)
    assert identity["implementation_root"] == str(REPO_ROOT / "03_implementation")
    assert identity["commit"] != "unknown"
    assert identity["branch"] != "unknown"
    assert identity["backend_source"].endswith("runtime_identity.py")
    assert "expected" in identity


def test_system_snapshot_includes_runtime_source_identity(client: TestClient) -> None:
    response = client.get("/api/system/snapshot")
    assert response.status_code == 200, response.text
    body = response.json()
    identity = body["runtime_identity"]
    assert body["database"]["path"]
    assert identity["repo_root"] == str(REPO_ROOT)
    assert identity["commit"] != "unknown"


def test_expected_repo_mismatch_marks_runtime_stale(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wrong_root = tmp_path / "wrong-checkout"
    monkeypatch.setenv("HERMES3D_EXPECTED_REPO_ROOT", str(wrong_root))

    identity = client.get("/api/system/runtime-identity").json()
    assert identity["status"] == "stale"
    assert identity["fresh"] is False
    assert identity["stale"] is True
    assert "repo_root" in identity["mismatches"]
    assert identity["expected"]["repo_root"] == str(wrong_root)

    health = client.get("/health").json()
    assert health["status"] == "degraded"
    assert health["runtime_identity"]["status"] == "stale"

    snapshot = client.get("/api/system/snapshot").json()
    assert snapshot["runtime_identity"]["status"] == "stale"
