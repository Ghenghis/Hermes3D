"""W21-A4 MVP-2 — integration tests: route + poller + persona dispatch.

Mission: drive the FastAPI app end-to-end and prove
  1. ``GET /api/agents/queue/status`` returns the live filesystem snapshot.
  2. ``POST /api/agents/queue/claim/{task_id}`` claims a real task on disk.
  3. The auto-poller ``tick_once()`` claims a matching pending task for an
     idle persona within ONE tick.
  4. A persona that does NOT match the ``target_owner_pattern`` is rejected
     with a 400, not silently allowed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A backend rooted at tmp_path so we control the queue contents."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    # Disable the auto-poller in this fixture so tests can drive ticks
    # synchronously without races. The poller is exercised separately
    # in test_poller_tick_once_claims_matching_task below.
    monkeypatch.setenv("HERMES3D_QUEUE_POLLER_DISABLED", "1")

    db_path = tmp_path / "hermes3d.db"
    # Force-reload app so the new HERMES3D_WORKSPACE_ROOT is picked up.
    for mod_name in list(sys.modules):
        if mod_name.startswith("hermes3d.api.app") or mod_name.startswith("hermes3d.api.routes"):
            sys.modules.pop(mod_name, None)
    sys.modules.pop("hermes3d.config.env_loader", None)
    sys.modules.pop("hermes3d.services.queue_bridge", None)
    sys.modules.pop("hermes3d.services.queue_poller", None)
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    import importlib

    app_mod = importlib.import_module("hermes3d.api.app")
    return TestClient(app_mod.create_gui_app())


def _seed_task(
    root: Path,
    task_id: str,
    *,
    state: str = "pending",
    target_owner_pattern: str = "factory-operator|oliver-qa-agent",
    priority: int = 100,
) -> Path:
    state_dir = root / ".hermes3d_orchestrator" / "tasks" / state
    state_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "task_schema_version": 1,
        "task_id": task_id,
        "title": f"int test {task_id}",
        "summary": "fake integration task",
        "target_owner_pattern": target_owner_pattern,
        "priority": priority,
        "claimed_by": None,
        "claimed_utc": None,
        "heartbeat_utc": None,
        "done_utc": None,
        "blocked_reason": None,
    }
    path = state_dir / f"{task_id}.json"
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# GET /api/agents/queue/status
# ---------------------------------------------------------------------------


def test_queue_status_returns_empty_when_no_tasks(client: TestClient) -> None:
    resp = client.get("/api/agents/queue/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted"] is True
    assert body["counts"] == {"pending": 0, "claimed": 0, "done": 0, "blocked": 0}
    assert body["pending"] == []


def test_queue_status_lists_seeded_tasks(client: TestClient, tmp_path: Path) -> None:
    _seed_task(tmp_path, "T1")
    _seed_task(tmp_path, "T2", priority=50)
    body = client.get("/api/agents/queue/status").json()
    assert body["counts"]["pending"] == 2
    ids = {t["task_id"] for t in body["pending"]}
    assert ids == {"T1", "T2"}


# ---------------------------------------------------------------------------
# POST /api/agents/queue/claim/{task_id}
# ---------------------------------------------------------------------------


def test_claim_via_route_moves_task_and_records_owner(client: TestClient, tmp_path: Path) -> None:
    _seed_task(tmp_path, "T1", target_owner_pattern="factory-operator")
    resp = client.post(
        "/api/agents/queue/claim/T1",
        json={"persona": "factory-operator"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted"] is True
    assert body["task"]["claimed_by"] == "hermes/factory-operator"
    # File moved on disk.
    claimed_path = tmp_path / ".hermes3d_orchestrator" / "tasks" / "claimed" / "T1.json"
    assert claimed_path.exists()
    body = client.get("/api/agents/queue/status").json()
    assert body["counts"]["pending"] == 0
    assert body["counts"]["claimed"] == 1


def test_claim_rejects_wrong_persona_with_400(client: TestClient, tmp_path: Path) -> None:
    _seed_task(tmp_path, "T1", target_owner_pattern="factory-operator|oliver-qa-agent")
    resp = client.post(
        "/api/agents/queue/claim/T1",
        json={"persona": "modeling-agent"},
    )
    assert resp.status_code == 400, resp.text
    detail = resp.json()["detail"]
    assert detail["accepted"] is False
    assert "target_owner_pattern" in detail["reason"]


def test_claim_returns_404_when_task_missing(client: TestClient) -> None:
    resp = client.post(
        "/api/agents/queue/claim/does_not_exist",
        json={"persona": "factory-operator"},
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Poller tick — proves the auto-claim path works
# ---------------------------------------------------------------------------


def test_poller_tick_once_claims_matching_task(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """tick_once() must claim a single pending task that matches a real
    persona id from the PERSONAS roster. This is the core proof that
    the auto-poller will pick up real W21 tasks in production."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    # Re-import to pick up the new env var.
    sys.modules.pop("hermes3d.services.queue_poller", None)
    from hermes3d.services import queue_poller

    # The real PERSONAS roster includes factory-operator; seed a matching task.
    _seed_task(
        tmp_path,
        "W21-A4-TEST-AUTOCLAIM",
        target_owner_pattern="factory-operator",
    )
    report = queue_poller.tick_once()
    assert report["pending_seen"] == 1
    assert report["claimed"] == 1
    # The task file moved to claimed/.
    claimed_path = (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "claimed" / "W21-A4-TEST-AUTOCLAIM.json"
    )
    assert claimed_path.exists()
    body = json.loads(claimed_path.read_text(encoding="utf-8"))
    assert body["claimed_by"] == "hermes/factory-operator"


def test_poller_tick_skips_unmatchable_task(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A task whose target_owner_pattern matches no persona stays pending."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    sys.modules.pop("hermes3d.services.queue_poller", None)
    from hermes3d.services import queue_poller

    _seed_task(
        tmp_path,
        "W21-A4-TEST-NO-MATCH",
        target_owner_pattern="not-a-real-persona",
    )
    report = queue_poller.tick_once()
    assert report["pending_seen"] == 1
    assert report["claimed"] == 0
    # Still in pending/.
    assert (
        tmp_path / ".hermes3d_orchestrator" / "tasks" / "pending" / "W21-A4-TEST-NO-MATCH.json"
    ).exists()


def test_poller_tick_respects_max_claims_per_tick(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If MAX_CLAIMS_PER_TICK is 1, only one task is claimed per tick even
    when many match — this prevents one persona from starving the queue."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("HERMES3D_QUEUE_MAX_CLAIMS_PER_TICK", "1")
    sys.modules.pop("hermes3d.services.queue_poller", None)
    from hermes3d.services import queue_poller

    for i in range(5):
        _seed_task(
            tmp_path,
            f"W21-MULTI-{i}",
            target_owner_pattern="factory-operator",
            priority=100 - i,
        )
    report = queue_poller.tick_once()
    assert report["pending_seen"] == 5
    assert report["claimed"] == 1


def test_poller_heartbeats_our_claimed_tasks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A task we already claimed in a prior tick should receive a
    heartbeat refresh on the next tick — the orchestrator uses this to
    avoid considering live claims stale."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    sys.modules.pop("hermes3d.services.queue_poller", None)
    from hermes3d.services import queue_poller

    # Manually seed a claimed task as if a prior tick had taken it.
    state_dir = tmp_path / ".hermes3d_orchestrator" / "tasks" / "claimed"
    state_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "task_schema_version": 1,
        "task_id": "W21-PRIOR-CLAIM",
        "title": "prior claim",
        "summary": "",
        "target_owner_pattern": "factory-operator",
        "priority": 50,
        "claimed_by": "hermes/factory-operator",
        "claimed_utc": "2026-01-01T00:00:00.000000Z",
        "heartbeat_utc": "2026-01-01T00:00:00.000000Z",
        "done_utc": None,
        "blocked_reason": None,
    }
    (state_dir / "W21-PRIOR-CLAIM.json").write_text(json.dumps(body, indent=2), encoding="utf-8")

    report = queue_poller.tick_once()
    assert report["heartbeats"] >= 1
    new_body = json.loads((state_dir / "W21-PRIOR-CLAIM.json").read_text(encoding="utf-8"))
    # The heartbeat is later than the original 2026-01-01.
    assert new_body["heartbeat_utc"] > "2026-01-01T00:00:00.000000Z"
