"""W18-A21 (2026-05-11): /api/code-operator/teams/team-tasks read-only endpoint.

The Hermes Agent code-operator writes proof_events rows of kind
``code_provider.coding_plan`` / ``code_provider.code_review`` whenever the
MiniMax-builders or DeepSeek-reviewers teams produce work. The #agents GUI
needs to render these so operators can see that real team tasks ran. The
new ``/api/code-operator/teams/team-tasks`` endpoint exposes the most
recent rows in a stable, public-safe shape.

These tests verify:

1. Empty proof_events -> empty items list and a count of 0; never raises.
2. A coding_plan + code_review row -> both appear newest-first with the
   provider_id, team_id, task_id, and response_sha256 echoed.
3. ``limit`` query is honored and clamped to [1, 100].
4. Non-team event_types in proof_events are filtered out.
5. The ``provider-smoke-history`` companion endpoint reads the local
   smoke-status JSON file.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    db_path = tmp_path / "hermes3d.db"
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    from hermes3d.api.app import create_gui_app

    return TestClient(create_gui_app())


def _insert_proof_event(
    *, event_type: str, source_agent: str, payload: dict, created_at: str | None = None
) -> str:
    from hermes3d.api.routes._common import as_json, execute, new_id

    event_id = new_id()
    if created_at is None:
        execute(
            "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
            (event_id, event_type, source_agent, as_json(payload)),
        )
    else:
        execute(
            "INSERT INTO proof_events (id, event_type, source_agent, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (event_id, event_type, source_agent, as_json(payload), created_at),
        )
    return event_id


def test_team_tasks_empty_returns_zero_items(client: TestClient) -> None:
    response = client.get("/api/code-operator/teams/team-tasks")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 0
    assert body["items"] == []
    assert "code_provider.coding_plan" in body["supported_event_types"]
    assert "code_provider.code_review" in body["supported_event_types"]


def test_team_tasks_returns_coding_and_review_rows(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    coding_id = _insert_proof_event(
        event_type="code_provider.coding_plan",
        source_agent="hermes-agent",
        payload={
            "task_id": "W18-A21-PROVIDER-SMOKE-INTEG",
            "run_id": "run-1",
            "team_id": "minimax-builders",
            "provider_id": "minimax",
            "files": ["03_implementation/ROADMAP.md"],
            "prompt_sha256": "a" * 64,
            "response_sha256": "b" * 64,
        },
        created_at=now.replace(microsecond=0).isoformat(sep=" "),
    )
    review_id = _insert_proof_event(
        event_type="code_provider.code_review",
        source_agent="hermes-agent",
        payload={
            "task_id": "W18-A21-PROVIDER-SMOKE-INTEG",
            "run_id": "run-2",
            "team_id": "deepseek-reviewers",
            "provider_id": "deepseek",
            "files": ["03_implementation/ROADMAP.md"],
            "prompt_sha256": "c" * 64,
            "response_sha256": "d" * 64,
        },
    )
    response = client.get("/api/code-operator/teams/team-tasks?limit=10")
    body = response.json()
    assert body["count"] == 2
    ids = {item["id"] for item in body["items"]}
    assert ids == {coding_id, review_id}
    by_id = {item["id"]: item for item in body["items"]}
    assert by_id[coding_id]["team_id"] == "minimax-builders"
    assert by_id[coding_id]["provider_id"] == "minimax"
    assert by_id[coding_id]["run_type"] == "coding_plan"
    assert by_id[coding_id]["response_sha256"] == "b" * 64
    assert by_id[coding_id]["task_id"] == "W18-A21-PROVIDER-SMOKE-INTEG"
    assert by_id[review_id]["team_id"] == "deepseek-reviewers"
    assert by_id[review_id]["provider_id"] == "deepseek"
    assert by_id[review_id]["run_type"] == "code_review"


def test_team_tasks_filters_non_team_event_types(client: TestClient) -> None:
    _insert_proof_event(
        event_type="code_git.committed",
        source_agent="hermes-agent",
        payload={"task_id": "noise"},
    )
    _insert_proof_event(
        event_type="voice.tts.synthesized",
        source_agent="hermes-agent",
        payload={"audio_base64": ""},
    )
    _insert_proof_event(
        event_type="code_provider.coding_plan",
        source_agent="hermes-agent",
        payload={"team_id": "minimax-builders", "provider_id": "minimax"},
    )
    body = client.get("/api/code-operator/teams/team-tasks").json()
    assert body["count"] == 1
    assert body["items"][0]["team_id"] == "minimax-builders"


def test_team_tasks_limit_clamped(client: TestClient) -> None:
    for index in range(5):
        _insert_proof_event(
            event_type="code_provider.coding_plan",
            source_agent="hermes-agent",
            payload={
                "task_id": f"W18-A21-LIMIT-{index}",
                "team_id": "minimax-builders",
                "provider_id": "minimax",
            },
        )
    body = client.get("/api/code-operator/teams/team-tasks?limit=2").json()
    assert body["count"] == 2
    # Even at limit=1000 the endpoint clamps and stays responsive.
    body_big = client.get("/api/code-operator/teams/team-tasks?limit=1000").json()
    assert body_big["count"] == 5


def test_provider_smoke_history_reads_local_status_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The smoke-history companion endpoint reads the var/code-history file."""
    smoke_root = tmp_path / "var" / "code-history"
    smoke_root.mkdir(parents=True, exist_ok=True)
    smoke_file = smoke_root / "provider-smoke-status.json"
    now = _iso(datetime.now(timezone.utc))
    smoke_file.write_text(
        json.dumps(
            {
                "schema": 1,
                "updated_at": now,
                "providers": {
                    "minimax": {
                        "provider_id": "minimax",
                        "accepted": True,
                        "status": "ready",
                        "ts_utc": now,
                        "blocked_reasons": [],
                        "auth_contract": {
                            "base_url_label": "api.minimax.io",
                            "model": "minimax-text-01",
                        },
                        "content_sha256": "f" * 64,
                        "evidence_id": "ev_w18a21_smoke",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    from hermes3d.services import code_history

    monkeypatch.setattr(code_history, "IMPLEMENTATION_ROOT", tmp_path)

    response = client.get("/api/code-operator/teams/provider-smoke-history")
    body = response.json()
    assert response.status_code == 200, response.text
    assert body["count"] == 1
    item = body["items"][0]
    assert item["provider_id"] == "minimax"
    assert item["status"] == "ready"
    assert item["evidence_id"] == "ev_w18a21_smoke"
    assert item["model"] == "minimax-text-01"
