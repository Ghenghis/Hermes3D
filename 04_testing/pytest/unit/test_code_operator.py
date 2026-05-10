"""Hermes Agent code-operator hardening tests."""

from __future__ import annotations

import subprocess
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
    assert "/api/code-operator/teams/run-coding-pass" in paths
    assert "/api/code-operator/teams/run-review-pass" in paths
    assert "/api/code-operator/patch/apply" in paths
    assert "/api/code-operator/patch/apply-reviewed" in paths
    assert "/api/code-operator/gates/run" in paths
    assert "/api/code-operator/git/branch" in paths
    assert "/api/code-operator/git/commit-owned" in paths
    assert "/api/code-operator/git/push" in paths
    assert "/api/code-operator/git/pr" in paths
    assert "/api/code-operator/history/restore" in paths
    assert "/api/code-operator/mcp-locks/evidence" in paths
    assert "/api/code-operator/e2e/jobs" in paths


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
        "/api/code-operator/teams/run-coding-pass",
        "/api/code-operator/teams/run-review-pass",
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


def test_provider_coding_pass_records_artifact_without_mutating(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)
    monkeypatch.setattr(
        code_history,
        "provider_team_readiness",
        lambda: {
            "ready": True,
            "status": "ready",
            "teams": [
                {"id": "minimax-builders", "ready": True, "blocked_reasons": []},
                {"id": "deepseek-reviewers", "ready": True, "blocked_reasons": []},
            ],
        },
    )
    monkeypatch.setattr(
        code_history,
        "_provider_file_context",
        lambda files: [{"path": "README.md", "exists": True, "sha256": "0" * 64, "size_bytes": 10, "truncated": False, "content": "# readme"}],
    )
    monkeypatch.setattr(
        code_history,
        "_call_provider_chat",
        lambda provider_id, messages, **kwargs: {
            "provider": {"id": provider_id, "model": "minimax-test", "base_url_label": "api.example", "http_status": 200},
            "content": '{"plan":["do work"]}',
            "content_sha256": "a" * 64,
            "raw_usage": {},
        },
    )
    monkeypatch.setattr(
        code_history,
        "_record_provider_run_artifact",
        lambda **kwargs: {"id": "run-1", "path": "03_implementation/var/code-history/provider-runs/run-1.json", "proof_event_id": "proof-1", "response_sha256": "a" * 64},
    )
    monkeypatch.setattr(code_history, "append_mcp_evidence", lambda **kwargs: {"status": "recorded", "evidence_id": "ev_coding"})

    result = code_history.run_provider_team_coding_pass(
        owner="hermes-agent",
        team_id="minimax-builders",
        task_id="TASK-1",
        title="Plan a fix",
        files=["README.md"],
        objective="Plan a README fix.",
    )

    assert result["accepted"] is True
    assert result["status"] == "coding_plan_recorded"
    assert result["artifact"]["id"] == "run-1"
    assert result["response"]["content_sha256"] == "a" * 64


def test_provider_review_pass_requires_deepseek_team(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_history, "_require_mcp_locks_ready", lambda: None)

    with pytest.raises(ValueError, match="Review execution requires"):
        code_history.run_provider_team_review_pass(
            owner="hermes-agent",
            task_id="TASK-1",
            summary="Review",
            files=["README.md"],
            proof_ids=["ev_1"],
            reviewer_team_id="minimax-builders",
        )


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


def test_provider_status_requires_live_smoke_proof(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(code_history, "PROVIDER_SMOKE_STATUS_FILE", tmp_path / "provider-smoke-status.json")

    status = code_history._provider_status(
        "minimax",
        {
            "HERMES3D_MINIMAX_API_KEY": "configured-but-unproven",
            "HERMES3D_MINIMAX_MODEL": "minimax-test",
        },
    )

    assert status["status"] == "smoke_required"
    assert status["live_status"] == "not_probed"
    assert "smoke proof" in status["blocked_reason"]


def test_provider_status_accepts_private_env_aliases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(code_history, "PROVIDER_SMOKE_STATUS_FILE", tmp_path / "provider-smoke-status.json")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    status = code_history._provider_status(
        "minimax",
        {
            "MINIMAX_API_KEY": "configured-through-user-env",
            "MINIMAX_BASE_URL": "https://api.minimax.io/v1",
            "MINIMAX_MODEL": "MiniMax-M2.7-highspeed",
        },
    )

    assert status["api_key_configured"] is True
    assert status["api_key_source"] == "private_env:MINIMAX_API_KEY"
    assert status["base_url_source"] == "private_env:MINIMAX_BASE_URL"
    assert status["model_source"] == "private_env:MINIMAX_MODEL"
    assert status["accepted_api_key_env"] == [
        "HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY",
        "MINIMAX_TOKEN_PLAN_API_KEY",
        "HERMES3D_MINIMAX_HIGHSPEED_API_KEY",
        "MINIMAX_HIGHSPEED_API_KEY",
        "HERMES3D_MINIMAX_API_KEY",
        "OPENAI_API_KEY",
        "MINIMAX_API_KEY",
    ]


def test_minimax_chat_payload_uses_current_openai_compatible_fields() -> None:
    payload = code_history._provider_chat_payload(
        "minimax",
        config={"model": "MiniMax-M2.7-highspeed"},
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.0,
        max_tokens=128,
    )

    assert payload["temperature"] == 0.01
    assert payload["max_completion_tokens"] == 256
    assert "max_tokens" not in payload


def test_minimax_provider_accepts_openai_token_plan_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "token-plan-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.minimax.io/v1")

    config = code_history._provider_chat_config("minimax", {}, require_ready=False)

    assert config["api_key_source"] == "environment:OPENAI_API_KEY"
    assert config["base_url_source"] == "environment:OPENAI_BASE_URL"
    assert config["accepted_api_key_env"] == [
        "HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY",
        "MINIMAX_TOKEN_PLAN_API_KEY",
        "HERMES3D_MINIMAX_HIGHSPEED_API_KEY",
        "MINIMAX_HIGHSPEED_API_KEY",
        "HERMES3D_MINIMAX_API_KEY",
        "OPENAI_API_KEY",
        "MINIMAX_API_KEY",
    ]
    assert config["model"] == "MiniMax-M2.7-highspeed"


def test_minimax_provider_prefers_explicit_token_plan_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIMAX_TOKEN_PLAN_API_KEY", "token-plan-key")
    monkeypatch.setenv("OPENAI_API_KEY", "generic-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.minimax.io/v1")

    config = code_history._provider_chat_config("minimax", {}, require_ready=False)

    assert config["api_key_source"] == "environment:MINIMAX_TOKEN_PLAN_API_KEY"
    assert config["base_url_source"] == "environment:OPENAI_BASE_URL"
    assert config["model"] == "MiniMax-M2.7-highspeed"


def test_deepseek_v4_pro_is_current_default_model() -> None:
    config = code_history._provider_chat_config("deepseek", {"DEEPSEEK_API_KEY": "configured"}, require_ready=False)

    assert config["model"] == "deepseek-v4-pro"


def test_deepseek_v4_pro_payload_uses_official_reasoning_fields() -> None:
    payload = code_history._provider_chat_payload(
        "deepseek",
        config={"model": "deepseek-v4-pro"},
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.0,
        max_tokens=128,
    )

    assert payload["model"] == "deepseek-v4-pro"
    assert payload["max_tokens"] == 256
    assert payload["thinking"] == {"type": "enabled"}
    assert payload["reasoning_effort"] == "high"


def test_cli_provider_env_contract_redacts_task_scoped_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "MINIMAX_TOKEN_PLAN_API_KEY",
        "DEEPSEEK_API_KEY",
    ]:
        monkeypatch.delenv(name, raising=False)

    contract = code_history._cli_provider_env_contract(
        {
            "HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY": "secret-minimax-token-plan",
            "OPENAI_BASE_URL": "https://api.minimax.io/v1",
            "MINIMAX_MODEL": "MiniMax-M2.7-highspeed",
            "DEEPSEEK_API_KEY": "secret-deepseek-key",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
            "DEEPSEEK_MODEL": "deepseek-v4-pro",
        }
    )

    assert contract["ready"] is True
    assert "OPENAI_API_KEY" in contract["exported_env_names"]
    assert "DEEPSEEK_API_KEY" in contract["exported_env_names"]
    assert "secret-minimax-token-plan" not in str(contract)
    assert "secret-deepseek-key" not in str(contract)
    assert all(item["value"] == "<redacted>" for profile in contract["profiles"] for item in profile["exports"])
    minimax = next(profile for profile in contract["profiles"] if profile["provider_id"] == "minimax")
    assert minimax["api_key_source"] == "private_env:HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY"


def test_provider_status_blocks_after_failed_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(code_history, "PROVIDER_SMOKE_STATUS_FILE", tmp_path / "provider-smoke-status.json")
    auth_contract = {
        "provider_id": "minimax",
        "base_url_label": "api.minimax.io",
        "chat_path": "/v1/chat/completions",
        "auth_scheme": "Authorization: Bearer <redacted>",
        "api_key_configured": True,
        "model": "minimax-test",
        "model_configured": True,
    }
    code_history._write_provider_smoke_status(
        "minimax",
        accepted=False,
        status="blocked",
        blocked_reasons=["Provider minimax returned HTTP 401: login fail"],
        auth_contract=auth_contract,
        evidence={"evidence_id": "ev_failed_smoke"},
    )

    status = code_history._provider_status(
        "minimax",
        {
            "HERMES3D_MINIMAX_API_KEY": "configured-but-rejected",
            "HERMES3D_MINIMAX_MODEL": "minimax-test",
        },
    )

    assert status["status"] == "auth_failed"
    assert status["live_status"] == "failed"
    assert status["last_smoke"]["evidence_id"] == "ev_failed_smoke"
    assert "401" in status["blocked_reason"]


def test_sandbox_readiness_inspects_configured_image(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        code_history,
        "private_env",
        lambda: {
            "HERMES3D_AGENT_SANDBOX_IMAGE": "ghcr.io/openhands/openhands:latest",
            "HERMES3D_AGENT_SANDBOX_NETWORK": "none",
        },
    )
    monkeypatch.setattr(code_history.shutil, "which", lambda _name: "docker")

    def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[1] == "version":
            return subprocess.CompletedProcess(args, 0, stdout="29.4.1\n", stderr="")
        if args[1:3] == ["image", "inspect"]:
            return subprocess.CompletedProcess(args, 0, stdout="sha256:abc123 123456\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(code_history.subprocess, "run", fake_run)

    status = code_history.code_sandbox_readiness()

    assert status["ready"] is True
    assert status["image_status"] == "present"
    assert status["image_id"] == "sha256:abc123"
    assert status["image_size_bytes"] == 123456


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


def test_list_e2e_jobs_returns_proof_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /e2e/jobs returns proof_events filtered to code_e2e/patch/git event types."""
    import json as _json

    fake_records = [
        {
            "id": "ev_e2e_1",
            "event_type": "code_e2e",
            "source_agent": "hermes-agent",
            "payload": _json.dumps({"task_id": "TASK-1", "title": "Wire gate", "files": ["README.md"], "next_status": "needs_reviewed_patch_proposal"}),
            "created_at": "2026-05-08T22:00:00",
        },
        {
            "id": "ev_patch_1",
            "event_type": "code_patch.applied",
            "source_agent": "hermes-agent",
            "payload": _json.dumps({"task_id": "TASK-1", "relative_path": "README.md"}),
            "created_at": "2026-05-08T22:01:00",
        },
    ]
    monkeypatch.setattr(code_history, "rows", lambda sql, params=(): fake_records)

    result = code_history.list_e2e_jobs(limit=50)

    assert result["status"] == "ready"
    assert result["count"] == 2
    assert result["unique_task_ids"] == 1
    assert result["jobs"][0]["task_id"] == "TASK-1"
    assert result["jobs"][0]["status"] == "needs_reviewed_patch_proposal"
    assert "needs_reviewed_patch_proposal" in result["state_legend"]


def test_list_e2e_jobs_route_returns_200() -> None:
    """GET /api/code-operator/e2e/jobs route is registered and returns 200."""
    import json as _json

    app = create_gui_app()
    client = TestClient(app)

    response = client.get("/api/code-operator/e2e/jobs?limit=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert "jobs" in payload
    assert "state_legend" in payload
# ---------------------------------------------------------------------------
# Recovery Controller v1 tests (lean ledger; no UI, no autonomous apply).
# Each test uses a unique task_id so ledger entries don't collide. Tests
# verify ledger writes, validation, redaction, outcome marking, and state
# read-back. Future v1.5 fields covered: failed_step_type, failure_fingerprint,
# retry_budget, agent_stack, worker_output_status, recommended_next_action.
# ---------------------------------------------------------------------------


from uuid import uuid4 as _recovery_uuid4


def _recovery_task_id(suffix: str) -> str:
    return f"H3D-TEST-RECOVERY-{_recovery_uuid4().hex[:12]}-{suffix}"


def test_recovery_records_gate_fail() -> None:
    client = TestClient(create_gui_app())
    task_id = _recovery_task_id("gate")

    response = client.post(
        "/api/code-operator/recovery/record-failure",
        json={
            "task_id": task_id,
            "failed_step": "git-diff-check",
            "failure_class": "gate_fail",
            "failure_summary": "trailing whitespace flagged on added line",
            "failed_step_type": "gate_run",
            "agent_stack": ["MiniMax", "DeepSeek", "Gate Runner"],
            "recommended_next_action": "rollback_and_retry",
            "worker_output_status": "complete",
            "attempt_n": 1,
            "max_attempts": 3,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "recorded"
    attempt_id = payload["attempt_id"]
    assert len(attempt_id) == 32
    assert all(c in "0123456789abcdef" for c in attempt_id)
    record = payload["record"]
    assert record["failure_class"] == "gate_fail"
    assert record["failed_step_type"] == "gate_run"
    assert record["agent_stack"] == ["MiniMax", "DeepSeek", "Gate Runner"]
    assert record["retry_budget"] == {"attempt_n": 1, "max_attempts": 3, "exhausted": False}
    assert len(record["failure_fingerprint"]) == 16


def test_recovery_records_patch_rejected() -> None:
    client = TestClient(create_gui_app())
    task_id = _recovery_task_id("patch")

    response = client.post(
        "/api/code-operator/recovery/record-failure",
        json={
            "task_id": task_id,
            "failed_step": "deepseek_review_v1",
            "failure_class": "patch_rejected",
            "failure_summary": "reviewer requested in-band evidence",
            "failed_step_type": "reviewer_pass",
            "recommended_next_action": "refresh_context",
            "worker_output_status": "complete",
        },
    )

    assert response.status_code == 200
    record = response.json()["record"]
    assert record["failure_class"] == "patch_rejected"
    assert record["failed_step_type"] == "reviewer_pass"
    assert record["recommended_next_action"] == "refresh_context"


def test_recovery_records_merge_git_fail() -> None:
    client = TestClient(create_gui_app())
    task_id = _recovery_task_id("merge")

    response = client.post(
        "/api/code-operator/recovery/record-failure",
        json={
            "task_id": task_id,
            "failed_step": "git_branch",
            "failure_class": "merge_git_fail",
            "failure_summary": "untracked files blocked branch creation",
            "failed_step_type": "git_branch",
            "recommended_next_action": "rollback_and_retry",
        },
    )

    assert response.status_code == 200
    record = response.json()["record"]
    assert record["failure_class"] == "merge_git_fail"
    assert record["failed_step_type"] == "git_branch"


def test_recovery_rejects_unknown_failure_class() -> None:
    client = TestClient(create_gui_app())
    task_id = _recovery_task_id("unknown")

    response = client.post(
        "/api/code-operator/recovery/record-failure",
        json={
            "task_id": task_id,
            "failed_step": "something",
            "failure_class": "not_a_real_class",
            "failure_summary": "this should reject",
        },
    )

    assert response.status_code == 422


def test_recovery_redacts_secret_like_values() -> None:
    client = TestClient(create_gui_app())
    task_id = _recovery_task_id("secret")
    bearer_value = "Bearer abcdefghijklmnop1234567890ABCDEFGH"

    response = client.post(
        "/api/code-operator/recovery/record-failure",
        json={
            "task_id": task_id,
            "failed_step": "auth_check",
            "failure_class": "provider_auth",
            "failure_summary": f"upstream returned {bearer_value} mismatch",
            "failed_step_type": "provider_smoke",
            "redaction_status": "pass",
        },
    )

    assert response.status_code == 200
    summary = response.json()["record"]["failure_summary"]
    assert bearer_value not in summary
    assert "abcdefghijklmnop1234567890" not in summary


def test_recovery_mark_outcome_recovered() -> None:
    client = TestClient(create_gui_app())
    task_id = _recovery_task_id("outcome")

    record_resp = client.post(
        "/api/code-operator/recovery/record-failure",
        json={
            "task_id": task_id,
            "failed_step": "git-diff-check",
            "failure_class": "gate_fail",
            "failure_summary": "initial gate failure",
            "failed_step_type": "gate_run",
            "recommended_next_action": "rollback_and_retry",
        },
    )
    assert record_resp.status_code == 200
    attempt_id = record_resp.json()["attempt_id"]

    outcome_resp = client.post(
        "/api/code-operator/recovery/mark-outcome",
        json={
            "attempt_id": attempt_id,
            "status": "recovered",
            "recovery_summary": "rollback + re-author + re-gate succeeded",
            "retry_gate_id": "gate_git-diff-check_demo",
        },
    )
    assert outcome_resp.status_code == 200
    payload = outcome_resp.json()
    assert payload["status"] == "recorded"
    outcome = payload["outcome"]
    assert outcome["status"] == "recovered"
    assert outcome["attempt_id"] == attempt_id


def test_recovery_state_route_returns_attempts() -> None:
    client = TestClient(create_gui_app())
    task_id = _recovery_task_id("state")

    record_resp = client.post(
        "/api/code-operator/recovery/record-failure",
        json={
            "task_id": task_id,
            "failed_step": "state_route_test",
            "failure_class": "missing_proof",
            "failure_summary": "for state route test",
            "failed_step_type": "reviewer_pass",
        },
    )
    assert record_resp.status_code == 200
    attempt_id = record_resp.json()["attempt_id"]

    state_resp = client.get(
        f"/api/code-operator/recovery/state?task_id={task_id}",
    )
    assert state_resp.status_code == 200
    payload = state_resp.json()
    assert "attempts" in payload
    assert payload["count"] >= 1
    assert any(item.get("attempt_id") == attempt_id for item in payload["attempts"])


# W8-7 unit pin (2026-05-09): pins the workspace-equivalence helper that
# fixes the worktree mismatch reported by W7-3's truth-check. The helper
# accepts:
#   1. Identical resolved paths (canonical workspace -- existing behaviour)
#   2. Two paths that share the same git-common-dir (linked worktrees of
#      the same repo) -- the new behaviour added in this PR.
# It must NOT accept arbitrary directories, the parent of the workspace,
# or unrelated git repos. See ``code_history._workspace_paths_equivalent``.
def test_workspace_check_accepts_worktrees(tmp_path: Path) -> None:
    helper = code_history._workspace_paths_equivalent

    # Identical paths -> True (the historical canonical case).
    assert helper(str(tmp_path), tmp_path) is True

    # Set up two linked worktrees of the same repo.
    main_repo = tmp_path / "main"
    main_repo.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(main_repo)],
        check=True,
        capture_output=True,
    )
    # git requires user.email/name + a commit before worktree-add.
    subprocess.run(
        ["git", "-C", str(main_repo), "config", "user.email", "w87@test.local"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(main_repo), "config", "user.name", "w87"],
        check=True,
        capture_output=True,
    )
    (main_repo / "README").write_text("seed\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(main_repo), "add", "README"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(main_repo), "commit", "-q", "-m", "seed"],
        check=True,
        capture_output=True,
    )
    linked = tmp_path / "linked"
    subprocess.run(
        ["git", "-C", str(main_repo), "worktree", "add", "-q", "-b", "branch-w87", str(linked)],
        check=True,
        capture_output=True,
    )

    # Two linked worktrees of the same repo -> True (the W8-7 fix).
    assert helper(str(main_repo), linked) is True
    assert helper(str(linked), main_repo) is True

    # An unrelated directory (no git repo) -> False.
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    assert helper(str(unrelated), main_repo) is False

    # An unrelated repo -> False (different git-common-dir).
    other_repo = tmp_path / "other"
    other_repo.mkdir()
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(other_repo)],
        check=True,
        capture_output=True,
    )
    assert helper(str(other_repo), main_repo) is False
