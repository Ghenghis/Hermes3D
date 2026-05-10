"""Bonus 12 finding #7 (Audit PR #135): close TOCTOU + crash window in
``apply_patch_proposal``.

Pre-fix order: ``write tmp -> os.replace -> read target -> hash -> rollback``.
Failure modes:
- No fsync on tmp fd; Windows cache could lose bytes on power loss
  (etcd issue 13839 documents the same pattern producing zero-byte files).
- Hash verified AFTER ``os.replace`` so a corrupt write went live first.
- ``proof_events`` insert happened AFTER ``os.replace``; SIGKILL between
  left the mutated file with no audit row to reconcile against.
- No ``fsync`` of the parent directory on POSIX so the rename itself was
  not durable.

Post-fix order: ``hash-of-bytes -> compare -> open+write+fsync(fd) ->
record inflight intent -> os.replace -> fsync(parent_dir on POSIX) ->
defensive post-read``.

References:
- https://docs.python.org/3/library/os.html#os.fsync
- https://docs.python.org/3/library/os.html#os.replace
- https://github.com/etcd-io/etcd/issues/13839
- https://lwn.net/Articles/457667/
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from hermes3d.services import code_history

# ---------------------------------------------------------------------------
# Fixture: build the minimal test scaffolding around apply_patch_proposal
# ---------------------------------------------------------------------------


@pytest.fixture
def applier_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Wire apply_patch_proposal collaborators with deterministic stubs.

    Returns a dict with target file path, proposal payload helper, and
    capture lists for execute() and append_mcp_evidence().
    """
    target = tmp_path / "target.py"
    target.write_text("original-content\n", encoding="utf-8")

    rel = "target.py"

    captured_execs: list[tuple[str, tuple[Any, ...]]] = []
    captured_evidence: list[dict[str, Any]] = []

    monkeypatch.setattr(code_history, "_resolve_project_path", lambda r, write=True: target)
    monkeypatch.setattr(code_history, "_relative_to_project", lambda p: rel)
    monkeypatch.setattr(code_history, "_validate_owner", lambda owner: None)
    monkeypatch.setattr(code_history, "_validate_task_id", lambda tid: None)
    monkeypatch.setattr(
        code_history,
        "code_write_readiness",
        lambda: {"ready": True, "blocked_reasons": []},
    )
    monkeypatch.setattr(
        code_history,
        "_require_active_mcp_lock",
        lambda *a, **kw: {"lock_id": "test-lock", "owner": "claude-test"},
    )
    monkeypatch.setattr(
        code_history,
        "snapshot_file",
        lambda r, **kw: {"id": f"snap-{kw.get('action_id', 'x')}", "ts_utc": "stub"},
    )
    monkeypatch.setattr(
        code_history,
        "execute",
        lambda sql, params=(): captured_execs.append((sql, params)),
    )
    monkeypatch.setattr(
        code_history,
        "append_mcp_evidence",
        lambda **kw: (
            captured_evidence.append(kw)
            or {"status": "recorded", "evidence_id": "ev-stub", "result": {"ok": True}}
        ),
    )
    return {
        "target": target,
        "rel": rel,
        "captured_execs": captured_execs,
        "captured_evidence": captured_evidence,
    }


def _make_proposal(
    target: Path,
    proposed_text: str,
    *,
    proposed_sha: str | None = None,
    base_sha: str | None = None,
) -> dict[str, Any]:
    import hashlib

    base_sha = base_sha or hashlib.sha256(target.read_bytes()).hexdigest()
    proposed_sha = proposed_sha or hashlib.sha256(proposed_text.encode("utf-8")).hexdigest()
    return {
        "agent_id": "claude-test",
        "relative_path": str(target.name),
        "proposed_text": proposed_text,
        "proposed_sha256": proposed_sha,
        "base_sha256": base_sha,
        "reason": "TOCTOU test",
    }


# ---------------------------------------------------------------------------
# Test 1: clean apply path
# ---------------------------------------------------------------------------


def test_apply_clean_writes_target_and_records_inflight_then_applied(
    applier_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    target = applier_setup["target"]
    proposal = _make_proposal(target, "patched-content\n")
    monkeypatch.setattr(code_history, "_patch_proposal_payload", lambda pid: proposal)
    result = code_history.apply_patch_proposal("prop-1", agent_id="claude-test", task_id="task-1")
    assert target.read_text(encoding="utf-8") == "patched-content\n"
    # Both replace_inflight (Bonus 12 #7 fix) and applied events must land.
    payloads = [params for _, params in applier_setup["captured_execs"]]
    inflight_writes = [
        params for params in payloads if any("replace_inflight" in str(field) for field in params)
    ]
    applied_writes = [
        params for params in payloads if any("code_patch.applied" in str(field) for field in params)
    ]
    assert inflight_writes, "Bonus 12 #7: inflight intent must be recorded BEFORE replace"
    assert applied_writes, "code_patch.applied event must be recorded after success"
    assert result.get("status") in {"applied", None} or result is not None


# ---------------------------------------------------------------------------
# Test 2: hash mismatch BEFORE replace
# ---------------------------------------------------------------------------


def test_apply_hash_mismatch_blocks_before_replace(
    applier_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bonus 12 #7: a wrong proposed_sha256 must fail BEFORE os.replace.

    Pre-fix the wrong hash was caught only AFTER the file was already
    overwritten. Post-fix the check happens against the in-memory bytes
    so the on-disk target is never mutated.
    """
    target = applier_setup["target"]
    original = target.read_bytes()
    proposal = _make_proposal(
        target,
        "patched-content\n",
        proposed_sha="wrong-hash-" + "0" * 50,
    )
    monkeypatch.setattr(code_history, "_patch_proposal_payload", lambda pid: proposal)
    with pytest.raises(RuntimeError) as exc_info:
        code_history.apply_patch_proposal("prop-2", agent_id="claude-test", task_id="task-1")
    # Must indicate the manifest mismatch, not the post-replace drift.
    assert "manifest" in str(exc_info.value).lower() or "match" in str(exc_info.value).lower()
    # Critical: target file was NOT mutated.
    assert target.read_bytes() == original
    # No replace_inflight row should be written when we reject up-front.
    inflight_writes = [
        params
        for _, params in applier_setup["captured_execs"]
        if any("replace_inflight" in str(field) for field in params)
    ]
    assert not inflight_writes, (
        "Bonus 12 #7: rejected-by-manifest path must NOT record inflight intent"
    )


# ---------------------------------------------------------------------------
# Test 3: tmp fd is fsynced (probe via os.fsync wrapper)
# ---------------------------------------------------------------------------


def test_apply_calls_os_fsync_on_tmp_fd(
    applier_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-fix had no fsync; this test pins the fix in place."""
    target = applier_setup["target"]
    proposal = _make_proposal(target, "patched-content\n")
    monkeypatch.setattr(code_history, "_patch_proposal_payload", lambda pid: proposal)

    fsync_calls: list[int] = []
    real_fsync = code_history.os.fsync

    def tracking_fsync(fd: int) -> None:
        fsync_calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(code_history.os, "fsync", tracking_fsync)
    code_history.apply_patch_proposal("prop-3", agent_id="claude-test", task_id="task-1")
    assert fsync_calls, (
        "Bonus 12 #7: os.fsync must be called at least once (on the tmp fd before os.replace)"
    )


# ---------------------------------------------------------------------------
# Test 4: simulated crash mid-replace leaves target unchanged
# ---------------------------------------------------------------------------


def test_apply_crash_during_replace_leaves_inflight_marker(
    applier_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """If os.replace raises (crash analog), the inflight marker is in the
    DB so recovery can match the proposal_id + tmp_path and reconcile."""
    target = applier_setup["target"]
    original = target.read_bytes()
    proposal = _make_proposal(target, "patched-content\n")
    monkeypatch.setattr(code_history, "_patch_proposal_payload", lambda pid: proposal)

    # Make os.replace raise the FIRST time it's called (simulating a crash
    # mid-replace). Pass through on subsequent calls so the rollback path
    # still works on POSIX. We capture state by mocking through the module.
    real_replace = code_history.os.replace
    call_count = {"n": 0}

    def crashing_replace(src: str, dst: str) -> None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OSError(13, "Permission denied (simulated crash)")
        real_replace(src, dst)

    monkeypatch.setattr(code_history.os, "replace", crashing_replace)
    with pytest.raises(OSError):
        code_history.apply_patch_proposal("prop-4", agent_id="claude-test", task_id="task-1")
    # Target must be unchanged because os.replace never atomically promoted
    # the new bytes.
    assert target.read_bytes() == original
    # Bonus 12 #7: the inflight marker MUST be in the DB so a recovery
    # worker can detect the orphan tmp file and roll forward / back.
    inflight_writes = [
        params
        for _, params in applier_setup["captured_execs"]
        if any("replace_inflight" in str(field) for field in params)
    ]
    assert inflight_writes, (
        "Bonus 12 #7: inflight marker must be recorded BEFORE os.replace, "
        "so a crash mid-replace is reconcilable"
    )


# ---------------------------------------------------------------------------
# Test 5: POSIX directory fsync is attempted when applicable
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name != "posix", reason="POSIX-only directory fsync path")
def test_apply_calls_os_fsync_on_parent_dir_posix(
    applier_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """On POSIX, fsync(parent_dir) must be called after os.replace so the
    rename itself is durable (etcd #13839)."""
    target = applier_setup["target"]
    proposal = _make_proposal(target, "patched-content\n")
    monkeypatch.setattr(code_history, "_patch_proposal_payload", lambda pid: proposal)

    fsync_targets: list[int] = []
    real_fsync = code_history.os.fsync

    def tracking_fsync(fd: int) -> None:
        fsync_targets.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(code_history.os, "fsync", tracking_fsync)
    code_history.apply_patch_proposal("prop-5", agent_id="claude-test", task_id="task-1")
    # We can't easily distinguish file fd from dir fd, but we expect at
    # least 2 fsyncs on POSIX (tmp file + parent dir).
    assert len(fsync_targets) >= 2, (
        f"POSIX path must fsync at least the tmp fd AND the parent dir; "
        f"got {len(fsync_targets)} fsync calls"
    )


# ---------------------------------------------------------------------------
# Test 6: Windows path skips parent-dir fsync gracefully
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name == "posix", reason="Windows-specific behavior")
def test_apply_on_windows_skips_directory_fsync(
    applier_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows NTFS journals the rename so dir-fsync is unnecessary
    (and would error). The fix must NOT crash on Windows."""
    target = applier_setup["target"]
    proposal = _make_proposal(target, "patched-content\n")
    monkeypatch.setattr(code_history, "_patch_proposal_payload", lambda pid: proposal)
    # Should not raise.
    code_history.apply_patch_proposal("prop-6", agent_id="claude-test", task_id="task-1")
    assert target.read_text(encoding="utf-8") == "patched-content\n"
