"""Hermes Agent canary env-switch resolver tests (Wave A4 + A5 combined).

Wave A5 hazard: ``DEFAULT_CHECKOUT`` at ``agent_updates.py:25`` was
captured at module-import time, so a ``HERMES_AGENT_CHECKOUT`` env flip
mid-process did NOT propagate without process restart.

Wave A4 hazard: 3 sister sites (``module_runtime.py``, ``code_history.py``,
``db/load_modules.py``) hard-coded the production path as a string
literal, ignoring the env entirely.

Combined fix:
- New shared resolver ``hermes_agent_checkout()`` reads env per-call.
- ``agent_updates._repo_path()`` now calls the resolver instead of
  returning the module-level constant — supports mid-process flip.
- Three sister sites import the resolver and call it at module-import
  (their data structures are module-level tuples/dicts; they accept
  the import-time semantics, but at least honor the env when set
  before process start).

References:
- 12-Factor App config rule III: https://12factor.net/config
- Wave A4 finding (canary adapter brief)
- Wave A5 finding (rollback verifier)
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

from hermes3d.services import agent_checkout as ac


# Post Wave 1 promotion (2026-05-09): v0.13 is the default; v0.12 is
# the opt-in fallback path.
V012_FALLBACK = "G:/Github/hermes-agent-fresh"
V013_DEFAULT = "G:/Github/hermes-agent-v013-canary"
# Aliases for tests authored before promotion.
PROD = V013_DEFAULT
CANARY = V013_DEFAULT


# ---------------------------------------------------------------------------
# Resolver direct tests
# ---------------------------------------------------------------------------


def test_default_is_v013_post_promotion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Post Wave 1 promotion: with env unset, resolver returns v0.13.

    Wave 1 (2026-05-09) cleared 6/7 hard gates: live MiniMax + DeepSeek
    probes both ``accepted=true``; canary runtime smoke 8/8 imports +
    10 MCP tools; production-untouched re-verify; per-call env resolver
    mid-process flip 4/4; zero secret leak. BLK-013 tracked separately.
    """
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    assert ac.hermes_agent_checkout() == Path(V013_DEFAULT)


def test_v012_fallback_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operators can revert to v0.12 mid-process by setting the env."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)
    assert ac.hermes_agent_checkout() == Path(V012_FALLBACK)


def test_resolver_constants_are_correct() -> None:
    """Post-promotion: DEFAULT and CANARY both point to v0.13;
    V012_FALLBACK is the explicit v0.12 path."""
    assert ac.DEFAULT_AGENT_CHECKOUT == Path(V013_DEFAULT)
    assert ac.CANARY_AGENT_CHECKOUT == Path(V013_DEFAULT)
    assert ac.V012_FALLBACK_CHECKOUT == Path(V012_FALLBACK)


# ---------------------------------------------------------------------------
# Wave A5 critical hazard pin: per-call env read (not module-import freeze)
# ---------------------------------------------------------------------------


def test_a5_per_call_env_flip_within_same_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wave A5 critical: flip env between calls; resolver MUST read live env.

    Post-promotion: default = v0.13. Operator flips to v0.12 fallback
    via the env var, then unsets to return to v0.13 default. Per-call
    read makes mid-process rollback work without process restart.
    """
    # Start at default (v0.13)
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    assert ac.hermes_agent_checkout() == Path(V013_DEFAULT)

    # Flip to v0.12 fallback
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)
    assert ac.hermes_agent_checkout() == Path(V012_FALLBACK), (
        "Wave A5 regression: env flip mid-process did NOT propagate; "
        "resolver may be caching at import time again."
    )

    # Flip back to default (unset = v0.13)
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT")
    assert ac.hermes_agent_checkout() == Path(V013_DEFAULT), (
        "Wave A5 regression: rollback to default v0.13 failed mid-process."
    )


def test_resolver_is_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin: hermes_agent_checkout MUST NOT be wrapped in lru_cache."""
    assert not hasattr(ac.hermes_agent_checkout, "cache_info"), (
        "Wave A5 regression: hermes_agent_checkout is wrapped in @lru_cache; "
        "would re-introduce the import-time-freeze hazard."
    )


# ---------------------------------------------------------------------------
# Wave A4 critical: agent_updates._repo_path uses the resolver per-call
# ---------------------------------------------------------------------------


def test_a4_agent_updates_repo_path_per_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """agent_updates._repo_path must reflect current env, not the
    module-level DEFAULT_CHECKOUT constant captured at import.

    Post-promotion: default unset = v0.13; explicit env = v0.12 fallback.
    """
    from hermes3d.api.routes import agent_updates

    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    assert agent_updates._repo_path() == Path(V013_DEFAULT)

    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", V012_FALLBACK)
    assert agent_updates._repo_path() == Path(V012_FALLBACK), (
        "Wave A4/A5 regression: _repo_path no longer reads env per-call."
    )

    monkeypatch.delenv("HERMES_AGENT_CHECKOUT")
    assert agent_updates._repo_path() == Path(V013_DEFAULT)


def test_agent_updates_imports_resolver() -> None:
    """Source-level pin: agent_updates must import hermes_agent_checkout."""
    import inspect

    from hermes3d.api.routes import agent_updates

    src = inspect.getsource(agent_updates)
    assert "from hermes3d.services.agent_checkout import hermes_agent_checkout" in src, (
        "Wave A4/A5 regression: agent_updates no longer imports the resolver."
    )


# ---------------------------------------------------------------------------
# Wave A4: 3 sister sites import the resolver
# ---------------------------------------------------------------------------


def test_module_runtime_imports_resolver() -> None:
    """module_runtime.py must import the resolver (Wave A4 sister site #1)."""
    import inspect

    from hermes3d.services import module_runtime

    src = inspect.getsource(module_runtime)
    assert "_hermes_agent_checkout_at_import" in src, (
        "Wave A4 regression: module_runtime no longer uses the resolver."
    )


def test_code_history_imports_resolver() -> None:
    """code_history.py must import the resolver (Wave A4 sister site #2)."""
    import inspect

    from hermes3d.services import code_history

    src = inspect.getsource(code_history)
    assert "hermes_agent_checkout" in src, (
        "Wave A4 regression: code_history no longer uses the resolver."
    )


def test_load_modules_imports_resolver() -> None:
    """db/load_modules.py must import the resolver (Wave A4 sister site #3)."""
    import inspect

    from hermes3d.db import load_modules

    src = inspect.getsource(load_modules)
    assert "_hermes_agent_checkout_at_import" in src, (
        "Wave A4 regression: load_modules no longer uses the resolver."
    )


# ---------------------------------------------------------------------------
# Production safety: default behavior preserved
# ---------------------------------------------------------------------------


def test_v013_default_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-promotion: env unset resolves to v0.13 production default.

    Operators wanting v0.12 must explicitly set
    ``HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh``.
    """
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    from hermes3d.api.routes import agent_updates

    # Test the live route helper.
    assert str(agent_updates._repo_path()) == str(Path(V013_DEFAULT))
    # Test the resolver directly.
    assert str(ac.hermes_agent_checkout()) == str(Path(V013_DEFAULT))


# ---------------------------------------------------------------------------
# F4 pin (P1-8 post-promotion hardening, 2026-05-09)
# ---------------------------------------------------------------------------


def test_agent_updates_default_checkout_aligned_to_resolver() -> None:
    """F4 pin: post-promotion ``DEFAULT_CHECKOUT`` in ``agent_updates``
    equals ``DEFAULT_AGENT_CHECKOUT`` from the resolver module.

    Pre-fix the alias was a stale literal pointing at the v0.12 fallback
    path. Post-fix the alias is the resolver's canonical default so any
    back-compat consumer gets the post-promotion path.
    """
    from hermes3d.api.routes.agent_updates import DEFAULT_CHECKOUT as au_default

    assert au_default == ac.DEFAULT_AGENT_CHECKOUT
    assert au_default == Path(V013_DEFAULT)
