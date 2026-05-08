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
    assert "/api/code-operator/patch/apply" in paths
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
