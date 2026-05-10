"""W15 A20 — integration tests for the 4 new backend gap routes.

Covers:
- ``GET /api/skills`` — honest blocked envelope.
- ``GET /api/connectors`` — honest blocked envelope.
- ``GET /api/settings/themes`` — 6 real palettes from
  ``03_implementation/data/themes/``.
- ``GET /api/dashboard/layouts`` — empty list when no rows.
- ``POST /api/dashboard/layouts`` — round-trip persistence.

The tests must NOT depend on any fabricated readiness. Skills and
connectors specifically assert ``accepted=False`` so the UI lanes
(A11–A19) cannot accidentally rely on a fake list.

References:
- FastAPI bigger-applications router contract:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- OpenAPI design conventions for resource collections.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """Isolated FastAPI TestClient with a temp SQLite DB."""
    db_path = tmp_path / "hermes3d.db"
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    from hermes3d.api.app import create_gui_app

    return TestClient(create_gui_app())


# ---------------------------------------------------------------------------
# /api/skills — honest blocked envelope
# ---------------------------------------------------------------------------


def test_skills_route_is_registered_and_returns_honest_blocked(client: TestClient) -> None:
    resp = client.get("/api/skills")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is False
    assert body["status"] == "unknown"
    assert body["reason"] == "skill_registry_not_yet_implemented"
    assert body["items"] == []
    assert body["total"] == 0


def test_skills_route_response_shape_matches_pydantic_envelope(client: TestClient) -> None:
    body = client.get("/api/skills").json()
    for field in ("accepted", "status", "reason", "items", "total"):
        assert field in body, f"missing envelope field {field!r}"
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)


# ---------------------------------------------------------------------------
# /api/connectors — honest blocked envelope
# ---------------------------------------------------------------------------


def test_connectors_route_is_registered_and_returns_honest_blocked(
    client: TestClient,
) -> None:
    resp = client.get("/api/connectors")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is False
    assert body["status"] == "unknown"
    assert body["reason"] == "connector_registry_not_yet_implemented"
    assert body["items"] == []
    assert body["total"] == 0


def test_connectors_route_does_not_invent_connectors(client: TestClient) -> None:
    body = client.get("/api/connectors").json()
    # Tightest contract: list must be empty so UI agents cannot accidentally
    # render fake connector names like "mcp-foo" / "azure-bar".
    assert body["items"] == []
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# /api/settings/themes — 6 real palettes
# ---------------------------------------------------------------------------


EXPECTED_THEME_IDS = {
    "default",
    "cyberpunk",
    "matrix",
    "tron",
    "industrial_forge",
    "aurora_operator",
}


def test_themes_route_returns_six_named_palettes(client: TestClient) -> None:
    resp = client.get("/api/settings/themes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert body["status"] == "ready"
    assert body["total"] == 6
    ids = {item["id"] for item in body["items"]}
    assert ids == EXPECTED_THEME_IDS, (
        f"missing palettes: {EXPECTED_THEME_IDS - ids} | "
        f"unexpected: {ids - EXPECTED_THEME_IDS}"
    )


def test_themes_palettes_have_full_token_set(client: TestClient) -> None:
    body = client.get("/api/settings/themes").json()
    required_tokens = {
        "bg_root",
        "bg_panel",
        "bg_elevated",
        "fg_primary",
        "fg_secondary",
        "fg_muted",
        "accent_primary",
        "accent_secondary",
        "border_subtle",
        "border_strong",
        "status_success",
        "status_warning",
        "status_danger",
        "status_info",
        "highlight",
    }
    for item in body["items"]:
        token_keys = set(item["tokens"].keys())
        missing = required_tokens - token_keys
        assert not missing, (
            f"theme {item['id']!r} missing tokens: {missing}"
        )
        # Hex sanity: every token starts with '#' and is 7 chars.
        for token_name, token_value in item["tokens"].items():
            assert token_value.startswith("#"), (
                f"theme {item['id']!r} token {token_name!r} = "
                f"{token_value!r} is not a hex color"
            )
            assert len(token_value) == 7, (
                f"theme {item['id']!r} token {token_name!r} = "
                f"{token_value!r} is not a 6-digit hex color"
            )


def test_themes_each_palette_status_is_ready(client: TestClient) -> None:
    body = client.get("/api/settings/themes").json()
    for item in body["items"]:
        assert item["status"] == "ready", (
            f"theme {item['id']!r} status={item['status']!r} "
            f"reason={item.get('reason')!r} — palette file likely missing"
        )


# ---------------------------------------------------------------------------
# /api/dashboard/layouts — round-trip
# ---------------------------------------------------------------------------


def test_dashboard_layouts_empty_when_no_rows(client: TestClient) -> None:
    resp = client.get("/api/dashboard/layouts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert body["status"] == "ready"
    assert body["items"] == []
    assert body["total"] == 0


def test_dashboard_layouts_post_persists_and_get_returns_it(
    client: TestClient,
) -> None:
    payload = {
        "user_id": "operator-1",
        "layout": {
            "panels": [
                {"id": "fleet", "x": 0, "y": 0, "w": 6, "h": 4},
                {"id": "jobs", "x": 6, "y": 0, "w": 6, "h": 4},
            ],
            "version": 1,
        },
    }
    resp = client.post("/api/dashboard/layouts", json=payload)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["user_id"] == "operator-1"
    assert created["layout"]["version"] == 1
    assert created["updated_at"] is not None

    listed = client.get("/api/dashboard/layouts").json()
    assert listed["total"] == 1
    assert listed["items"][0]["user_id"] == "operator-1"
    assert listed["items"][0]["layout"]["panels"][0]["id"] == "fleet"


def test_dashboard_layouts_post_is_idempotent_upsert(client: TestClient) -> None:
    user_id = "operator-2"
    client.post(
        "/api/dashboard/layouts",
        json={"user_id": user_id, "layout": {"version": 1}},
    )
    resp = client.post(
        "/api/dashboard/layouts",
        json={"user_id": user_id, "layout": {"version": 2}},
    )
    assert resp.status_code == 201
    assert resp.json()["layout"]["version"] == 2

    listed = client.get("/api/dashboard/layouts").json()
    matches = [item for item in listed["items"] if item["user_id"] == user_id]
    assert len(matches) == 1, (
        f"upsert must keep a single row for user_id={user_id!r}; "
        f"got {len(matches)}"
    )
    assert matches[0]["layout"]["version"] == 2


def test_dashboard_layouts_post_rejects_empty_user_id(client: TestClient) -> None:
    resp = client.post(
        "/api/dashboard/layouts",
        json={"user_id": "   ", "layout": {}},
    )
    # Whitespace passes Pydantic min_length=1 but our handler rejects it.
    assert resp.status_code == 400


def test_dashboard_layouts_uses_agent_config_table(
    client: TestClient, tmp_path: Path
) -> None:
    """The W15 A20 contract says we persist in ``agent_config`` (no new
    migration). Confirm the row lands there with the documented key
    prefix so future refactors know what to migrate."""
    client.post(
        "/api/dashboard/layouts",
        json={"user_id": "audit-user", "layout": {"x": 1}},
    )
    from hermes3d.db.init import DB_PATH

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT key FROM agent_config WHERE key = ?",
            ("dashboard.layouts.audit-user",),
        )
        match = cur.fetchone()
    finally:
        conn.close()
    assert match is not None, (
        "dashboard layout must be persisted at agent_config key "
        "dashboard.layouts.<user_id>"
    )


# ---------------------------------------------------------------------------
# App-level wire-up sanity
# ---------------------------------------------------------------------------


def test_all_four_w15_a20_routes_are_registered() -> None:
    """create_gui_app must include all 4 new routes."""
    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    paths = {route.path for route in app.routes}
    assert "/api/skills" in paths
    assert "/api/connectors" in paths
    assert "/api/settings/themes" in paths
    assert "/api/dashboard/layouts" in paths
