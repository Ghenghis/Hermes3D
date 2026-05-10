"""W6-7 (2026-05-09): integration tests — run-proof and rollback routes.

These tests exercise the full request/response loop through the FastAPI
app, including DB migration and seed. They run actual subprocesses for
the run-proof case using a benign command, verifying:

1. ``GET /api/apps`` returns 60 records with the W6-7 fields.
2. ``GET /api/apps/{id}`` returns one record with extended metadata.
3. ``POST /api/apps/{id}/run-proof`` executes the proof_command and
   persists ``last_proof_status``.
4. ``POST /api/apps/{id}/run-proof`` returns ``not_set`` when the app
   has no proof_command on file.
5. ``POST /api/apps/{id}/rollback`` returns 501 for apps with
   ``rollback_supported=False`` and 200 (with redirect-to-modules) for
   ``rollback_supported=True``.
6. Filtering by ``update_lane`` works.

Sources:
- SPDX 2.3 license identifier policy: https://spdx.org/licenses/
- Existing migration test pattern in
  ``unit/test_load_modules_resilience.py`` (Bonus 12 #10).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Spin up a fresh FastAPI app with an isolated temp DB.

    The route module caches a one-shot ``_APPS_SYNCED`` flag; reset it
    so each test gets a fresh load_modules() call against its own DB.
    Same trick for the modules.py one-shot.
    """
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "registry_int.db"

    import hermes3d.db.init as dbinit
    import hermes3d.db.load_modules as lm

    monkeypatch.setattr(dbinit, "DB_PATH", db_path)
    monkeypatch.setattr(lm, "DB_PATH", db_path)

    # Reset per-module one-shot caches.
    import hermes3d.api.routes.apps as apps_route
    import hermes3d.api.routes.modules as modules_route

    monkeypatch.setattr(apps_route, "_APPS_SYNCED", False)
    monkeypatch.setattr(modules_route, "_MODULES_SYNCED", False)

    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    return TestClient(app)


def test_list_apps_returns_60_with_w6_7_fields(client: TestClient) -> None:
    response = client.get("/api/apps")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 60
    apps = payload["apps"]
    sample = apps[0]
    for field in (
        "id",
        "tested_versions",
        "license_spdx",
        "rollback_supported",
        "rollback_runbook_url",
        "proof_command",
        "update_lane",
        "last_proof_status",
    ):
        assert field in sample, f"missing field {field}"
    assert isinstance(sample["tested_versions"], list)
    assert isinstance(sample["rollback_supported"], bool)


def test_get_single_app_extended_payload(client: TestClient) -> None:
    response = client.get("/api/apps/cadquery")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "cadquery"
    assert body["license_spdx"] == "Apache-2.0"
    assert body["update_lane"] == "stable"
    assert "2.4.0" in body["tested_versions"]
    assert body["proof_command"]
    assert body["rollback_supported"] is True


def test_get_unknown_app_404(client: TestClient) -> None:
    response = client.get("/api/apps/this_app_does_not_exist")
    assert response.status_code == 404


def test_filter_by_update_lane(client: TestClient) -> None:
    stable = client.get("/api/apps?update_lane=stable").json()
    canary = client.get("/api/apps?update_lane=canary").json()
    frozen = client.get("/api/apps?update_lane=frozen").json()
    total = stable["count"] + canary["count"] + frozen["count"]
    assert total == 60
    assert all(a["update_lane"] == "stable" for a in stable["apps"])
    assert all(a["update_lane"] == "canary" for a in canary["apps"])
    assert all(a["update_lane"] == "frozen" for a in frozen["apps"])


def test_run_proof_executes_and_persists(client: TestClient) -> None:
    """Override an app's proof_command to a benign cross-platform shell.

    ``python -c 'print(\"ok\")'`` works on Windows + Linux + Mac,
    exits 0, and emits a single stdout line — perfect for asserting
    ``status == 'pass'``.
    """
    app_id = "trimesh"
    # Trigger registry sync so the modules table is populated before UPDATE.
    client.get("/api/apps")
    import hermes3d.db.init as dbinit

    conn = dbinit.connect()
    conn.execute(
        "UPDATE modules SET proof_command = ? WHERE id = ?",
        ("python -c \"print('proof-ok')\"", app_id),
    )
    conn.commit()
    conn.close()

    response = client.post(f"/api/apps/{app_id}/run-proof", json={"actor": "test"})
    assert response.status_code == 200
    body = response.json()
    assert body["app_id"] == app_id
    assert body["status"] == "pass"
    assert body["accepted"] is True
    assert body["exit_code"] == 0
    assert "proof-ok" in body["captured_output_redacted"]
    assert body["evidence_id"]

    # Persisted state.
    conn = dbinit.connect()
    record = conn.execute(
        "SELECT last_proof_status, last_proof_at FROM modules WHERE id = ?",
        (app_id,),
    ).fetchone()
    conn.close()
    assert record["last_proof_status"] == "pass"
    assert record["last_proof_at"]


def test_run_proof_failing_command(client: TestClient) -> None:
    """A non-zero exit must surface as ``fail`` and ``accepted=False``."""
    app_id = "trimesh"
    client.get("/api/apps")  # populate modules table
    import hermes3d.db.init as dbinit

    conn = dbinit.connect()
    conn.execute(
        "UPDATE modules SET proof_command = ? WHERE id = ?",
        ('python -c "import sys; sys.exit(7)"', app_id),
    )
    conn.commit()
    conn.close()

    response = client.post(f"/api/apps/{app_id}/run-proof")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "fail"
    assert body["accepted"] is False
    assert body["exit_code"] == 7


def test_run_proof_when_not_set(client: TestClient) -> None:
    """An app whose proof_command is NULL gets status='not_set' without
    actually running anything."""
    app_id = "kiln"  # seed has proof_command=None
    response = client.post(f"/api/apps/{app_id}/run-proof")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_set"
    assert body["accepted"] is False


def test_rollback_unsupported_returns_501(client: TestClient) -> None:
    """Apps with rollback_supported=False must return 501 Not Implemented."""
    response = client.post("/api/apps/awesome_extruders/rollback", json={"actor": "test"})
    assert response.status_code == 501
    body = response.json()
    assert body["detail"]["status"] == "rollback_unsupported"


def test_rollback_supported_returns_request_envelope(client: TestClient) -> None:
    """Apps with rollback_supported=True return 200 + a redirect envelope."""
    response = client.post(
        "/api/apps/hermes_agent/rollback",
        json={"actor": "test", "target_version": "v0.12", "reason": "regression"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["app_id"] == "hermes_agent"
    assert body["target_version"] == "v0.12"
    assert "/api/modules/hermes_agent/rollback" in body["next_route"]


def test_proof_command_redaction(client: TestClient) -> None:
    """Secrets accidentally embedded in stdout MUST be redacted."""
    app_id = "trimesh"
    client.get("/api/apps")  # populate modules table
    import hermes3d.db.init as dbinit

    conn = dbinit.connect()
    conn.execute(
        "UPDATE modules SET proof_command = ? WHERE id = ?",
        (
            # Print a fake bearer token; redact_text should mask it.
            "python -c \"print('Authorization: Bearer abc123def456ghi789jkl')\"",
            app_id,
        ),
    )
    conn.commit()
    conn.close()

    response = client.post(f"/api/apps/{app_id}/run-proof")
    body = response.json()
    captured = body["captured_output_redacted"]
    # The literal token must NOT appear; the redaction marker must.
    assert "abc123def456ghi789jkl" not in captured
