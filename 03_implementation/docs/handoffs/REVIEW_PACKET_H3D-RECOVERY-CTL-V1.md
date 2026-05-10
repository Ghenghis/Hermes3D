# Recovery Controller v1.5 Review Packet

Task: H3D-RECOVERY-CTL-V1
Provenance: MiniMax artifacts 2130e9e1d12d4686ac4d788bfd136673 + 459bc9c00d6049dd949fa84e61f09c7a (both truncated). Manually assembled with v1.5 fields.
Local py_compile: PASS on all 3 files (output shown above).
Contract: lean v1 backend ONLY — no UI, no autonomous apply, no file mutation by controller.

v1.5 fields added on RecoveryAttempt: agent_stack, failed_step_type, resume_from_step, recommended_next_action, provenance_ids, redaction_status, retry_budget, failure_fingerprint, context_pack, worker_output_status.

RECOVERY_FAILURE_CLASSES (9): missing_proof, patch_rejected, gate_fail, merge_git_fail, runner_fail, sandbox_fail, provider_auth, ui_fail, secret_risk
RECOVERY_OUTCOME_STATUSES (3): recovered, retry_failed, escalated
RECOVERY_FAILED_STEP_TYPES (10): provider_smoke, builder_pass, reviewer_pass, patch_apply, gate_run, git_branch, git_push, pr_open, visual_proof, unknown
RECOVERY_RECOMMENDED_ACTIONS (8): retry_review, split_patch_by_file, rollback_and_retry, run_gate_again, escalate_user, refresh_context, reduce_review_context, none
RECOVERY_REDACTION_STATUSES (3): pass, warning, blocked
RECOVERY_WORKER_OUTPUT_STATUSES (6): complete, truncated, timeout, empty, malformed_json, rejected
RECOVERY_AGENT_STACK_VALUES (8): MiniMax, DeepSeek, OpenCode, OpenHands, Gate Runner, Human, Claude, Codex

---

## proposal b63cd8b665bf4c2488591f8350b91cf5
file: 03_implementation/src/hermes3d/services/code_history.py
base_sha256: c55c8b9537173e8fb9ff164ee07d2c219952876e855261fca55ff87804abe94e
proposed_sha256: 65d72e0b0f0cd67d721480e1a954027b407e4e172e7f9a8b1f9dd559768e9f00
```diff
--- 03_implementation/src/hermes3d/services/code_history.py
+++ 03_implementation/src/hermes3d/services/code_history.py (proposed)
@@ -7,6 +7,7 @@
 import json
 import os
 import re
+import secrets
 import shutil
 import subprocess
 import tempfile
@@ -3660,3 +3661,373 @@
     if not snapshot:
         raise FileNotFoundError("Snapshot record was not found.")
     return {"status": "ready", **snapshot}
+
+
+# ---------------------------------------------------------------------------
+# Recovery Controller v1 — durable failure ledger for Hermes Agent Recovery.
+#
+# The lean v1 controller is a pure ledger: it records failure/outcome rows
+# and emits MCP evidence. It does NOT mutate any source file, dispatch any
+# repair, or trigger any retry. The v1.5 schema (this file) adds future-proof
+# fields the Hermes Agent Task Monitor UI will surface without a backend
+# refactor: agent_stack, failed_step_type, resume_from_step,
+# recommended_next_action, provenance_ids, redaction_status, retry_budget,
+# failure_fingerprint, context_pack, worker_output_status.
+#
+# Provenance: assembled from MiniMax builder artifacts
+# 2130e9e1d12d4686ac4d788bfd136673 + 459bc9c00d6049dd949fa84e61f09c7a
+# (both completion-token-truncated). Manual fixes preserved chain-of-custody.
+# ---------------------------------------------------------------------------
+
+_RECOVERY_LEDGER_PATH = HISTORY_ROOT / "recovery" / "recovery-ledger.jsonl"
+
+RECOVERY_FAILURE_CLASSES = frozenset({
+    "missing_proof",
+    "patch_rejected",
+    "gate_fail",
+    "merge_git_fail",
+    "runner_fail",
+    "sandbox_fail",
+    "provider_auth",
+    "ui_fail",
+    "secret_risk",
+})
+
+RECOVERY_OUTCOME_STATUSES = frozenset({
+    "recovered",
+    "retry_failed",
+    "escalated",
+})
+
+RECOVERY_FAILED_STEP_TYPES = frozenset({
+    "provider_smoke",
+    "builder_pass",
+    "reviewer_pass",
+    "patch_apply",
+    "gate_run",
+    "git_branch",
+    "git_push",
+    "pr_open",
+    "visual_proof",
+    "unknown",
+})
+
+RECOVERY_RECOMMENDED_ACTIONS = frozenset({
+    "retry_review",
+    "split_patch_by_file",
+    "rollback_and_retry",
+    "run_gate_again",
+    "escalate_user",
+    "refresh_context",
+    "reduce_review_context",
+    "none",
+})
+
+RECOVERY_REDACTION_STATUSES = frozenset({"pass", "warning", "blocked"})
+
+RECOVERY_WORKER_OUTPUT_STATUSES = frozenset({
+    "complete",
+    "truncated",
+    "timeout",
+    "empty",
+    "malformed_json",
+    "rejected",
+})
+
+RECOVERY_AGENT_STACK_VALUES = frozenset({
+    "MiniMax",
+    "DeepSeek",
+    "OpenCode",
+    "OpenHands",
+    "Gate Runner",
+    "Human",
+    "Claude",
+    "Codex",
+})
+
+_RECOVERY_MAX_ATTEMPTS_DEFAULT = 3
+
+
+def _validate_recovery_enum(value: str, choices: frozenset[str], label: str) -> str:
+    if value not in choices:
+        raise ValueError(
+            f"{label} must be one of {sorted(choices)}; got {value!r}."
+        )
+    return value
+
+
+def _validate_recovery_agent_stack(stack: list[str] | None) -> list[str]:
+    if not stack:
+        return []
+    cleaned: list[str] = []
+    for item in stack:
+        text = str(item).strip()
+        if not text:
+            continue
+        if text not in RECOVERY_AGENT_STACK_VALUES:
+            raise ValueError(
+                f"agent_stack entry must be one of {sorted(RECOVERY_AGENT_STACK_VALUES)}; got {text!r}."
+            )
+        cleaned.append(text)
+    return cleaned
+
+
+def _validate_recovery_id_list(values: list[str] | None, *, label: str, max_items: int = 32) -> list[str]:
+    if not values:
+        return []
+    if len(values) > max_items:
+        raise ValueError(f"{label} accepts at most {max_items} items.")
+    cleaned: list[str] = []
+    for item in values:
+        text = str(item).strip()
+        if not text:
+            continue
+        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,160}", text):
+            raise ValueError(
+                f"{label} entry must be 1-160 safe characters (letters, digits, dot, underscore, slash, hyphen)."
+            )
+        cleaned.append(text)
+    return cleaned
+
+
+def _validate_recovery_retry_budget(attempt_n: int, max_attempts: int) -> dict[str, Any]:
+    if not isinstance(attempt_n, int) or attempt_n < 1:
+        raise ValueError("attempt_n must be an integer >= 1.")
+    if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 32:
+        raise ValueError("max_attempts must be an integer in 1..32.")
+    if attempt_n > max_attempts + 32:
+        raise ValueError("attempt_n is unreasonably large compared to max_attempts.")
+    return {
+        "attempt_n": attempt_n,
+        "max_attempts": max_attempts,
+        "exhausted": attempt_n >= max_attempts,
+    }
+
+
+def _recovery_failure_fingerprint(
+    *,
+    failure_class: str,
+    failed_step_type: str,
+    failed_step: str,
+    failure_summary: str,
+) -> str:
+    """Stable short hash so repeated failures group together in the UI."""
+    payload = "|".join((
+        failure_class,
+        failed_step_type,
+        failed_step.strip().lower(),
+        failure_summary.strip().lower()[:200],
+    ))
+    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
+
+
+def record_step_failure(
+    *,
+    owner: str,
+    task_id: str,
+    failed_step: str,
+    failure_class: str,
+    failure_summary: str,
+    failed_step_type: str = "unknown",
+    agent_stack: list[str] | None = None,
+    resume_from_step: str = "",
+    recommended_next_action: str = "none",
+    redaction_status: str = "pass",
+    worker_output_status: str = "complete",
+    context_pack: list[str] | None = None,
+    provenance_ids: list[str] | None = None,
+    evidence_id: str = "",
+    affected_files: list[str] | None = None,
+    attempt_n: int = 1,
+    max_attempts: int = _RECOVERY_MAX_ATTEMPTS_DEFAULT,
+) -> dict[str, Any]:
+    """Append a failure row to the recovery ledger and emit MCP evidence.
+
+    The controller is read-only on source: it never edits files, dispatches
+    repair work, or triggers retries. Higher-level orchestration code is
+    responsible for acting on a recorded failure. This function exists to
+    keep a durable, redacted, structured record so the Task Monitor UI and
+    later automated repair stages have stable data to read.
+    """
+    _require_mcp_locks_ready()
+    _validate_owner(owner)
+    _validate_task_id(task_id)
+    clean_step = _validate_bounded_text(failed_step, "failed_step", max_chars=120)
+    _validate_recovery_enum(failure_class, RECOVERY_FAILURE_CLASSES, "failure_class")
+    _validate_recovery_enum(failed_step_type, RECOVERY_FAILED_STEP_TYPES, "failed_step_type")
+    _validate_recovery_enum(redaction_status, RECOVERY_REDACTION_STATUSES, "redaction_status")
+    _validate_recovery_enum(worker_output_status, RECOVERY_WORKER_OUTPUT_STATUSES, "worker_output_status")
+    _validate_recovery_enum(recommended_next_action, RECOVERY_RECOMMENDED_ACTIONS, "recommended_next_action")
+    clean_summary = redact_text(_validate_bounded_text(failure_summary, "failure_summary", max_chars=400))
+    clean_resume = ""
+    if resume_from_step:
+        clean_resume = _validate_bounded_text(resume_from_step, "resume_from_step", max_chars=120)
+    clean_stack = _validate_recovery_agent_stack(agent_stack)
+    clean_context = _validate_recovery_id_list(context_pack, label="context_pack", max_items=64)
+    clean_provenance = _validate_recovery_id_list(provenance_ids, label="provenance_ids", max_items=64)
+    safe_evidence_id = ""
+    if evidence_id:
+        safe_evidence_id = _validate_bounded_text(evidence_id, "evidence_id", max_chars=120)
+    clean_affected = _safe_mcp_files(affected_files or [], must_exist=False)
+    budget = _validate_recovery_retry_budget(attempt_n, max_attempts)
+
+    attempt_id = secrets.token_hex(16)
+    fingerprint = _recovery_failure_fingerprint(
+        failure_class=failure_class,
+        failed_step_type=failed_step_type,
+        failed_step=clean_step,
+        failure_summary=clean_summary,
+    )
+    record = {
+        "kind": "failure",
+        "attempt_id": attempt_id,
+        "task_id": task_id,
+        "failed_step": clean_step,
+        "failed_step_type": failed_step_type,
+        "failure_class": failure_class,
+        "failure_summary": clean_summary,
+        "failure_fingerprint": fingerprint,
+        "agent_stack": clean_stack,
+        "resume_from_step": clean_resume,
+        "recommended_next_action": recommended_next_action,
+        "redaction_status": redaction_status,
+        "worker_output_status": worker_output_status,
+        "context_pack": clean_context,
+        "provenance_ids": clean_provenance,
+        "evidence_id": safe_evidence_id,
+        "affected_files": clean_affected,
+        "retry_budget": budget,
+        "attempt_n": attempt_n,
+        "status": "recorded",
+        "ts_utc": utc_now(),
+    }
+    _RECOVERY_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
+    with _RECOVERY_LEDGER_PATH.open("a", encoding="utf-8") as fh:
+        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
+    summary = f"Recovery failure {failure_class}/{failed_step_type} on {clean_step}"[:400]
+    mcp_evidence = append_mcp_evidence(
+        owner=owner,
+        task_id=task_id,
+        kind="recovery_failure",
+        summary=summary,
+        data={
+            "attempt_id": attempt_id,
+            "failure_class": failure_class,
+            "failed_step_type": failed_step_type,
+            "failure_fingerprint": fingerprint,
+            "retry_budget": budget,
+            "recommended_next_action": recommended_next_action,
+        },
+    )
+    return {
+        "status": "recorded",
+        "attempt_id": attempt_id,
+        "record": record,
+        "mcp_evidence": mcp_evidence,
+    }
+
+
+def mark_recovery_outcome(
+    *,
+    owner: str,
+    attempt_id: str,
+    status: str,
+    recovery_summary: str,
+    proposal_id: str | None = None,
+    review_evidence_id: str | None = None,
+    apply_evidence_id: str | None = None,
+    retry_gate_id: str | None = None,
+) -> dict[str, Any]:
+    """Append an outcome row referencing an existing failure attempt_id."""
+    _require_mcp_locks_ready()
+    _validate_owner(owner)
+    _validate_recovery_enum(status, RECOVERY_OUTCOME_STATUSES, "status")
+    if not re.fullmatch(r"[a-f0-9]{32}", attempt_id or ""):
+        raise ValueError("attempt_id must be a 32-character lowercase hex string.")
+    clean_summary = redact_text(_validate_bounded_text(recovery_summary, "recovery_summary", max_chars=400))
+    if not _RECOVERY_LEDGER_PATH.exists():
+        raise FileNotFoundError(f"Recovery ledger does not exist; cannot find attempt {attempt_id}.")
+    found = False
+    with _RECOVERY_LEDGER_PATH.open("r", encoding="utf-8") as fh:
+        for line in fh:
+            line = line.strip()
+            if not line:
+                continue
+            try:
+                entry = json.loads(line)
+            except json.JSONDecodeError:
+                continue
+            if entry.get("kind") == "failure" and entry.get("attempt_id") == attempt_id:
+                found = True
+                break
+    if not found:
+        raise ValueError(f"attempt_id {attempt_id!r} not found in recovery ledger.")
+
+    optional_ids = {
+        "proposal_id": proposal_id,
+        "review_evidence_id": review_evidence_id,
+        "apply_evidence_id": apply_evidence_id,
+        "retry_gate_id": retry_gate_id,
+    }
+    for label, value in optional_ids.items():
+        if value is not None and not re.fullmatch(r"[A-Za-z0-9._/-]{1,160}", value):
+            raise ValueError(f"{label} must be 1-160 safe characters or null.")
+
+    outcome = {
+        "kind": "outcome",
+        "attempt_id": attempt_id,
+        "status": status,
+        "recovery_summary": clean_summary,
+        "proposal_id": proposal_id,
+        "review_evidence_id": review_evidence_id,
+        "apply_evidence_id": apply_evidence_id,
+        "retry_gate_id": retry_gate_id,
+        "ts_utc": utc_now(),
+    }
+    with _RECOVERY_LEDGER_PATH.open("a", encoding="utf-8") as fh:
+        fh.write(json.dumps(outcome, ensure_ascii=False) + "\n")
+    mcp_evidence = append_mcp_evidence(
+        owner=owner,
+        task_id=attempt_id,
+        kind="recovery_outcome",
+        summary=f"Recovery outcome {status} for attempt {attempt_id[:8]}",
+        data={
+            "attempt_id": attempt_id,
+            "status": status,
+            "proposal_id": proposal_id,
+            "apply_evidence_id": apply_evidence_id,
+            "retry_gate_id": retry_gate_id,
+        },
+    )
+    return {"status": "recorded", "outcome": outcome, "mcp_evidence": mcp_evidence}
+
+
+def list_recovery_attempts(task_id: str | None = None) -> dict[str, Any]:
+    """Read recovery ledger; optionally filter by task_id. Read-only."""
+    if not _RECOVERY_LEDGER_PATH.exists():
+        return {"attempts": [], "outcomes": [], "count": 0, "task_id_filter": task_id}
+    attempts: list[dict[str, Any]] = []
+    outcomes: list[dict[str, Any]] = []
+    with _RECOVERY_LEDGER_PATH.open("r", encoding="utf-8") as fh:
+        for line in fh:
+            line = line.strip()
+            if not line:
+                continue
+            try:
+                entry = json.loads(line)
+            except json.JSONDecodeError:
+                continue
+            if entry.get("kind") == "failure":
+                if task_id is None or entry.get("task_id") == task_id:
+                    attempts.append(entry)
+            elif entry.get("kind") == "outcome":
+                outcomes.append(entry)
+    if task_id is not None:
+        wanted_ids = {item.get("attempt_id") for item in attempts}
+        outcomes = [o for o in outcomes if o.get("attempt_id") in wanted_ids]
+    return {
+        "attempts": attempts,
+        "outcomes": outcomes,
+        "count": len(attempts),
+        "task_id_filter": task_id,
+    }

```

## proposal 7b76f0eae91a4f0d8c80850fcef0b4f0
file: 03_implementation/src/hermes3d/api/routes/code_operator.py
base_sha256: c7bacb96434369372de7fb56ff0f111a016c898fca5e0ccff7f8ed53d31eaa54
proposed_sha256: b1946952293cb20c9b7fc11a5ffad458777e6f8f348cdc8d0cc3a0ba87700dcd
```diff
--- 03_implementation/src/hermes3d/api/routes/code_operator.py
+++ 03_implementation/src/hermes3d/api/routes/code_operator.py (proposed)
@@ -657,3 +657,90 @@
         raise HTTPException(status_code=404, detail={"reason": str(exc)}) from exc
     except ValueError as exc:
         raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc
+
+
+# ---------------------------------------------------------------------------
+# Recovery Controller v1 — failure ledger routes (no UI, no autonomous apply,
+# no file mutation by the controller). Each route dispatches to code_history
+# helpers that append MCP evidence and write the JSONL ledger.
+# ---------------------------------------------------------------------------
+
+
+class RecoveryRecordFailureRequest(StrictBody):
+    task_id: str
+    failed_step: str = Field(min_length=1, max_length=120)
+    failure_class: str
+    failure_summary: str = Field(min_length=1, max_length=400)
+    failed_step_type: str = "unknown"
+    agent_stack: list[str] = Field(default_factory=list)
+    resume_from_step: str = ""
+    recommended_next_action: str = "none"
+    redaction_status: str = "pass"
+    worker_output_status: str = "complete"
+    context_pack: list[str] = Field(default_factory=list)
+    provenance_ids: list[str] = Field(default_factory=list)
+    evidence_id: str = ""
+    affected_files: list[str] = Field(default_factory=list)
+    attempt_n: int = Field(default=1, ge=1)
+    max_attempts: int = Field(default=3, ge=1, le=32)
+
+
+class RecoveryMarkOutcomeRequest(StrictBody):
+    attempt_id: str = Field(min_length=32, max_length=32)
+    status: str
+    recovery_summary: str = Field(min_length=1, max_length=400)
+    proposal_id: str | None = None
+    review_evidence_id: str | None = None
+    apply_evidence_id: str | None = None
+    retry_gate_id: str | None = None
+
+
+@router.post("/recovery/record-failure")
+def recovery_record_failure(body: RecoveryRecordFailureRequest) -> dict[str, Any]:
+    try:
+        return code_history.record_step_failure(
+            owner=CODE_OPERATOR_ACTOR,
+            task_id=body.task_id,
+            failed_step=body.failed_step,
+            failure_class=body.failure_class,
+            failure_summary=body.failure_summary,
+            failed_step_type=body.failed_step_type,
+            agent_stack=body.agent_stack,
+            resume_from_step=body.resume_from_step,
+            recommended_next_action=body.recommended_next_action,
+            redaction_status=body.redaction_status,
+            worker_output_status=body.worker_output_status,
+            context_pack=body.context_pack,
+            provenance_ids=body.provenance_ids,
+            evidence_id=body.evidence_id,
+            affected_files=body.affected_files,
+            attempt_n=body.attempt_n,
+            max_attempts=body.max_attempts,
+        )
+    except (RuntimeError, ValueError, FileNotFoundError) as exc:
+        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc
+
+
+@router.post("/recovery/mark-outcome")
+def recovery_mark_outcome(body: RecoveryMarkOutcomeRequest) -> dict[str, Any]:
+    try:
+        return code_history.mark_recovery_outcome(
+            owner=CODE_OPERATOR_ACTOR,
+            attempt_id=body.attempt_id,
+            status=body.status,
+            recovery_summary=body.recovery_summary,
+            proposal_id=body.proposal_id,
+            review_evidence_id=body.review_evidence_id,
+            apply_evidence_id=body.apply_evidence_id,
+            retry_gate_id=body.retry_gate_id,
+        )
+    except (RuntimeError, ValueError, FileNotFoundError) as exc:
+        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc
+
+
+@router.get("/recovery/state")
+def recovery_state(task_id: str | None = None) -> dict[str, Any]:
+    try:
+        return code_history.list_recovery_attempts(task_id=task_id)
+    except (RuntimeError, ValueError, FileNotFoundError) as exc:
+        raise HTTPException(status_code=422, detail={"reason": str(exc)}) from exc

```

## proposal 33d7dbc691b146f7a495c6c23fa148b0
file: 04_testing/pytest/unit/test_code_operator.py
base_sha256: d74af4caa88523f3ef991c36410de662ef62cf227dd8a08b86560cb731bcabec
proposed_sha256: a2b41473db6b3f73520bab0549aa78a9a040a92cdb4319471fc0803cc29e5eea
```diff
--- 04_testing/pytest/unit/test_code_operator.py
+++ 04_testing/pytest/unit/test_code_operator.py (proposed)
@@ -632,3 +632,201 @@
 
     with pytest.raises(ValueError, match="no pre-change snapshot"):
         code_history.git_stage_owned_files(owner="hermes-agent", task_id="TASK-1", files=["README.md"])
+
+
+# ---------------------------------------------------------------------------
+# Recovery Controller v1 tests (lean ledger; no UI, no autonomous apply).
+# Each test uses a unique task_id so ledger entries don't collide. Tests
+# verify ledger writes, validation, redaction, outcome marking, and state
+# read-back. Future v1.5 fields covered: failed_step_type, failure_fingerprint,
+# retry_budget, agent_stack, worker_output_status, recommended_next_action.
+# ---------------------------------------------------------------------------
+
+
+from uuid import uuid4 as _recovery_uuid4
+
+
+def _recovery_task_id(suffix: str) -> str:
+    return f"H3D-TEST-RECOVERY-{_recovery_uuid4().hex[:12]}-{suffix}"
+
+
+def test_recovery_records_gate_fail() -> None:
+    client = TestClient(create_gui_app())
+    task_id = _recovery_task_id("gate")
+
+    response = client.post(
+        "/api/code-operator/recovery/record-failure",
+        json={
+            "task_id": task_id,
+            "failed_step": "git-diff-check",
+            "failure_class": "gate_fail",
+            "failure_summary": "trailing whitespace flagged on added line",
+            "failed_step_type": "gate_run",
+            "agent_stack": ["MiniMax", "DeepSeek", "Gate Runner"],
+            "recommended_next_action": "rollback_and_retry",
+            "worker_output_status": "complete",
+            "attempt_n": 1,
+            "max_attempts": 3,
+        },
+    )
+
+    assert response.status_code == 200, response.text
+    payload = response.json()
+    assert payload["status"] == "recorded"
+    attempt_id = payload["attempt_id"]
+    assert len(attempt_id) == 32
+    assert all(c in "0123456789abcdef" for c in attempt_id)
+    record = payload["record"]
+    assert record["failure_class"] == "gate_fail"
+    assert record["failed_step_type"] == "gate_run"
+    assert record["agent_stack"] == ["MiniMax", "DeepSeek", "Gate Runner"]
+    assert record["retry_budget"] == {"attempt_n": 1, "max_attempts": 3, "exhausted": False}
+    assert len(record["failure_fingerprint"]) == 16
+
+
+def test_recovery_records_patch_rejected() -> None:
+    client = TestClient(create_gui_app())
+    task_id = _recovery_task_id("patch")
+
+    response = client.post(
+        "/api/code-operator/recovery/record-failure",
+        json={
+            "task_id": task_id,
+            "failed_step": "deepseek_review_v1",
+            "failure_class": "patch_rejected",
+            "failure_summary": "reviewer requested in-band evidence",
+            "failed_step_type": "reviewer_pass",
+            "recommended_next_action": "refresh_context",
+            "worker_output_status": "complete",
+        },
+    )
+
+    assert response.status_code == 200
+    record = response.json()["record"]
+    assert record["failure_class"] == "patch_rejected"
+    assert record["failed_step_type"] == "reviewer_pass"
+    assert record["recommended_next_action"] == "refresh_context"
+
+
+def test_recovery_records_merge_git_fail() -> None:
+    client = TestClient(create_gui_app())
+    task_id = _recovery_task_id("merge")
+
+    response = client.post(
+        "/api/code-operator/recovery/record-failure",
+        json={
+            "task_id": task_id,
+            "failed_step": "git_branch",
+            "failure_class": "merge_git_fail",
+            "failure_summary": "untracked files blocked branch creation",
+            "failed_step_type": "git_branch",
+            "recommended_next_action": "rollback_and_retry",
+        },
+    )
+
+    assert response.status_code == 200
+    record = response.json()["record"]
+    assert record["failure_class"] == "merge_git_fail"
+    assert record["failed_step_type"] == "git_branch"
+
+
+def test_recovery_rejects_unknown_failure_class() -> None:
+    client = TestClient(create_gui_app())
+    task_id = _recovery_task_id("unknown")
+
+    response = client.post(
+        "/api/code-operator/recovery/record-failure",
+        json={
+            "task_id": task_id,
+            "failed_step": "something",
+            "failure_class": "not_a_real_class",
+            "failure_summary": "this should reject",
+        },
+    )
+
+    assert response.status_code == 422
+
+
+def test_recovery_redacts_secret_like_values() -> None:
+    client = TestClient(create_gui_app())
+    task_id = _recovery_task_id("secret")
+    bearer_value = "Bearer abcdefghijklmnop1234567890ABCDEFGH"
+
+    response = client.post(
+        "/api/code-operator/recovery/record-failure",
+        json={
+            "task_id": task_id,
+            "failed_step": "auth_check",
+            "failure_class": "provider_auth",
+            "failure_summary": f"upstream returned {bearer_value} mismatch",
+            "failed_step_type": "provider_smoke",
+            "redaction_status": "pass",
+        },
+    )
+
+    assert response.status_code == 200
+    summary = response.json()["record"]["failure_summary"]
+    assert bearer_value not in summary
+    assert "abcdefghijklmnop1234567890" not in summary
+
+
+def test_recovery_mark_outcome_recovered() -> None:
+    client = TestClient(create_gui_app())
+    task_id = _recovery_task_id("outcome")
+
+    record_resp = client.post(
+        "/api/code-operator/recovery/record-failure",
+        json={
+            "task_id": task_id,
+            "failed_step": "git-diff-check",
+            "failure_class": "gate_fail",
+            "failure_summary": "initial gate failure",
+            "failed_step_type": "gate_run",
+            "recommended_next_action": "rollback_and_retry",
+        },
+    )
+    assert record_resp.status_code == 200
+    attempt_id = record_resp.json()["attempt_id"]
+
+    outcome_resp = client.post(
+        "/api/code-operator/recovery/mark-outcome",
+        json={
+            "attempt_id": attempt_id,
+            "status": "recovered",
+            "recovery_summary": "rollback + re-author + re-gate succeeded",
+            "retry_gate_id": "gate_git-diff-check_demo",
+        },
+    )
+    assert outcome_resp.status_code == 200
+    payload = outcome_resp.json()
+    assert payload["status"] == "recorded"
+    outcome = payload["outcome"]
+    assert outcome["status"] == "recovered"
+    assert outcome["attempt_id"] == attempt_id
+
+
+def test_recovery_state_route_returns_attempts() -> None:
+    client = TestClient(create_gui_app())
+    task_id = _recovery_task_id("state")
+
+    record_resp = client.post(
+        "/api/code-operator/recovery/record-failure",
+        json={
+            "task_id": task_id,
+            "failed_step": "state_route_test",
+            "failure_class": "missing_proof",
+            "failure_summary": "for state route test",
+            "failed_step_type": "reviewer_pass",
+        },
+    )
+    assert record_resp.status_code == 200
+    attempt_id = record_resp.json()["attempt_id"]
+
+    state_resp = client.get(
+        f"/api/code-operator/recovery/state?task_id={task_id}",
+    )
+    assert state_resp.status_code == 200
+    payload = state_resp.json()
+    assert "attempts" in payload
+    assert payload["count"] >= 1
+    assert any(item.get("attempt_id") == attempt_id for item in payload["attempts"])

```
