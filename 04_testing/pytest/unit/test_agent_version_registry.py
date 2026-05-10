"""Wave 2 P2-1 — multi-version Hermes Agent registry tests.

Pins:
- ``KNOWN_VERSIONS`` always contains v0.12 + v0.13 with the upstream
  tags Wave 1 promoted (v2026.4.30 / v2026.5.7).
- ``redaction_default_on`` matches upstream PR #21193 (verified by
  Wave A3): v0.12=False, v0.13=True.
- ``active_version()`` keys off ``hermes_agent_checkout()`` so the
  per-call env-flip semantics from PR #155 / Wave A5 propagate.
- Frozen dataclasses cannot leak state between calls (no shared
  mutable defaults, ``__setattr__`` raises).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from hermes3d.services import agent_version_registry as avr
from hermes3d.services.agent_checkout import (
    DEFAULT_AGENT_CHECKOUT,
    V012_FALLBACK_CHECKOUT,
)


def test_registry_lists_v012_and_v013_in_order() -> None:
    labels = [v.label for v in avr.KNOWN_VERSIONS]
    assert labels == ["v0.12", "v0.13"], "fallback then production default"


def test_v012_upstream_tag_is_v2026_4_30() -> None:
    assert avr.V012.upstream_tag == "v2026.4.30"
    assert avr.V012.checkout_path == V012_FALLBACK_CHECKOUT


def test_v013_upstream_tag_is_v2026_5_7() -> None:
    assert avr.V013.upstream_tag == "v2026.5.7"
    assert avr.V013.checkout_path == DEFAULT_AGENT_CHECKOUT


def test_v013_redaction_default_on_per_upstream_pr_21193() -> None:
    """Wave A3 verified: NousResearch/hermes-agent#21193 made
    redaction default-ON in v0.13. Pin so a future copy-paste from v0.12
    cannot silently flip this back to False."""
    assert avr.V013.redaction_default_on is True


def test_v012_redaction_default_off_per_wave2_swarm() -> None:
    """Wave 2 prior swarm Agent 2 confirmed v0.12 ships with redaction
    OFF. Pin so a future bump cannot silently mis-tag history."""
    assert avr.V012.redaction_default_on is False


def test_v013_kanban_heartbeat_zombie_providers_all_true() -> None:
    assert avr.V013.has_kanban is True
    assert avr.V013.has_heartbeat_reclaim is True
    assert avr.V013.has_zombie_detection is True
    assert avr.V013.has_pluggable_providers_dir is True


def test_v012_does_not_advertise_v013_only_features() -> None:
    assert avr.V012.has_kanban is False
    assert avr.V012.has_heartbeat_reclaim is False
    assert avr.V012.has_zombie_detection is False
    assert avr.V012.has_pluggable_providers_dir is False


def test_active_version_v013_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post PR #160 default: env unset resolves to v0.13."""
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    active = avr.active_version()
    assert active is not None and active.label == "v0.13"


def test_active_version_v012_when_env_points_to_fresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", str(V012_FALLBACK_CHECKOUT))
    active = avr.active_version()
    assert active is not None and active.label == "v0.12"


def test_active_version_none_for_unknown_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Operator pointed env at a custom checkout we don't know about."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", str(tmp_path / "custom-fork"))
    assert avr.active_version() is None


def test_each_entry_is_frozen_no_cross_version_leak() -> None:
    """Frozen dataclass: ``__setattr__`` raises, so two callers cannot
    accidentally observe each other's mutations of v0.12 or v0.13."""
    with pytest.raises(FrozenInstanceError):
        avr.V012.has_kanban = True  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        avr.V013.redaction_default_on = False  # type: ignore[misc]


def test_known_versions_is_a_tuple_not_a_list() -> None:
    """Tuple => structural immutability; reads-by-iteration cannot
    mutate the registry."""
    assert isinstance(avr.KNOWN_VERSIONS, tuple)


def test_venv_python_is_path_or_none() -> None:
    """venv_python is a filesystem ref or None — never a string,
    never a credential."""
    for v in avr.KNOWN_VERSIONS:
        assert v.venv_python is None or isinstance(v.venv_python, Path)
