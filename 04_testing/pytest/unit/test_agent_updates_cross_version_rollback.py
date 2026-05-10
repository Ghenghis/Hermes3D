"""F1 pin (P1-8 post-promotion hardening, 2026-05-09):
cross-version rollback safety for the Hermes Agent updater.

Hazard: post Wave 1 promotion (PR #160), v0.13 is the process default
at ``G:/Github/hermes-agent-v013-canary``. An operator wanting to revert
sets ``HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`` (v0.12). If
the implicit rollback still selects the most-recent backup globally
(taken under v0.13), it would check out a v0.13 tag/commit into the
v0.12 working tree -> repo corruption or HTTP 502.

Fix surface in ``agent_updates.py``:
1. ``_create_backup`` records ``checkout_path`` and a short
   ``checkout_path_hash`` in the backup metadata + ``backup_id``.
2. ``_latest_backup(checkout_path=...)`` filters by the persisted
   ``checkout_path``; backups missing the field (legacy) are excluded
   from a filtered query.
3. ``rollback_update``:
   - Implicit (no ``backup_id``) calls the filtered ``_latest_backup``
     and refuses with HTTP 409 + operator-clear detail when no backup
     matches the active checkout.
   - Explicit (``backup_id`` supplied) cross-checks the backup's
     recorded ``checkout_path`` against the active one and refuses on
     mismatch.

References:
- Adversarial review P1-8 (post-promotion hardening 2026-05-09)
- Wave 1 promotion PR #160 / per-call resolver PR #155
- 12-Factor App config rule III: https://12factor.net/config
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from hermes3d.api.routes import agent_updates


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


V012_FALLBACK = "G:/Github/hermes-agent-fresh"
V013_DEFAULT = "G:/Github/hermes-agent-v013-canary"


def _write_backup(
    backup_root: Path,
    backup_id: str,
    *,
    checkout_path: str | None,
    tag: str = "v2026.5.7",
    commit: str = "abcdef012345",
) -> Path:
    """Create a backup metadata JSON the way ``_create_backup`` would.

    ``checkout_path=None`` simulates a legacy (pre-F1) backup whose
    metadata predates the field — the F1 filter must EXCLUDE these.
    """
    payload: dict[str, Any] = {
        "backup_id": backup_id,
        "tag": tag,
        "branch": "main",
        "commit": commit,
        "dirty": False,
        "bundle_path": str(backup_root / f"{backup_id}.bundle"),
        "dirty_zip_path": None,
    }
    if checkout_path is not None:
        # Production ``_create_backup`` writes ``str(repo)`` where ``repo``
        # is a ``Path``; on Windows that means OS-native backslashes.
        # Mirror that exact normalization so the F1 filter (which also
        # uses ``str(Path(...))``) matches in tests.
        payload["checkout_path"] = str(Path(checkout_path))
    meta_path = backup_root / f"{backup_id}.json"
    meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return meta_path


# ---------------------------------------------------------------------------
# F1 backup_id format
# ---------------------------------------------------------------------------


def test_f1_checkout_path_hash_is_deterministic_and_distinct() -> None:
    """``_checkout_path_hash`` is a stable per-path label; different
    paths -> different hashes."""
    h_v013 = agent_updates._checkout_path_hash(Path(V013_DEFAULT))
    h_v012 = agent_updates._checkout_path_hash(Path(V012_FALLBACK))
    # 8 hex chars
    assert len(h_v013) == 8
    assert len(h_v012) == 8
    assert all(c in "0123456789abcdef" for c in h_v013)
    assert all(c in "0123456789abcdef" for c in h_v012)
    # Distinct paths must produce distinct labels.
    assert h_v013 != h_v012
    # Stable across calls.
    assert h_v013 == agent_updates._checkout_path_hash(Path(V013_DEFAULT))


# ---------------------------------------------------------------------------
# F1 ``_latest_backup`` filter behavior
# ---------------------------------------------------------------------------


def test_f1_latest_backup_unfiltered_back_compat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``checkout_path is None`` legacy behavior is preserved."""
    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", tmp_path)
    _write_backup(tmp_path, "20260509T000000Z_aaaaaaaa_v2026.5.7_abcdef012345", checkout_path=V013_DEFAULT)
    result = agent_updates._latest_backup()
    assert result is not None
    assert result["backup_id"].endswith("_abcdef012345")


def test_f1_latest_backup_filter_excludes_other_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A backup taken on v0.13 must NOT be returned when the active
    checkout is v0.12 — that is the documented corruption hazard."""
    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", tmp_path)
    _write_backup(
        tmp_path,
        "20260509T000000Z_v013hash_v2026.5.7_v013commit",
        checkout_path=V013_DEFAULT,
    )
    # Active checkout is v0.12 fallback; resolver returns no match.
    result = agent_updates._latest_backup(checkout_path=Path(V012_FALLBACK))
    assert result is None, (
        "F1 regression: a v0.13-side backup was selected for a v0.12 rollback"
    )


def test_f1_latest_backup_filter_returns_matching_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a backup with the right ``checkout_path`` exists, return it."""
    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", tmp_path)
    _write_backup(
        tmp_path,
        "20260509T000000Z_v012hash_v2026.4.30_v012commit",
        checkout_path=V012_FALLBACK,
        tag="v2026.4.30",
    )
    result = agent_updates._latest_backup(checkout_path=Path(V012_FALLBACK))
    assert result is not None
    # Persisted ``checkout_path`` is normalized via ``str(Path(...))``
    # so the OS-native form (backslashes on Windows) is what is stored
    # — matching what ``_create_backup`` writes in production.
    assert result["checkout_path"] == str(Path(V012_FALLBACK))
    assert result["tag"] == "v2026.4.30"


def test_f1_legacy_backups_without_checkout_path_excluded_from_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-F1 backup metadata blob lacking ``checkout_path`` must be
    EXCLUDED from a filtered ``_latest_backup`` query — its producing
    checkout is unknown so we cannot prove it is safe to apply."""
    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", tmp_path)
    # Legacy: no checkout_path field
    _write_backup(
        tmp_path,
        "20260501T000000Z_legacy_v2026.4.30_legacycom",
        checkout_path=None,
    )
    result = agent_updates._latest_backup(checkout_path=Path(V012_FALLBACK))
    assert result is None, (
        "F1 regression: legacy backup without checkout_path was returned "
        "by a filtered query; it must be excluded as untrustworthy."
    )


def test_f1_filter_picks_newer_match_over_older_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multiple matching backups -> newest wins (consistent with the
    legacy ordering by mtime)."""
    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", tmp_path)
    older = _write_backup(
        tmp_path,
        "20260501T000000Z_v012hash_v2026.4.30_olderv012",
        checkout_path=V012_FALLBACK,
    )
    newer = _write_backup(
        tmp_path,
        "20260509T000000Z_v012hash_v2026.4.30_newerv012",
        checkout_path=V012_FALLBACK,
    )
    # Force older mtime to be older; newer to be newer (some FS may give same).
    import os as _os
    import time as _time
    older_ts = _time.time() - 10_000
    newer_ts = _time.time()
    _os.utime(older, (older_ts, older_ts))
    _os.utime(newer, (newer_ts, newer_ts))
    result = agent_updates._latest_backup(checkout_path=Path(V012_FALLBACK))
    assert result is not None
    assert result["backup_id"].endswith("_newerv012")


# ---------------------------------------------------------------------------
# F1 ``rollback_update`` route refusal behavior
# ---------------------------------------------------------------------------


def _stub_repo_state_ready(_repo: Path) -> dict[str, Any]:
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


def test_f1_rollback_implicit_refuses_when_no_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Implicit rollback (no backup_id) must refuse with HTTP 409 + an
    operator-clear detail when no backup matches the active checkout."""
    repo_v012 = tmp_path / "v012-repo"
    repo_v012.mkdir()
    (repo_v012 / ".git").mkdir()

    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    # Only a v0.13-side backup exists.
    _write_backup(
        backup_root,
        "20260509T000000Z_v013hash_v2026.5.7_v013commit",
        checkout_path=V013_DEFAULT,
    )

    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", backup_root)
    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo_v012)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state_ready)
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)

    body = agent_updates.RollbackRequest(actor="claude-test")
    with pytest.raises(HTTPException) as excinfo:
        agent_updates.rollback_update(body)
    assert excinfo.value.status_code == 409
    detail_lc = str(excinfo.value.detail).lower()
    assert "no backup found for current checkout" in detail_lc
    assert "rollback" in detail_lc


def test_f1_rollback_explicit_refuses_on_checkout_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Explicit rollback (backup_id supplied) must refuse when the
    backup's recorded ``checkout_path`` differs from the active one."""
    repo_v012 = tmp_path / "v012-repo"
    repo_v012.mkdir()
    (repo_v012 / ".git").mkdir()

    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    backup_id = "20260509T000000Z_v013hash_v2026.5.7_v013commit"
    _write_backup(backup_root, backup_id, checkout_path=V013_DEFAULT)

    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", backup_root)
    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo_v012)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state_ready)
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)

    body = agent_updates.RollbackRequest(actor="claude-test", backup_id=backup_id)
    with pytest.raises(HTTPException) as excinfo:
        agent_updates.rollback_update(body)
    assert excinfo.value.status_code == 409
    detail = str(excinfo.value.detail).lower()
    assert "different checkout" in detail
    assert "hermes_agent_checkout" in detail


def test_f1_rollback_explicit_legacy_backup_no_checkout_path_is_allowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-F1 backup that lacks ``checkout_path`` is still allowed when
    referenced explicitly by ``backup_id`` — operator-named back-compat.
    Filter behavior (implicit) excludes legacy; explicit lookup does NOT
    so existing operator runbooks keep working."""
    repo = tmp_path / "v012-repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    backup_id = "20260501T000000Z_legacyrec_v2026.4.30_legacycom"
    _write_backup(backup_root, backup_id, checkout_path=None)

    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", backup_root)
    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state_ready)
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "_create_backup", lambda *a, **kw: {"backup_id": "auto"})
    monkeypatch.setattr(agent_updates, "_run_git", lambda *a, **kw: "")
    monkeypatch.setattr(
        agent_updates,
        "_run_update_checks",
        lambda _r: [{"name": "git status", "status": "pass", "output": ""}],
    )

    body = agent_updates.RollbackRequest(actor="claude-test", backup_id=backup_id)
    payload = agent_updates.rollback_update(body)
    # No HTTPException -> explicit legacy backup path is honored.
    assert payload["rolled_back"] is True


def test_f1_rollback_explicit_matching_checkout_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Smoke: a backup whose ``checkout_path`` matches the active one
    proceeds without 409. Pin against accidental over-restriction."""
    repo = tmp_path / "v013-repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    backup_id = "20260509T000000Z_v013hash_v2026.5.7_v013commit"
    _write_backup(backup_root, backup_id, checkout_path=str(repo))

    monkeypatch.setattr(agent_updates, "BACKUP_ROOT", backup_root)
    monkeypatch.setattr(agent_updates, "_repo_path", lambda: repo)
    monkeypatch.setattr(agent_updates, "_repo_state", _stub_repo_state_ready)
    monkeypatch.setattr(agent_updates, "execute", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "_append_proof_event", lambda *a, **kw: None)
    monkeypatch.setattr(agent_updates, "_create_backup", lambda *a, **kw: {"backup_id": "auto"})
    monkeypatch.setattr(agent_updates, "_run_git", lambda *a, **kw: "")
    monkeypatch.setattr(
        agent_updates,
        "_run_update_checks",
        lambda _r: [{"name": "git status", "status": "pass", "output": ""}],
    )

    body = agent_updates.RollbackRequest(actor="claude-test", backup_id=backup_id)
    payload = agent_updates.rollback_update(body)
    assert payload["rolled_back"] is True
    assert payload["status"] == "rolled_back"
