"""Hermes Agent action-catalog contract tests."""

from __future__ import annotations

from hermes3d.api.routes import agents


def _reset_action_catalog_cache() -> None:
    agents._ACTION_CONTRACT_CACHE["contracts"] = None
    agents._ACTION_CONTRACT_CACHE["ts"] = 0.0


def test_action_catalog_hides_internal_handlers_and_exposes_code_actions() -> None:
    _reset_action_catalog_cache()

    payload = agents.action_catalog()
    contracts = payload["contracts"]
    by_id = {contract["id"]: contract for contract in contracts}

    assert "code.patch.apply" in by_id
    assert "code.mcp_locks.lock_files" in by_id
    assert "code.git.commit_owned" in by_id
    assert "code.teams.assign_task" in by_id
    assert "code.teams.request_review" in by_id
    assert all("handler" not in contract for contract in contracts)
    assert set(by_id["code.mcp_locks.lock_files"]["payload_schema"]["required"]) == {"files", "task_id"}


def test_code_patch_apply_declares_high_risk_proof_and_rollback_contract() -> None:
    _reset_action_catalog_cache()

    patch_apply = {
        contract["id"]: contract
        for contract in agents.action_catalog()["contracts"]
    }["code.patch.apply"]

    assert patch_apply["kind"] == "mutate"
    assert patch_apply["risk"] == "high"
    assert patch_apply["approval_required"] is True
    assert patch_apply["rollback_required"] is True
    assert patch_apply["proof_required"] is True
    assert set(patch_apply["payload_schema"]["required"]) == {"proposal_id", "task_id"}
    assert "same-owner Hermes MCP file lock" in patch_apply["summary"]


def test_code_git_commit_declares_owned_snapshot_contract() -> None:
    _reset_action_catalog_cache()

    git_commit = {
        contract["id"]: contract
        for contract in agents.action_catalog()["contracts"]
    }["code.git.commit_owned"]

    assert git_commit["kind"] == "mutate"
    assert git_commit["risk"] == "high"
    assert git_commit["approval_required"] is True
    assert git_commit["rollback_required"] is True
    assert set(git_commit["payload_schema"]["required"]) == {"task_id", "files", "message"}
    assert "owned snapshot" in git_commit["payload_schema"]["safety"]


def test_code_team_actions_declare_assignment_and_review_contracts() -> None:
    _reset_action_catalog_cache()

    by_id = {contract["id"]: contract for contract in agents.action_catalog()["contracts"]}
    assignment = by_id["code.teams.assign_task"]
    review = by_id["code.teams.request_review"]

    assert assignment["kind"] == "proof"
    assert assignment["risk"] == "medium"
    assert assignment["proof_required"] is True
    assert assignment["approval_required"] is False
    assert set(assignment["payload_schema"]["required"]) == {"team_id", "task_id", "title", "files", "objective"}
    assert "minimax-builders" in assignment["payload_schema"]["safety"]

    assert review["kind"] == "proof"
    assert review["risk"] == "medium"
    assert set(review["payload_schema"]["required"]) == {"task_id", "summary", "files", "proof_ids"}
    assert "proof/evidence id" in review["payload_schema"]["safety"]
