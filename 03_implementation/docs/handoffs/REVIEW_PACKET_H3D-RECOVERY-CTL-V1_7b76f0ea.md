# Review packet — H3D-RECOVERY-CTL-V1 / code_operator.py

proposal_id: 7b76f0eae91a4f0d8c80850fcef0b4f0
file: 03_implementation/src/hermes3d/api/routes/code_operator.py
base_sha256: c7bacb96434369372de7fb56ff0f111a016c898fca5e0ccff7f8ed53d31eaa54
proposed_sha256: b1946952293cb20c9b7fc11a5ffad458777e6f8f348cdc8d0cc3a0ba87700dcd
diff_bytes: 4085
reason: H3D-RECOVERY-CTL-V1 v1.5 file 03_implementation/src/hermes3d/api/routes/code_operator.py. Provenance: MiniMax artifacts 2130e9e1d12d4686ac4d788bfd136673 + 459bc9c00d6049dd949fa84e61f09c7a (both completion-token-truncated, manually assembled). Adds 10 future-proof fields for the Hermes Agent Task Monitor: agent_stack, failed_step_type, resume_from_step, recommended_next_action, provenance_ids, redaction_status, retry_budget, failure_fingerprint, context_pack, worker_output_status. Lean v1 contract preserved: NO UI, NO autonomous apply, NO file mutation by controller. Local py_compile PASS. No private values exposed.

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
