"""Bonus 12 finding #6 (Audit PR #135): redaction symmetry for agent_config.

Pre-fix: ``staged_update`` and ``rollback_update`` wrote the FULL ``payload``
(including 800-char ``check.output`` strings that only had the narrow
``_redact()`` pass applied) into ``agent_config.last_run`` /
``last_rollback``. Meanwhile ``proof_events`` correctly used
``_proof_summary(payload)`` which truncates each ``check.output`` to a
180-char ``output_head`` AFTER ``_redact``.

Result: a one-sided redaction guarantee. Operators reading
``SELECT value FROM agent_config WHERE key='hermes_agent.update.last_run'``
saw 800 chars of partially-redacted bytes; readers of ``proof_events``
saw 180-char redacted heads. Asymmetric data-at-rest minimization (OWASP
A02:2021 / A09:2021).

Post-fix: a single ``persisted = _proof_summary(payload)`` is computed
once and written to BOTH sinks, mirroring Sentry's
single-redaction-hook pattern.

References:
- https://owasp.org/Top10/A02_2021-Cryptographic_Failures/
- https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/
- https://docs.sentry.io/platforms/python/data-management/sensitive-data/
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hermes3d.api.routes import agent_updates

# ---------------------------------------------------------------------------
# Stubs / helpers
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


def _make_stage_setup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, list[tuple]]:
    """Wire up the FastAPI route's collaborators with deterministic stubs.

    Returns (repo_path, captured_executes) where captured_executes is the
    accumulator the test will inspect for the ``agent_config`` write.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    captured_executes: list[tuple[str, tuple[Any, ...]]] = []

    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state)
    monkeypatch.setattr(agent_updates, "_ensure_remote", lambda _r: None)
    monkeypatch.setattr(agent_updates, "_run_git", lambda *a, **kw: "")
    monkeypatch.setattr(
        agent_updates, "_remote_release_tags", lambda _r: ["v2026.5.7", "v2026.5.8"]
    )
    monkeypatch.setattr(
        agent_updates,
        "_latest_release",
        lambda _t: {"tag": "v2026.5.8", "name": "Tenacity+1", "source": "stub"},
    )
    monkeypatch.setattr(agent_updates, "_pending_tags", lambda *a, **kw: ["v2026.5.8"])
    monkeypatch.setattr(agent_updates, "_create_backup", _stub_create_backup)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)
    monkeypatch.setattr(
        agent_updates,
        "execute",
        lambda sql, params=(): captured_executes.append((sql, params)),
    )
    return repo, captured_executes


def _checks_with_huge_redacted_output() -> list[dict[str, Any]]:
    """A check whose `output` is a long bearer-shaped blob.

    `_redact()` will mask the bearer token but leave a 800-char string;
    `_proof_summary()` should truncate that to 180 chars (`output_head`).
    """
    long_output = "Bearer " + "x" * 500 + " other-debug-noise " + "y" * 300
    return [
        {
            "name": "python pytest non-integration",
            "status": "fail",
            "output": long_output,
        }
    ]


# ---------------------------------------------------------------------------
# staged_update: agent_config now stores the proof summary, not raw payload
# ---------------------------------------------------------------------------


def test_staged_update_agent_config_uses_proof_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bonus 12 #6: the agent_config row must contain `output_head` (proof
    summary), NOT the raw `output` field."""
    _repo, captured = _make_stage_setup(monkeypatch, tmp_path)
    monkeypatch.setattr(
        agent_updates,
        "_run_update_checks",
        lambda _r: _checks_with_huge_redacted_output(),
    )
    body = agent_updates.StagedUpdateRequest(
        actor="claude-test",
        target_tag="v2026.5.8",
        max_steps=1,
        run_checks=True,
        create_backup=True,
    )
    agent_updates.staged_update(body)

    # The agent_config row written via execute(...)
    cfg_writes = [
        params for sql, params in captured if "agent_config" in sql and "last_run" in str(params)
    ]
    assert cfg_writes, "agent_config last_run row was not written"
    _key, value = cfg_writes[-1][0], cfg_writes[-1][1]
    parsed = json.loads(value)

    # The proof-summary key is `output_head`; the raw key is `output`.
    for step in parsed.get("steps", []):
        for check in step.get("checks", []):
            assert "output_head" in check, (
                f"Bonus 12 #6 regression: agent_config check missing output_head: {check!r}"
            )
            assert "output" not in check, (
                f"Bonus 12 #6 regression: agent_config check still has raw 'output': {check!r}"
            )
            assert len(check["output_head"]) <= 180, (
                f"output_head exceeds 180 chars: {len(check['output_head'])}"
            )


def test_staged_update_agent_config_preserves_actionable_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operators must still see status, verified, backup_id, etc. in the
    persisted blob — _proof_summary must NOT strip those."""
    _repo, captured = _make_stage_setup(monkeypatch, tmp_path)
    monkeypatch.setattr(
        agent_updates,
        "_run_update_checks",
        lambda _r: [{"name": "git status", "status": "pass", "output": ""}],
    )
    body = agent_updates.StagedUpdateRequest(
        actor="claude-test",
        target_tag="v2026.5.8",
        max_steps=1,
        run_checks=True,
        create_backup=True,
    )
    agent_updates.staged_update(body)
    cfg_value = json.loads(
        next(
            params[1]
            for sql, params in captured
            if "agent_config" in sql and "last_run" in str(params)
        )
    )
    assert cfg_value.get("actor") == "claude-test"
    assert "status" in cfg_value
    assert "verified" in cfg_value
    assert "backup" in cfg_value, "backup metadata must still be persisted"
    assert "steps" in cfg_value
    # latest_release stays for operator triage even though it's a small dict.
    assert "latest_release" in cfg_value


def test_staged_update_proof_events_match_agent_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invariant: the same `persisted` blob feeds both sinks (proof_events
    and agent_config). This proves single-redaction-hook symmetry.
    """
    _repo, captured = _make_stage_setup(monkeypatch, tmp_path)
    monkeypatch.setattr(
        agent_updates,
        "_run_update_checks",
        lambda _r: _checks_with_huge_redacted_output(),
    )

    # Capture the proof_event payload via _append_proof_event
    proof_payloads: list[dict[str, Any]] = []
    monkeypatch.setattr(
        agent_updates,
        "_append_proof_event",
        lambda *args, **kw: proof_payloads.append(args[2] if len(args) >= 3 else kw.get("payload")),
    )
    body = agent_updates.StagedUpdateRequest(
        actor="claude-test",
        target_tag="v2026.5.8",
        max_steps=1,
        run_checks=True,
        create_backup=True,
    )
    agent_updates.staged_update(body)
    cfg_value = json.loads(
        next(
            params[1]
            for sql, params in captured
            if "agent_config" in sql and "last_run" in str(params)
        )
    )
    # Drop the "actor" key to compare apples-to-apples
    cfg_minus_actor = {k: v for k, v in cfg_value.items() if k != "actor"}
    assert proof_payloads, "proof_event payload was not captured"
    assert proof_payloads[-1] == cfg_minus_actor, (
        "agent_config and proof_events must be byte-equivalent (single-redaction)"
    )


# ---------------------------------------------------------------------------
# rollback_update: same symmetry
# ---------------------------------------------------------------------------


def test_rollback_update_agent_config_uses_proof_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same Bonus 12 #6 guarantee for the rollback flow."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    captured: list[tuple[str, tuple[Any, ...]]] = []
    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state)
    monkeypatch.setattr(
        agent_updates,
        "_find_backup",
        lambda _bid: {
            "backup_id": "test-backup",
            "tag": "v2026.5.6",
            "branch": "main",
            "commit": "abc",
        },
    )
    monkeypatch.setattr(agent_updates, "_create_backup", _stub_create_backup)
    monkeypatch.setattr(agent_updates, "_run_git", lambda *a, **kw: "")
    monkeypatch.setattr(
        agent_updates,
        "_run_update_checks",
        lambda _r: _checks_with_huge_redacted_output(),
    )
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)
    monkeypatch.setattr(
        agent_updates,
        "execute",
        lambda sql, params=(): captured.append((sql, params)),
    )

    body = agent_updates.RollbackRequest(
        actor="claude-test", backup_id="test-backup", tag="v2026.5.6"
    )
    agent_updates.rollback_update(body)

    cfg_writes = [
        params
        for sql, params in captured
        if "agent_config" in sql and "last_rollback" in str(params)
    ]
    assert cfg_writes, "agent_config last_rollback row was not written"
    parsed = json.loads(cfg_writes[-1][1])
    for check in parsed.get("checks", []):
        assert "output_head" in check
        assert "output" not in check
