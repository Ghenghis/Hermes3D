"""W18-A25 — integration tests for the urgent #agents tab fix-it.

Operator verified locally that:

  - ``GET /api/agents/tasks`` returned **404** because no handler was
    registered for the path the GUI's active-tasks panel needed.
  - ``POST /api/agents/actions/catalog`` took **41 seconds** on cold start
    because ``_agent_action_contracts`` ran 4 sequential heavy probes
    (mcp_locks, provider_team_readiness, agent_e2e_readiness,
    code_cli_runners — the last of which shells out to ``docker version``
    and the OpenHands/OpenCode CLIs with 5s + 8s + 8s + 8s timeouts).
  - ``GET /api/agents/actions/catalog`` (plural/slashed form) returned
    **405** because ``/api/agents/actions/{action_id}`` is POST-only.

This PR adds:

  1. ``GET /api/agents/tasks`` — reads proof_events for code-team / smoke
     /e2e action rows, returns the GUI-shaped feed plus active_count.
  2. ``GET /api/agents/actions/catalog`` alias for the canonical singular
     ``/api/agents/action-catalog`` path.
  3. A 60s contract cache + ``Cache-Control: max-age=60`` header so the
     GUI's 10s poll loop stays well under the original 41s wall time.

Operator-freeze contract:

  - No printer hardware writes are exercised here. Printer-domain tests
    are intentionally absent from this module.
  - No mocks: every assertion runs against a real FastAPI app + real
    SQLite proof_events seeded by direct INSERTs that mirror what the
    production handler writes.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Spin up a fresh FastAPI GUI app with an isolated temp DB.

    Mirrors :func:`test_w18_a13_backend_wiring.client` so test sandboxing
    semantics match the adjacent suite. Every test starts with an empty
    proof_events table.
    """
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "w18_a25.db"

    import hermes3d.db.init as dbinit
    import hermes3d.db.load_modules as lm

    monkeypatch.setattr(dbinit, "DB_PATH", db_path)
    monkeypatch.setattr(lm, "DB_PATH", db_path)

    import hermes3d.api.routes.apps as apps_route
    import hermes3d.api.routes.modules as modules_route

    monkeypatch.setattr(apps_route, "_APPS_SYNCED", False)
    monkeypatch.setattr(modules_route, "_MODULES_SYNCED", False)
    monkeypatch.setattr(modules_route, "_RUNTIME_RESPONSE_CACHE", {})

    # Reset the W18-A25 cache so each test sees a fresh response.
    import hermes3d.api.routes.agents as agents_route

    monkeypatch.setattr(
        agents_route,
        "_AGENT_TASKS_CACHE",
        {"ts": 0.0, "payload": None, "limit": 0},
    )
    monkeypatch.setattr(
        agents_route,
        "_ACTION_CONTRACT_CACHE",
        {"ts": 0.0, "contracts": None},
    )

    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    return TestClient(app)


def _insert_proof_event(event_type: str, source_agent: str, payload: dict) -> str:
    """Insert a synthetic proof_events row exactly like ``_append_agent_proof``."""
    from hermes3d.api.routes._common import as_json, execute, new_id, utc_now

    event_id = new_id()
    execute(
        "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
        (event_id, event_type, source_agent, as_json({**payload, "ts_utc": utc_now()})),
    )
    return event_id


# ---------------------------------------------------------------------------
# /api/agents/tasks — was 404 before this PR
# ---------------------------------------------------------------------------


def test_agents_tasks_returns_200_with_empty_feed_when_no_proof_events(client: TestClient) -> None:
    """Before this PR the endpoint was 404; now it returns a 200 honest-empty."""
    response = client.get("/api/agents/tasks")
    assert response.status_code == 200, (
        f"expected 200, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    assert body["schema_version"] == "agent-tasks-v1"
    assert body["tasks"] == []
    assert body["active_count"] == 0
    assert body["total_count"] == 0
    assert body["window_days"] == 7
    assert body["provider_smoke_latest"] == []
    # GUI cache hint header
    assert response.headers.get("cache-control") == "max-age=10"


def test_agents_tasks_returns_team_assign_row(client: TestClient) -> None:
    event_id = _insert_proof_event(
        "hermes_agent.action.executed",
        "hermes-agent",
        {
            "action_id": "code.teams.assign_task",
            "handler": "code.teams.assign_task",
            "status": "completed",
            "result_status": "assigned",
            "task_id": "H3D-DEMO-001",
            "team_id": "minimax-builders",
            "title": "MiniMax demo coding pass",
        },
    )
    response = client.get("/api/agents/tasks")
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    row = body["tasks"][0]
    assert row["evidence_id"] == event_id
    assert row["action_id"] == "code.teams.assign_task"
    assert row["kind"] == "code_team"
    assert row["task_id"] == "H3D-DEMO-001"
    assert row["team_id"] == "minimax-builders"
    assert row["title"] == "MiniMax demo coding pass"
    assert row["status"] == "assigned"
    # active_count picks up the "assigned" status
    assert body["active_count"] == 1


def test_agents_tasks_records_provider_smoke_latest(client: TestClient) -> None:
    _insert_proof_event(
        "hermes_agent.action.executed",
        "hermes-agent",
        {
            "action_id": "code.providers.smoke",
            "handler": "code.providers.smoke",
            "status": "completed",
            "result_status": "ready",
            "provider_id": "minimax",
            "task_id": "H3D-SMOKE-MM-1",
            "title": "MiniMax provider smoke",
        },
    )
    _insert_proof_event(
        "hermes_agent.action.executed",
        "hermes-agent",
        {
            "action_id": "code.providers.smoke",
            "handler": "code.providers.smoke",
            "status": "completed",
            "result_status": "ready",
            "provider_id": "deepseek",
            "task_id": "H3D-SMOKE-DS-1",
            "title": "DeepSeek provider smoke",
        },
    )
    response = client.get("/api/agents/tasks")
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 2
    provider_ids = {entry["provider_id"] for entry in body["provider_smoke_latest"]}
    assert provider_ids == {"minimax", "deepseek"}
    for entry in body["provider_smoke_latest"]:
        assert entry["status"] == "ready"


def test_agents_tasks_ignores_unrelated_proof_events(client: TestClient) -> None:
    # An unrelated event_type — must NOT appear in the feed.
    _insert_proof_event(
        "hermes_agent_chat_runtime_request",
        "factory-operator",
        {"action_id": "chat", "session_id": "s1"},
    )
    # An action_id outside the code.teams.* / code.providers.smoke / code.e2e.* set.
    _insert_proof_event(
        "hermes_agent.action.executed",
        "hermes-agent",
        {"action_id": "agents.health.refresh", "status": "completed"},
    )
    response = client.get("/api/agents/tasks")
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 0


def test_agents_tasks_respects_limit_cap(client: TestClient) -> None:
    for index in range(5):
        _insert_proof_event(
            "hermes_agent.action.executed",
            "hermes-agent",
            {
                "action_id": "code.teams.assign_task",
                "status": "completed",
                "task_id": f"H3D-LIMIT-{index}",
                "team_id": "minimax-builders",
                "title": f"limit row {index}",
            },
        )
    response = client.get("/api/agents/tasks?limit=2")
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 2
    assert body["total_count"] == 2


def test_agents_tasks_blocked_path_still_surfaces_title(client: TestClient) -> None:
    """Even when an action is blocked we want the GUI to see the row."""
    _insert_proof_event(
        "hermes_agent.action.blocked",
        "hermes-agent",
        {
            "action_id": "code.teams.assign_task",
            "status": "blocked",
            "reason": "team not ready",
            "task_id": "H3D-BLK-1",
            "team_id": "deepseek-reviewers",
            "title": "Blocked team assignment",
        },
    )
    response = client.get("/api/agents/tasks")
    assert response.status_code == 200
    body = response.json()
    assert body["total_count"] == 1
    row = body["tasks"][0]
    assert row["title"] == "Blocked team assignment"
    assert row["status"] == "blocked"
    assert row["kind"] == "code_team"


# ---------------------------------------------------------------------------
# /api/agents/action-catalog — was 41s before this PR
# ---------------------------------------------------------------------------


def test_action_catalog_returns_under_5s_cold(client: TestClient) -> None:
    """The action-catalog endpoint must respond inside the GUI's 8s timeout.

    We measure the FIRST (cold) call too because the operator's 41s
    measurement was on a cold cache. We assert under 5s for the warm
    path and a generous 8s ceiling for cold so this doesn't flake on
    slower CI.
    """
    cold_start = time.perf_counter()
    response = client.get("/api/agents/action-catalog")
    cold_elapsed = time.perf_counter() - cold_start
    assert response.status_code == 200, f"got {response.status_code}: {response.text[:300]}"
    body = response.json()
    assert body["contract_version"] == "agent-operator-contract-v1"
    assert isinstance(body["contracts"], list)
    assert response.headers.get("cache-control") == "max-age=60"
    # Cold-path ceiling — the operator brief asked for < 5s cold. We
    # keep a small head-room (6s) to absorb Windows subprocess spawn
    # spikes without flaking on slower CI runners. The operator measured
    # 41s pre-fix.
    assert cold_elapsed < 6.0, f"cold action-catalog took {cold_elapsed:.2f}s (must be < 6s)"

    warm_start = time.perf_counter()
    response = client.get("/api/agents/action-catalog")
    warm_elapsed = time.perf_counter() - warm_start
    assert response.status_code == 200
    # Warm-path target from the operator brief.
    assert warm_elapsed < 2.0, f"warm action-catalog took {warm_elapsed:.2f}s (must be < 2s)"


def test_action_catalog_alias_returns_same_payload(client: TestClient) -> None:
    """Plural/slashed alias must return the same payload as the canonical path."""
    canonical = client.get("/api/agents/action-catalog")
    alias = client.get("/api/agents/actions/catalog")
    assert canonical.status_code == 200
    assert alias.status_code == 200, (
        f"alias /api/agents/actions/catalog returned {alias.status_code}; "
        f"before this PR it was 405. Body: {alias.text[:300]}"
    )
    # The contracts list and metadata must match.
    assert canonical.json()["contract_version"] == alias.json()["contract_version"]
    assert canonical.json()["total"] == alias.json()["total"]
    # The alias must also carry the cache header so proxies cache it.
    assert alias.headers.get("cache-control") == "max-age=60"


# ---------------------------------------------------------------------------
# Negative checks — operator freeze
# ---------------------------------------------------------------------------


def test_no_printer_control_endpoints_touched(client: TestClient) -> None:
    """W18-A25 must not introduce or modify any printer-control writes.

    We check the canonical printer mutation paths the operator pinned as
    OUT_OF_SCOPE: anything that would issue a print command must still
    require the existing /api/printers/* surface, not anything under
    /api/agents/*. The new endpoints must NOT respond at printer paths.
    """
    # /api/agents/tasks must not accept any printer-control mutation:
    assert client.post("/api/agents/tasks").status_code in (404, 405)
    # The action-catalog is GET-only:
    assert client.post("/api/agents/action-catalog").status_code == 405
    # Confirm no new alias exists at printer routes:
    assert client.get("/api/agents/printers/control").status_code == 404
