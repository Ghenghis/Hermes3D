"""Skip-path / dry-run tests for ``_run_update_checks``.

Verifies the staged update gate is **fail-closed** when:
- ``HERMES_AGENT_RUN_PYTEST`` is unset or != ``"1"``
- ``HERMES_AGENT_PYTEST_WORKERS`` is ``"0"`` or ``"1"`` in production
- ``HERMES_AGENT_PYTEST_WORKERS`` is non-numeric junk

And **succeeds** (in the sense of building a well-formed pytest invocation) when:
- ``HERMES_AGENT_RUN_PYTEST=1`` + default workers (=4)
- ``HERMES_AGENT_PYTEST_WORKERS=auto``
- ``HERMES_AGENT_PYTEST_WORKERS=0`` + ``HERMES_AGENT_DIAGNOSTIC=1``

Cross-references (Audit PR #135 / commit 5ecd8ff):
- Agent 6 must-fix #1: skip path returns ``status="fail"``, not ``"skipped"``.
- Agent 6 must-fix #2: workers<2 disables xdist isolation; production rejects.
- Agent 6 must-fix #4: ``--maxfail=1`` stays the production default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from hermes3d.api.routes import agent_updates


def _make_repo(tmp_path: Path) -> Path:
    """Build a minimal repo layout that triggers the pytest gate path."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    return tmp_path


def _stub_external_pass(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Replace ``_check_external`` so we can inspect the call without running pytest."""
    return {"name": "stub", "status": "pass", "output": ""}


def _stub_command_pass(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Replace ``_check_command`` (git status) with a deterministic pass."""
    return {"name": "git status", "status": "pass", "output": ""}


# ---------------------------------------------------------------------------
# Skip-path tests — FAIL-CLOSED behavior when HERMES_AGENT_RUN_PYTEST is unset
# ---------------------------------------------------------------------------

def test_skip_path_returns_fail_when_run_pytest_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When HERMES_AGENT_RUN_PYTEST is unset, gate must FAIL CLOSED.

    Audit PR #135 Agent 6 must-fix #1: never return status="skipped" or 200/OK
    here — that's a CICD-SEC-1 fake-pass surface.
    """
    repo = _make_repo(tmp_path)
    monkeypatch.delenv("HERMES_AGENT_RUN_PYTEST", raising=False)
    monkeypatch.delenv("HERMES_AGENT_DIAGNOSTIC", raising=False)
    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _stub_external_pass):
        checks = agent_updates._run_update_checks(repo)
    pytest_check = next((c for c in checks if c["name"] == "python pytest non-integration"), None)
    assert pytest_check is not None, "pytest gate must be present when tests/ exists"
    assert pytest_check["status"] == "fail", (
        f"Skip path must return status='fail', got {pytest_check['status']!r}. "
        "Regression of CICD-SEC-1 fake-pass guard."
    )
    assert "REQUIRES_CONFIRMATION:" in pytest_check["output"], (
        "Skip path output must contain REQUIRES_CONFIRMATION sentinel."
    )


def test_skip_path_returns_fail_when_run_pytest_is_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HERMES_AGENT_RUN_PYTEST='0' is also fail-closed."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "0")
    monkeypatch.delenv("HERMES_AGENT_DIAGNOSTIC", raising=False)
    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _stub_external_pass):
        checks = agent_updates._run_update_checks(repo)
    pytest_check = next((c for c in checks if c["name"] == "python pytest non-integration"), None)
    assert pytest_check is not None
    assert pytest_check["status"] == "fail"
    assert "REQUIRES_CONFIRMATION:" in pytest_check["output"]


def test_skipped_pytest_cannot_make_update_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """staged_update acceptance logic uses ``all(item.status == 'pass')``.

    With the skip path now returning ``status="fail"``, ``all_ok`` will be
    False and ``verified`` will be False. This test pins that contract.
    """
    repo = _make_repo(tmp_path)
    monkeypatch.delenv("HERMES_AGENT_RUN_PYTEST", raising=False)
    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _stub_external_pass):
        checks = agent_updates._run_update_checks(repo)
    all_ok = all(item.get("status") == "pass" for item in checks)
    assert all_ok is False, (
        "Skipped pytest gate must NOT make all_ok=True. "
        "verified=true acceptance is gated on every check having status='pass'."
    )


# ---------------------------------------------------------------------------
# Worker-count guards — production rejects 0/1; diagnostic mode allows
# ---------------------------------------------------------------------------

def test_workers_zero_rejected_in_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HERMES_AGENT_PYTEST_WORKERS=0 must raise HTTPException(400) in production."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "1")
    monkeypatch.setenv("HERMES_AGENT_PYTEST_WORKERS", "0")
    monkeypatch.delenv("HERMES_AGENT_DIAGNOSTIC", raising=False)
    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _stub_external_pass):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._run_update_checks(repo)
    assert exc_info.value.status_code == 400
    assert "HERMES_AGENT_DIAGNOSTIC=1" in exc_info.value.detail


def test_workers_one_rejected_in_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HERMES_AGENT_PYTEST_WORKERS=1 must also raise HTTPException(400) in production."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "1")
    monkeypatch.setenv("HERMES_AGENT_PYTEST_WORKERS", "1")
    monkeypatch.delenv("HERMES_AGENT_DIAGNOSTIC", raising=False)
    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _stub_external_pass):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._run_update_checks(repo)
    assert exc_info.value.status_code == 400


def test_workers_zero_allowed_in_diagnostic_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HERMES_AGENT_DIAGNOSTIC=1 + HERMES_AGENT_PYTEST_WORKERS=0 must NOT raise."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "1")
    monkeypatch.setenv("HERMES_AGENT_PYTEST_WORKERS", "0")
    monkeypatch.setenv("HERMES_AGENT_DIAGNOSTIC", "1")
    captured_args: list[Any] = []

    def _capture(_repo: Path, _name: str, args: list[str], **_kw: Any) -> dict[str, Any]:
        captured_args.append(args)
        return {"name": "python pytest non-integration", "status": "pass", "output": ""}

    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _capture):
        agent_updates._run_update_checks(repo)
    pytest_call = next((a for a in captured_args if "pytest" in a), None)
    assert pytest_call is not None, "pytest gate must run under diagnostic mode"
    assert "-n" in pytest_call and "0" in pytest_call


def test_workers_garbage_string_raises_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HERMES_AGENT_PYTEST_WORKERS=non-int-non-'auto' raises HTTPException(400)."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "1")
    monkeypatch.setenv("HERMES_AGENT_PYTEST_WORKERS", "not-a-number")
    monkeypatch.delenv("HERMES_AGENT_DIAGNOSTIC", raising=False)
    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _stub_external_pass):
        with pytest.raises(HTTPException) as exc_info:
            agent_updates._run_update_checks(repo)
    assert exc_info.value.status_code == 400
    assert "positive integer" in exc_info.value.detail or "auto" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Production default — workers=4, maxfail=1, path-ignores present
# ---------------------------------------------------------------------------

def test_production_default_workers_is_4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No HERMES_AGENT_PYTEST_WORKERS + HERMES_AGENT_RUN_PYTEST=1 -> -n 4."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "1")
    monkeypatch.delenv("HERMES_AGENT_PYTEST_WORKERS", raising=False)
    monkeypatch.delenv("HERMES_AGENT_DIAGNOSTIC", raising=False)
    captured_args: list[list[str]] = []

    def _capture(_repo: Path, _name: str, args: list[str], **_kw: Any) -> dict[str, Any]:
        captured_args.append(args)
        return {"name": "python pytest non-integration", "status": "pass", "output": ""}

    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _capture):
        agent_updates._run_update_checks(repo)
    pytest_call = next((a for a in captured_args if "pytest" in a), None)
    assert pytest_call is not None
    assert "-n" in pytest_call
    n_idx = pytest_call.index("-n")
    assert pytest_call[n_idx + 1] == "4", (
        f"Production default workers must be '4', got {pytest_call[n_idx + 1]!r}."
    )


def test_production_pytest_args_have_path_ignores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production pytest args mirror upstream tests.yml: --ignore on both paths."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "1")
    monkeypatch.delenv("HERMES_AGENT_DIAGNOSTIC", raising=False)
    captured_args: list[list[str]] = []

    def _capture(_repo: Path, _name: str, args: list[str], **_kw: Any) -> dict[str, Any]:
        captured_args.append(args)
        return {"name": "python pytest non-integration", "status": "pass", "output": ""}

    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _capture):
        agent_updates._run_update_checks(repo)
    pytest_call = next((a for a in captured_args if "pytest" in a), None)
    assert pytest_call is not None
    assert "--ignore=tests/integration" in pytest_call
    assert "--ignore=tests/e2e" in pytest_call
    assert "-m" in pytest_call
    assert "not integration" in pytest_call  # marker filter preserved as defense-in-depth
    assert "--maxfail=1" in pytest_call  # production default per spec point #1


def test_diagnostic_mode_uses_maxfail_5(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HERMES_AGENT_DIAGNOSTIC=1 swaps --maxfail=1 -> --maxfail=5 for triage."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "1")
    monkeypatch.setenv("HERMES_AGENT_DIAGNOSTIC", "1")
    captured_args: list[list[str]] = []

    def _capture(_repo: Path, _name: str, args: list[str], **_kw: Any) -> dict[str, Any]:
        captured_args.append(args)
        return {"name": "python pytest non-integration", "status": "pass", "output": ""}

    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _capture):
        agent_updates._run_update_checks(repo)
    pytest_call = next((a for a in captured_args if "pytest" in a), None)
    assert pytest_call is not None
    assert "--maxfail=5" in pytest_call
    assert "--maxfail=1" not in pytest_call


def test_workers_auto_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HERMES_AGENT_PYTEST_WORKERS='auto' must NOT raise (sentinel value)."""
    repo = _make_repo(tmp_path)
    monkeypatch.setenv("HERMES_AGENT_RUN_PYTEST", "1")
    monkeypatch.setenv("HERMES_AGENT_PYTEST_WORKERS", "auto")
    monkeypatch.delenv("HERMES_AGENT_DIAGNOSTIC", raising=False)
    captured_args: list[list[str]] = []

    def _capture(_repo: Path, _name: str, args: list[str], **_kw: Any) -> dict[str, Any]:
        captured_args.append(args)
        return {"name": "python pytest non-integration", "status": "pass", "output": ""}

    with patch.object(agent_updates, "_check_command", _stub_command_pass), \
         patch.object(agent_updates, "_check_external", _capture):
        agent_updates._run_update_checks(repo)
    pytest_call = next((a for a in captured_args if "pytest" in a), None)
    assert pytest_call is not None
    n_idx = pytest_call.index("-n")
    assert pytest_call[n_idx + 1] == "auto"
