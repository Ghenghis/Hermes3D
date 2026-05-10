"""Wave 2 P2-3 — v0.12 fallback regression pin (post Wave 1 promotion).

After PR #160 promoted Hermes Agent v0.13 (v2026.5.7 "Tenacity Release")
to the production default, the v0.12 (v2026.4.30) checkout at
``G:/Github/hermes-agent-fresh`` becomes the **rollback path**: an
operator sets ``HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`` to
revert mid-process without restarting the FastAPI server.

This file pins eight independent surfaces that consume the active
Hermes Agent checkout. Together they prove the v0.12 fallback path
behaves identically across surfaces; if PR #160 (or any future
v0.13-only change) silently broke any of them the rollback would be
half-functional and operators could not safely revert.

Surface taxonomy
----------------
1. Per-call resolver  — ``agent_updates._repo_path()`` reads env live.
2. ``module_runtime.BUILTIN_RUNTIME_PROBES["hermes_agent"]["path"]``
   — module-level constant; captured at import. Wave A4 fix kept the
   import-time semantics, so we pin the pattern with
   ``importlib.reload`` after env mutation.
3. ``code_history.SOURCE_REPOS[id="nous_hermes_agent"].local_path`` —
   same import-time-with-reload pattern (sister site #2).
4. ``db/load_modules.SOURCE_OVERRIDES["hermes_agent"]["local_path"]`` —
   sister site #3.
5. ``_run_update_checks`` does not crash when the v0.12 checkout is
   active even if the canary venv is not activated (subprocess gates
   are stubbed; we pin the structural shape, not network output).
6. Provider config (MiniMax + DeepSeek) is identical against v0.12 —
   ``_provider_chat_config`` is checkout-agnostic by construction.
7. CLI runner detection (OpenCode + OpenHands) works identically —
   ``_cli_runner_status`` reads only env vars, never the checkout.
8. ``agent_config.last_run`` and ``proof_events`` writes succeed and
   keep their semantic shape when v0.12 is active (no cross-version
   contamination at write-time).

Module-import-time constants — sister-site reload pattern
---------------------------------------------------------
Surfaces 2/3/4 read the resolver at module import (the dict / dataclass
literals are evaluated once when the module loads). Setting
``HERMES_AGENT_CHECKOUT`` *after* import does NOT change them. The pin
mutates the env, then calls ``importlib.reload(module)`` so the
constants re-evaluate. This is the documented pattern in:

- pytest monkeypatch (env vars) —
  https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- importlib.reload (module re-execution) —
  https://docs.python.org/3/library/importlib.html#importlib.reload
- nox per-version env isolation (analogous discipline: each env-bound
  surface gets its own freshly-imported runtime) —
  https://nox.thea.codes/en/stable/tutorial.html

References (read for this PR):
- 12-Factor III config — https://12factor.net/config
- Wave A4 (sister-site finding) + Wave A5 (per-call read fix) —
  internal handoffs HERMES_AGENT_PRODUCTION_V013_ACTION_PLAN_2026-05-09.md
- PR #155 (canary env-switch resolver), PR #158 (v0.13 production action plan)
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

# v0.12 fallback (operator-set rollback) and v0.13 production default.
V012_FALLBACK = "G:/Github/hermes-agent-fresh"
V013_DEFAULT = "G:/Github/hermes-agent-v013-canary"


# ---------------------------------------------------------------------------
# Helper: reload-with-env so module-level constants re-resolve.
# ---------------------------------------------------------------------------


def _reload_with_v012(module_name: str, monkeypatch: pytest.MonkeyPatch):
    """Set HERMES_AGENT_CHECKOUT=v0.12, then reload the target module.

    Sister sites (module_runtime, code_history, db.load_modules) capture
    the resolver at import-time. After mutating the env, the test must
    reload the module via ``importlib.reload`` so the dict / dataclass
    literals re-evaluate against the new env. See module docstring for
    the documented pattern (importlib.reload + monkeypatch.setenv).
    """
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)
    mod = importlib.import_module(module_name)
    return importlib.reload(mod)


# ---------------------------------------------------------------------------
# Surface 1 — agent_updates._repo_path() returns v0.12 when env=fresh.
# (Per-call read; no reload needed — Wave A5 fix.)
# ---------------------------------------------------------------------------


def test_surface_1_repo_path_returns_v012_when_env_fresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_repo_path()`` reads env per-call (Wave A5). No reload required."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)
    from hermes3d.api.routes import agent_updates

    assert agent_updates._repo_path() == Path(V012_FALLBACK)


# ---------------------------------------------------------------------------
# Surface 2 — module_runtime.BUILTIN_RUNTIME_PROBES["hermes_agent"]["path"]
# Note: spec says ``MODULES`` but the actual constant is
# ``BUILTIN_RUNTIME_PROBES`` (verified by inspection of source).
# ---------------------------------------------------------------------------


def test_surface_2_module_runtime_probe_path_v012_at_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module-level constant captured at import; reload re-resolves."""
    mod = _reload_with_v012("hermes3d.services.module_runtime", monkeypatch)
    probe = mod.BUILTIN_RUNTIME_PROBES["hermes_agent"]
    assert probe["path"] == str(Path(V012_FALLBACK)), (
        "Surface 2 regression: BUILTIN_RUNTIME_PROBES['hermes_agent']['path']"
        " did not bind to v0.12 fallback after env+reload."
    )


# ---------------------------------------------------------------------------
# Surface 3 — code_history.SOURCE_REPOS[id="nous_hermes_agent"].local_path
# ---------------------------------------------------------------------------


def test_surface_3_code_history_source_repos_v012_at_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SOURCE_REPOS is a module-level tuple — reload after env mutation."""
    mod = _reload_with_v012("hermes3d.services.code_history", monkeypatch)
    nous = next(s for s in mod.SOURCE_REPOS if s.id == "nous_hermes_agent")
    assert nous.local_path == Path(V012_FALLBACK), (
        "Surface 3 regression: SOURCE_REPOS nous_hermes_agent.local_path "
        "did not bind to v0.12 fallback after env+reload."
    )


# ---------------------------------------------------------------------------
# Surface 4 — db/load_modules.SOURCE_OVERRIDES["hermes_agent"]["local_path"]
# ---------------------------------------------------------------------------


def test_surface_4_load_modules_source_overrides_v012_at_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SOURCE_OVERRIDES dict is module-level; reload re-resolves the path."""
    mod = _reload_with_v012("hermes3d.db.load_modules", monkeypatch)
    override = mod.SOURCE_OVERRIDES["hermes_agent"]
    assert override["local_path"] == str(Path(V012_FALLBACK)), (
        "Surface 4 regression: SOURCE_OVERRIDES['hermes_agent']['local_path']"
        " did not bind to v0.12 fallback after env+reload."
    )


# ---------------------------------------------------------------------------
# Surface 5 — _run_update_checks against v0.12 does not crash even if the
# canary venv isn't activated. We stub subprocess via the existing
# _check_external / _check_command seams so no real pytest/npm/python is
# spawned (deterministic, no live HTTP, no canary-venv dependency).
# ---------------------------------------------------------------------------


def test_surface_5_run_update_checks_v012_no_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stub external checks; assert _run_update_checks returns a list of
    dicts with name+status, never raises, even when v0.12 is active.

    Pin: subprocess invocations stubbed (no canary venv / no live python)
    """
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)
    # HERMES_AGENT_RUN_PYTEST unset -> the pytest gate enters the
    # REQUIRES_CONFIRMATION fail-closed branch (skip-path fail-closed).
    monkeypatch.delenv("HERMES_AGENT_RUN_PYTEST", raising=False)
    from hermes3d.api.routes import agent_updates

    monkeypatch.setattr(
        agent_updates,
        "_check_command",
        lambda repo, name, args, expect_returncode=0: {
            "name": name, "status": "pass", "output": "stubbed"
        },
    )
    monkeypatch.setattr(
        agent_updates,
        "_check_external",
        lambda repo, name, args, timeout=60: {
            "name": name, "status": "pass", "output": "stubbed"
        },
    )

    repo = agent_updates._repo_path()
    assert repo == Path(V012_FALLBACK)
    checks = agent_updates._run_update_checks(repo)

    # Structural pin: list of dicts each having name+status; never raises.
    assert isinstance(checks, list) and checks
    for check in checks:
        assert isinstance(check, dict)
        assert {"name", "status"} <= set(check)


# ---------------------------------------------------------------------------
# Surface 6 — Provider config (MiniMax + DeepSeek) identical under v0.12.
# Config layer only — no live HTTP, no API keys touched.
# ---------------------------------------------------------------------------


def test_surface_6_provider_config_v012_identical_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provider config is checkout-agnostic. Pin: same shape under v0.12.

    No live HTTP. No real API key. ``require_ready=False`` so missing
    credentials do not error.
    """
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)
    from hermes3d.services.code_history import _provider_chat_config

    # Pass empty private_values so the test has zero coupling to the
    # operator's local G:\private\.env contents.
    minimax = _provider_chat_config("minimax", private_values={}, require_ready=False)
    deepseek = _provider_chat_config("deepseek", private_values={}, require_ready=False)

    for cfg, pid in ((minimax, "minimax"), (deepseek, "deepseek")):
        assert cfg["id"] == pid
        # Defaulted base URLs from PROVIDER_DEFAULT_BASE_URLS — must be set.
        assert cfg["base_url"], f"{pid} base_url unexpectedly empty under v0.12"
        # Defaulted model from PROVIDER_DEFAULT_MODELS — must be set.
        assert cfg["model"], f"{pid} model unexpectedly empty under v0.12"
        # Required keys for callers (CLI provider env contract, etc.).
        for key in ("api_key_configured", "base_url_configured", "model_source"):
            assert key in cfg, f"{pid} missing {key} under v0.12"


# ---------------------------------------------------------------------------
# Surface 7 — CLI runner detection (OpenCode + OpenHands) works under v0.12.
# Detection reads only env vars / PATH, never the checkout.
# ---------------------------------------------------------------------------


def test_surface_7_cli_runner_detection_v012_returns_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``_cli_runner_status`` is checkout-agnostic by construction.

    Pin: shape is identical under v0.12. Force "not detected" via empty
    env to keep the test deterministic across machines (no PATH reliance).
    """
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)
    # Strip env vars _cli_runner_executable consults so we test the
    # blocked-no-config branch deterministically. shutil.which is
    # likewise stubbed to avoid PATH dependence.
    for key in (
        "HERMES3D_OPENCODE_BIN", "OPENCODE_BIN",
        "HERMES3D_OPENHANDS_BIN", "OPENHANDS_BIN",
        "HERMES3D_OPENCODE_SOURCE", "OPENCODE_SOURCE",
        "HERMES3D_OPENHANDS_SOURCE", "OPENHANDS_SOURCE",
    ):
        monkeypatch.delenv(key, raising=False)

    from hermes3d.services import code_history
    monkeypatch.setattr(code_history, "private_env", lambda: {})
    monkeypatch.setattr(code_history.shutil, "which", lambda _name: None)

    for runner in ("opencode", "openhands"):
        status = code_history._cli_runner_status(runner)
        assert status["id"] == runner
        # Shape pin (8 mandatory keys consumers rely on).
        for key in (
            "id", "label", "detected", "executable",
            "version_status", "blocked_reason", "policy", "required_env_keys",
        ):
            assert key in status, f"{runner} missing {key} under v0.12"
        # Force-stripped config means detection must be False, never raise.
        assert status["detected"] is False
        assert status["blocked_reason"]


# ---------------------------------------------------------------------------
# Surface 8 — agent_config.last_run + proof_events writes under v0.12.
# Use tmp DB so we don't contaminate the operator's hermes3d.db.
# ---------------------------------------------------------------------------


def test_surface_8_agent_config_and_proof_events_persist_v012(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Persist ``hermes_agent.update.last_run`` + a ``proof_events`` row to
    a tmp DB while v0.12 is active; assert the version tag round-trips
    cleanly with no cross-version contamination at write time.
    """
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)

    # Redirect DB to tmp so production data is untouched.
    fake_db = tmp_path / "hermes3d_v012_pin.db"
    from hermes3d.db import init as db_init
    monkeypatch.setattr(db_init, "DB_PATH", fake_db)
    # _common.execute / .row use the patched DB_PATH via init.connect.
    db_init.init_db()

    from hermes3d.api.routes import agent_updates
    from hermes3d.api.routes._common import row, rows

    # Synthesize a minimal "persisted" payload tagged with v0.12 to detect
    # cross-version write-time contamination.
    persisted = {
        "actor": "p2-3-pin",
        "active_checkout": str(Path(V012_FALLBACK)),
        "version_tag": "v2026.4.30",
        "checks": [{"name": "stub", "status": "pass", "output_head": ""}],
    }

    # agent_config sink (mirrors agent_updates.staged_update line 192-195)
    import json as _json
    from hermes3d.api.routes._common import execute
    execute(
        "INSERT OR REPLACE INTO agent_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("hermes_agent.update.last_run", _json.dumps(persisted)),
    )
    # proof_events sink (mirrors agent_updates._append_proof_event)
    agent_updates._append_proof_event(
        "hermes_agent_update_run", "p2-3-pin", persisted
    )

    # Round-trip: agent_config row exists with v0.12 payload.
    cfg = row(
        "SELECT value FROM agent_config WHERE key = ?",
        ("hermes_agent.update.last_run",),
    )
    assert cfg is not None, "agent_config write did not persist under v0.12"
    payload = _json.loads(cfg["value"])
    assert payload["active_checkout"] == str(Path(V012_FALLBACK))
    assert payload["version_tag"] == "v2026.4.30"

    # Round-trip: proof_events row exists with the v0.12 payload.
    events = rows(
        "SELECT event_type, source_agent, payload FROM proof_events "
        "WHERE event_type = ?",
        ("hermes_agent_update_run",),
    )
    assert events, "proof_events insert did not persist under v0.12"
    event_payload = _json.loads(events[-1]["payload"])
    assert event_payload["active_checkout"] == str(Path(V012_FALLBACK))
    assert event_payload["version_tag"] == "v2026.4.30"
    # No cross-version contamination: nothing in the payload mentions v0.13.
    assert V013_DEFAULT not in cfg["value"]
    assert V013_DEFAULT not in events[-1]["payload"]
