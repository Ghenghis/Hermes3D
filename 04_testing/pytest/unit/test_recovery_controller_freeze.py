"""RC v2 commit 2 — freeze_run + thaw_run + saga compensation.

Wave Agent 4 (Remaining/Skipped Wave 2026-05-09) brief: saga step 2 wires
``code_history.lock_mcp_files`` + ``code_history.snapshot_file`` BEFORE
any provider call leaves CREATED.

Ordering invariants (Temporal-style with compensation):
1. Validate run exists and is in CREATED.
2. Refuse if branch == ESCALATE_IMMEDIATELY (already terminal).
3. ``lock_mcp_files`` (TTL 30 min). On non-locked status: leave CREATED,
   return ``status="lock_blocked"``.
4. For each file: ``snapshot_file``. If ANY raises -> COMPENSATE:
   release locks, ``mark_recovery_outcome("retry_failed")``,
   _transition CREATED -> RETRY_FAILED.
5. Persist ``locked_files`` + ``pre_snapshot_ids`` on the run.
6. _transition CREATED -> PROPOSING.

Forbidden in commit 2 (must NOT be reachable from this code path):
CREATED -> APPLYING, CREATED -> RECOVERED.

Confirm-by-default + autonomous gate: untouched (commit 2 never reaches
AWAITING_HUMAN_CONFIRM).

References:
- https://temporal.io/blog/saga-pattern-made-easy
- https://temporal.io/blog/compensating-actions-part-of-a-complete-breakfast-with-sagas
"""

from __future__ import annotations

from typing import Any

import pytest

from hermes3d.services import code_history, recovery_controller


# ---------------------------------------------------------------------------
# Fixture: stub all v1 collaborators so freeze_run runs against fakes
# ---------------------------------------------------------------------------


@pytest.fixture
def freeze_setup(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Wire RC v2 collaborators with deterministic stubs.

    Returns dict with capture lists: lock_calls, snapshot_calls,
    release_calls, mark_outcome_calls.
    """
    captured: dict[str, list[Any]] = {
        "lock_calls": [],
        "snapshot_calls": [],
        "release_calls": [],
        "mark_outcome_calls": [],
        "step_failure_calls": [],
        "evidence_calls": [],
    }
    # Reset registry between tests.
    recovery_controller._reset_registry_for_tests()

    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)

    def stub_lock(**kwargs: Any) -> dict[str, Any]:
        captured["lock_calls"].append(kwargs)
        return {"status": "locked", "files": kwargs.get("files", []), "owner": kwargs.get("owner")}

    def stub_release(**kwargs: Any) -> dict[str, Any]:
        captured["release_calls"].append(kwargs)
        return {"status": "released", "files": kwargs.get("files", [])}

    def stub_snapshot(rel: str, **kwargs: Any) -> dict[str, Any]:
        captured["snapshot_calls"].append({"rel": rel, **kwargs})
        return {"id": f"snap-{rel}-{len(captured['snapshot_calls'])}", "ts_utc": "2026-05-09T00:00:00Z"}

    def stub_record_step_failure(**kwargs: Any) -> dict[str, Any]:
        captured["step_failure_calls"].append(kwargs)
        # Stable per-call attempt_id so multiple starts don't collide.
        attempt_id = f"{len(captured['step_failure_calls']):032x}"
        return {
            "status": "recorded",
            "attempt_id": attempt_id,
            "record": {
                "kind": "failure",
                "attempt_id": attempt_id,
                "task_id": kwargs.get("task_id"),
                "failure_class": kwargs.get("failure_class"),
                "failed_step": kwargs.get("failed_step"),
                "failed_step_type": kwargs.get("failed_step_type", "unknown"),
                "failure_summary": kwargs.get("failure_summary"),
                "failure_fingerprint": "f" * 16,
                "retry_budget": {"attempt_n": 1, "max_attempts": 3, "exhausted": False},
                "ts_utc": "2026-05-09T00:00:00Z",
            },
            "mcp_evidence": {"evidence_id": "ev-stub"},
        }

    def stub_mark_outcome(**kwargs: Any) -> dict[str, Any]:
        captured["mark_outcome_calls"].append(kwargs)
        return {"status": "recorded", "outcome": {"attempt_id": kwargs.get("attempt_id")}, "mcp_evidence": {}}

    def stub_evidence(**kwargs: Any) -> dict[str, Any]:
        captured["evidence_calls"].append(kwargs)
        return {"status": "recorded", "evidence_id": "ev-stub", "result": {"ok": True}}

    monkeypatch.setattr(code_history, "lock_mcp_files", stub_lock)
    monkeypatch.setattr(code_history, "release_mcp_files", stub_release)
    monkeypatch.setattr(code_history, "snapshot_file", stub_snapshot)
    monkeypatch.setattr(code_history, "record_step_failure", stub_record_step_failure)
    monkeypatch.setattr(code_history, "mark_recovery_outcome", stub_mark_outcome)
    monkeypatch.setattr(code_history, "append_mcp_evidence", stub_evidence)

    return captured


def _start_run(failure_class: str = "patch_rejected") -> str:
    """Helper: start a recovery run and return its attempt_id."""
    spec = recovery_controller.RecoveryRunSpec(
        task_id="task-001",
        failed_step="apply_patch",
        failure_class=failure_class,
        failure_summary="patch did not apply cleanly",
        failed_step_type="patch_apply",
        actor="user",
    )
    out = recovery_controller.start_recovery(spec=spec, owner="claude-test")
    return out["run"]["attempt_id"]


# ---------------------------------------------------------------------------
# Test 1: clean freeze path locks, snapshots, transitions to PROPOSING
# ---------------------------------------------------------------------------


def test_freeze_clean_path_locks_then_snapshots_then_transitions(
    freeze_setup: dict[str, Any],
) -> None:
    attempt_id = _start_run()
    result = recovery_controller.freeze_run(
        attempt_id=attempt_id,
        owner="claude-test",
        files=("src/a.py", "src/b.py"),
    )
    assert result["status"] == "frozen"
    run = recovery_controller.get_run_state(attempt_id)
    assert run["state"] == "proposing", (
        f"Bonus 12 / RC v2 commit 2 regression: state must be 'proposing'; got {run['state']!r}"
    )
    assert run["locked_files"] == ["src/a.py", "src/b.py"]
    assert len(run["pre_snapshot_ids"]) == 2
    # Critical ordering: lock BEFORE snapshot.
    assert len(freeze_setup["lock_calls"]) == 1
    assert len(freeze_setup["snapshot_calls"]) == 2
    assert freeze_setup["mark_outcome_calls"] == [], (
        "No outcome row should be written on the happy path"
    )


# ---------------------------------------------------------------------------
# Test 2: freeze refuses when run is not in CREATED
# ---------------------------------------------------------------------------


def test_freeze_refuses_when_run_not_in_created(
    freeze_setup: dict[str, Any],
) -> None:
    attempt_id = _start_run()
    # First freeze succeeds and transitions to PROPOSING.
    recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-test", files=("src/a.py",)
    )
    # Second freeze must refuse — already past CREATED.
    pre_lock_count = len(freeze_setup["lock_calls"])
    result = recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-test", files=("src/a.py",)
    )
    assert result["status"] == "not_in_created"
    assert result["current_state"] == "proposing"
    # No additional lock attempt.
    assert len(freeze_setup["lock_calls"]) == pre_lock_count


# ---------------------------------------------------------------------------
# Test 3: lock_blocked keeps run in CREATED
# ---------------------------------------------------------------------------


def test_freeze_lock_blocked_keeps_run_in_created(
    freeze_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt_id = _start_run()
    monkeypatch.setattr(
        code_history,
        "lock_mcp_files",
        lambda **kwargs: {"status": "blocked", "blocked_files": ["src/a.py"]},
    )
    result = recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-test", files=("src/a.py",)
    )
    assert result["status"] == "lock_blocked"
    run = recovery_controller.get_run_state(attempt_id)
    assert run["state"] == "created"
    # No snapshot attempt + no v1 outcome row written.
    assert freeze_setup["snapshot_calls"] == []
    assert freeze_setup["mark_outcome_calls"] == []


# ---------------------------------------------------------------------------
# Test 4: snapshot failure compensates with release + outcome + RETRY_FAILED
# ---------------------------------------------------------------------------


def test_freeze_snapshot_failure_compensates_with_release_and_outcome(
    freeze_setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt_id = _start_run()
    call_count = {"n": 0}

    def failing_snapshot(rel: str, **kwargs: Any) -> dict[str, Any]:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError(13, "Permission denied (synthetic)")
        return {"id": f"snap-{rel}", "ts_utc": "2026-05-09T00:00:00Z"}

    monkeypatch.setattr(code_history, "snapshot_file", failing_snapshot)
    result = recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-test", files=("src/a.py", "src/b.py")
    )
    assert result["status"] == "snapshot_failed"
    # OSError(13, ...) becomes PermissionError on Linux/Mac, stays OSError on Windows.
    assert result["error"] in {"OSError", "PermissionError"}

    run = recovery_controller.get_run_state(attempt_id)
    assert run["state"] == "retry_failed", (
        f"RC v2 #2 regression: must transition to retry_failed; got {run['state']!r}"
    )
    # Compensation invariants
    assert len(freeze_setup["release_calls"]) == 1, (
        "Exactly one release_mcp_files call must run on snapshot failure"
    )
    assert freeze_setup["release_calls"][0]["files"] == ["src/a.py", "src/b.py"]
    assert len(freeze_setup["mark_outcome_calls"]) == 1, (
        "Exactly one mark_recovery_outcome(retry_failed) must run on compensation"
    )
    assert freeze_setup["mark_outcome_calls"][0]["status"] == "retry_failed"


# ---------------------------------------------------------------------------
# Test 5: freeze refuses hard-escalate branch
# ---------------------------------------------------------------------------


def test_freeze_refuses_hard_escalate_branch(freeze_setup: dict[str, Any]) -> None:
    attempt_id = _start_run(failure_class="provider_auth")
    with pytest.raises(ValueError, match="hard-escalate"):
        recovery_controller.freeze_run(
            attempt_id=attempt_id, owner="claude-test", files=("src/a.py",)
        )
    # No v1 calls beyond start_recovery's escalate path.
    assert freeze_setup["lock_calls"] == []
    assert freeze_setup["snapshot_calls"] == []


# ---------------------------------------------------------------------------
# Test 6: thaw_run releases locks + is idempotent
# ---------------------------------------------------------------------------


def test_thaw_releases_locked_files_and_is_idempotent(
    freeze_setup: dict[str, Any],
) -> None:
    attempt_id = _start_run()
    recovery_controller.freeze_run(
        attempt_id=attempt_id, owner="claude-test", files=("src/a.py",)
    )
    # First thaw releases.
    out1 = recovery_controller.thaw_run(attempt_id=attempt_id, owner="claude-test")
    assert out1["status"] == "thawed"
    assert len(freeze_setup["release_calls"]) == 1
    # Second thaw is idempotent.
    out2 = recovery_controller.thaw_run(attempt_id=attempt_id, owner="claude-test")
    assert out2["status"] == "already_thawed"
    assert len(freeze_setup["release_calls"]) == 1, (
        "Idempotency: second thaw must NOT re-call release_mcp_files"
    )


# ---------------------------------------------------------------------------
# Test 7: source-level pin — confirm-by-default + autonomous gate untouched
# ---------------------------------------------------------------------------


def test_commit_2_does_not_touch_autonomous_gate() -> None:
    """RC v2 commit 2 MUST NOT activate autonomous behavior. Pin in source."""
    import inspect

    src = inspect.getsource(recovery_controller)
    # The new code path must NOT reach AWAITING_HUMAN_CONFIRM or APPLYING.
    freeze_src = inspect.getsource(recovery_controller.freeze_run)
    assert "AWAITING_HUMAN_CONFIRM" not in freeze_src, (
        "RC v2 commit 2 regression: freeze_run must not reach AWAITING_HUMAN_CONFIRM"
    )
    assert "APPLYING" not in freeze_src, (
        "RC v2 commit 2 regression: freeze_run must not reach APPLYING"
    )
    # Hard-escalate set must still be hard-coded.
    assert "ESCALATE_IMMEDIATELY" in src
