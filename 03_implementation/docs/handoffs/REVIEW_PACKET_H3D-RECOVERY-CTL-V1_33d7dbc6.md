# Review packet — H3D-RECOVERY-CTL-V1 / test_code_operator.py

proposal_id: 33d7dbc691b146f7a495c6c23fa148b0
file: 04_testing/pytest/unit/test_code_operator.py
base_sha256: d74af4caa88523f3ef991c36410de662ef62cf227dd8a08b86560cb731bcabec
proposed_sha256: a2b41473db6b3f73520bab0549aa78a9a040a92cdb4319471fc0803cc29e5eea
diff_bytes: 7510
reason: H3D-RECOVERY-CTL-V1 v1.5 file 04_testing/pytest/unit/test_code_operator.py. Provenance: MiniMax artifacts 2130e9e1d12d4686ac4d788bfd136673 + 459bc9c00d6049dd949fa84e61f09c7a (both completion-token-truncated, manually assembled). Adds 10 future-proof fields for the Hermes Agent Task Monitor: agent_stack, failed_step_type, resume_from_step, recommended_next_action, provenance_ids, redaction_status, retry_budget, failure_fingerprint, context_pack, worker_output_status. Lean v1 contract preserved: NO UI, NO autonomous apply, NO file mutation by controller. Local py_compile PASS. No private values exposed.

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
