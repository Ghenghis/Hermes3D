"""Hermes Agent Recovery Controller v2 — active orchestrator on top of v1 ledger.

Scope of THIS commit (1 of 5):
    * Public types for the recovery state machine.
    * In-memory run registry keyed by attempt_id.
    * Idempotency on (task_id, failure_fingerprint) so re-fired failures with
      the same fingerprint reuse the existing run.
    * Failure-class -> initial-branch decision table; provider_auth, secret_risk,
      and sandbox_fail are HARD-CODED to escalate immediately and cannot be
      overridden by the caller.
    * start_recovery / get_run_state / cancel_run / list_active_runs read+write
      surface that callers (the routes in commit 2, and tests in commit 3) drive.
    * Confirm-by-default policy: every run that requires patch application must
      reach 'awaiting_human_confirm' first; only an explicit caller-side
      confirmation transitions to 'applying'. Autonomous mode is gated behind
      HERMES_RECOVERY_AUTONOMOUS=1 AND requires confirm=True at start_recovery
      time; this commit deliberately does NOT activate autonomous behavior.

Out of scope for this commit (will land in commits 2-5):
    * HTTP routes (commit 2).
    * Calls into MiniMax / DeepSeek / apply_reviewed_patch_proposal /
      run_mcp_gate (commit 2).
    * Pytest unit suite (commit 3).
    * Agents.tsx UI panel (commit 4).
    * Review packet + adversarial walk-through (commit 5).

The controller is a thin coordinator. v1's ledger
(code_history.record_step_failure / mark_recovery_outcome) remains the source
of truth; v2 only composes that ledger plus a transient in-memory registry to
track the live state of each run between v1 ledger writes.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hermes3d.services import code_history


# ---------------------------------------------------------------------------
# State machine types
# ---------------------------------------------------------------------------

class RecoveryState(str, Enum):
    """Live state of a recovery run.

    The string values are stable wire formats — they appear in HTTP responses
    (commit 2) and in the UI (commit 4). Do NOT rename existing values; add new
    ones at the end if needed.
    """

    CREATED = "created"
    PROPOSING = "proposing"
    REVIEWING = "reviewing"
    AWAITING_HUMAN_CONFIRM = "awaiting_human_confirm"
    APPLYING = "applying"
    RE_RUNNING_GATE = "re_running_gate"
    RECOVERED = "recovered"
    RETRY_FAILED = "retry_failed"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in _TERMINAL_STATES

    @property
    def is_cancellable(self) -> bool:
        # Mid-apply cancel is forbidden: a partially-applied patch is worse
        # than a fully-applied or fully-rolled-back one.
        return self in _CANCELLABLE_STATES


_TERMINAL_STATES: frozenset[RecoveryState] = frozenset({
    RecoveryState.RECOVERED,
    RecoveryState.RETRY_FAILED,
    RecoveryState.ESCALATED,
    RecoveryState.CANCELLED,
})

_CANCELLABLE_STATES: frozenset[RecoveryState] = frozenset({
    RecoveryState.CREATED,
    RecoveryState.PROPOSING,
    RecoveryState.REVIEWING,
    RecoveryState.AWAITING_HUMAN_CONFIRM,
    RecoveryState.RE_RUNNING_GATE,
    # APPLYING is intentionally NOT cancellable.
})


# ---------------------------------------------------------------------------
# Failure-class -> initial branch decision table
# ---------------------------------------------------------------------------

class RecoveryBranch(str, Enum):
    """Which playbook branch the controller takes after recording a failure."""

    PROPOSE_REVIEW_APPLY_RERUN = "propose_review_apply_rerun"
    PROPOSE_WITH_REDUCED_CONTEXT = "propose_with_reduced_context"
    REFRESH_CONTEXT_THEN_RETRY_STEP = "refresh_context_then_retry_step"
    ROLLBACK_THEN_RETRY = "rollback_then_retry"
    REFRESH_CONTEXT_RETRY_ONCE = "refresh_context_retry_once"
    PROPOSE_REVIEW_APPLY_RERUN_VISUAL = "propose_review_apply_rerun_visual"
    ESCALATE_IMMEDIATELY = "escalate_immediately"


# Hard rule: classes in this set ALWAYS escalate, regardless of caller intent.
# These are the security/auth/env classes where auto-recovery is unsafe.
_HARD_ESCALATE_CLASSES: frozenset[str] = frozenset({
    "provider_auth",
    "secret_risk",
    "sandbox_fail",
})


# Auto-attemptable classes (can enter the propose/review loop). The mapping
# returns the playbook branch a fresh run would take.
_AUTO_BRANCH_TABLE: dict[str, RecoveryBranch] = {
    "gate_fail": RecoveryBranch.PROPOSE_REVIEW_APPLY_RERUN,
    "patch_rejected": RecoveryBranch.PROPOSE_WITH_REDUCED_CONTEXT,
    "missing_proof": RecoveryBranch.REFRESH_CONTEXT_THEN_RETRY_STEP,
    "merge_git_fail": RecoveryBranch.ROLLBACK_THEN_RETRY,
    "runner_fail": RecoveryBranch.REFRESH_CONTEXT_RETRY_ONCE,
    "ui_fail": RecoveryBranch.PROPOSE_REVIEW_APPLY_RERUN_VISUAL,
}


def select_branch_for_class(failure_class: str) -> RecoveryBranch:
    """Return the playbook branch for a given failure class.

    Hard-escalate classes (provider_auth, secret_risk, sandbox_fail) ALWAYS
    return ESCALATE_IMMEDIATELY and cannot be overridden. This is by design:
    auto-recovery on these classes would risk leaking secrets, masking
    auth misconfiguration, or running unverified code in a broken sandbox.

    Raises ValueError if the class is not in the v1 enum
    (code_history.RECOVERY_FAILURE_CLASSES).
    """
    if failure_class not in code_history.RECOVERY_FAILURE_CLASSES:
        raise ValueError(
            f"failure_class {failure_class!r} is not in "
            f"code_history.RECOVERY_FAILURE_CLASSES; reuse v1 enum."
        )
    if failure_class in _HARD_ESCALATE_CLASSES:
        return RecoveryBranch.ESCALATE_IMMEDIATELY
    return _AUTO_BRANCH_TABLE.get(failure_class, RecoveryBranch.ESCALATE_IMMEDIATELY)


# ---------------------------------------------------------------------------
# Run dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecoveryRunSpec:
    """Immutable input parameters for a recovery run.

    Mirrors the v1 record_step_failure signature so the controller can pass
    these straight through. The ``confirm`` flag is the caller's explicit
    statement that they want the controller to proceed past
    AWAITING_HUMAN_CONFIRM; without it the run halts at that state and waits
    for a follow-up confirm call. This is the "confirm-by-default" policy.
    """

    task_id: str
    failed_step: str
    failure_class: str  # validated against code_history.RECOVERY_FAILURE_CLASSES
    failed_step_type: str  # validated against code_history.RECOVERY_FAILED_STEP_TYPES
    failure_summary: str
    actor: str = "user"  # "user" (default) or "autonomous" (gated; see below)
    confirm: bool = False
    relative_path: str | None = None
    context_pack: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    retry_budget_max: int = 3
    agent_stack: tuple[str, ...] = ()
    resume_from_step: str = ""
    redaction_status: str = "pass"
    worker_output_status: str = "complete"


@dataclass
class RecoveryRun:
    """Live state of a recovery run.

    Backed by a v1 ledger row (attempt_id matches code_history's secrets.token_hex(16),
    32-char lowercase hex). Fields here that are not on the v1 ledger row are
    transient in-process state managed by this controller.
    """

    attempt_id: str
    spec: RecoveryRunSpec
    state: RecoveryState
    branch: RecoveryBranch
    failure_fingerprint: str
    retry_count: int = 0
    started_utc: str = ""
    last_event_utc: str = ""
    last_event_summary: str = ""
    proposal_id: str | None = None
    review_evidence_id: str | None = None
    apply_evidence_id: str | None = None
    retry_gate_id: str | None = None
    terminal_status: str | None = None  # one of code_history.RECOVERY_OUTCOME_STATUSES
    cancelled_reason: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_state_payload(self) -> dict[str, Any]:
        """Render the public state payload (used by /state route in commit 2)."""
        return {
            "attempt_id": self.attempt_id,
            "task_id": self.spec.task_id,
            "state": self.state.value,
            "branch": self.branch.value,
            "failure_class": self.spec.failure_class,
            "failed_step_type": self.spec.failed_step_type,
            "failure_fingerprint": self.failure_fingerprint,
            "retry_count": self.retry_count,
            "retry_budget_max": self.spec.retry_budget_max,
            "actor": self.spec.actor,
            "confirm": self.spec.confirm,
            "started_utc": self.started_utc,
            "last_event_utc": self.last_event_utc,
            "last_event_summary": self.last_event_summary,
            "proposal_id": self.proposal_id,
            "review_evidence_id": self.review_evidence_id,
            "apply_evidence_id": self.apply_evidence_id,
            "retry_gate_id": self.retry_gate_id,
            "terminal_status": self.terminal_status,
            "cancelled_reason": self.cancelled_reason,
            "is_terminal": self.state.is_terminal,
            "is_cancellable": self.state.is_cancellable,
            "next_action": _describe_next_action(self.state, self.branch),
        }


def _describe_next_action(state: RecoveryState, branch: RecoveryBranch) -> str:
    """Human-readable hint about what the controller will do next."""
    if state.is_terminal:
        return "none (run is terminal)"
    if state == RecoveryState.CREATED:
        if branch == RecoveryBranch.ESCALATE_IMMEDIATELY:
            return "escalate immediately (hard-escalate failure class)"
        return f"start branch: {branch.value}"
    if state == RecoveryState.PROPOSING:
        return "waiting for MiniMax coding pass"
    if state == RecoveryState.REVIEWING:
        return "waiting for DeepSeek review pass"
    if state == RecoveryState.AWAITING_HUMAN_CONFIRM:
        return "waiting for user confirm to apply reviewed proposal"
    if state == RecoveryState.APPLYING:
        return "applying reviewed proposal"
    if state == RecoveryState.RE_RUNNING_GATE:
        return "re-running failed gate to verify fix"
    return "unknown"


# ---------------------------------------------------------------------------
# In-memory run registry
# ---------------------------------------------------------------------------

# Maps attempt_id -> RecoveryRun
_RUNS: dict[str, RecoveryRun] = {}

# Maps (task_id, failure_fingerprint) -> attempt_id, but only while the
# pointed-to run is non-terminal. Used for idempotency on start_recovery.
_OPEN_BY_FINGERPRINT: dict[tuple[str, str], str] = {}

# Single coarse-grained lock. Recovery runs are rare and short relative to
# routine HTTP traffic; finer locking would just add risk without measurable
# throughput gain.
_REGISTRY_LOCK = threading.Lock()


def _autonomous_mode_enabled() -> bool:
    """True only if HERMES_RECOVERY_AUTONOMOUS=1 in os.environ.

    Default is False. Confirm-by-default policy depends on this gate.
    """
    return os.environ.get("HERMES_RECOVERY_AUTONOMOUS", "").strip() == "1"


# ---------------------------------------------------------------------------
# Public API (read+write surface; routes in commit 2 wrap these)
# ---------------------------------------------------------------------------

def start_recovery(
    *,
    spec: RecoveryRunSpec,
    owner: str,
) -> dict[str, Any]:
    """Begin a recovery run for the given failure spec.

    Behavior:
        1. Validates ``spec.failure_class`` and ``spec.failed_step_type``
           against v1's enums; raises ValueError on unknown values.
        2. Computes the failure fingerprint identically to v1
           (``code_history._recovery_failure_fingerprint``).
        3. **Idempotency**: if a non-terminal run already exists for
           ``(task_id, fingerprint)``, returns it with status="duplicate" —
           does NOT create a new ledger row. Caller can poll its state.
        4. Otherwise calls ``code_history.record_step_failure`` to allocate a
           fresh attempt_id and write the v1 ledger row + emit MCP evidence.
        5. Selects the playbook branch via ``select_branch_for_class``.
        6. Hard-escalate classes immediately transition to ESCALATED and
           write the v1 outcome via ``code_history.mark_recovery_outcome``.
        7. Auto-attemptable classes enter state CREATED and remain there
           until commit 2 wires the actual propose/review/apply pipeline.
           This commit does NOT mutate state past CREATED for non-escalating
           classes.

    Returns dict with keys:
        status: "created" | "duplicate" | "hard_escalated"
        run: state payload (from RecoveryRun.to_state_payload)
        ledger_record: full v1 record (from record_step_failure)
        mcp_evidence: v1 evidence row (from record_step_failure)
        outcome (only on hard_escalated): the v1 outcome row

    Confirm-by-default: ``spec.confirm`` is recorded but does NOT cause the
    controller to apply anything in this commit. A future commit (2) will
    only honor confirm=True when transitioning out of AWAITING_HUMAN_CONFIRM.
    Autonomous mode (``spec.actor == "autonomous"``) requires both the
    HERMES_RECOVERY_AUTONOMOUS env flag AND ``spec.confirm=True``; otherwise
    the run still halts at AWAITING_HUMAN_CONFIRM (when commit 2 lands).
    """
    if spec.failure_class not in code_history.RECOVERY_FAILURE_CLASSES:
        raise ValueError(
            f"failure_class {spec.failure_class!r} not in v1 enum; "
            f"valid: {sorted(code_history.RECOVERY_FAILURE_CLASSES)}"
        )
    if spec.failed_step_type not in code_history.RECOVERY_FAILED_STEP_TYPES:
        raise ValueError(
            f"failed_step_type {spec.failed_step_type!r} not in v1 enum; "
            f"valid: {sorted(code_history.RECOVERY_FAILED_STEP_TYPES)}"
        )
    if spec.actor not in ("user", "autonomous"):
        raise ValueError(f"actor must be 'user' or 'autonomous'; got {spec.actor!r}.")
    if spec.actor == "autonomous":
        if not _autonomous_mode_enabled():
            raise PermissionError(
                "actor='autonomous' requires HERMES_RECOVERY_AUTONOMOUS=1; "
                "this is intentionally off by default in v2."
            )
        if not spec.confirm:
            raise PermissionError(
                "actor='autonomous' also requires confirm=True at start_recovery time."
            )
    if spec.retry_budget_max < 1 or spec.retry_budget_max > 32:
        raise ValueError("retry_budget_max must be in 1..32.")

    # Compute fingerprint exactly like v1 so a v1 record_step_failure result
    # would carry the same fingerprint we use for idempotency lookup.
    fingerprint = code_history._recovery_failure_fingerprint(
        failure_class=spec.failure_class,
        failed_step_type=spec.failed_step_type,
        failed_step=spec.failed_step,
        failure_summary=spec.failure_summary,
    )
    fingerprint_key = (spec.task_id, fingerprint)

    with _REGISTRY_LOCK:
        existing_attempt_id = _OPEN_BY_FINGERPRINT.get(fingerprint_key)
        if existing_attempt_id is not None:
            existing_run = _RUNS.get(existing_attempt_id)
            if existing_run is not None and not existing_run.state.is_terminal:
                return {
                    "status": "duplicate",
                    "run": existing_run.to_state_payload(),
                    "ledger_record": None,
                    "mcp_evidence": None,
                }
            # Stale entry in the index — clean it.
            _OPEN_BY_FINGERPRINT.pop(fingerprint_key, None)

    # Allocate via v1; this also writes the failure ledger row + MCP evidence.
    v1_result = code_history.record_step_failure(
        owner=owner,
        task_id=spec.task_id,
        failed_step=spec.failed_step,
        failure_class=spec.failure_class,
        failure_summary=spec.failure_summary,
        failed_step_type=spec.failed_step_type,
        agent_stack=list(spec.agent_stack),
        resume_from_step=spec.resume_from_step,
        recommended_next_action="none",  # controller chooses; v1 row stores fallback
        redaction_status=spec.redaction_status,
        worker_output_status=spec.worker_output_status,
        context_pack=list(spec.context_pack),
        provenance_ids=list(spec.provenance_ids),
        attempt_n=1,
        max_attempts=spec.retry_budget_max,
    )
    attempt_id: str = v1_result["attempt_id"]
    ledger_record: dict[str, Any] = v1_result["record"]

    # The v1 fingerprint is computed from the *redacted* summary inside
    # record_step_failure, while ours uses the raw summary. They typically
    # match because redact_text is a no-op on assertion text, but use the
    # ledger's value for the canonical fingerprint we index against.
    canonical_fingerprint: str = ledger_record["failure_fingerprint"]
    canonical_key = (spec.task_id, canonical_fingerprint)

    branch = select_branch_for_class(spec.failure_class)
    started_utc: str = ledger_record["ts_utc"]

    run = RecoveryRun(
        attempt_id=attempt_id,
        spec=spec,
        state=RecoveryState.CREATED,
        branch=branch,
        failure_fingerprint=canonical_fingerprint,
        started_utc=started_utc,
        last_event_utc=started_utc,
        last_event_summary="run created from failure record",
    )
    run.history.append({
        "ts_utc": started_utc,
        "from": None,
        "to": RecoveryState.CREATED.value,
        "note": f"created branch={branch.value} fingerprint={canonical_fingerprint}",
    })

    with _REGISTRY_LOCK:
        _RUNS[attempt_id] = run
        _OPEN_BY_FINGERPRINT[canonical_key] = attempt_id

    if branch == RecoveryBranch.ESCALATE_IMMEDIATELY:
        # Hard-escalate path: transition to ESCALATED and close the v1 row now.
        outcome_summary = (
            f"hard-escalate failure class {spec.failure_class}; "
            f"controller refuses auto-recovery for security/env reasons."
        )[:400]
        v1_outcome = code_history.mark_recovery_outcome(
            owner=owner,
            attempt_id=attempt_id,
            status="escalated",
            recovery_summary=outcome_summary,
        )
        _transition(
            run,
            new_state=RecoveryState.ESCALATED,
            note=outcome_summary,
            terminal_status="escalated",
        )
        return {
            "status": "hard_escalated",
            "run": run.to_state_payload(),
            "ledger_record": ledger_record,
            "mcp_evidence": v1_result["mcp_evidence"],
            "outcome": v1_outcome["outcome"],
        }

    return {
        "status": "created",
        "run": run.to_state_payload(),
        "ledger_record": ledger_record,
        "mcp_evidence": v1_result["mcp_evidence"],
    }


def get_run_state(attempt_id: str) -> dict[str, Any] | None:
    """Return the public state payload for a run, or None if unknown.

    Lookup is in-memory only (no ledger replay); a server restart between
    failure recording and state polling will return None — callers should
    fall back to v1's GET /recovery/state in that case.
    """
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return None
        return run.to_state_payload()


def cancel_run(*, attempt_id: str, owner: str, reason: str = "") -> dict[str, Any]:
    """Cancel a non-terminal run.

    If the run is already terminal, returns status="already_terminal" without
    side effects. If the run is in APPLYING, refuses the cancel (a partial
    apply is more dangerous than letting it finish). Otherwise transitions
    to CANCELLED and writes the v1 outcome row with status="retry_failed"
    (the v1 enum has no 'cancelled' status; we record cancellation as
    retry_failed with a recovery_summary that names the reason).
    """
    clean_reason = (reason or "user cancelled").strip()[:400] or "user cancelled"
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if run.state.is_terminal:
            return {
                "status": "already_terminal",
                "attempt_id": attempt_id,
                "state": run.state.value,
                "terminal_status": run.terminal_status,
            }
        if not run.state.is_cancellable:
            return {
                "status": "not_cancellable",
                "attempt_id": attempt_id,
                "state": run.state.value,
                "reason": (
                    "Run is in APPLYING state; cancelling now would risk a "
                    "partially applied patch. Wait for the apply step to finish."
                ),
            }

    # Write v1 outcome OUTSIDE the registry lock — the v1 helper acquires its
    # own MCP lock guard and we don't want to hold our local lock during file IO.
    summary = f"run cancelled: {clean_reason}"[:400]
    v1_outcome = code_history.mark_recovery_outcome(
        owner=owner,
        attempt_id=attempt_id,
        status="retry_failed",  # v1 enum has no 'cancelled'; closest signal
        recovery_summary=summary,
    )

    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        # Re-check terminal: another caller may have transitioned it.
        if run.state.is_terminal:
            return {
                "status": "race_already_terminal",
                "attempt_id": attempt_id,
                "state": run.state.value,
                "terminal_status": run.terminal_status,
            }
        run.cancelled_reason = clean_reason
        _transition(
            run,
            new_state=RecoveryState.CANCELLED,
            note=summary,
            terminal_status="retry_failed",
        )
        payload = run.to_state_payload()

    return {
        "status": "cancelled",
        "attempt_id": attempt_id,
        "run": payload,
        "outcome": v1_outcome["outcome"],
    }


def list_active_runs(*, task_id: str | None = None) -> dict[str, Any]:
    """Return a snapshot of currently-tracked runs (terminal and non-terminal).

    The in-memory registry only holds runs from the current process lifetime.
    For the durable history, callers should use v1's
    ``code_history.list_recovery_attempts``. This function is the live
    counterpart.
    """
    with _REGISTRY_LOCK:
        runs = list(_RUNS.values())

    if task_id is not None:
        runs = [run for run in runs if run.spec.task_id == task_id]

    payloads = [run.to_state_payload() for run in runs]
    by_state: dict[str, int] = {}
    for payload in payloads:
        by_state[payload["state"]] = by_state.get(payload["state"], 0) + 1
    return {
        "count": len(payloads),
        "by_state": by_state,
        "runs": payloads,
        "task_id_filter": task_id,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _transition(
    run: RecoveryRun,
    *,
    new_state: RecoveryState,
    note: str,
    terminal_status: str | None = None,
) -> None:
    """Mutate a RecoveryRun in place. Caller must hold _REGISTRY_LOCK.

    Drops the (task_id, fingerprint) idempotency entry once the new state is
    terminal. Also validates the v1 outcome status enum if a terminal_status
    is supplied.
    """
    if terminal_status is not None:
        if terminal_status not in code_history.RECOVERY_OUTCOME_STATUSES:
            raise ValueError(
                f"terminal_status {terminal_status!r} must be in "
                f"{sorted(code_history.RECOVERY_OUTCOME_STATUSES)}."
            )
        if not new_state.is_terminal:
            raise ValueError(
                f"terminal_status set but new_state {new_state.value} is not terminal."
            )

    from_state = run.state
    run.state = new_state
    run.last_event_utc = code_history.utc_now()
    run.last_event_summary = note[:400]
    run.history.append({
        "ts_utc": run.last_event_utc,
        "from": from_state.value,
        "to": new_state.value,
        "note": run.last_event_summary,
    })
    if new_state.is_terminal:
        run.terminal_status = terminal_status
        key = (run.spec.task_id, run.failure_fingerprint)
        existing = _OPEN_BY_FINGERPRINT.get(key)
        if existing == run.attempt_id:
            _OPEN_BY_FINGERPRINT.pop(key, None)


# ---------------------------------------------------------------------------
# Test-only utilities (kept module-private; covered by commit 3 tests)
# ---------------------------------------------------------------------------

def _reset_registry_for_tests() -> None:
    """Clear in-memory state. Tests call this in setUp/setdown."""
    with _REGISTRY_LOCK:
        _RUNS.clear()
        _OPEN_BY_FINGERPRINT.clear()


__all__ = [
    "RecoveryState",
    "RecoveryBranch",
    "RecoveryRunSpec",
    "RecoveryRun",
    "select_branch_for_class",
    "start_recovery",
    "get_run_state",
    "cancel_run",
    "list_active_runs",
]
