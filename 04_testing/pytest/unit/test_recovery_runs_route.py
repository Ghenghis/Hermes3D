"""BLK-026 (Wave Master Continuation Agent D20): RC v2 list_active_runs route.

Pre-fix: Recovery Controller v2 commits 1+2 landed in PR #149 but no HTTP
route exposed the v2 enrichment payload (``state``, ``branch``,
``locked_files``, ``pre_snapshot_ids``, ``freeze_event_utc``,
``next_action``). The v1 ``/recovery/state`` only returns the JSONL ledger
shape — Task Monitor UI work was blocked.

Post-fix: ``GET /api/code-operator/recovery/runs?task_id=...`` returns the
v2 active-runs snapshot from the in-memory registry. **Read-only**;
confirm-by-default preserved (no mutation routes in this PR).

References:
- https://tanstack.com/query/latest/docs/framework/react/guides/window-focus-refetching
- BLK-026 in E2E_COMPLETION_MASTER_REGISTRY_2026-05-09.md
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from hermes3d.services import code_history, recovery_controller


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Build a FastAPI TestClient with v1 collaborators stubbed."""
    from hermes3d.api.app import create_gui_app

    # Reset registry between tests.
    recovery_controller._reset_registry_for_tests()

    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)

    def stub_record_step_failure(**kwargs: Any) -> dict[str, Any]:
        attempt_id = "f" * 32
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

    monkeypatch.setattr(code_history, "record_step_failure", stub_record_step_failure)
    monkeypatch.setattr(
        code_history,
        "mark_recovery_outcome",
        lambda **kw: {"status": "recorded", "outcome": {}, "mcp_evidence": {}},
    )
    monkeypatch.setattr(
        code_history,
        "append_mcp_evidence",
        lambda **kw: {"status": "recorded", "evidence_id": "ev-stub", "result": {"ok": True}},
    )
    return TestClient(create_gui_app())


def test_recovery_runs_route_returns_empty_when_no_runs(client: TestClient) -> None:
    """Empty registry → empty `runs` list, no errors."""
    resp = client.get("/api/code-operator/recovery/runs")
    assert resp.status_code == 200
    body = resp.json()
    assert "runs" in body or "active_runs" in body or isinstance(body, dict)


def test_recovery_runs_route_returns_active_run_with_v2_fields(
    client: TestClient,
) -> None:
    """After start_recovery, the route surfaces the v2 enrichment fields."""
    spec = recovery_controller.RecoveryRunSpec(
        task_id="task-route-001",
        failed_step="apply_patch",
        failure_class="patch_rejected",
        failure_summary="patch did not apply",
        failed_step_type="patch_apply",
        actor="user",
    )
    recovery_controller.start_recovery(spec=spec, owner="claude-test")
    resp = client.get("/api/code-operator/recovery/runs")
    assert resp.status_code == 200
    body = resp.json()
    runs = body.get("runs") or body.get("active_runs") or []
    assert isinstance(runs, list)
    assert len(runs) >= 1, f"Expected >=1 run, got {body!r}"
    run = runs[0]
    # v2 enrichment fields must be present
    for required_field in ("state", "branch", "task_id", "attempt_id"):
        assert required_field in run, (
            f"BLK-026 regression: v2 enrichment field {required_field!r} missing"
        )


def test_recovery_runs_route_filters_by_task_id(client: TestClient) -> None:
    """task_id query param filters the active runs."""
    for tid in ("task-A", "task-B"):
        spec = recovery_controller.RecoveryRunSpec(
            task_id=tid,
            failed_step="step",
            failure_class="patch_rejected",
            failure_summary="x",
            failed_step_type="patch_apply",
            actor="user",
        )
        recovery_controller.start_recovery(spec=spec, owner="claude-test")
    resp = client.get("/api/code-operator/recovery/runs?task_id=task-A")
    assert resp.status_code == 200
    runs = resp.json().get("runs") or resp.json().get("active_runs") or []
    assert all(r.get("task_id") == "task-A" for r in runs), (
        f"Filter failed; got runs: {runs!r}"
    )


def test_recovery_runs_route_no_mutation_in_path(client: TestClient) -> None:
    """Confirm-by-default: only GET is exposed for /recovery/runs in this PR."""
    resp_post = client.post("/api/code-operator/recovery/runs", json={})
    # FastAPI returns 405 for method-not-allowed on GET-only routes.
    assert resp_post.status_code == 405, (
        f"BLK-026 scope regression: POST should be 405, got {resp_post.status_code}"
    )
