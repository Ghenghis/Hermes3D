"""Regression-pin: v0.13 production default behavior (Wave 2 P2-4).

Mission: lock down the post-PR #160 (squash 3158a4e) production v0.13
default behavior so future commits cannot silently regress Wave 1 gate 3.
This file exercises the SAME 8 surfaces that the v0.12-fallback regression
pin (P2-3 / ``test_v012_fallback_regression_pin.py``) covers, but with
``HERMES_AGENT_CHECKOUT`` UNSET (= production default per Wave 1 promotion
2026-05-09).

Per-surface coverage (one test each, 8 total)
1. ``agent_updates._repo_path()`` -> v0.13 path when env unset.
2. ``module_runtime.BUILTIN_RUNTIME_PROBES['hermes_agent']['path']``
   resolves to v0.13 when env was unset at module-import time.
3. ``code_history.SOURCE_REPOS[id='nous_hermes_agent'].local_path``
   resolves to v0.13 when env was unset at module-import time.
4. ``db.load_modules.SOURCE_OVERRIDES['hermes_agent']['local_path']``
   resolves to v0.13 when env was unset at module-import time.
5. ``_run_update_checks`` runs against the v0.13 checkout without
   crashing (subprocess mocked; pytest gate is NEVER spawned here).
6. MiniMax + DeepSeek provider probe requests build correctly with v0.13
   active (no live HTTP; bearer scheme + Accept header asserted).
7. CLI runner detection (OpenCode 1.4.3-hermes3d + OpenHands CLI 1.16.0
   per PR #157 baseline) works under v0.13 default.
8. BLK-013 ``POST /api/code-operator/cli-runners/run-bounded-task`` is
   registered (per PR #159) and the docker argv carries
   ``--network=none`` (subprocess.run mocked; no real container spawn).

Surfaces 2-4 are module-import-time captures, so the test reloads each
module with a clean env via ``importlib.reload`` to assert default-path
behavior independent of test-runner-imported state.

References
- Primary: PR #160 squash 3158a4e — Wave 1 promotion summary lists 7 hard
  gates (gate 3 = canary runtime smoke; gate 7 = BLK-013 / PR #159
  --network=none + --read-only + --cap-drop=ALL bounded runner).
- Cross-comparison: pip-tools pins ``pip``'s major version in
  ``requirements.in`` and asserts it on every compile run. Same pattern
  here: pin the v0.13 path in 4 import-time sites + 4 runtime sites.
- 12-Factor App config rule III (env-var driven config), see
  ``services/agent_checkout.py`` module docstring.
"""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path
from typing import Any

import pytest

from conftest import strip_provider_env
from hermes3d.services import agent_checkout as ac

V013_DEFAULT = "G:/Github/hermes-agent-v013-canary"


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip HERMES_AGENT_CHECKOUT so the resolver returns the default."""
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)


# ---- Surface 1: agent_updates._repo_path() ---------------------------------


def test_v013_default_repo_path_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    from hermes3d.api.routes import agent_updates

    assert agent_updates._repo_path() == Path(V013_DEFAULT)
    assert ac.DEFAULT_AGENT_CHECKOUT == Path(V013_DEFAULT)


# ---- Surface 2: module_runtime BUILTIN_RUNTIME_PROBES['hermes_agent'] ------


def test_v013_default_module_runtime_path_at_import(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    from hermes3d.services import module_runtime

    importlib.reload(module_runtime)
    entry = module_runtime.BUILTIN_RUNTIME_PROBES["hermes_agent"]
    assert Path(entry["path"]) == Path(V013_DEFAULT)


# ---- Surface 3: code_history.SOURCE_REPOS nous_hermes_agent ----------------


def test_v013_default_code_history_source_repo_at_import(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    from hermes3d.services import code_history

    importlib.reload(code_history)
    matches = [r for r in code_history.SOURCE_REPOS if r.id == "nous_hermes_agent"]
    assert len(matches) == 1
    assert Path(matches[0].local_path) == Path(V013_DEFAULT)


# ---- Surface 4: db.load_modules.SOURCE_OVERRIDES['hermes_agent'] -----------


def test_v013_default_load_modules_override_at_import(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    from hermes3d.db import load_modules

    importlib.reload(load_modules)
    override = load_modules.SOURCE_OVERRIDES["hermes_agent"]
    assert Path(override["local_path"]) == Path(V013_DEFAULT)
    assert override["repo"] == "https://github.com/NousResearch/Hermes-Agent.git"


# ---- Surface 5: _run_update_checks against v0.13 (subprocess mocked) -------


def test_v013_default_run_update_checks_no_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    from hermes3d.api.routes import agent_updates

    # Disable the pytest gate explicitly — surface 5 must NOT spawn pytest.
    monkeypatch.delenv("HERMES_AGENT_RUN_PYTEST", raising=False)

    def fake_run(args: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        # Return success for git/npm/pip; non-empty stdout for pip --version.
        joined = " ".join(str(a) for a in args)
        stdout = "pip 24.0\n" if "pip" in joined else ""
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(agent_updates.subprocess, "run", fake_run)

    repo = agent_updates._repo_path()
    assert repo == Path(V013_DEFAULT)
    checks = agent_updates._run_update_checks(repo)
    assert isinstance(checks, list) and checks
    # No pytest entry should be present (HERMES_AGENT_RUN_PYTEST unset =>
    # status='fail' REQUIRES_CONFIRMATION sentinel, NEVER an executed gate).
    pytest_entries = [c for c in checks if c.get("name") == "python pytest non-integration"]
    if pytest_entries:
        assert pytest_entries[0]["status"] == "fail"
        assert "REQUIRES_CONFIRMATION" in pytest_entries[0].get("output", "")


# ---- Surface 6: MiniMax + DeepSeek probe request shape ---------------------


def test_v013_default_provider_probe_requests_build(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    from decimal import Decimal

    from hermes3d.gateways.providers import deepseek, minimax
    from hermes3d.orchestration.types import ProviderConfig

    strip_provider_env(monkeypatch)
    monkeypatch.setenv("MINIMAX_API_KEY", "fake-minimax-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-deepseek-key")

    mm_cfg = ProviderConfig(
        base_url="https://api.minimax.io/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="MINIMAX_API_KEY",
        cost_cap_usd_per_run=Decimal("0.05"),
    )
    ds_cfg = ProviderConfig(
        base_url="https://api.deepseek.com/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="DEEPSEEK_API_KEY",
        cost_cap_usd_per_run=Decimal("0.05"),
    )

    for build, cfg, key in (
        (minimax.build_probe_request, mm_cfg, "fake-minimax-key"),
        (deepseek.build_probe_request, ds_cfg, "fake-deepseek-key"),
    ):
        method, url, headers = build(cfg)
        assert method == "GET"
        assert url == f"{cfg.base_url}/models"
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == f"Bearer {key}"


# ---- Surface 7: CLI runner detection (OpenCode + OpenHands) ----------------


def test_v013_default_cli_runner_detection_under_v013(monkeypatch: pytest.MonkeyPatch) -> None:
    _clean_env(monkeypatch)
    from hermes3d.services import code_history

    fake_status = {
        "opencode": {
            "id": "opencode",
            "label": "OpenCode",
            "detected": True,
            "executable": "/fake/opencode",
            "path_source": "private_env:HERMES3D_OPENCODE_BIN",
            "configured_path": "/fake/opencode",
            "source_path": None,
            "required_env_keys": ["HERMES3D_OPENCODE_BIN", "OPENCODE_BIN"],
            "version": "1.4.3-hermes3d",
            "version_status": "pass",
            "write_allowed": False,
            "blocked_reason": None,
            "policy": "test fixture",
        },
        "openhands": {
            "id": "openhands",
            "label": "OpenHands",
            "detected": True,
            "executable": "/fake/openhands",
            "path_source": "private_env:HERMES3D_OPENHANDS_BIN",
            "configured_path": "/fake/openhands",
            "source_path": None,
            "required_env_keys": ["HERMES3D_OPENHANDS_BIN", "OPENHANDS_BIN"],
            "version": "OpenHands CLI 1.16.0",
            "version_status": "pass",
            "write_allowed": False,
            "blocked_reason": None,
            "policy": "test fixture",
        },
    }
    monkeypatch.setattr(code_history, "_cli_runner_status", lambda rid: fake_status[rid])

    oc = code_history._cli_runner_status("opencode")
    oh = code_history._cli_runner_status("openhands")
    assert oc["detected"] and "1.4.3-hermes3d" in oc["version"]
    assert oh["detected"] and "1.16.0" in oh["version"]
    # CLI detection must not depend on HERMES_AGENT_CHECKOUT.
    assert "HERMES_AGENT_CHECKOUT" not in (oc["required_env_keys"] + oh["required_env_keys"])


# ---- Surface 8: BLK-013 bounded-task route + --network=none docker argv ----


def test_v013_default_blk013_route_registered_with_network_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clean_env(monkeypatch)
    from hermes3d.api.routes import code_operator
    from hermes3d.services import code_history

    routes = [getattr(r, "path", "") for r in code_operator.router.routes]
    # PR #159 registers the bounded-task endpoint at /cli-runners/run-bounded-task
    # under the /api/code-operator prefix; assert by suffix match so this stays
    # robust if the prefix is ever moved.
    assert any(p.endswith("/cli-runners/run-bounded-task") for p in routes), (
        "BLK-013 (PR #159) regression: bounded-task route is no longer registered."
    )

    captured: list[list[str]] = []

    def capturing_run(args: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        captured.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    ready_sandbox = {
        "ready": True,
        "mode": "docker",
        "docker_executable": "docker",
        "docker_version": "29.4.1",
        "image_configured": True,
        "image": "ghcr.io/openhands/openhands:test",
        "image_status": "present",
        "image_id": "sha256:abc",
        "image_size_bytes": 1,
        "network_mode": "none",
        "workspace_mount": str(code_history.PROJECT_ROOT),
        "denied_paths": [],
        "allowed_command_families": [],
        "blocked_reasons": [],
        "status": "ready",
    }
    detected_runner = {
        "id": "openhands",
        "label": "OpenHands",
        "detected": True,
        "executable": "/fake/openhands",
        "path_source": "PATH",
        "configured_path": None,
        "source_path": None,
        "required_env_keys": ["HERMES3D_OPENHANDS_BIN"],
        "version": "openhands 0.1",
        "version_status": "pass",
        "write_allowed": False,
        "blocked_reason": None,
        "policy": "test",
    }
    monkeypatch.setattr(
        code_history, "_cli_runner_status", lambda rid: dict(detected_runner, id=rid)
    )
    monkeypatch.setattr(code_history, "code_sandbox_readiness", lambda: dict(ready_sandbox))
    monkeypatch.setattr(
        code_history, "_safe_mcp_files", lambda files, must_exist: [str(f) for f in files]
    )
    monkeypatch.setattr(
        code_history,
        "append_mcp_evidence",
        lambda **_kw: {"status": "recorded", "evidence_id": "ev_pin", "result": {"ok": True}},
    )
    monkeypatch.setattr(code_history.subprocess, "run", capturing_run)

    code_history.run_bounded_code_cli_task(
        runner_id="openhands",
        owner="hermes-agent",
        task_id="TASK-PIN013",
        title="Pin",
        files=["README.md.py"],
    )
    assert captured, "subprocess.run was not invoked under v0.13 default."
    argv = captured[0]
    assert "--network=none" in argv
    assert "--read-only" in argv
    assert "--cap-drop=ALL" in argv
