"""Auto-repair guard tests for ``staged_update`` (Audit PR #135 Bonus 12 #3).

The pre-fix code had a path where ``_run_git(["checkout", "--detach", tag])``
inside the ``for tag in steps:`` loop raises ``HTTPException(502)``. That
exception escapes the loop without reaching ``_auto_repair_to_backup``,
leaving the Hermes Agent checkout on the previous (still-unverified) tag and
returning a raw 502 to the caller instead of a clean structured rollback.

This test pins the post-fix behavior:
- A failed checkout pivots to ``_auto_repair_to_backup``.
- The synthetic step entry has ``status="fail"`` and a redacted detail.
- ``HTTPException`` raised by ``_run_update_checks`` (e.g. workers env
  validation from PR #136) also gets caught — the new tag must not stick.

References:
- https://docs.python.org/3/library/exceptions.html#bdb.BdbQuit (control-flow caveats)
- OWASP CICD-SEC-1: https://owasp.org/www-project-top-10-ci-cd-security-risks/
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from hermes3d.api.routes import agent_updates


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _stub_repo_state(_repo: Path) -> dict[str, Any]:
    return {
        "repo_ready": True,
        "commit": "abcdef012345",
        "exact_tag": "v2026.5.7",
        "nearest_tag": "v2026.5.7",
        "branch": "main",
        "dirty": False,
        "dirty_entries": [],
        "remote": "https://github.com/example/example",
    }


def _stub_create_backup(_repo: Path, note: str) -> dict[str, Any]:
    return {
        "backup_id": "20260509T000000Z_v2026.5.7_abcdef012345",
        "tag": "v2026.5.7",
        "branch": "main",
        "commit": "abcdef012345",
        "dirty": False,
        "bundle_path": "/tmp/fake.bundle",
        "dirty_zip_path": None,
    }


def _stub_pending_tags(*_args: Any, **_kwargs: Any) -> list[str]:
    return ["v2026.5.8", "v2026.5.9"]


def _stub_remote_release_tags(*_args: Any, **_kwargs: Any) -> list[str]:
    return ["v2026.5.7", "v2026.5.8", "v2026.5.9"]


def _stub_latest_release(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {"tag": "v2026.5.9", "name": "Tenacity", "source": "stub"}


def _stub_run_checks_pass(_repo: Path) -> list[dict[str, Any]]:
    return [{"name": "git status", "status": "pass", "output": ""}]


def _make_request_body() -> agent_updates.StagedUpdateRequest:
    return agent_updates.StagedUpdateRequest(
        actor="claude-test",
        target_tag="v2026.5.9",
        max_steps=2,
        run_checks=True,
        create_backup=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_failed_checkout_pivots_to_auto_repair_not_502_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bonus 12 finding #3: HTTPException from _run_git must not escape the loop.

    Pre-fix: a failed mid-step ``git checkout`` raised 502 directly to the
    caller and left the repo on the prior tag. Post-fix: the exception is
    caught, recorded as a synthetic step failure, and ``_auto_repair_to_backup``
    is invoked exactly as if a normal gate had failed.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state)
    monkeypatch.setattr(agent_updates, "_ensure_remote", lambda _r: None)
    monkeypatch.setattr(agent_updates, "_run_git", lambda *a, **kw: "")  # fetch + others succeed
    monkeypatch.setattr(agent_updates, "_remote_release_tags", _stub_remote_release_tags)
    monkeypatch.setattr(agent_updates, "_latest_release", _stub_latest_release)
    monkeypatch.setattr(agent_updates, "_pending_tags", _stub_pending_tags)
    monkeypatch.setattr(agent_updates, "_create_backup", _stub_create_backup)
    monkeypatch.setattr(agent_updates, "_run_update_checks", _stub_run_checks_pass)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)

    repair_calls: list[dict[str, Any]] = []

    def fake_auto_repair(
        _repo: Path,
        backup: dict[str, Any] | None,
        actor: str,
        *,
        failed_tag: str,
    ) -> dict[str, Any]:
        repair_calls.append({"failed_tag": failed_tag, "actor": actor, "backup": backup})
        return {
            "attempted": True,
            "rolled_back": True,
            "failed_tag": failed_tag,
            "target": (backup or {}).get("tag"),
            "checks": [{"name": "post-rollback git status", "status": "pass", "output": ""}],
        }

    monkeypatch.setattr(agent_updates, "_auto_repair_to_backup", fake_auto_repair)

    # Make checkout fail on the first staged tag with a 502, like the real
    # code would on a tag-not-found / shallow-clone race.
    def failing_run_git(_repo: Path, args: list[str], timeout: int = 30) -> str:
        if args[:2] == ["checkout", "--detach"]:
            raise HTTPException(status_code=502, detail=f"git {' '.join(args)} failed: not found")
        return ""

    monkeypatch.setattr(agent_updates, "_run_git", failing_run_git)

    body = _make_request_body()
    payload = agent_updates.staged_update(body)

    # Post-fix: NO HTTPException 502 escapes; we get a structured rollback.
    assert payload["updated"] is False
    assert payload["status"] == "rolled_back_after_failed_check", (
        f"Failed-checkout flow must report rollback status; got {payload['status']!r}"
    )
    assert payload["repair"] is not None and payload["repair"]["rolled_back"] is True
    assert len(repair_calls) == 1, (
        "Auto-repair must be invoked exactly once, not zero (escape) or twice (duplicate)"
    )
    # Synthetic step entry must mark the failure with a redacted detail.
    assert payload["steps"], "At least one step entry must be recorded"
    failed_step = payload["steps"][0]
    assert failed_step["ok"] is False
    failed_check = failed_step["checks"][0]
    assert failed_check["status"] == "fail"
    assert failed_check["name"] == "git checkout to staged tag"
    assert "git checkout --detach" in failed_check["output"], (
        "Output must include the failing git command for operator triage"
    )


def test_failed_run_update_checks_http_exception_also_pivots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HTTPException from _run_update_checks (e.g. PR #136 worker validation)
    must also be caught — checkout has already moved the repo, so the only
    safe response is auto-repair to the pre-update backup.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state)
    monkeypatch.setattr(agent_updates, "_ensure_remote", lambda _r: None)
    monkeypatch.setattr(agent_updates, "_run_git", lambda *a, **kw: "")
    monkeypatch.setattr(agent_updates, "_remote_release_tags", _stub_remote_release_tags)
    monkeypatch.setattr(agent_updates, "_latest_release", _stub_latest_release)
    monkeypatch.setattr(agent_updates, "_pending_tags", _stub_pending_tags)
    monkeypatch.setattr(agent_updates, "_create_backup", _stub_create_backup)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)

    def failing_checks(_repo: Path) -> list[dict[str, Any]]:
        # PR #136-style worker validation failure
        raise HTTPException(
            status_code=400,
            detail="HERMES_AGENT_PYTEST_WORKERS<2 disables xdist isolation; "
                   "set HERMES_AGENT_DIAGNOSTIC=1 to override in triage.",
        )

    monkeypatch.setattr(agent_updates, "_run_update_checks", failing_checks)

    repair_calls: list[str] = []

    def fake_auto_repair(_repo, backup, actor, *, failed_tag):
        repair_calls.append(failed_tag)
        return {"attempted": True, "rolled_back": True, "failed_tag": failed_tag}

    monkeypatch.setattr(agent_updates, "_auto_repair_to_backup", fake_auto_repair)

    body = _make_request_body()
    payload = agent_updates.staged_update(body)

    assert payload["updated"] is False
    assert payload["repair"] is not None
    assert len(repair_calls) == 1, (
        "Workers-env HTTPException(400) must also pivot to auto-repair, "
        "not escape the loop and leave repo on the new tag."
    )
    # The synthetic check should preserve the operator-actionable detail.
    failed_check = payload["steps"][0]["checks"][0]
    assert "HERMES_AGENT_PYTEST_WORKERS" in failed_check["output"]


def test_successful_path_unaffected_by_repair_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Smoke: the new try/except must not regress the all-pass path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state)
    monkeypatch.setattr(agent_updates, "_ensure_remote", lambda _r: None)
    monkeypatch.setattr(agent_updates, "_run_git", lambda *a, **kw: "")
    monkeypatch.setattr(agent_updates, "_remote_release_tags", _stub_remote_release_tags)
    monkeypatch.setattr(agent_updates, "_latest_release", _stub_latest_release)
    monkeypatch.setattr(agent_updates, "_pending_tags", _stub_pending_tags)
    monkeypatch.setattr(agent_updates, "_create_backup", _stub_create_backup)
    monkeypatch.setattr(agent_updates, "_run_update_checks", _stub_run_checks_pass)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)

    def auto_repair_should_not_fire(*_a, **_kw):
        raise AssertionError("auto_repair must not fire on the all-pass path")

    monkeypatch.setattr(agent_updates, "_auto_repair_to_backup", auto_repair_should_not_fire)

    body = _make_request_body()
    payload = agent_updates.staged_update(body)
    assert payload["updated"] is True
    assert payload["status"] == "updated"
    assert payload["repair"] is None
    assert all(step["ok"] is True for step in payload["steps"])


# ---------------------------------------------------------------------------
# BLK-022 + BLK-023 (Master Continuation Agent A6 findings)
# ---------------------------------------------------------------------------


def test_blk022_subprocess_timeout_expired_pivots_to_auto_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BLK-022 (Wave Master Continuation Agent A6): pre-fix the for-tag loop
    only caught HTTPException. ``subprocess.TimeoutExpired`` raised by
    ``_run_git`` (when ``subprocess.run(timeout=120)`` fires) escaped the
    guard and bypassed ``_auto_repair_to_backup``. Post-fix we catch both.
    """
    import subprocess as _subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state)
    monkeypatch.setattr(agent_updates, "_ensure_remote", lambda _r: None)
    monkeypatch.setattr(agent_updates, "_remote_release_tags", _stub_remote_release_tags)
    monkeypatch.setattr(agent_updates, "_latest_release", _stub_latest_release)
    monkeypatch.setattr(agent_updates, "_pending_tags", _stub_pending_tags)
    monkeypatch.setattr(agent_updates, "_create_backup", _stub_create_backup)
    monkeypatch.setattr(agent_updates, "_run_update_checks", _stub_run_checks_pass)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)

    # _run_git for "fetch" + others succeeds; for "checkout --detach" raises
    # subprocess.TimeoutExpired (NOT HTTPException).
    def timeout_run_git(_repo: Path, args: list[str], timeout: int = 30) -> str:
        if args[:2] == ["checkout", "--detach"]:
            raise _subprocess.TimeoutExpired(cmd=["git"] + list(args), timeout=timeout)
        return ""

    monkeypatch.setattr(agent_updates, "_run_git", timeout_run_git)

    repair_calls: list[str] = []

    def fake_auto_repair(_repo, backup, actor, *, failed_tag):
        repair_calls.append(failed_tag)
        return {"attempted": True, "rolled_back": True, "failed_tag": failed_tag}

    monkeypatch.setattr(agent_updates, "_auto_repair_to_backup", fake_auto_repair)

    body = _make_request_body()
    payload = agent_updates.staged_update(body)

    assert payload["updated"] is False, (
        "BLK-022 regression: TimeoutExpired escaped and updated stayed True"
    )
    assert payload["repair"] is not None, (
        "BLK-022 regression: TimeoutExpired bypassed _auto_repair_to_backup"
    )
    assert len(repair_calls) == 1, (
        "BLK-022 regression: auto_repair must be invoked exactly once on TimeoutExpired"
    )
    failed_check = payload["steps"][0]["checks"][0]
    assert failed_check["status"] == "fail"
    assert "timeout" in failed_check["name"].lower() or "timeout" in failed_check["output"].lower()


def test_blk023_auto_backup_emits_proof_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BLK-023 (Wave Master Continuation Agent A6): the staged_update path
    creates an automatic backup at line 113 but pre-fix wrote ONLY to
    agent_config (no proof_events row). Post-fix emits
    ``hermes_agent_backup_auto_created`` proof_event for symmetry with the
    manual /backup endpoint.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    proof_events: list[tuple[str, str, dict[str, Any]]] = []

    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state)
    monkeypatch.setattr(agent_updates, "_ensure_remote", lambda _r: None)
    monkeypatch.setattr(agent_updates, "_run_git", lambda *a, **kw: "")
    monkeypatch.setattr(agent_updates, "_remote_release_tags", _stub_remote_release_tags)
    monkeypatch.setattr(agent_updates, "_latest_release", _stub_latest_release)
    monkeypatch.setattr(agent_updates, "_pending_tags", _stub_pending_tags)
    monkeypatch.setattr(agent_updates, "_create_backup", _stub_create_backup)
    monkeypatch.setattr(agent_updates, "_run_update_checks", _stub_run_checks_pass)
    monkeypatch.setattr(
        agent_updates,
        "_append_proof_event",
        lambda event_type, source_agent, payload: proof_events.append((event_type, source_agent, payload)),
    )
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "_auto_repair_to_backup", lambda *a, **kw: None)

    body = _make_request_body()
    agent_updates.staged_update(body)

    backup_proof_events = [pe for pe in proof_events if pe[0] == "hermes_agent_backup_auto_created"]
    assert len(backup_proof_events) == 1, (
        f"BLK-023 regression: expected exactly 1 hermes_agent_backup_auto_created "
        f"proof_event, got {len(backup_proof_events)}. All events: {[pe[0] for pe in proof_events]}"
    )
    event_type, source_agent, payload = backup_proof_events[0]
    assert source_agent == "claude-test"
    assert "backup" in payload
    assert payload["backup"]["backup_id"] == "20260509T000000Z_v2026.5.7_abcdef012345"
