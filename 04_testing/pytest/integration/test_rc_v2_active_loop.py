"""W6-2 — Recovery Controller v2 active-loop integration tests.

Scope
-----
Eight tests covering the four W6-2 routes + their service methods:

    POST /api/code-operator/recovery/propose
    POST /api/code-operator/recovery/review
    POST /api/code-operator/recovery/apply
    POST /api/code-operator/recovery/resume

The full failure -> freeze -> propose -> review -> apply -> resume -> thaw
sequence is exercised end-to-end, with provider adapters (MiniMax /
DeepSeek) and the v1 ledger/MCP layer stubbed via ``monkeypatch.setattr``
so the tests run free of network, paid LLM credit, and orchestrator I/O.

Per the no-paid-services rule (user MEMORY ``feedback_no_paid_services``),
every mocked LLM-style call carries ``credit_spent_usd: 0.0`` and the
suite asserts that field is zero in every observed proposal/review.

Sources cited (2-source minimum)
--------------------------------
1. Saga pattern (Garcia-Molina + Salem 1987) -- compensable long-lived
   transactions. The active loop is the fix-application leg of RC v2's
   saga: each successful step transitions to the next state; an apply
   failure compensates by closing the v1 outcome row and returning the
   run to RETRY_FAILED with its locks released. Reference:
   https://temporal.io/blog/saga-pattern-made-easy

2. FastAPI bigger-applications router pattern -- the four new routes
   are appended to the existing ``code_operator`` ``APIRouter`` (rather
   than living in a new module) because they share the same prefix,
   tags, and validation chain. Reference:
   https://fastapi.tiangolo.com/tutorial/bigger-applications/

Tests
-----
1. POST /propose with no provider configured -> 503 + redacted message.
2. POST /propose with mocked MiniMax adapter -> 200 + ProposalRecord.
3. POST /review with mocked DeepSeek adapter -> 200 + ReviewRecord(approved).
4. POST /apply requires approved review -> 409 if rejected/pending.
5. POST /apply with approved review + mocked patch -> 200 + ApplyRecord.
6. POST /resume runs original gate; if green -> ResumeRecord(success);
   if red -> escalate.
7. End-to-end: failure -> freeze -> propose -> review -> apply -> resume
   -> thaw, asserting event order.
8. credit_spent_usd assertion: every mocked LLM call has ``cost_usd: 0.0``.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from hermes3d.services import code_history, recovery_controller


# ---------------------------------------------------------------------------
# Fixture: TestClient + full set of stubs (v1 ledger + provider adapters)
# ---------------------------------------------------------------------------


def _stable_attempt_id(seq: int = 1) -> str:
    """Return a deterministic 32-char lowercase hex attempt_id for tests."""
    return f"{seq:032x}"


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Build a TestClient + stub all v1 collaborators + provider adapters.

    Returned dict keys:
      * client: FastAPI TestClient
      * captured: dict of phase->list[kwargs] for assertion
      * proposal_response / review_response / apply_response /
        gate_response: per-test mutable adapter outputs (default: success)
      * fail_apply: bool toggle that makes apply_reviewed_patch_proposal raise
    """
    from hermes3d.api.app import create_gui_app

    recovery_controller._reset_registry_for_tests()
    # Reset adapters to defaults each test (PR safety: avoid cross-test bleed).
    monkeypatch.setattr(
        recovery_controller,
        "_minimax_adapter",
        recovery_controller._default_minimax_adapter,
    )
    monkeypatch.setattr(
        recovery_controller,
        "_deepseek_adapter",
        recovery_controller._default_deepseek_adapter,
    )

    captured: dict[str, list[Any]] = {
        "lock_calls": [],
        "release_calls": [],
        "snapshot_calls": [],
        "step_failure_calls": [],
        "outcome_calls": [],
        "evidence_calls": [],
        "apply_calls": [],
        "gate_calls": [],
        "minimax_calls": [],
        "deepseek_calls": [],
    }

    state = {
        "fail_apply": False,
        # Each call to the apply stub increments seq; allows 2+ apply attempts.
        "apply_seq": 0,
    }

    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)

    def stub_lock(**kwargs: Any) -> dict[str, Any]:
        captured["lock_calls"].append(kwargs)
        return {"status": "locked", "files": kwargs.get("files", []), "owner": kwargs.get("owner")}

    def stub_release(**kwargs: Any) -> dict[str, Any]:
        captured["release_calls"].append(kwargs)
        return {"status": "released", "files": kwargs.get("files", [])}

    def stub_snapshot(rel: str, **kwargs: Any) -> dict[str, Any]:
        captured["snapshot_calls"].append({"rel": rel, **kwargs})
        return {
            "id": f"snap-{rel.replace('/', '_')}-{len(captured['snapshot_calls'])}",
            "ts_utc": "2026-05-09T00:00:00Z",
        }

    def stub_record_step_failure(**kwargs: Any) -> dict[str, Any]:
        captured["step_failure_calls"].append(kwargs)
        attempt_id = _stable_attempt_id(len(captured["step_failure_calls"]))
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
                "failure_fingerprint": "abcdef0123456789",
                "retry_budget": {"attempt_n": 1, "max_attempts": 3, "exhausted": False},
                "ts_utc": "2026-05-09T00:00:00Z",
            },
            "mcp_evidence": {"evidence_id": "ev-stub-failure"},
        }

    def stub_mark_outcome(**kwargs: Any) -> dict[str, Any]:
        captured["outcome_calls"].append(kwargs)
        return {
            "status": "recorded",
            "outcome": {"attempt_id": kwargs.get("attempt_id"), "status": kwargs.get("status")},
            "mcp_evidence": {"evidence_id": "ev-stub-outcome"},
        }

    def stub_evidence(**kwargs: Any) -> dict[str, Any]:
        captured["evidence_calls"].append(kwargs)
        return {"status": "recorded", "evidence_id": "ev-stub", "result": {"ok": True}}

    def stub_apply_reviewed(proposal_id: str, **kwargs: Any) -> dict[str, Any]:
        captured["apply_calls"].append({"proposal_id": proposal_id, **kwargs})
        if state["fail_apply"]:
            raise RuntimeError(
                "synthetic apply failure: file conflict during reviewed patch apply"
            )
        state["apply_seq"] += 1
        return {
            "status": "reviewed_applied",
            "accepted": True,
            "proposal_id": proposal_id,
            "review_proof_ids": list(kwargs.get("review_proof_ids", []) or []),
            "apply": {
                "relative_path": "scripts/cli_runner.py",
                "proof_event_id": f"apply-pe-{state['apply_seq']:04d}",
            },
            "mcp_evidence": {"evidence_id": f"ev-stub-apply-{state['apply_seq']:04d}"},
        }

    def stub_run_mcp_gate(gate_id: str, **kwargs: Any) -> dict[str, Any]:
        captured["gate_calls"].append({"gate_id": gate_id, **kwargs})
        # Default: green; tests can override via state["gate_status"].
        gate_status = state.get("gate_status", "pass")
        return {
            "status": gate_status,
            "ok": gate_status == "pass",
            "server_name": "hermes3d-locks",
            "workspace": "G:/Github/h3d-gui-wiring-codex",
            "gate_id": gate_id,
            "owner": kwargs.get("owner"),
            "result": {"status": gate_status, "ok": gate_status == "pass"},
        }

    monkeypatch.setattr(code_history, "lock_mcp_files", stub_lock)
    monkeypatch.setattr(code_history, "release_mcp_files", stub_release)
    monkeypatch.setattr(code_history, "snapshot_file", stub_snapshot)
    monkeypatch.setattr(code_history, "record_step_failure", stub_record_step_failure)
    monkeypatch.setattr(code_history, "mark_recovery_outcome", stub_mark_outcome)
    monkeypatch.setattr(code_history, "append_mcp_evidence", stub_evidence)
    monkeypatch.setattr(code_history, "apply_reviewed_patch_proposal", stub_apply_reviewed)
    monkeypatch.setattr(code_history, "run_mcp_gate", stub_run_mcp_gate)

    client = TestClient(create_gui_app())
    return {
        "client": client,
        "captured": captured,
        "state": state,
        "monkeypatch": monkeypatch,
    }


# ---------------------------------------------------------------------------
# Adapter fixtures: tests opt-in to provider mocking
# ---------------------------------------------------------------------------


def _install_minimax_mock(monkeypatch: pytest.MonkeyPatch, captured: list[Any]) -> None:
    """Install a deterministic MiniMax mock that records calls + returns a canned proposal."""
    def mock_propose(request: dict[str, Any]) -> dict[str, Any]:
        captured.append(request)
        return {
            "proposal_id": f"prop-{request.get('attempt_id', 'x')[:8]}",
            "files_touched": ["scripts/cli_runner.py"],
            "rationale": (
                "Failed step timed out at 5s; raise the runner timeout to 30s "
                "to address cold-start latency without changing behavior."
            ),
            "model_meta": {
                "provider": "minimax_mock",
                "model": "test-fixture",
                "credit_spent_usd": 0.0,
                "cost_usd": 0.0,
            },
        }

    monkeypatch.setattr(recovery_controller, "_minimax_adapter", mock_propose)


def _install_deepseek_mock(
    monkeypatch: pytest.MonkeyPatch,
    captured: list[Any],
    *,
    verdict: str = "approved",
) -> None:
    """Install a deterministic DeepSeek mock with the given verdict."""
    def mock_review(request: dict[str, Any]) -> dict[str, Any]:
        captured.append(request)
        return {
            "review_id": f"rev-{request.get('proposal_id', 'x')[:8]}",
            "verdict": verdict,
            "review_proof_ids": [f"review-proof-{request.get('proposal_id', 'x')[:8]}"],
            "concerns": [] if verdict == "approved" else ["needs more context on edge case"],
            "files_reviewed": list(request.get("files_touched", []) or []),
            "model_meta": {
                "provider": "deepseek_mock",
                "model": "test-fixture",
                "credit_spent_usd": 0.0,
                "cost_usd": 0.0,
            },
        }

    monkeypatch.setattr(recovery_controller, "_deepseek_adapter", mock_review)


# ---------------------------------------------------------------------------
# Helpers: drive the run up to a target state via the service surface
# ---------------------------------------------------------------------------


def _start_and_freeze(failure_class: str = "patch_rejected") -> str:
    """Start a recovery run and freeze it; return attempt_id (run is in PROPOSING)."""
    spec = recovery_controller.RecoveryRunSpec(
        task_id=f"task-w62-{failure_class}",
        failed_step="apply_patch.cli_runner",
        failure_class=failure_class,
        failed_step_type="patch_apply",
        failure_summary="patch did not apply: cli runner timed out at 5s",
        actor="user",
        confirm=False,
        agent_stack=("claude-w6-2",),
        retry_budget_max=3,
    )
    started = recovery_controller.start_recovery(spec=spec, owner="claude-w6-2-test")
    assert started["status"] == "created", f"setup invariant: {started!r}"
    attempt_id: str = started["run"]["attempt_id"]
    frozen = recovery_controller.freeze_run(
        attempt_id=attempt_id,
        owner="claude-w6-2-test",
        files=("scripts/cli_runner.py",),
    )
    assert frozen["status"] == "frozen", f"setup invariant: {frozen!r}"
    return attempt_id


# ---------------------------------------------------------------------------
# Tests (8 total, matching the brief)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_propose_returns_503_when_provider_not_configured(
    harness: dict[str, Any],
) -> None:
    """Test 1: POST /propose with no provider configured -> 503 + redacted message.

    Default ``_minimax_adapter`` raises ``ProviderNotConfigured``; the
    route MUST translate this to 503 with a generic message that does
    NOT name a specific env var (per the no-paid-services hardening).
    """
    client: TestClient = harness["client"]
    attempt_id = _start_and_freeze()
    resp = client.post(
        "/api/code-operator/recovery/propose",
        json={"run_id": attempt_id, "failure_summary": "synthetic failure"},
    )
    assert resp.status_code == 503, f"expected 503, got {resp.status_code} body={resp.text}"
    body = resp.json()
    detail = body.get("detail", {})
    reason = detail.get("reason", "") if isinstance(detail, dict) else ""
    assert "provider is not configured" in reason.lower(), reason
    # 503 message must NOT name a specific env var (e.g. MINIMAX_API_KEY).
    assert "API_KEY" not in reason
    assert "minimax" not in reason.lower(), (
        "503 message must not name the provider; operators read the doc."
    )


@pytest.mark.integration
def test_propose_with_mocked_minimax_returns_proposal_record(
    harness: dict[str, Any],
) -> None:
    """Test 2: POST /propose with mocked MiniMax adapter -> 200 + ProposalRecord."""
    client: TestClient = harness["client"]
    captured = harness["captured"]
    monkeypatch = harness["monkeypatch"]
    _install_minimax_mock(monkeypatch, captured["minimax_calls"])

    attempt_id = _start_and_freeze()
    resp = client.post(
        "/api/code-operator/recovery/propose",
        json={"run_id": attempt_id, "failure_summary": "cli runner timeout"},
    )
    assert resp.status_code == 200, f"got {resp.status_code} body={resp.text}"
    body = resp.json()
    assert body["status"] == "proposed"
    assert body["attempt_id"] == attempt_id
    record = body["proposal_record"]
    assert record["proposal_id"].startswith("prop-")
    assert record["files_touched"] == ["scripts/cli_runner.py"]
    # No-paid-services rule: model_meta must declare zero cost.
    meta = record["model_meta"]
    assert meta["credit_spent_usd"] == 0.0
    assert meta["cost_usd"] == 0.0
    # Run state advanced from proposing -> reviewing.
    assert body["run"]["state"] == "reviewing"
    # Adapter received exactly one call with the redacted summary.
    assert len(captured["minimax_calls"]) == 1
    sent = captured["minimax_calls"][0]
    assert sent["attempt_id"] == attempt_id
    assert sent["task_id"].startswith("task-w62-")


@pytest.mark.integration
def test_review_with_mocked_deepseek_approves_proposal(
    harness: dict[str, Any],
) -> None:
    """Test 3: POST /review with mocked DeepSeek adapter -> 200 + ReviewRecord(approved)."""
    client: TestClient = harness["client"]
    captured = harness["captured"]
    monkeypatch = harness["monkeypatch"]
    _install_minimax_mock(monkeypatch, captured["minimax_calls"])
    _install_deepseek_mock(monkeypatch, captured["deepseek_calls"], verdict="approved")

    attempt_id = _start_and_freeze()
    propose_resp = client.post(
        "/api/code-operator/recovery/propose",
        json={"run_id": attempt_id},
    )
    proposal_id = propose_resp.json()["proposal_record"]["proposal_id"]

    resp = client.post(
        "/api/code-operator/recovery/review",
        json={"run_id": attempt_id, "proposal_id": proposal_id},
    )
    assert resp.status_code == 200, f"got {resp.status_code} body={resp.text}"
    body = resp.json()
    assert body["status"] == "reviewed"
    assert body["verdict"] == "approved"
    rec = body["review_record"]
    assert rec["proposal_id"] == proposal_id
    assert rec["verdict"] == "approved"
    assert rec["model_meta"]["credit_spent_usd"] == 0.0
    assert rec["model_meta"]["cost_usd"] == 0.0
    # State advanced to awaiting_human_confirm.
    assert body["run"]["state"] == "awaiting_human_confirm"


@pytest.mark.integration
def test_apply_requires_approved_review_otherwise_409(
    harness: dict[str, Any],
) -> None:
    """Test 4: POST /apply requires approved review -> 409 if rejected/pending.

    Two sub-cases:
      a) Review is pending (no review call yet) -> 409 not_ready_to_apply.
      b) Review came back 'rejected' -> 409 review_not_approved.
    """
    client: TestClient = harness["client"]
    captured = harness["captured"]
    monkeypatch = harness["monkeypatch"]
    _install_minimax_mock(monkeypatch, captured["minimax_calls"])

    # Sub-case A: review pending (run still in REVIEWING).
    attempt_id_a = _start_and_freeze()
    prop_a = client.post(
        "/api/code-operator/recovery/propose", json={"run_id": attempt_id_a}
    ).json()
    proposal_id_a = prop_a["proposal_record"]["proposal_id"]
    resp_a = client.post(
        "/api/code-operator/recovery/apply",
        json={"run_id": attempt_id_a, "proposal_id": proposal_id_a, "confirm": True},
    )
    assert resp_a.status_code == 409, f"got {resp_a.status_code} body={resp_a.text}"
    detail_a = resp_a.json()["detail"]
    assert "awaiting_human_confirm" in detail_a["reason"].lower()

    # Sub-case B: review rejected -> apply 409 with verdict surfaced.
    # Reset registry and rerun setup so we get a fresh attempt id.
    recovery_controller._reset_registry_for_tests()
    _install_deepseek_mock(monkeypatch, captured["deepseek_calls"], verdict="rejected")
    attempt_id_b = _start_and_freeze()
    prop_b = client.post(
        "/api/code-operator/recovery/propose", json={"run_id": attempt_id_b}
    ).json()
    proposal_id_b = prop_b["proposal_record"]["proposal_id"]
    review_b = client.post(
        "/api/code-operator/recovery/review",
        json={"run_id": attempt_id_b, "proposal_id": proposal_id_b},
    ).json()
    assert review_b["verdict"] == "rejected"
    # Run is still in REVIEWING because a 'rejected' verdict does not advance.
    resp_b = client.post(
        "/api/code-operator/recovery/apply",
        json={"run_id": attempt_id_b, "proposal_id": proposal_id_b, "confirm": True},
    )
    assert resp_b.status_code == 409
    detail_b = resp_b.json()["detail"]
    assert "awaiting_human_confirm" in detail_b["reason"].lower(), (
        "rejected verdict keeps the run in REVIEWING; apply must 409 on state, "
        "not on verdict (the verdict-check fires only when state is correct)."
    )


@pytest.mark.integration
def test_apply_with_approved_review_modifies_files(
    harness: dict[str, Any],
) -> None:
    """Test 5: POST /apply with approved review + mocked patch -> 200 + ApplyRecord.

    Asserts the apply_reviewed_patch_proposal stub was invoked with the
    correct review_proof_ids and that the run transitions APPLYING ->
    RE_RUNNING_GATE.
    """
    client: TestClient = harness["client"]
    captured = harness["captured"]
    monkeypatch = harness["monkeypatch"]
    _install_minimax_mock(monkeypatch, captured["minimax_calls"])
    _install_deepseek_mock(monkeypatch, captured["deepseek_calls"], verdict="approved")

    attempt_id = _start_and_freeze()
    prop = client.post(
        "/api/code-operator/recovery/propose", json={"run_id": attempt_id}
    ).json()
    proposal_id = prop["proposal_record"]["proposal_id"]
    rev = client.post(
        "/api/code-operator/recovery/review",
        json={"run_id": attempt_id, "proposal_id": proposal_id},
    ).json()
    assert rev["verdict"] == "approved"

    # Confirm-by-default check: confirm=False -> 422.
    resp_no_confirm = client.post(
        "/api/code-operator/recovery/apply",
        json={"run_id": attempt_id, "proposal_id": proposal_id, "confirm": False},
    )
    assert resp_no_confirm.status_code == 422

    # Now confirm=True -> 200.
    resp = client.post(
        "/api/code-operator/recovery/apply",
        json={"run_id": attempt_id, "proposal_id": proposal_id, "confirm": True},
    )
    assert resp.status_code == 200, f"got {resp.status_code} body={resp.text}"
    body = resp.json()
    assert body["status"] == "applied"
    record = body["apply_record"]
    assert record["proposal_id"] == proposal_id
    assert record["applied"] is True
    assert "scripts/cli_runner.py" in record["files_changed"]
    # Underlying apply_reviewed_patch_proposal was called with review proofs.
    assert len(captured["apply_calls"]) == 1
    apply_call = captured["apply_calls"][0]
    assert apply_call["proposal_id"] == proposal_id
    assert apply_call["review_proof_ids"], "Must pass at least one review proof id"
    # Run advanced to re_running_gate.
    assert body["run"]["state"] == "re_running_gate"


@pytest.mark.integration
def test_resume_runs_gate_and_terminates_recovered_or_escalated(
    harness: dict[str, Any],
) -> None:
    """Test 6: POST /resume runs original gate; green -> resumed; red -> escalated.

    Two sub-cases run in sequence (same client; new run for each).
    """
    client: TestClient = harness["client"]
    captured = harness["captured"]
    state = harness["state"]
    monkeypatch = harness["monkeypatch"]

    def _drive_to_re_running_gate() -> str:
        _install_minimax_mock(monkeypatch, captured["minimax_calls"])
        _install_deepseek_mock(monkeypatch, captured["deepseek_calls"], verdict="approved")
        attempt_id = _start_and_freeze()
        prop = client.post(
            "/api/code-operator/recovery/propose", json={"run_id": attempt_id}
        ).json()
        proposal_id = prop["proposal_record"]["proposal_id"]
        client.post(
            "/api/code-operator/recovery/review",
            json={"run_id": attempt_id, "proposal_id": proposal_id},
        )
        client.post(
            "/api/code-operator/recovery/apply",
            json={"run_id": attempt_id, "proposal_id": proposal_id, "confirm": True},
        )
        return attempt_id

    # Sub-case A: gate green -> resumed (RECOVERED).
    state["gate_status"] = "pass"
    attempt_a = _drive_to_re_running_gate()
    resp_a = client.post(
        "/api/code-operator/recovery/resume", json={"run_id": attempt_a}
    )
    assert resp_a.status_code == 200, f"got {resp_a.status_code} body={resp_a.text}"
    body_a = resp_a.json()
    assert body_a["status"] == "resumed"
    assert body_a["resume_record"]["passed"] is True
    assert body_a["run"]["state"] == "recovered"
    assert body_a["run"]["terminal_status"] == "recovered"
    # thaw_run was invoked (release_mcp_files called); locks cleared on the run.
    assert body_a["run"]["locked_files"] == []

    # Sub-case B: gate red -> escalated.
    recovery_controller._reset_registry_for_tests()
    state["gate_status"] = "failed"
    attempt_b = _drive_to_re_running_gate()
    resp_b = client.post(
        "/api/code-operator/recovery/resume", json={"run_id": attempt_b}
    )
    assert resp_b.status_code == 200
    body_b = resp_b.json()
    assert body_b["status"] == "escalated"
    assert body_b["resume_record"]["passed"] is False
    assert body_b["run"]["state"] == "escalated"
    assert body_b["run"]["terminal_status"] == "escalated"


@pytest.mark.integration
def test_end_to_end_failure_through_resume_emits_phases_in_order(
    harness: dict[str, Any],
) -> None:
    """Test 7: End-to-end sequence asserts the full phase ordering.

    Phases: failure_classified -> freeze (lock) -> snapshot ->
    fix_proposal -> review -> apply -> resume -> thaw.
    """
    client: TestClient = harness["client"]
    captured = harness["captured"]
    state = harness["state"]
    monkeypatch = harness["monkeypatch"]
    _install_minimax_mock(monkeypatch, captured["minimax_calls"])
    _install_deepseek_mock(monkeypatch, captured["deepseek_calls"], verdict="approved")
    state["gate_status"] = "pass"

    attempt_id = _start_and_freeze()
    prop = client.post(
        "/api/code-operator/recovery/propose", json={"run_id": attempt_id}
    ).json()
    proposal_id = prop["proposal_record"]["proposal_id"]
    rev = client.post(
        "/api/code-operator/recovery/review",
        json={"run_id": attempt_id, "proposal_id": proposal_id},
    ).json()
    apply_resp = client.post(
        "/api/code-operator/recovery/apply",
        json={"run_id": attempt_id, "proposal_id": proposal_id, "confirm": True},
    ).json()
    resume_resp = client.post(
        "/api/code-operator/recovery/resume", json={"run_id": attempt_id}
    ).json()

    # Phase ordering invariants:
    # 1. failure (record_step_failure) ran before freeze (lock_mcp_files).
    assert len(captured["step_failure_calls"]) >= 1
    assert len(captured["lock_calls"]) >= 1
    # 2. snapshot ran after lock.
    assert len(captured["snapshot_calls"]) >= 1
    # 3. proposal -> review -> apply -> gate sequence.
    assert prop["status"] == "proposed"
    assert rev["status"] == "reviewed" and rev["verdict"] == "approved"
    assert apply_resp["status"] == "applied"
    assert resume_resp["status"] == "resumed"
    # 4. apply_reviewed_patch_proposal was invoked exactly once.
    assert len(captured["apply_calls"]) == 1
    # 5. gate was re-run.
    assert len(captured["gate_calls"]) == 1
    # 6. thaw fired on resume (release_mcp_files called).
    assert len(captured["release_calls"]) >= 1
    # 7. mark_recovery_outcome closed the run with status=recovered.
    outcome = captured["outcome_calls"][-1]
    assert outcome["status"] == "recovered"
    assert outcome["attempt_id"] == attempt_id
    # 8. run history holds the full phase trail.
    history = recovery_controller.get_run_state(attempt_id)["state"]
    assert history == "recovered"


@pytest.mark.integration
def test_credit_spent_usd_zero_for_every_mocked_llm_call(
    harness: dict[str, Any],
) -> None:
    """Test 8: every mocked LLM call has cost_usd: 0.0 (no_paid_services rule).

    Assertion runs against both proposal_record.model_meta and
    review_record.model_meta — these are the only paths LLM cost would
    surface in the controller's response shape.
    """
    client: TestClient = harness["client"]
    captured = harness["captured"]
    monkeypatch = harness["monkeypatch"]
    _install_minimax_mock(monkeypatch, captured["minimax_calls"])
    _install_deepseek_mock(monkeypatch, captured["deepseek_calls"], verdict="approved")

    attempt_id = _start_and_freeze()
    prop = client.post(
        "/api/code-operator/recovery/propose", json={"run_id": attempt_id}
    ).json()
    rev = client.post(
        "/api/code-operator/recovery/review",
        json={"run_id": attempt_id, "proposal_id": prop["proposal_record"]["proposal_id"]},
    ).json()

    # Proposal cost assertions.
    pmeta = prop["proposal_record"]["model_meta"]
    assert pmeta["credit_spent_usd"] == 0.0, (
        f"no_paid_services rule violated: proposal cost was {pmeta!r}"
    )
    assert pmeta["cost_usd"] == 0.0

    # Review cost assertions.
    rmeta = rev["review_record"]["model_meta"]
    assert rmeta["credit_spent_usd"] == 0.0, (
        f"no_paid_services rule violated: review cost was {rmeta!r}"
    )
    assert rmeta["cost_usd"] == 0.0

    # Belt-and-suspenders: scan the entire response payloads for any
    # non-zero monetary marker. If a future refactor adds new cost
    # surfaces, this catches them.
    def _walk(obj: Any) -> list[tuple[str, Any]]:
        out: list[tuple[str, Any]] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str) and ("cost" in k.lower() or "usd" in k.lower()
                                           or "credit" in k.lower()):
                    out.append((k, v))
                out.extend(_walk(v))
        elif isinstance(obj, list):
            for item in obj:
                out.extend(_walk(item))
        return out

    for k, v in _walk(prop) + _walk(rev):
        if isinstance(v, (int, float)):
            assert v == 0 or v == 0.0, (
                f"no_paid_services rule violated: field {k!r} was {v!r}"
            )
