"""Hermes Agent action-catalog contract tests."""

from __future__ import annotations

from hermes3d.api.routes import agents


def test_action_catalog_hides_internal_handlers_and_exposes_code_actions() -> None:
    agents._ACTION_CONTRACT_CACHE["contracts"] = None
    agents._ACTION_CONTRACT_CACHE["ts"] = 0.0

    payload = agents.action_catalog()
    contracts = payload["contracts"]
    by_id = {contract["id"]: contract for contract in contracts}

    assert "code.patch.apply" in by_id
    assert "code.mcp_locks.lock_files" in by_id
    assert "code.git.commit_owned" in by_id
    assert all("handler" not in contract for contract in contracts)
    assert set(by_id["code.mcp_locks.lock_files"]["payload_schema"]["required"]) == {"files", "task_id"}


def test_code_patch_apply_declares_high_risk_proof_and_rollback_contract() -> None:
    agents._ACTION_CONTRACT_CACHE["contracts"] = None
    agents._ACTION_CONTRACT_CACHE["ts"] = 0.0

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
    agents._ACTION_CONTRACT_CACHE["contracts"] = None
    agents._ACTION_CONTRACT_CACHE["ts"] = 0.0

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
