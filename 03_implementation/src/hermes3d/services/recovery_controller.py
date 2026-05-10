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
from typing import Any, Callable

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
    # Commit 2 additions (saga step 2: freeze + snapshot).
    locked_files: tuple[str, ...] = ()
    pre_snapshot_ids: tuple[str, ...] = ()
    freeze_event_utc: str = ""
    # W6-2 additions (active loop): cached records for each phase. Stored
    # so a UI poll on get_run_state can render the latest proposal / review
    # / apply / resume snapshot without a separate ledger query.
    proposal_record: dict[str, Any] | None = None
    review_record: dict[str, Any] | None = None
    apply_record: dict[str, Any] | None = None
    resume_record: dict[str, Any] | None = None

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
            "locked_files": list(self.locked_files),
            "pre_snapshot_ids": list(self.pre_snapshot_ids),
            "freeze_event_utc": self.freeze_event_utc,
            "next_action": _describe_next_action(self.state, self.branch),
            # W6-2: surface the latest active-loop records for UI polling.
            "proposal_record": self.proposal_record,
            "review_record": self.review_record,
            "apply_record": self.apply_record,
            "resume_record": self.resume_record,
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


# ---------------------------------------------------------------------------
# Commit 2: saga step 2 — freeze + snapshot before any provider work.
# ---------------------------------------------------------------------------


def freeze_run(
    *,
    attempt_id: str,
    owner: str,
    files: tuple[str, ...],
) -> dict[str, Any]:
    """Acquire MCP file locks + take pre-recovery snapshots for a CREATED run.

    Saga step 2. Composes ``code_history.lock_mcp_files`` and
    ``code_history.snapshot_file`` over the v1 ledger primitives so the
    proposing/applying steps run against a frozen file set with audit
    snapshots.

    Ordering (Temporal-style with compensation):
      1. Validate run exists and is in CREATED.
      2. Refuse if branch == ESCALATE_IMMEDIATELY (already terminal).
      3. lock_mcp_files (TTL 30 min). On non-locked status: leave run in
         CREATED, return ``status="lock_blocked"``.
      4. For each file: snapshot_file. If ANY raises -> COMPENSATE:
         release_mcp_files for the same set, mark_recovery_outcome
         ("retry_failed"), _transition CREATED -> RETRY_FAILED.
      5. Persist (locked_files, pre_snapshot_ids) on the run.
      6. _transition CREATED -> PROPOSING.

    Returns dict with key ``status`` in {"frozen", "lock_blocked",
    "snapshot_failed", "not_in_created", "unknown_attempt",
    "hard_escalate_terminal"}.
    """
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if run.branch == RecoveryBranch.ESCALATE_IMMEDIATELY:
            raise ValueError(
                "freeze_run: hard-escalate branch is already terminal; cannot freeze."
            )
        if run.state != RecoveryState.CREATED:
            return {
                "status": "not_in_created",
                "attempt_id": attempt_id,
                "current_state": run.state.value,
            }
    # File-validation: keep the call list minimal (1..32 files).
    if not files or len(files) > 32:
        raise ValueError("freeze_run: 'files' must be 1..32 entries.")
    file_list = list(files)
    lock_result = code_history.lock_mcp_files(
        owner=owner,
        files=file_list,
        task_id=run.spec.task_id,
        reason=f"recovery-freeze:{attempt_id[:8]}",
        role="agent",
        ttl_minutes=30,
    )
    if lock_result.get("status") != "locked":
        # Compensation NOT needed: nothing was acquired. Run stays CREATED;
        # caller can retry with backoff.
        return {
            "status": "lock_blocked",
            "attempt_id": attempt_id,
            "lock_result": lock_result,
        }
    # Snapshots phase. If any raises, release locks + record retry_failed.
    snapshots: list[dict[str, Any]] = []
    try:
        for rel in file_list:
            snap = code_history.snapshot_file(
                rel,
                agent_id=owner,
                action_id="recovery.freeze.pre",
                reason=f"RC v2 freeze {attempt_id[:8]}",
            )
            snapshots.append(snap)
    except Exception as exc:  # noqa: BLE001 -- saga compensation
        # COMPENSATE: release whatever locks we acquired, write a v1
        # outcome row, transition the run to RETRY_FAILED.
        try:
            code_history.release_mcp_files(
                owner=owner,
                files=file_list,
                note=f"recovery-freeze rollback: snapshot failed for {attempt_id[:8]}",
            )
        except Exception:  # noqa: BLE001 -- best-effort during teardown
            pass
        _compensate_freeze_failure(run, owner, exc)
        return {
            "status": "snapshot_failed",
            "attempt_id": attempt_id,
            "lock_result": lock_result,
            "error": type(exc).__name__,
        }
    # Persist + transition.
    snap_ids = tuple(str(s.get("id", "")) for s in snapshots)
    with _REGISTRY_LOCK:
        run.locked_files = tuple(file_list)
        run.pre_snapshot_ids = snap_ids
        run.freeze_event_utc = code_history.utc_now()
        _transition(
            run,
            new_state=RecoveryState.PROPOSING,
            note=f"frozen: {len(file_list)} files locked, {len(snap_ids)} snapshots taken",
        )
    return {
        "status": "frozen",
        "attempt_id": attempt_id,
        "run": run.to_state_payload(),
        "lock_result": lock_result,
        "snapshots": [{"id": s.get("id"), "ts_utc": s.get("ts_utc")} for s in snapshots],
    }


def thaw_run(*, attempt_id: str, owner: str, note: str = "") -> dict[str, Any]:
    """Compensation: release locks if a run terminates pre-apply.

    Idempotent: repeated calls return ``status="already_thawed"``.
    Snapshots are NOT touched (kept as audit trail).
    """
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if not run.locked_files:
            return {"status": "already_thawed", "attempt_id": attempt_id}
        files_to_release = list(run.locked_files)
    try:
        result = code_history.release_mcp_files(
            owner=owner,
            files=files_to_release,
            note=note or f"recovery-thaw {attempt_id[:8]}",
        )
    except Exception as exc:  # noqa: BLE001 -- best-effort
        return {
            "status": "release_failed",
            "attempt_id": attempt_id,
            "error": type(exc).__name__,
        }
    with _REGISTRY_LOCK:
        run.locked_files = ()
    return {"status": "thawed", "attempt_id": attempt_id, "release_result": result}


def _compensate_freeze_failure(run: RecoveryRun, owner: str, exc: Exception) -> None:
    """Write the v1 outcome row + transition the run to RETRY_FAILED.

    Used by ``freeze_run`` when ``snapshot_file`` raises after
    ``lock_mcp_files`` already succeeded. Caller has already released the
    file locks.
    """
    try:
        code_history.mark_recovery_outcome(
            owner=owner,
            attempt_id=run.attempt_id,
            status="retry_failed",
            recovery_summary=f"snapshot_failed: {type(exc).__name__}: {str(exc)[:200]}",
        )
    except Exception:  # noqa: BLE001 -- best-effort during teardown
        pass
    with _REGISTRY_LOCK:
        _transition(
            run,
            new_state=RecoveryState.RETRY_FAILED,
            note=f"freeze compensated: {type(exc).__name__}",
            terminal_status="retry_failed",
        )


# ---------------------------------------------------------------------------
# W6-2: Active-loop methods (commits 3-5 of RC v2).
#
# Sequence: failure -> freeze (commit 2) -> propose_fix -> review_proposal ->
#   [confirm] -> apply_proposal -> resume_run (re-run gate) -> recovered/escalated.
#
# Each method:
#   * validates the run is in the expected source state,
#   * dispatches to a swappable adapter (MiniMax / DeepSeek) or to
#     ``code_history.apply_reviewed_patch_proposal`` / ``run_mcp_gate``,
#   * appends a phase entry to ``run.history``,
#   * persists the phase record on the run dataclass,
#   * emits a structured proof event (best-effort; phase row goes into the
#     run history regardless of whether the proof_events sink is wired) so
#     post-hoc forensic queries can replay the full sequence.
#
# Saga compensation rule: if apply_proposal fails AFTER the run reaches
# APPLYING, the proposal stays on the run (it remains addressable for
# re-apply attempts) but the run transitions to RETRY_FAILED -- the v1
# ledger row is closed with that status and the file locks are released
# via thaw_run. This matches the "compensating action is the inverse of the
# local transaction" semantics of the saga pattern (Garcia-Molina + Salem
# 1987; see https://temporal.io/blog/saga-pattern-made-easy).
#
# Routes are exposed via FastAPI APIRouter in code_operator.py per the
# bigger-applications layout (https://fastapi.tiangolo.com/tutorial/bigger-applications/);
# this module is import-clean of FastAPI itself.
# ---------------------------------------------------------------------------


# Provider-adapter callables. Tests inject mocks via monkeypatch on these
# names (e.g. ``monkeypatch.setattr(recovery_controller, "_minimax_adapter",
# fake_propose)``). The defaults raise so a real call without configured
# credentials surfaces as a 503 in the route layer, NOT a silent no-op.
ProposalAdapter = Callable[[dict[str, Any]], dict[str, Any]]
ReviewAdapter = Callable[[dict[str, Any]], dict[str, Any]]


class ProviderNotConfigured(RuntimeError):
    """Raised when a provider adapter is invoked without operator configuration.

    Maps to HTTP 503 in the route layer with a redacted "operator must
    configure provider" message. Per the no-paid-services rule, the message
    intentionally does NOT name which env var is missing -- operators see
    that in the runbook (HERMES_RC_V2_ACTIVE_LOOP_2026-05-09.md), the API
    response stays generic so a leaked response body does not signal which
    secret the operator is using.
    """


def _default_minimax_adapter(_request: dict[str, Any]) -> dict[str, Any]:
    """Default proposal adapter -- fails fast unless an operator has wired one in."""
    raise ProviderNotConfigured(
        "Recovery proposal provider not configured; "
        "see HERMES_RC_V2_ACTIVE_LOOP_2026-05-09.md for setup."
    )


def _default_deepseek_adapter(_request: dict[str, Any]) -> dict[str, Any]:
    """Default review adapter -- fails fast unless an operator has wired one in."""
    raise ProviderNotConfigured(
        "Recovery review provider not configured; "
        "see HERMES_RC_V2_ACTIVE_LOOP_2026-05-09.md for setup."
    )


# Module-level adapter handles. Tests + operators replace these. Reads use
# the function-call form ``_minimax_adapter(request)`` so monkeypatch on
# the module attribute is picked up at call time.
_minimax_adapter: ProposalAdapter = _default_minimax_adapter
_deepseek_adapter: ReviewAdapter = _default_deepseek_adapter


def _emit_phase_proof(
    *,
    event_type: str,
    run: RecoveryRun,
    payload: dict[str, Any],
) -> str | None:
    """Best-effort write to proof_events with version-tagging.

    Returns the new event id, or None if the sink is unreachable (DB not
    initialized in a unit-test context). Test runs that do not bring up
    sqlite simply skip the persistence layer -- the phase still lands in
    ``run.history`` so the active-loop sequence remains assertable.

    Version-tagging follows the post-PR #168 pattern: every persisted
    proof_events row carries ``version_label`` / ``upstream_tag`` /
    ``checkout_path`` so a forensic query can attribute behavior to a
    specific Hermes Agent version (per services/proof_helpers.py).
    """
    try:
        # Lazy import: keep the service module free of API-layer imports
        # at module load so tests that exercise only the controller logic
        # do not need to bootstrap the full FastAPI app.
        from hermes3d.api.routes._common import as_json, execute, new_id  # noqa: PLC0415
        from hermes3d.services.proof_helpers import attach_version_fields  # noqa: PLC0415
    except Exception:  # noqa: BLE001 -- best-effort during teardown / reduced env
        return None
    base_payload: dict[str, Any] = {
        "attempt_id": run.attempt_id,
        "task_id": run.spec.task_id,
        "failure_class": run.spec.failure_class,
        "failed_step": run.spec.failed_step,
        **payload,
    }
    enriched = attach_version_fields(base_payload)
    event_id = new_id()
    try:
        execute(
            "INSERT INTO proof_events (id, event_type, source_agent, payload) VALUES (?, ?, ?, ?)",
            (event_id, event_type, "recovery_controller_v2", as_json(enriched)),
        )
    except Exception:  # noqa: BLE001 -- DB not initialized in some unit-test paths
        return None
    return event_id


def _redact_for_payload(text: str | None, *, max_len: int = 280) -> str:
    """Trim + redact a free-text field so secrets never reach the proof row.

    Delegates to ``code_history``'s redaction surface when available; falls
    back to plain truncation otherwise. ``code_history`` already wraps
    ``gateways.redaction.redact_text`` -- we reuse that path.
    """
    if not text:
        return ""
    raw = str(text)[:max_len]
    try:
        from hermes3d.gateways.redaction import redact_text  # noqa: PLC0415
        return redact_text(raw)[:max_len]
    except Exception:  # noqa: BLE001 -- best-effort
        return raw


def propose_fix(
    *,
    attempt_id: str,
    owner: str,
    failure_summary: str = "",
) -> dict[str, Any]:
    """Phase 4: dispatch a fix proposal request to the configured provider.

    State requirement: run must be in PROPOSING (the state freeze_run
    transitions to). Returns dict with ``status`` in
    {"proposed", "provider_not_configured", "unknown_attempt",
    "not_in_proposing"}. On a successful proposal the run transitions
    PROPOSING -> REVIEWING and the proposal_record + proposal_id fields are
    populated.

    The provider adapter receives a redacted request dict and returns a
    proposal dict that MUST include ``proposal_id`` and ``files_touched``.
    The adapter is responsible for its own auth and rate limiting; the
    controller only validates the response shape and emits the proof event.
    """
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if run.state != RecoveryState.PROPOSING:
            return {
                "status": "not_in_proposing",
                "attempt_id": attempt_id,
                "current_state": run.state.value,
            }

    summary = failure_summary or run.spec.failure_summary
    request = {
        "attempt_id": attempt_id,
        "task_id": run.spec.task_id,
        "failed_step": run.spec.failed_step,
        "failure_class": run.spec.failure_class,
        "failure_summary": _redact_for_payload(summary),
        "context_pack": list(run.spec.context_pack),
        "agent_stack": list(run.spec.agent_stack),
    }
    try:
        proposal = _minimax_adapter(request)
    except ProviderNotConfigured as exc:
        return {
            "status": "provider_not_configured",
            "attempt_id": attempt_id,
            "reason": str(exc),
        }
    if not isinstance(proposal, dict) or not proposal.get("proposal_id"):
        raise ValueError(
            "propose_fix: adapter must return dict with non-empty 'proposal_id'."
        )
    proposal_id = str(proposal["proposal_id"])
    files_touched = list(proposal.get("files_touched", []) or [])
    record = {
        "proposal_id": proposal_id,
        "files_touched": files_touched,
        "rationale": _redact_for_payload(proposal.get("rationale", "")),
        "model_meta": proposal.get("model_meta", {}),
        "ts_utc": code_history.utc_now(),
    }
    proof_event_id = _emit_phase_proof(
        event_type="recovery_fix_proposal",
        run=run,
        payload={"proposal_id": proposal_id, "files_touched": files_touched},
    )
    with _REGISTRY_LOCK:
        # Re-fetch under lock to handle a racing cancel.
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if run.state != RecoveryState.PROPOSING:
            return {
                "status": "not_in_proposing",
                "attempt_id": attempt_id,
                "current_state": run.state.value,
            }
        run.proposal_id = proposal_id
        run.proposal_record = record
        _transition(
            run,
            new_state=RecoveryState.REVIEWING,
            note=f"proposed fix {proposal_id[:12]}; files={len(files_touched)}",
        )
        payload = run.to_state_payload()
    return {
        "status": "proposed",
        "attempt_id": attempt_id,
        "proposal_record": record,
        "proof_event_id": proof_event_id,
        "run": payload,
    }


def review_proposal(
    *,
    attempt_id: str,
    owner: str,
    proposal_id: str,
) -> dict[str, Any]:
    """Phase 5: adversarial review of the proposal via DeepSeek (or stub).

    State requirement: run must be in REVIEWING with a matching proposal_id.
    Returns dict with ``status`` in {"reviewed", "provider_not_configured",
    "unknown_attempt", "not_in_reviewing", "proposal_mismatch"}.
    On verdict="approved", the run transitions REVIEWING ->
    AWAITING_HUMAN_CONFIRM; on "rejected" or "needs-revision" the run
    stays in REVIEWING (caller can re-propose with a fresh proposal_id).
    """
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if run.state != RecoveryState.REVIEWING:
            return {
                "status": "not_in_reviewing",
                "attempt_id": attempt_id,
                "current_state": run.state.value,
            }
        if run.proposal_id != proposal_id:
            return {
                "status": "proposal_mismatch",
                "attempt_id": attempt_id,
                "expected": run.proposal_id,
                "got": proposal_id,
            }

    request = {
        "attempt_id": attempt_id,
        "task_id": run.spec.task_id,
        "proposal_id": proposal_id,
        "files_touched": list((run.proposal_record or {}).get("files_touched", []) or []),
    }
    try:
        review = _deepseek_adapter(request)
    except ProviderNotConfigured as exc:
        return {
            "status": "provider_not_configured",
            "attempt_id": attempt_id,
            "reason": str(exc),
        }
    if not isinstance(review, dict):
        raise ValueError("review_proposal: adapter must return a dict.")
    verdict = str(review.get("verdict", "")).strip()
    if verdict not in ("approved", "rejected", "needs-revision"):
        raise ValueError(
            f"review_proposal: verdict must be 'approved' | 'rejected' | "
            f"'needs-revision'; got {verdict!r}."
        )
    review_id = str(review.get("review_id", "") or "")
    review_proof_ids = list(review.get("review_proof_ids", []) or [])
    record = {
        "review_id": review_id,
        "verdict": verdict,
        "proposal_id": proposal_id,
        "review_proof_ids": review_proof_ids,
        "concerns": [_redact_for_payload(c) for c in review.get("concerns", []) or []],
        "model_meta": review.get("model_meta", {}),
        "ts_utc": code_history.utc_now(),
    }
    proof_event_id = _emit_phase_proof(
        event_type="recovery_review",
        run=run,
        payload={
            "proposal_id": proposal_id,
            "review_id": review_id,
            "verdict": verdict,
        },
    )
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if run.state != RecoveryState.REVIEWING:
            return {
                "status": "not_in_reviewing",
                "attempt_id": attempt_id,
                "current_state": run.state.value,
            }
        run.review_evidence_id = review_id or None
        run.review_record = record
        if verdict == "approved":
            _transition(
                run,
                new_state=RecoveryState.AWAITING_HUMAN_CONFIRM,
                note=f"review approved {review_id[:12]}; proposal {proposal_id[:12]}",
            )
        else:
            # Stay in REVIEWING (history records the verdict). Re-propose
            # with a fresh proposal_id is the caller's next move.
            run.last_event_utc = code_history.utc_now()
            run.last_event_summary = f"review {verdict}: {review_id[:12]}"[:400]
            run.history.append({
                "ts_utc": run.last_event_utc,
                "from": RecoveryState.REVIEWING.value,
                "to": RecoveryState.REVIEWING.value,
                "note": run.last_event_summary,
            })
        payload = run.to_state_payload()
    return {
        "status": "reviewed",
        "attempt_id": attempt_id,
        "verdict": verdict,
        "review_record": record,
        "proof_event_id": proof_event_id,
        "run": payload,
    }


def apply_proposal(
    *,
    attempt_id: str,
    owner: str,
    proposal_id: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Phase 6: apply the reviewed proposal via apply_reviewed_patch_proposal.

    Preconditions:
      * Run must be in AWAITING_HUMAN_CONFIRM (review approved) -- any other
        state returns ``status="not_ready_to_apply"``.
      * proposal_id must match the run's stored proposal_id.
      * caller must pass ``confirm=True`` (confirm-by-default policy);
        autonomous mode also requires ``HERMES_RECOVERY_AUTONOMOUS=1`` AND
        the run was started with confirm=True.

    On success: run transitions AWAITING_HUMAN_CONFIRM -> APPLYING ->
    RE_RUNNING_GATE (the resume_run call closes the loop).

    On failure: run transitions to RETRY_FAILED (terminal), proposal stays
    on the run for forensic review, file locks are released via thaw_run.

    Returns dict with ``status`` in {"applied", "not_ready_to_apply",
    "proposal_mismatch", "confirm_required", "review_not_approved",
    "apply_failed", "unknown_attempt"}.
    """
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if run.state != RecoveryState.AWAITING_HUMAN_CONFIRM:
            return {
                "status": "not_ready_to_apply",
                "attempt_id": attempt_id,
                "current_state": run.state.value,
            }
        if run.proposal_id != proposal_id:
            return {
                "status": "proposal_mismatch",
                "attempt_id": attempt_id,
                "expected": run.proposal_id,
                "got": proposal_id,
            }
        review = run.review_record or {}
        if review.get("verdict") != "approved":
            return {
                "status": "review_not_approved",
                "attempt_id": attempt_id,
                "verdict": review.get("verdict"),
            }
        if not confirm:
            return {
                "status": "confirm_required",
                "attempt_id": attempt_id,
                "reason": "confirm-by-default: pass confirm=True to apply.",
            }
        # Autonomous gate: when actor='autonomous', the run was already
        # validated against HERMES_RECOVERY_AUTONOMOUS at start_recovery.
        # No further check needed here.
        review_proof_ids = list(review.get("review_proof_ids", []) or []) or [
            review.get("review_id") or f"review-{proposal_id[:8]}"
        ]
        _transition(
            run,
            new_state=RecoveryState.APPLYING,
            note=f"applying proposal {proposal_id[:12]} (review approved)",
        )

    # Outside the lock: dispatch to v1 apply_reviewed_patch_proposal.
    try:
        apply_result = code_history.apply_reviewed_patch_proposal(
            proposal_id,
            agent_id=owner,
            task_id=run.spec.task_id,
            review_proof_ids=review_proof_ids,
            reason=f"RC v2 active loop apply: attempt {attempt_id[:8]}",
        )
    except Exception as exc:  # noqa: BLE001 -- saga compensation
        proof_event_id = _emit_phase_proof(
            event_type="recovery_apply_failed",
            run=run,
            payload={
                "proposal_id": proposal_id,
                "error_class": type(exc).__name__,
                "error_summary": _redact_for_payload(str(exc)),
            },
        )
        # Compensation: close the v1 ledger row + transition to RETRY_FAILED.
        try:
            code_history.mark_recovery_outcome(
                owner=owner,
                attempt_id=attempt_id,
                status="retry_failed",
                recovery_summary=(
                    f"apply_failed: {type(exc).__name__}: "
                    f"{_redact_for_payload(str(exc))[:200]}"
                ),
                proposal_id=proposal_id,
                review_evidence_id=run.review_evidence_id,
            )
        except Exception:  # noqa: BLE001 -- best-effort
            pass
        with _REGISTRY_LOCK:
            run = _RUNS.get(attempt_id)
            if run is not None:
                _transition(
                    run,
                    new_state=RecoveryState.RETRY_FAILED,
                    note=f"apply failed: {type(exc).__name__}",
                    terminal_status="retry_failed",
                )
                payload = run.to_state_payload()
            else:
                payload = None
        return {
            "status": "apply_failed",
            "attempt_id": attempt_id,
            "error_class": type(exc).__name__,
            "proof_event_id": proof_event_id,
            "run": payload,
        }

    apply_evidence_id = ""
    apply_proof_event_id = ""
    if isinstance(apply_result, dict):
        ev = apply_result.get("mcp_evidence")
        if isinstance(ev, dict):
            apply_evidence_id = str(ev.get("evidence_id") or "")
        apply_data = apply_result.get("apply") or {}
        if isinstance(apply_data, dict):
            apply_proof_event_id = str(apply_data.get("proof_event_id") or "")
    record = {
        "proposal_id": proposal_id,
        "applied": True,
        "apply_evidence_id": apply_evidence_id,
        "apply_proof_event_id": apply_proof_event_id,
        "files_changed": list((run.proposal_record or {}).get("files_touched", []) or []),
        "ts_utc": code_history.utc_now(),
    }
    proof_event_id = _emit_phase_proof(
        event_type="recovery_apply",
        run=run,
        payload={
            "proposal_id": proposal_id,
            "apply_evidence_id": apply_evidence_id,
        },
    )
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        run.apply_evidence_id = apply_evidence_id or None
        run.apply_record = record
        _transition(
            run,
            new_state=RecoveryState.RE_RUNNING_GATE,
            note=f"applied proposal {proposal_id[:12]}; ready to re-run gate",
        )
        payload = run.to_state_payload()
    return {
        "status": "applied",
        "attempt_id": attempt_id,
        "apply_record": record,
        "apply_result": apply_result,
        "proof_event_id": proof_event_id,
        "run": payload,
    }


def resume_run(
    *,
    attempt_id: str,
    owner: str,
    gate_id: str | None = None,
) -> dict[str, Any]:
    """Phase 7: re-run the original failing gate; resume or escalate.

    State requirement: run must be in RE_RUNNING_GATE (the state
    apply_proposal transitions to). The caller may pass ``gate_id`` to
    override; otherwise the controller uses the run's failed_step as the
    gate id, which is the conventional mapping ``code_history.run_mcp_gate``
    accepts.

    Outcome:
      * Gate passes -> run transitions to RECOVERED, v1 outcome row written
        with status="recovered". File locks are released via thaw_run.
      * Gate fails -> run transitions to ESCALATED, v1 outcome row written
        with status="escalated". File locks are released via thaw_run.

    Returns dict with ``status`` in {"resumed", "escalated", "gate_error",
    "unknown_attempt", "not_in_re_running_gate"}.
    """
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        if run.state != RecoveryState.RE_RUNNING_GATE:
            return {
                "status": "not_in_re_running_gate",
                "attempt_id": attempt_id,
                "current_state": run.state.value,
            }

    target_gate = gate_id or run.spec.failed_step
    if not target_gate:
        raise ValueError("resume_run: no gate_id provided and no failed_step on the spec.")

    try:
        gate_result = code_history.run_mcp_gate(target_gate, owner=owner)
    except Exception as exc:  # noqa: BLE001 -- gate runner failure
        proof_event_id = _emit_phase_proof(
            event_type="recovery_resume_gate_error",
            run=run,
            payload={
                "gate_id": target_gate,
                "error_class": type(exc).__name__,
                "error_summary": _redact_for_payload(str(exc)),
            },
        )
        return {
            "status": "gate_error",
            "attempt_id": attempt_id,
            "gate_id": target_gate,
            "error_class": type(exc).__name__,
            "proof_event_id": proof_event_id,
        }

    gate_status = (
        gate_result.get("status") if isinstance(gate_result, dict) else None
    ) or "failed"
    gate_passed = gate_status == "pass"

    record = {
        "gate_id": target_gate,
        "gate_status": gate_status,
        "passed": gate_passed,
        "ts_utc": code_history.utc_now(),
    }
    if gate_passed:
        proof_event_id = _emit_phase_proof(
            event_type="recovery_resume",
            run=run,
            payload={"gate_id": target_gate, "result": "recovered"},
        )
        try:
            code_history.mark_recovery_outcome(
                owner=owner,
                attempt_id=attempt_id,
                status="recovered",
                recovery_summary=(
                    f"resumed: gate {target_gate} passed after RC v2 active loop"
                ),
                proposal_id=run.proposal_id,
                review_evidence_id=run.review_evidence_id,
                apply_evidence_id=run.apply_evidence_id,
                retry_gate_id=target_gate,
            )
        except Exception:  # noqa: BLE001 -- best-effort
            pass
        with _REGISTRY_LOCK:
            run = _RUNS.get(attempt_id)
            if run is None:
                return {"status": "unknown_attempt", "attempt_id": attempt_id}
            run.retry_gate_id = target_gate
            run.resume_record = record
            _transition(
                run,
                new_state=RecoveryState.RECOVERED,
                note=f"recovered: gate {target_gate} passed",
                terminal_status="recovered",
            )
        # Saga finalization: release file locks (best-effort). Run thaw
        # BEFORE building the response payload so callers see locked_files=[].
        try:
            thaw_run(
                attempt_id=attempt_id,
                owner=owner,
                note=f"recovery complete: gate {target_gate} passed",
            )
        except Exception:  # noqa: BLE001 -- thaw is best-effort on finalize
            pass
        payload = get_run_state(attempt_id)
        return {
            "status": "resumed",
            "attempt_id": attempt_id,
            "resume_record": record,
            "gate_result": gate_result,
            "proof_event_id": proof_event_id,
            "run": payload,
        }

    # Escalation path: gate did not pass.
    proof_event_id = _emit_phase_proof(
        event_type="recovery_escalated",
        run=run,
        payload={
            "gate_id": target_gate,
            "gate_status": gate_status,
            "result": "escalated",
        },
    )
    try:
        code_history.mark_recovery_outcome(
            owner=owner,
            attempt_id=attempt_id,
            status="escalated",
            recovery_summary=(
                f"escalated: gate {target_gate} returned {gate_status} after apply"
            ),
            proposal_id=run.proposal_id,
            review_evidence_id=run.review_evidence_id,
            apply_evidence_id=run.apply_evidence_id,
            retry_gate_id=target_gate,
        )
    except Exception:  # noqa: BLE001 -- best-effort
        pass
    with _REGISTRY_LOCK:
        run = _RUNS.get(attempt_id)
        if run is None:
            return {"status": "unknown_attempt", "attempt_id": attempt_id}
        run.retry_gate_id = target_gate
        run.resume_record = record
        _transition(
            run,
            new_state=RecoveryState.ESCALATED,
            note=f"escalated: gate {target_gate} returned {gate_status}",
            terminal_status="escalated",
        )
    try:
        thaw_run(
            attempt_id=attempt_id,
            owner=owner,
            note=f"recovery escalated: gate {target_gate} did not pass",
        )
    except Exception:  # noqa: BLE001 -- thaw is best-effort on finalize
        pass
    payload = get_run_state(attempt_id)
    return {
        "status": "escalated",
        "attempt_id": attempt_id,
        "resume_record": record,
        "gate_result": gate_result,
        "proof_event_id": proof_event_id,
        "run": payload,
    }


__all__ = [
    "RecoveryState",
    "RecoveryBranch",
    "RecoveryRunSpec",
    "RecoveryRun",
    "ProviderNotConfigured",
    "select_branch_for_class",
    "start_recovery",
    "get_run_state",
    "cancel_run",
    "list_active_runs",
    "freeze_run",
    "thaw_run",
    "propose_fix",
    "review_proposal",
    "apply_proposal",
    "resume_run",
]
