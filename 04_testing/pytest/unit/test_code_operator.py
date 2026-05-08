"""Hermes Agent code-operator hardening tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hermes3d.api.app import create_gui_app
from hermes3d.services import code_history


def test_code_operator_routes_are_registered() -> None:
    app = create_gui_app()
    paths = {route.path for route in app.routes}

    assert "/api/code-operator/programming-readiness" in paths
    assert "/api/code-operator/teams/readiness" in paths
    assert "/api/code-operator/teams/assign-task" in paths
    assert "/api/code-operator/teams/request-review" in paths
    assert "/api/code-operator/patch/apply" in paths
    assert "/api/code-operator/git/commit-owned" in paths
    assert "/api/code-operator/history/restore" in paths
    assert "/api/code-operator/mcp-locks/evidence" in paths


@pytest.mark.parametrize(
    "payload",
    [
        {"proposal_id": "a" * 32, "task_id": "TASK-1", "agent_id": "spoofed-agent"},
        {"proposal_id": "a" * 32, "task_id": "TASK-1", "owner": "spoofed-agent"},
    ],
)
def test_patch_apply_rejects_spoofed_actor_fields(payload: dict[str, str]) -> None:
    client = TestClient(create_gui_app())

    response = client.post("/api/code-operator/patch/apply", json=payload)

    assert response.status_code == 422


def test_mcp_evidence_requires_server_side_actor_and_task() -> None:
    client = TestClient(create_gui_app())

    spoofed = client.post(
        "/api/code-operator/mcp-locks/evidence",
        json={"owner": "other-agent", "task_id": "TASK-1", "summary": "proof"},
    )
    missing_task = client.post(
        "/api/code-operator/mcp-locks/evidence",
        json={"summary": "proof"},
    )

    assert spoofed.status_code == 422
    assert missing_task.status_code == 422


def test_mcp_file_locks_require_claimed_task() -> None:
    client = TestClient(create_gui_app())

    missing_task = client.post(
        "/api/code-operator/mcp-locks/lock-files",
        json={"files": ["README.md"]},
    )
    spoofed = client.post(
        "/api/code-operator/mcp-locks/lock-files",
        json={"files": ["README.md"], "task_id": "TASK-1", "owner": "other-agent"},
    )

    assert missing_task.status_code == 422
    assert spoofed.status_code == 422


def test_git_commit_rejects_spoofed_actor_fields() -> None:
    client = TestClient(create_gui_app())

    response = client.post(
        "/api/code-operator/git/commit-owned",
        json={
            "task_id": "TASK-1",
            "files": ["README.md"],
            "message": "test",
            "owner": "other-agent",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "path",
    [
        "/api/code-operator/teams/assign-task",
        "/api/code-operator/teams/request-review",
    ],
)
def test_provider_team_routes_reject_spoofed_actor_fields(path: str) -> None:
    client = TestClient(create_gui_app())
    payload = {
        "team_id": "dual",
        "reviewer_team_id": "deepseek-reviewers",
        "task_id": "TASK-1",
        "title": "Fix a tab",
        "summary": "Review a tab fix",
        "files": ["README.md"],
        "objective": "Make the tab real-backed.",
        "proof_ids": ["ev_test_1"],
        "owner": "other-agent",
    }

    response = client.post(path, json=payload)

    assert response.status_code == 422


def test_provider_team_readiness_uses_mocked_inputs_not_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_history, "private_env", lambda: {})
    monkeypatch.setattr(
        code_history,
        "_source_repo_status",
        lambda source: {
            "id": source.id,
            "status": "ready",
            "exists": True,
            "missing_required_files": [],
        },
    )
    monkeypatch.setattr(
        code_history,
        "_provider_status",
        lambda provider_id, _private_values: {
            "id": provider_id,
            "status": "ready",
            "api_key_configured": True,
            "base_url_configured": True,
            "model_configured": True,
            "base_url_label": "local-or-private",
            "model": f"{provider_id}-test",
        },
    )
    monkeypatch.setattr(
        code_history,
        "mcp_lock_readiness",
        lambda _private_values=None: {
            "status": "ready",
            "ready": True,
            "blocked_reason": None,
            "required_workflow": [],
        },
    )

    response = TestClient(create_gui_app()).get("/api/code-operator/teams/readiness")
    payload = response.json()

    assert response.status_code == 200
    assert payload["ready"] is True
    assert {team["id"] for team in payload["teams"]} == {"minimax-builders", "deepseek-reviewers"}
    assert all("api_key" not in str(team["provider"].get("base_url_label", "")).lower() for team in payload["teams"])


def test_provider_team_assignment_blocks_when_provider_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)
    monkeypatch.setattr(code_history, "private_env", lambda: {})
    monkeypatch.setattr(
        code_history,
        "_source_repo_status",
        lambda source: {"id": source.id, "status": "ready", "exists": True, "missing_required_files": []},
    )
    monkeypatch.setattr(
        code_history,
        "_provider_status",
        lambda provider_id, _private_values: {
            "id": provider_id,
            "status": "ready" if provider_id == "minimax" else "missing_config",
            "api_key_configured": provider_id == "minimax",
            "base_url_configured": False,
            "model_configured": provider_id == "minimax",
            "base_url_label": None,
            "model": f"{provider_id}-test" if provider_id == "minimax" else None,
        },
    )
    monkeypatch.setattr(
        code_history,
        "mcp_lock_readiness",
        lambda _private_values=None: {"status": "ready", "ready": True, "blocked_reason": None, "required_workflow": []},
    )
    monkeypatch.setattr(
        code_history,
        "append_mcp_evidence",
        lambda **kwargs: {"status": "recorded", "evidence_id": "ev_team_blocked", "kwargs": kwargs},
    )

    result = code_history.assign_provider_team_task(
        owner="hermes-agent",
        team_id="dual",
        task_id="TASK-1",
        title="Fix dashboard truth",
        files=["README.md"],
        objective="Make dashboard proof-backed.",
    )

    assert result["accepted"] is False
    assert result["status"] == "blocked"
    assert "deepseek-reviewers" in result["blocked_reasons"][0]
    assert result["mcp_evidence"]["evidence_id"] == "ev_team_blocked"


def test_provider_team_review_requires_proof_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)

    with pytest.raises(ValueError, match="proof"):
        code_history.request_provider_team_review(
            owner="hermes-agent",
            task_id="TASK-1",
            summary="Review the fix.",
            files=["README.md"],
            proof_ids=[],
        )


@pytest.mark.parametrize(
    "malicious",
    [
        "/etc/passwd",
        "//server/share/secret.py",
        "\\\\server\\share\\secret.py",
        "C:/Windows/System32/cmd.exe",
        "../escape.py",
        "file\x00name.py",
        ".env.local",
        ".npmrc",
        "03_implementation/var/code-history/snapshot.py",
        "03_implementation/proof/evidence.json",
    ],
)
def test_code_policy_rejects_escape_secret_and_generated_paths(malicious: str) -> None:
    with pytest.raises((ValueError, FileNotFoundError, OSError)):
        code_history._resolve_project_subpath(malicious, must_exist=False)


def test_write_policy_is_positive_allowlist() -> None:
    readme = code_history._resolve_project_path("README.md", write=True)
    assert readme.name == "README.md"

    site_index = Path("site/index.html")
    if (code_history.PROJECT_ROOT / site_index).exists():
        with pytest.raises(ValueError, match="limited to source"):
            code_history._resolve_project_path(site_index.as_posix(), write=True)


def test_mcp_server_path_is_hard_pinned() -> None:
    readiness = code_history.mcp_lock_readiness(
        {
            "MCP_LOCK_WORKSPACE": str(code_history.PROJECT_ROOT),
            "MCP_LOCK_SERVER": "G:/tmp/evil-server.mjs",
        }
    )

    assert readiness["server_entry"] == str(code_history.LOCK_SERVER_ENTRY.resolve())
    assert readiness["configured_server_override"] == "G:/tmp/evil-server.mjs"
    assert readiness["configured_server_override_used"] is False


def test_patch_apply_rejects_proposal_owner_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        code_history,
        "code_write_readiness",
        lambda: {"ready": True, "blocked_reasons": []},
    )
    monkeypatch.setattr(
        code_history,
        "_patch_proposal_payload",
        lambda _proposal_id: {
            "id": "a" * 32,
            "agent_id": "other-agent",
            "relative_path": "README.md",
            "proposed_text": "replacement",
            "base_sha256": "0" * 64,
            "proposed_sha256": "1" * 64,
        },
    )

    with pytest.raises(ValueError, match="owner"):
        code_history.apply_patch_proposal(
            "a" * 32,
            agent_id="hermes-agent",
            task_id="TASK-1",
        )


def test_restore_requires_same_owner_mcp_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    def deny_lock(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise ValueError("Active Hermes MCP file lock is required before restore.")

    monkeypatch.setattr(code_history, "_require_active_mcp_lock", deny_lock)

    with pytest.raises(ValueError, match="Active Hermes MCP file lock"):
        code_history.restore_snapshot(
            "README.md",
            "a" * 32,
            agent_id="hermes-agent",
            task_id="TASK-1",
        )


def test_same_owner_mcp_lock_accepts_task_id_key_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        code_history,
        "mcp_lock_state",
        lambda: {
            "state": {
                "locks": [
                    {
                        "path": "README.md",
                        "owner": "hermes-agent",
                        "taskId": "TASK-1",
                        "stale": False,
                    }
                ]
            }
        },
    )

    lock = code_history._require_active_mcp_lock("README.md", owner="hermes-agent", task_id="TASK-1")

    assert lock["taskId"] == "TASK-1"


def test_git_branch_names_are_limited_to_agent_prefixes() -> None:
    assert code_history._validate_agent_branch_name("codex/test-lane") == "codex/test-lane"
    assert code_history._validate_agent_branch_name("hermes-agent/test-lane") == "hermes-agent/test-lane"

    with pytest.raises(ValueError):
        code_history._validate_agent_branch_name("main")
    with pytest.raises(ValueError):
        code_history._validate_agent_branch_name("codex/../escape")


def test_git_stage_requires_snapshot_and_same_owner_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)
    monkeypatch.setattr(code_history, "_agent_snapshot_files", lambda owner: {"README.md"})
    monkeypatch.setattr(code_history, "_changed_git_files", lambda: {"README.md"})
    monkeypatch.setattr(code_history, "_require_active_mcp_lock", lambda path, *, owner, task_id: {"lock_id": "lock-1"})
    monkeypatch.setattr(code_history, "_run_git", lambda args, **_kwargs: calls.append(args) or {"stdout": "", "stderr": "", "returncode": 0})

    result = code_history.git_stage_owned_files(owner="hermes-agent", task_id="TASK-1", files=["README.md"])

    assert result["status"] == "staged"
    assert calls == [["add", "--", "README.md"]]


def test_git_stage_rejects_unsnapshotted_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)
    monkeypatch.setattr(code_history, "_agent_snapshot_files", lambda owner: set())
    monkeypatch.setattr(code_history, "_changed_git_files", lambda: {"README.md"})

    with pytest.raises(ValueError, match="no pre-change snapshot"):
        code_history.git_stage_owned_files(owner="hermes-agent", task_id="TASK-1", files=["README.md"])
