"""W17 — integration tests for /api/mcp/locks (W17-NEW-A6 finding).

Covers:
- Honest-blocked envelope when the orchestrator state dir is absent
  (``reason="mcp_server_unreachable"``).
- Real proxy mode: when ``.hermes3d_orchestrator/locks/<id>.lockdir/
  metadata.json`` files are present, the route enumerates them with the
  documented LockItem schema (lock_id, owner, files, ttl_remaining).
- Garbage / partial lock dirs are skipped, not 5xx'd.
- ttl_remaining_seconds reflects ``expires_utc`` minus now, clamped to
  zero for stale locks.
- Route is wired into ``create_gui_app``.

References:
- FastAPI bigger-applications router contract:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- HermesProof lock manager schema (``src/core/lock-manager.mjs``):
  one ``metadata.json`` per ``<lock_id>.lockdir`` under the workspace
  ``.hermes3d_orchestrator/locks/`` directory.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """Isolated FastAPI TestClient with a tmp DB and tmp orchestrator dir."""
    db_path = tmp_path / "hermes3d.db"
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    # Redirect the mcp_locks route to a tmp orchestrator state dir so the
    # test does not read the real workspace's live locks (those are
    # transient and would make the test flaky).
    from hermes3d.api.routes import mcp_locks as route_module

    tmp_locks_dir = tmp_path / ".hermes3d_orchestrator" / "locks"

    monkeypatch.setattr(
        route_module,
        "_orchestrator_locks_dir",
        lambda: tmp_locks_dir,
    )

    from hermes3d.api.app import create_gui_app

    return TestClient(create_gui_app())


def _write_lock(
    locks_dir: Path,
    *,
    lock_id: str,
    owner: str,
    file: str,
    expires_in_seconds: int = 3600,
    role: str = "agent",
    task_id: str | None = "TEST-TASK",
    reason: str = "test reason",
) -> Path:
    """Write a metadata.json that mirrors lock-manager.mjs output."""
    lockdir = locks_dir / f"{lock_id}.lockdir"
    lockdir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=expires_in_seconds)
    payload = {
        "lock_id": lock_id,
        "file": file,
        "owner": owner,
        "role": role,
        "task_id": task_id,
        "reason": reason,
        "acquired_utc": now.isoformat().replace("+00:00", "Z"),
        "heartbeat_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_utc": expires.isoformat().replace("+00:00", "Z"),
        "history": [
            {
                "ts_utc": now.isoformat().replace("+00:00", "Z"),
                "type": "acquired",
                "owner": owner,
                "task_id": task_id,
                "reason": reason,
            }
        ],
    }
    (lockdir / "metadata.json").write_text(json.dumps(payload), encoding="utf-8")
    return lockdir


# ---------------------------------------------------------------------------
# Honest-blocked when orchestrator dir absent
# ---------------------------------------------------------------------------


def test_mcp_locks_returns_unknown_when_orchestrator_dir_absent(
    client: TestClient,
) -> None:
    """No state dir on disk → ``mcp_server_unreachable`` envelope."""
    resp = client.get("/api/mcp/locks")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted"] is False
    assert body["status"] == "unknown"
    assert body["reason"] == "mcp_server_unreachable"
    assert body["items"] == []
    assert body["total"] == 0


def test_mcp_locks_envelope_shape_matches_contract(client: TestClient) -> None:
    body = client.get("/api/mcp/locks").json()
    for field in ("accepted", "status", "reason", "items", "total"):
        assert field in body, f"missing envelope field {field!r}"
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)


# ---------------------------------------------------------------------------
# Real proxy mode — populated lock dir
# ---------------------------------------------------------------------------


def test_mcp_locks_returns_real_items_when_locks_present(
    client: TestClient, tmp_path: Path
) -> None:
    locks_dir = tmp_path / ".hermes3d_orchestrator" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    _write_lock(
        locks_dir,
        lock_id="abc123",
        owner="claude-test-agent",
        file="03_implementation/src/hermes3d/api/routes/mcp_locks.py",
        expires_in_seconds=3600,
    )
    _write_lock(
        locks_dir,
        lock_id="def456",
        owner="codex-other-agent",
        file="03_implementation/src/hermes3d/api/app.py",
        expires_in_seconds=1800,
    )

    resp = client.get("/api/mcp/locks")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted"] is True
    assert body["status"] == "ready"
    assert body["total"] == 2
    assert len(body["items"]) == 2

    by_id = {item["lock_id"]: item for item in body["items"]}
    assert "abc123" in by_id
    assert "def456" in by_id

    item = by_id["abc123"]
    assert item["owner"] == "claude-test-agent"
    assert item["files"] == ["03_implementation/src/hermes3d/api/routes/mcp_locks.py"]
    assert item["role"] == "agent"
    assert item["task_id"] == "TEST-TASK"
    assert item["is_stale"] is False
    assert isinstance(item["ttl_remaining_seconds"], int)
    assert 0 < item["ttl_remaining_seconds"] <= 3600


def test_mcp_locks_marks_expired_lock_as_stale_with_zero_ttl(
    client: TestClient, tmp_path: Path
) -> None:
    locks_dir = tmp_path / ".hermes3d_orchestrator" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    _write_lock(
        locks_dir,
        lock_id="expired",
        owner="stale-owner",
        file="some/file.py",
        expires_in_seconds=-60,
    )

    body = client.get("/api/mcp/locks").json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["lock_id"] == "expired"
    assert item["is_stale"] is True
    assert item["ttl_remaining_seconds"] == 0


def test_mcp_locks_skips_malformed_metadata(client: TestClient, tmp_path: Path) -> None:
    """Garbage in one lockdir must not break the listing of healthy locks."""
    locks_dir = tmp_path / ".hermes3d_orchestrator" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)

    # Good lock.
    _write_lock(
        locks_dir,
        lock_id="good",
        owner="claude-good",
        file="good.py",
    )
    # Lockdir with corrupt JSON.
    bad_dir = locks_dir / "bad.lockdir"
    bad_dir.mkdir()
    (bad_dir / "metadata.json").write_text("{not valid json", encoding="utf-8")
    # Lockdir with no metadata.json at all.
    (locks_dir / "empty.lockdir").mkdir()
    # Lockdir with wrong-shape metadata (missing required fields).
    shape_dir = locks_dir / "shape.lockdir"
    shape_dir.mkdir()
    (shape_dir / "metadata.json").write_text(json.dumps({"foo": "bar"}), encoding="utf-8")

    resp = client.get("/api/mcp/locks")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["lock_id"] == "good"


def test_mcp_locks_ignores_non_lockdir_entries(client: TestClient, tmp_path: Path) -> None:
    """Stray files / unrelated directories must be ignored."""
    locks_dir = tmp_path / ".hermes3d_orchestrator" / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)
    _write_lock(
        locks_dir,
        lock_id="real",
        owner="claude-real",
        file="real.py",
    )
    # Stray plain file.
    (locks_dir / "readme.txt").write_text("not a lock", encoding="utf-8")
    # Stray non-.lockdir directory.
    (locks_dir / "scratch").mkdir()

    body = client.get("/api/mcp/locks").json()
    assert body["total"] == 1
    assert body["items"][0]["lock_id"] == "real"


# ---------------------------------------------------------------------------
# Wire-up sanity
# ---------------------------------------------------------------------------


def test_mcp_locks_route_is_registered() -> None:
    """create_gui_app must include /api/mcp/locks."""
    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    paths = {route.path for route in app.routes}
    assert "/api/mcp/locks" in paths


def test_mcp_locks_never_returns_5xx_for_missing_dir(client: TestClient) -> None:
    """The diagnostic route MUST be robust — always 200, never 5xx."""
    resp = client.get("/api/mcp/locks")
    assert resp.status_code == 200
    assert resp.status_code < 500
