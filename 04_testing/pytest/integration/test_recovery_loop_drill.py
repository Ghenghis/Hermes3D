"""Hermes Agent Recovery Loop end-to-end drill (W5-5, 2026-05-09).

Purpose: confirm the user-mandated recovery loop works END-TO-END against
the v0.13 production-default stack. RC v2 commits 1+2 (PR #149: scaffold +
freeze_run + thaw_run + saga compensation), PR #154 (GET /api/code-operator
/recovery/runs route), and PR #171 (cross-version saga semantics pin) have
all landed; this drill exercises the full failure -> classify -> freeze ->
snapshot -> fix-proposal -> review -> apply -> thaw -> resume sequence
without burning real LLM credit (per the user's "no paid services" rule).

What is REAL in this drill:
    * recovery_controller.start_recovery (real call -> real branch selection
      via select_branch_for_class).
    * recovery_controller.freeze_run (real saga step 2 logic: validate run,
      check branch, lock-then-snapshot ordering, persist locked_files +
      pre_snapshot_ids, transition CREATED -> PROPOSING).
    * recovery_controller.thaw_run (real release + idempotency).
    * The full RecoveryRun state machine and history list.

What is MOCKED in this drill (and why):
    * code_history.lock_mcp_files / release_mcp_files / snapshot_file:
      these issue real MCP RPC calls into the orchestrator binary; in CI
      we don't have a live orchestrator, so they are stubbed to return
      deterministic dicts. The real freeze/thaw saga ordering still runs
      on top of the stubs.
    * code_history.record_step_failure / mark_recovery_outcome: write
      to JSONL ledgers and emit MCP evidence; stubbed to capture call
      kwargs without filesystem side effects.
    * "MiniMax fix proposal" and "DeepSeek review" stages: these would
      otherwise call paid provider APIs. Per MEMORY rule
      "feedback_no_paid_services", they are mocked here to return a canned
      patch proposal and an "approved" review verdict. Real wiring lives
      behind the routes that commits 3-5 will land; this drill stops at
      the in-process orchestrator surface.
    * "apply_reviewed_patch_proposal": no-op stub that records the call.
    * "run_mcp_gate" (re-run after fix): stub returns {"status": "passed"}
      so the run can transition to RECOVERED.

Sources for the saga compensation pattern:
    1. Garcia-Molina, H. & Salem, K. (1987). "Sagas." ACM SIGMOD Record,
       16(3): 249-259. The original saga paper that defines a long-lived
       transaction as a sequence of steps with per-step compensating
       actions; freeze_run's lock-then-snapshot-then-rollback structure
       follows this pattern verbatim.
    2. Hermes Agent Recovery Loop spec (user MEMORY.md
       feedback_recovery_loop, 2026-05-09): "failure -> classify -> freeze
       -> snapshot -> MiniMax fix -> DeepSeek review -> apply -> re-run ->
       resume. Never stop at first blocker." This drill enumerates that
       phase list and asserts the captured event sequence matches it.

Marker: pytest.mark.integration so the drill stays out of the default
unit sweep (per pyproject.toml addopts="-q --strict-markers").
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from hermes3d.services import code_history, recovery_controller


# ---------------------------------------------------------------------------
# Phase enum: the canonical event sequence the drill asserts on.
# ---------------------------------------------------------------------------

DRILL_PHASES: tuple[str, ...] = (
    "failure_classified",
    "freeze",
    "snapshot",
    "fix_proposal",
    "review",
    "apply",
    "thaw",
    "resume",
)


# Patterns that would indicate an accidentally-leaked secret in any captured
# payload. These match the project's existing redaction surface; the drill
# walks every captured payload and asserts none of them appear.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9]{20,}"),         # OpenAI/Anthropic-style keys
    re.compile(r"AKIA[0-9A-Z]{16}"),            # AWS access key IDs
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),        # GitHub PATs
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack tokens
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),  # PEM material
)


def _assert_no_secret(payload: Any, where: str) -> None:
    """Recursively walk a captured payload + assert nothing matches a secret regex."""
    if payload is None:
        return
    if isinstance(payload, str):
        for pat in _SECRET_PATTERNS:
            assert not pat.search(payload), (
                f"Secret-like material leaked at {where}: matched {pat.pattern!r}"
            )
        return
    if isinstance(payload, dict):
        for k, v in payload.items():
            _assert_no_secret(k, f"{where}.<key>")
            _assert_no_secret(v, f"{where}.{k}")
        return
    if isinstance(payload, (list, tuple)):
        for i, v in enumerate(payload):
            _assert_no_secret(v, f"{where}[{i}]")
        return
    # Other primitives (int, bool, float) are inherently safe.


# ---------------------------------------------------------------------------
# Drill harness fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def drill_setup(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Wire RC v2 collaborators with deterministic stubs and an event capture log.

    The ``events`` list is the single source of truth the drill asserts on:
    every phase appends one entry with ``phase`` + a redacted snapshot of the
    relevant payload. Real freeze/thaw orchestration runs on top of these
    stubs; the stubs only replace the v1 ledger primitives + the LLM/apply
    steps that would otherwise need paid credentials or live MCP I/O.
    """
    events: list[dict[str, Any]] = []
    captured: dict[str, list[Any]] = {
        "lock_calls": [],
        "snapshot_calls": [],
        "release_calls": [],
        "mark_outcome_calls": [],
        "step_failure_calls": [],
    }
    recovery_controller._reset_registry_for_tests()

    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)

    def stub_lock(**kwargs: Any) -> dict[str, Any]:
        captured["lock_calls"].append(kwargs)
        events.append({
            "phase": "freeze",
            "files": list(kwargs.get("files", [])),
            "ttl_minutes": kwargs.get("ttl_minutes"),
        })
        return {
            "status": "locked",
            "files": kwargs.get("files", []),
            "owner": kwargs.get("owner"),
        }

    def stub_release(**kwargs: Any) -> dict[str, Any]:
        captured["release_calls"].append(kwargs)
        events.append({
            "phase": "thaw",
            "files": list(kwargs.get("files", [])),
            "note": kwargs.get("note", ""),
        })
        return {"status": "released", "files": kwargs.get("files", [])}

    def stub_snapshot(rel: str, **kwargs: Any) -> dict[str, Any]:
        captured["snapshot_calls"].append({"rel": rel, **kwargs})
        events.append({
            "phase": "snapshot",
            "rel": rel,
            "action_id": kwargs.get("action_id"),
        })
        snap_id = f"snap-{rel.replace('/', '_')}-{len(captured['snapshot_calls'])}"
        return {"id": snap_id, "ts_utc": "2026-05-09T00:00:00Z"}

    def stub_record_step_failure(**kwargs: Any) -> dict[str, Any]:
        captured["step_failure_calls"].append(kwargs)
        events.append({
            "phase": "failure_classified",
            "task_id": kwargs.get("task_id"),
            "failure_class": kwargs.get("failure_class"),
            "failed_step_type": kwargs.get("failed_step_type"),
        })
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
                # 16-char fingerprint matches code_history's hex digest length.
                "failure_fingerprint": "abcdef0123456789",
                "retry_budget": {"attempt_n": 1, "max_attempts": 3, "exhausted": False},
                "ts_utc": "2026-05-09T00:00:00Z",
            },
            "mcp_evidence": {"evidence_id": "ev-stub-failure"},
        }

    def stub_mark_outcome(**kwargs: Any) -> dict[str, Any]:
        captured["mark_outcome_calls"].append(kwargs)
        events.append({
            "phase": "resume",
            "attempt_id": kwargs.get("attempt_id"),
            "status": kwargs.get("status"),
            "summary": kwargs.get("recovery_summary", "")[:80],
        })
        return {
            "status": "recorded",
            "outcome": {
                "attempt_id": kwargs.get("attempt_id"),
                "status": kwargs.get("status"),
            },
            "mcp_evidence": {"evidence_id": "ev-stub-outcome"},
        }

    monkeypatch.setattr(code_history, "lock_mcp_files", stub_lock)
    monkeypatch.setattr(code_history, "release_mcp_files", stub_release)
    monkeypatch.setattr(code_history, "snapshot_file", stub_snapshot)
    monkeypatch.setattr(code_history, "record_step_failure", stub_record_step_failure)
    monkeypatch.setattr(code_history, "mark_recovery_outcome", stub_mark_outcome)

    return {"events": events, "captured": captured}


# ---------------------------------------------------------------------------
# Mocked external phases (would otherwise need paid LLM credit)
# ---------------------------------------------------------------------------


def _mock_minimax_fix_proposal(
    *,
    events: list[dict[str, Any]],
    attempt_id: str,
    failed_step: str,
) -> dict[str, Any]:
    """Stand-in for a real MiniMax coding-pass call.

    A live wiring would POST to /api/code-operator/recovery/propose with
    the failed step + context pack and stream a coding proposal back. Here
    we emit a deterministic canned proposal so the drill stays free.
    """
    proposal = {
        "proposal_id": f"prop-{attempt_id[:8]}",
        "diff_preview": (
            "--- a/scripts/cli_runner.py\n"
            "+++ b/scripts/cli_runner.py\n"
            "@@ -42,7 +42,7 @@\n"
            "-    timeout = 5\n"
            "+    timeout = 30  # raise: cli runner needs >5s for cold start\n"
        ),
        "files_touched": ["scripts/cli_runner.py"],
        "rationale": (
            f"Failed step {failed_step!r} timed out at 5s; raising the "
            "runner timeout to 30s addresses the symptom without changing behavior."
        ),
        "model_meta": {
            "provider": "minimax_mock",
            "model": "drill-fixture",
            "credit_spent_usd": 0.0,
        },
    }
    events.append({"phase": "fix_proposal", **{k: v for k, v in proposal.items() if k != "diff_preview"}})
    return proposal


def _mock_deepseek_review(
    *,
    events: list[dict[str, Any]],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    """Stand-in for a real DeepSeek adversarial-review pass."""
    review = {
        "review_id": f"rev-{proposal['proposal_id']}",
        "verdict": "approved",
        "concerns": [],
        "files_reviewed": list(proposal["files_touched"]),
        "model_meta": {
            "provider": "deepseek_mock",
            "model": "drill-fixture",
            "credit_spent_usd": 0.0,
        },
    }
    events.append({"phase": "review", **review})
    return review


def _mock_apply_reviewed_patch(
    *,
    events: list[dict[str, Any]],
    proposal: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    """Stand-in for code_operator.apply_reviewed_patch_proposal.

    No-op apply; in production this would write the patch to disk + commit.
    The drill records the apply event to confirm sequence ordering.
    """
    assert review["verdict"] == "approved", "Apply must only run on approved review"
    apply_record = {
        "apply_evidence_id": f"apply-{proposal['proposal_id']}",
        "files_changed": list(proposal["files_touched"]),
        "applied": True,
    }
    events.append({"phase": "apply", **apply_record})
    return apply_record


def _mock_re_run_gate(
    *,
    events: list[dict[str, Any]],
    failed_step: str,
) -> dict[str, Any]:
    """Stand-in for the gate re-run after the fix lands. Always passes in the drill."""
    gate = {
        "gate_id": f"gate-{failed_step}-rerun",
        "status": "passed",
        "duration_seconds": 0.42,
    }
    # Re-run is part of the apply->resume bridge; we don't emit a separate
    # phase here because the resume phase below logs the terminal outcome.
    return gate


# ---------------------------------------------------------------------------
# The drill itself
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_recovery_loop_drill_end_to_end(drill_setup: dict[str, Any]) -> None:
    """Full failure -> resume drill against the v0.13 production-default stack.

    Synthetic failure: a "cli_runner" task timing out at 5s. Failure class
    ``runner_fail`` is in the auto-attemptable set (per
    ``recovery_controller._AUTO_BRANCH_TABLE``), so the run enters
    ``REFRESH_CONTEXT_RETRY_ONCE`` branch and proceeds through freeze.
    """
    events: list[dict[str, Any]] = drill_setup["events"]
    captured = drill_setup["captured"]

    # --------- Phase 1: synthetic failure + classify (real start_recovery) ---------
    spec = recovery_controller.RecoveryRunSpec(
        task_id="drill-task-w55",
        failed_step="cli_runner.exec",
        failure_class="runner_fail",
        failed_step_type="provider_smoke",
        failure_summary="cli runner timed out after 5s on cold start",
        actor="user",
        confirm=False,  # confirm-by-default policy: do not auto-apply
        agent_stack=("claude-w5-5",),
        retry_budget_max=3,
    )
    start_result = recovery_controller.start_recovery(spec=spec, owner="claude-w5-5-drill")
    assert start_result["status"] == "created", (
        f"Drill setup invariant: runner_fail is auto-attemptable, "
        f"expected status='created' but got {start_result['status']!r}"
    )
    attempt_id: str = start_result["run"]["attempt_id"]
    assert start_result["run"]["state"] == "created"
    assert start_result["run"]["branch"] == "refresh_context_retry_once"

    # --------- Phase 2 + 3: freeze + snapshot (real freeze_run) ---------
    files_to_freeze = ("scripts/cli_runner.py",)
    freeze_result = recovery_controller.freeze_run(
        attempt_id=attempt_id,
        owner="claude-w5-5-drill",
        files=files_to_freeze,
    )
    assert freeze_result["status"] == "frozen"
    state_after_freeze = recovery_controller.get_run_state(attempt_id)
    assert state_after_freeze["state"] == "proposing", (
        "Saga step 2: freeze_run must transition CREATED -> PROPOSING"
    )
    assert state_after_freeze["locked_files"] == list(files_to_freeze)
    assert len(state_after_freeze["pre_snapshot_ids"]) == 1
    assert state_after_freeze["freeze_event_utc"] != ""

    # --------- Phase 4: MiniMax fix proposal (mocked) ---------
    proposal = _mock_minimax_fix_proposal(
        events=events,
        attempt_id=attempt_id,
        failed_step=spec.failed_step,
    )
    assert proposal["proposal_id"]
    assert proposal["model_meta"]["credit_spent_usd"] == 0.0, (
        "no_paid_services rule: drill MUST NOT spend real credit"
    )

    # --------- Phase 5: DeepSeek review (mocked) ---------
    review = _mock_deepseek_review(events=events, proposal=proposal)
    assert review["verdict"] == "approved"
    assert review["model_meta"]["credit_spent_usd"] == 0.0

    # --------- Phase 6: apply (mocked no-op) ---------
    apply_record = _mock_apply_reviewed_patch(
        events=events, proposal=proposal, review=review
    )
    assert apply_record["applied"] is True

    # --------- Phase 7: thaw (real thaw_run) ---------
    thaw_result = recovery_controller.thaw_run(
        attempt_id=attempt_id,
        owner="claude-w5-5-drill",
        note="drill apply complete; releasing pre-recovery locks",
    )
    assert thaw_result["status"] == "thawed"
    state_after_thaw = recovery_controller.get_run_state(attempt_id)
    assert state_after_thaw["locked_files"] == [], "Thaw must clear locked_files"

    # --------- Phase 8: re-run + resume (mocked re-run, real mark_outcome) ---------
    gate_rerun = _mock_re_run_gate(events=events, failed_step=spec.failed_step)
    assert gate_rerun["status"] == "passed"
    # Real mark_recovery_outcome closes the v1 ledger row; stubbed here but
    # exercises the real call shape so a future un-mock would be drop-in.
    outcome = code_history.mark_recovery_outcome(
        owner="claude-w5-5-drill",
        attempt_id=attempt_id,
        status="recovered",
        recovery_summary="drill: synthetic runner_fail recovered via mocked propose+review+apply",
    )
    assert outcome["outcome"]["status"] == "recovered"

    # --------- Phase 9: assert canonical event sequence ---------
    phases_seen = tuple(ev["phase"] for ev in events)
    # Snapshots can repeat (one per file); collapse consecutive duplicates
    # before comparing to DRILL_PHASES.
    collapsed: list[str] = []
    for p in phases_seen:
        if not collapsed or collapsed[-1] != p:
            collapsed.append(p)
    assert tuple(collapsed) == DRILL_PHASES, (
        f"Drill phase ordering broke: expected {DRILL_PHASES}, got {tuple(collapsed)}"
    )

    # --------- Phase 10: assert no secret leaked anywhere ---------
    for i, ev in enumerate(events):
        _assert_no_secret(ev, f"events[{i}]")
    for kind, calls in captured.items():
        _assert_no_secret(calls, f"captured.{kind}")
    _assert_no_secret(start_result, "start_result")
    _assert_no_secret(freeze_result, "freeze_result")
    _assert_no_secret(thaw_result, "thaw_result")
    _assert_no_secret(proposal, "proposal")
    _assert_no_secret(review, "review")
    _assert_no_secret(apply_record, "apply_record")

    # --------- Phase 11: invariants ---------
    # Lock count = 1; release count = 1; snapshot count = len(files); outcome = 1.
    assert len(captured["lock_calls"]) == 1
    assert len(captured["release_calls"]) == 1
    assert len(captured["snapshot_calls"]) == len(files_to_freeze)
    assert len(captured["mark_outcome_calls"]) == 1
    # The lock call must come BEFORE any snapshot call (saga ordering rule).
    # Compare phase indices in events.
    first_freeze_idx = next(i for i, ev in enumerate(events) if ev["phase"] == "freeze")
    first_snapshot_idx = next(i for i, ev in enumerate(events) if ev["phase"] == "snapshot")
    assert first_freeze_idx < first_snapshot_idx, (
        "Saga step 2 ordering invariant: lock_mcp_files MUST run before snapshot_file"
    )
    # Apply must come AFTER review.
    apply_idx = next(i for i, ev in enumerate(events) if ev["phase"] == "apply")
    review_idx = next(i for i, ev in enumerate(events) if ev["phase"] == "review")
    assert review_idx < apply_idx
    # Thaw must come AFTER apply.
    thaw_idx = next(i for i, ev in enumerate(events) if ev["phase"] == "thaw")
    assert apply_idx < thaw_idx


@pytest.mark.integration
def test_recovery_loop_drill_hard_escalate_short_circuits_freeze(
    drill_setup: dict[str, Any],
) -> None:
    """Hard-escalate failure classes (provider_auth, secret_risk, sandbox_fail)
    must short-circuit at start_recovery and refuse to enter the freeze phase.

    This is the security invariant from recovery_controller._HARD_ESCALATE_CLASSES:
    auto-recovery on these classes is unsafe (would risk leaking secrets, masking
    auth misconfiguration, or running unverified code in a broken sandbox).
    """
    events: list[dict[str, Any]] = drill_setup["events"]
    captured = drill_setup["captured"]

    spec = recovery_controller.RecoveryRunSpec(
        task_id="drill-task-w55-escalate",
        failed_step="provider.auth_check",
        failure_class="provider_auth",  # hard-escalate
        failed_step_type="provider_smoke",
        failure_summary="provider rejected api key (synthetic)",
        actor="user",
    )
    result = recovery_controller.start_recovery(spec=spec, owner="claude-w5-5-drill")
    assert result["status"] == "hard_escalated"
    assert result["run"]["state"] == "escalated"
    assert result["run"]["is_terminal"] is True

    # Trying to freeze a hard-escalated run must raise.
    attempt_id = result["run"]["attempt_id"]
    with pytest.raises(ValueError, match="hard-escalate"):
        recovery_controller.freeze_run(
            attempt_id=attempt_id,
            owner="claude-w5-5-drill",
            files=("nope.py",),
        )

    # No locks acquired, no snapshots taken.
    assert captured["lock_calls"] == []
    assert captured["snapshot_calls"] == []
    # Single failure_classified event + single mark_outcome (the escalate close).
    classified = [ev for ev in events if ev["phase"] == "failure_classified"]
    assert len(classified) == 1
    # No fix_proposal / review / apply events allowed for hard-escalate.
    for forbidden in ("fix_proposal", "review", "apply"):
        assert all(ev["phase"] != forbidden for ev in events), (
            f"Hard-escalate path emitted forbidden phase {forbidden!r}"
        )
