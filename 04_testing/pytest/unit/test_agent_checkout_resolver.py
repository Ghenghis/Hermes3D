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


PROD = "G:/Github/hermes-agent-fresh"
CANARY = "G:/Github/hermes-agent-v013-canary"


# ---------------------------------------------------------------------------
# Resolver direct tests
# ---------------------------------------------------------------------------


def test_default_is_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """With env unset, resolver returns the production v0.12 path."""
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    assert ac.hermes_agent_checkout() == Path(PROD)


def test_canary_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting HERMES_AGENT_CHECKOUT flips to the canary path."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", CANARY)
    assert ac.hermes_agent_checkout() == Path(CANARY)


def test_resolver_constants_are_correct() -> None:
    """The two named constants are the canonical production + canary paths."""
    assert ac.DEFAULT_AGENT_CHECKOUT == Path(PROD)
    assert ac.CANARY_AGENT_CHECKOUT == Path(CANARY)


# ---------------------------------------------------------------------------
# Wave A5 critical hazard pin: per-call env read (not module-import freeze)
# ---------------------------------------------------------------------------


def test_a5_per_call_env_flip_within_same_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wave A5 critical: flip env between calls; resolver MUST read live env.

    Pre-fix the resolver would have captured the value at import. This
    test calls hermes_agent_checkout() multiple times across env flips
    in the same process and asserts each call reflects the current env.
    """
    # Start production
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    assert ac.hermes_agent_checkout() == Path(PROD)

    # Flip to canary
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", CANARY)
    assert ac.hermes_agent_checkout() == Path(CANARY), (
        "Wave A5 regression: env flip mid-process did NOT propagate; "
        "resolver may be caching at import time again."
    )

    # Flip back to production
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT")
    assert ac.hermes_agent_checkout() == Path(PROD), (
        "Wave A5 regression: rollback to production failed mid-process."
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
    module-level DEFAULT_CHECKOUT constant captured at import."""
    from hermes3d.api.routes import agent_updates

    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    assert agent_updates._repo_path() == Path(PROD)

    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", CANARY)
    assert agent_updates._repo_path() == Path(CANARY), (
        "Wave A4/A5 regression: _repo_path no longer reads env per-call."
    )

    monkeypatch.delenv("HERMES_AGENT_CHECKOUT")
    assert agent_updates._repo_path() == Path(PROD)


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


def test_production_path_unchanged_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The production v0.12 path must be the byte-identical default.

    Operators relying on the existing path see zero behavior change.
    """
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    from hermes3d.api.routes import agent_updates

    # Test the live route helper.
    assert str(agent_updates._repo_path()) == str(Path(PROD))
    # Test the resolver directly.
    assert str(ac.hermes_agent_checkout()) == str(Path(PROD))
