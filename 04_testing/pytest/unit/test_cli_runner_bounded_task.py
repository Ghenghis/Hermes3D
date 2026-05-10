"""BLK-013 bounded CLI runner task — service-level tests.

These tests exercise ``code_history.run_bounded_code_cli_task`` with
monkeypatched docker / readiness so the suite is portable to CI workers
that have no docker daemon and no OpenHands/OpenCode binary on PATH.

Test coverage (per Wave Agent B10 refined brief, 6 cases):
  1. happy path — fake CompletedProcess returns a JSON array of names;
     evidence is recorded; stdout excerpt is redacted and bounded.
  2. sandbox not ready — returns ``status="blocked"`` and never spawns docker.
  3. runner not detected — returns ``status="blocked"`` and never spawns docker.
  4. timeout reaped — ``subprocess.TimeoutExpired`` propagates as
     ``status="timeout"`` and ``exit_code=-1``.
  5. docker argv pin — every hardened-docker flag is present in argv.
  6. sandbox isolation — argv carries no ``-v G:/private``, no ``~/.aws``
     mount, and no ``OPENAI_API_KEY``-shaped env-var pass-through.
"""

from __future__ import annotations

import subprocess
from typing import Any

import pytest
from hermes3d.services import code_history


_READY_SANDBOX = {
    "status": "ready",
    "ready": True,
    "mode": "docker",
    "docker_executable": "docker",
    "docker_version": "29.4.1",
    "image_configured": True,
    "image": "ghcr.io/openhands/openhands:test",
    "image_status": "present",
    "image_id": "sha256:abc123",
    "image_size_bytes": 12345,
    "network_mode": "none",
    "workspace_mount": str(code_history.PROJECT_ROOT),
    "denied_paths": [],
    "allowed_command_families": [],
    "blocked_reasons": [],
}

_DETECTED_RUNNER = {
    "id": "openhands",
    "label": "OpenHands",
    "detected": True,
    "executable": "/fake/openhands",
    "path_source": "PATH",
    "configured_path": None,
    "source_path": None,
    "required_env_keys": ["HERMES3D_OPENHANDS_BIN", "OPENHANDS_BIN"],
    "version": "openhands 0.1",
    "version_status": "pass",
    "write_allowed": False,
    "blocked_reason": None,
    "policy": "test fixture",
}


def _patch_evidence_capture(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []

    def fake_evidence(**kwargs: Any) -> dict[str, Any]:
        captured.append(kwargs)
        return {"status": "recorded", "evidence_id": "ev_test_blk013", "result": {"ok": True}}

    monkeypatch.setattr(code_history, "append_mcp_evidence", fake_evidence)
    return captured


def _patch_ready_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_history, "_cli_runner_status", lambda runner_id: dict(_DETECTED_RUNNER, id=runner_id))
    monkeypatch.setattr(code_history, "code_sandbox_readiness", lambda: dict(_READY_SANDBOX))
    monkeypatch.setattr(code_history, "_safe_mcp_files", lambda files, must_exist: [str(f) for f in files])


def test_bounded_task_happy_path_records_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ready_runner(monkeypatch)
    captured_evidence = _patch_evidence_capture(monkeypatch)

    def fake_run(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, stdout='["foo","bar"]', stderr="warn")

    monkeypatch.setattr(code_history.subprocess, "run", fake_run)

    result = code_history.run_bounded_code_cli_task(
        runner_id="openhands",
        owner="hermes-agent",
        task_id="TASK-BLK013",
        title="Bounded scan",
        files=["README.md.py"],
    )

    assert result["status"] == "ok"
    assert result["accepted"] is True
    assert result["exit_code"] == 0
    assert result["network_mode"] == "none"
    assert result["timeout_s"] == 30
    assert result["stdout_excerpt"] == '["foo","bar"]'
    # Stderr never appears in the response body — only its sha256.
    assert "stderr" not in result
    assert "stderr_excerpt" not in result
    assert isinstance(result["stderr_sha256"], str) and len(result["stderr_sha256"]) == 64
    assert isinstance(result["stdout_sha256"], str) and len(result["stdout_sha256"]) == 64
    assert result["mcp_evidence"]["evidence_id"] == "ev_test_blk013"
    assert captured_evidence and captured_evidence[-1]["kind"] == "code_cli_runner_bounded_task"
    assert captured_evidence[-1]["data"]["status"] == "ok"


def test_bounded_task_sandbox_not_ready_blocks_without_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_history, "_cli_runner_status", lambda runner_id: dict(_DETECTED_RUNNER, id=runner_id))
    monkeypatch.setattr(
        code_history,
        "code_sandbox_readiness",
        lambda: {"ready": False, "blocked_reasons": ["docker daemon not reachable"], "image": None},
    )
    monkeypatch.setattr(code_history, "_safe_mcp_files", lambda files, must_exist: [str(f) for f in files])
    _patch_evidence_capture(monkeypatch)

    def explode(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess.run must not be called when sandbox is not ready")

    monkeypatch.setattr(code_history.subprocess, "run", explode)

    result = code_history.run_bounded_code_cli_task(
        runner_id="openhands",
        owner="hermes-agent",
        task_id="TASK-BLK013",
        title="Bounded scan",
        files=["README.md.py"],
    )

    assert result["status"] == "blocked"
    assert result["accepted"] is False
    assert "docker daemon not reachable" in result["blocked_reasons"]


def test_bounded_task_runner_not_detected_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    blocked_runner = dict(_DETECTED_RUNNER, detected=False, executable=None, blocked_reason="openhands not installed")
    monkeypatch.setattr(code_history, "_cli_runner_status", lambda runner_id: dict(blocked_runner, id=runner_id))
    monkeypatch.setattr(code_history, "code_sandbox_readiness", lambda: dict(_READY_SANDBOX))
    monkeypatch.setattr(code_history, "_safe_mcp_files", lambda files, must_exist: [str(f) for f in files])
    _patch_evidence_capture(monkeypatch)

    def explode(*_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess.run must not be called when runner is not detected")

    monkeypatch.setattr(code_history.subprocess, "run", explode)

    result = code_history.run_bounded_code_cli_task(
        runner_id="openhands",
        owner="hermes-agent",
        task_id="TASK-BLK013",
        title="Bounded scan",
        files=["README.md.py"],
    )

    assert result["status"] == "blocked"
    assert result["accepted"] is False
    assert any("openhands not installed" in reason for reason in result["blocked_reasons"])


def test_bounded_task_timeout_is_reaped(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ready_runner(monkeypatch)
    _patch_evidence_capture(monkeypatch)

    def fake_run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout", 30), output=b"", stderr=b"warn")

    monkeypatch.setattr(code_history.subprocess, "run", fake_run)

    result = code_history.run_bounded_code_cli_task(
        runner_id="openhands",
        owner="hermes-agent",
        task_id="TASK-BLK013",
        title="Bounded scan",
        files=["README.md.py"],
    )

    assert result["status"] == "timeout"
    assert result["exit_code"] == -1
    assert result["accepted"] is False
    # Stderr still never returned in body — only sha256.
    assert "stderr" not in result
    assert isinstance(result["stderr_sha256"], str) and len(result["stderr_sha256"]) == 64


def test_bounded_task_docker_argv_pins_hardened_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ready_runner(monkeypatch)
    _patch_evidence_capture(monkeypatch)
    captured_argv: list[list[str]] = []

    def capturing_run(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured_argv.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(code_history.subprocess, "run", capturing_run)

    code_history.run_bounded_code_cli_task(
        runner_id="openhands",
        owner="hermes-agent",
        task_id="TASK-BLK013",
        title="Bounded scan",
        files=["README.md.py"],
    )

    assert captured_argv, "subprocess.run was not invoked"
    argv = captured_argv[0]
    # Hardened docker flags — non-negotiable.
    assert "--network=none" in argv
    assert "--read-only" in argv
    assert "--tmpfs" in argv
    tmpfs_value = argv[argv.index("--tmpfs") + 1]
    assert tmpfs_value.startswith("/tmp:") and "noexec" in tmpfs_value and "nosuid" in tmpfs_value
    assert "--memory=512m" in argv
    assert "--cpus=1" in argv
    assert "--pids-limit=128" in argv
    assert "--cap-drop=ALL" in argv
    assert "--security-opt=no-new-privileges" in argv
    # The hardened image and bounded prompt flags reach the inner CLI.
    assert "--headless" in argv
    assert "--json" in argv
    assert "-t" in argv
    prompt_idx = argv.index("-t") + 1
    assert "JSON array of names" in argv[prompt_idx]
    assert "max 50 items" in argv[prompt_idx]


def test_bounded_task_argv_does_not_leak_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ready_runner(monkeypatch)
    _patch_evidence_capture(monkeypatch)
    captured_argv: list[list[str]] = []

    def capturing_run(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured_argv.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(code_history.subprocess, "run", capturing_run)

    code_history.run_bounded_code_cli_task(
        runner_id="openhands",
        owner="hermes-agent",
        task_id="TASK-BLK013",
        title="Bounded scan",
        files=["README.md.py"],
    )

    argv = captured_argv[0]
    joined = " ".join(argv).lower()

    # Sensitive host paths must never appear as -v mounts.
    assert "g:/private" not in joined
    assert "g:\\private" not in joined
    assert "/.aws" not in joined
    assert "${home}" not in joined
    assert " -v %userprofile" not in joined
    # Also assert no occurrence of -v with a sensitive host directory.
    for index, token in enumerate(argv):
        if token == "-v" and index + 1 < len(argv):
            mount = argv[index + 1].lower()
            assert "/private" not in mount.replace("/workspace", "")
            assert ".aws" not in mount
            assert ".ssh" not in mount

    # Provider-API env vars must NEVER appear in argv (no `-e OPENAI_API_KEY=...`,
    # no plain `OPENAI_API_KEY=...` token).
    forbidden_env = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "MINIMAX_API_KEY",
        "DEEPSEEK_API_KEY",
        "HUGGINGFACE_TOKEN",
    )
    for token in argv:
        for name in forbidden_env:
            assert name not in token, f"argv leaks env name {name}: {token}"
    # And the docker `-e` pass-through flag must be absent entirely.
    assert "-e" not in argv
