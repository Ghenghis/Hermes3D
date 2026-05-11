"""W17 — /api/agents/update/status must NEVER 5xx; returns honest blocked envelope.

Root-cause-fix coverage (2026-05-11): Codex observed the endpoint returning a
hard 502 to the browser when the GitHub Releases API was rate-limited (403) or
when the v0.13 canary checkout was missing/unconfigured. The handler now
catches every upstream failure mode and returns:

  - ``200 + accepted=True, status="ready"`` when canary reachable + state ok
  - ``200 + accepted=False, status="unknown"`` when env unset / repo missing
  - ``200 + accepted=False, status="offline"`` when upstream API down

This test covers each failure mode by monkey-patching the upstream-querying
helpers, ensuring the route returns 200 in every adversarial scenario.

References:
- FastAPI exception handler patterns:
  https://fastapi.tiangolo.com/tutorial/handling-errors/
- W17-A1 honest-blocked contract:
  03_implementation/docs/handoffs/W17_A5_BACKEND_API_WIRING_2026-05-11.md
- Underlying defect: GitHub /repos/.../releases 403 surfaced as 502 to UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
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
# CASE 1 — canary path env unset / repo missing -> 200 + status="unknown"
# ---------------------------------------------------------------------------


def test_update_status_returns_200_when_canary_repo_missing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Repo path does not exist on disk -> honest-blocked, never 5xx."""
    nonexistent = tmp_path / "no_such_canary_checkout"

    from hermes3d.api.routes import agent_updates

    monkeypatch.setattr(agent_updates, "_repo_path", lambda: nonexistent)

    resp = client.get("/api/agents/update/status")
    assert resp.status_code == 200, (
        f"Expected 200 honest-blocked, got {resp.status_code} body={resp.text!r}"
    )
    body = resp.json()
    assert body["accepted"] is False
    assert body["status"] == "unknown"
    assert body["reason"] == "canary_not_configured"
    assert body["version"] == "v0.13.0"
    assert body["repo_ready"] is False
    assert body["current"]["repo_ready"] is False
    # Must NOT pretend the canary is current; pending/outdated stay empty.
    assert body["outdated"] is False
    assert body["pending_tags"] == []


# ---------------------------------------------------------------------------
# CASE 2 — GitHub Releases API rate-limited / unreachable -> 200 + status="offline"
# ---------------------------------------------------------------------------


def test_update_status_returns_200_when_github_api_rate_limited(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GitHub API raises HTTPException(502) inside _remote_release_tags; route
    must return 200 with status="offline" and surface the upstream error
    in ``upstream_error`` (redacted) for operator triage."""
    from hermes3d.api.routes import agent_updates

    monkeypatch.setattr(
        agent_updates,
        "_repo_state",
        lambda repo: {
            "repo_ready": True,
            "commit": "abc123",
            "exact_tag": "v2026.4.30",
            "nearest_tag": "v2026.4.30",
            "branch": "detached",
            "dirty": False,
            "dirty_entries": [],
            "remote": agent_updates.UPSTREAM_URL,
        },
    )

    def _boom(_repo: Any) -> list[str]:
        raise HTTPException(
            status_code=502,
            detail=(
                "GitHub Releases API unreachable for "
                "https://api.github.com/repos/NousResearch/hermes-agent/releases?per_page=100: "
                "HTTPError: HTTP Error 403: rate limit exceeded"
            ),
        )

    monkeypatch.setattr(agent_updates, "_remote_release_tags", _boom)

    resp = client.get("/api/agents/update/status")
    assert resp.status_code == 200, (
        f"Expected 200 honest-blocked, got {resp.status_code} body={resp.text!r}"
    )
    body = resp.json()
    assert body["accepted"] is False
    assert body["status"] == "offline"
    assert body["reason"] == "canary_unreachable"
    assert body["version"] == "v0.13.0"
    assert body["upstream_error"] is not None
    assert "GitHub" in body["upstream_error"] or "rate limit" in body["upstream_error"]
    # Repo *is* present, just upstream is down. repo_ready stays true.
    assert body["repo_ready"] is True


# ---------------------------------------------------------------------------
# CASE 3 — generic Exception inside upstream helpers -> still 200
# ---------------------------------------------------------------------------


def test_update_status_returns_200_even_on_unexpected_exception(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-HTTPException blowup inside _remote_release_tags (e.g. attribute
    error from a future refactor) must still surface as 200 honest-blocked,
    not a bare 500 from FastAPI's default handler."""
    from hermes3d.api.routes import agent_updates

    monkeypatch.setattr(
        agent_updates,
        "_repo_state",
        lambda repo: {
            "repo_ready": True,
            "commit": "abc123",
            "exact_tag": None,
            "nearest_tag": None,
            "branch": "detached",
            "dirty": False,
            "dirty_entries": [],
            "remote": agent_updates.UPSTREAM_URL,
        },
    )

    def _boom(_repo: Any) -> list[str]:
        raise RuntimeError("unexpected upstream parse error")

    monkeypatch.setattr(agent_updates, "_remote_release_tags", _boom)

    resp = client.get("/api/agents/update/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is False
    assert body["status"] == "offline"
    assert body["reason"] == "canary_unreachable"
    assert body["upstream_error"] is not None
    assert "RuntimeError" in body["upstream_error"]


# ---------------------------------------------------------------------------
# CASE 4 — _repo_state itself raises HTTPException (git probe failure)
# ---------------------------------------------------------------------------


def test_update_status_returns_200_when_repo_state_raises(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_repo_state`` calls ``_run_git`` which raises HTTPException(502) when
    git itself fails. The route must still return 200 honest-blocked."""
    from hermes3d.api.routes import agent_updates

    def _boom(_repo: Any) -> dict[str, Any]:
        raise HTTPException(
            status_code=502, detail="git rev-parse --short=12 HEAD failed: fatal: not a git repo"
        )

    monkeypatch.setattr(agent_updates, "_repo_state", _boom)

    resp = client.get("/api/agents/update/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is False
    assert body["status"] == "offline"
    assert body["reason"] == "repo_state_unreachable"


# ---------------------------------------------------------------------------
# CASE 5 — happy path: canary reachable + GitHub API responding
# ---------------------------------------------------------------------------


def test_update_status_returns_200_ready_when_canary_and_upstream_ok(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When everything works, return ``accepted=True``, ``status="ready"``,
    and the legacy back-compat keys remain populated."""
    from hermes3d.api.routes import agent_updates

    monkeypatch.setattr(
        agent_updates,
        "_repo_state",
        lambda repo: {
            "repo_ready": True,
            "commit": "abc123def456",
            "exact_tag": "v2026.4.30",
            "nearest_tag": "v2026.4.30",
            "branch": "detached",
            "dirty": False,
            "dirty_entries": [],
            "remote": agent_updates.UPSTREAM_URL,
        },
    )
    monkeypatch.setattr(
        agent_updates,
        "_remote_release_tags",
        lambda repo: ["v2026.4.30", "v2026.5.7"],
    )
    monkeypatch.setattr(
        agent_updates,
        "_latest_release",
        lambda tags: {
            "tag": "v2026.5.7",
            "name": "Tenacity Release",
            "source": "github_releases_api",
        },
    )

    resp = client.get("/api/agents/update/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert body["status"] == "ready"
    assert body["reason"] is None
    assert body["version"] == "v0.13.0"
    assert body["upstream_error"] is None
    # Legacy shape preserved.
    assert body["repo_ready"] is True
    assert body["latest_release"]["tag"] == "v2026.5.7"
    assert body["outdated"] is True  # v2026.5.7 > v2026.4.30
    assert body["pending_tags"] == ["v2026.5.7"]


# ---------------------------------------------------------------------------
# CASE 6 — bare-minimum contract: NEVER 5xx, regardless of internal failure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        HTTPException(status_code=502, detail="GitHub down"),
        HTTPException(status_code=500, detail="internal"),
        RuntimeError("anything"),
        ValueError("anything"),
        ConnectionError("network"),
    ],
)
def test_update_status_never_returns_5xx(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    exc: Exception,
) -> None:
    """The strict W17 contract: regardless of what blows up internally,
    this endpoint must respond with status_code < 500."""
    from hermes3d.api.routes import agent_updates

    monkeypatch.setattr(
        agent_updates,
        "_repo_state",
        lambda repo: {
            "repo_ready": True,
            "commit": "abc123",
            "exact_tag": None,
            "nearest_tag": None,
            "branch": "detached",
            "dirty": False,
            "dirty_entries": [],
            "remote": agent_updates.UPSTREAM_URL,
        },
    )

    def _boom(_repo: Any) -> list[str]:
        raise exc

    monkeypatch.setattr(agent_updates, "_remote_release_tags", _boom)

    resp = client.get("/api/agents/update/status")
    assert resp.status_code < 500, (
        f"5xx leaked! status={resp.status_code} body={resp.text!r} for exc={exc!r}"
    )
    assert resp.status_code == 200
