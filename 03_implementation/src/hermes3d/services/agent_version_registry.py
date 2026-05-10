"""Read-only registry of known Hermes Agent versions (Wave 2 P2-1).

Pairs with :mod:`hermes3d.services.agent_checkout`. Where ``agent_checkout``
answers *which path is active right now*, this registry answers *what we
know about each version we've shipped* (upstream tag, bundled venv,
feature flags) so downstream code (compat matrix, proof-event tagging,
rollback UI) can branch on capabilities without re-deriving them.

Pattern is the standard ``@dataclass(frozen=True)`` immutable-record
recipe (https://docs.python.org/3/library/dataclasses.html#frozen-instances)
mirrored against Django's ``AppConfig`` registry (a tuple of class-level
metadata records exposed via ``get_app_configs``,
https://docs.djangoproject.com/en/5.1/ref/applications/#methods).

Persistence note: feature flags are static booleans per shipped version.
Conditionally-available features (e.g. only present when an extra is
installed) are out of scope here; if such a feature appears, add a
follow-up ``next_fix_attempt`` entry in the Wave 2 plan rather than
mutating these frozen records.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hermes3d.services.agent_checkout import (
    DEFAULT_AGENT_CHECKOUT,
    V012_FALLBACK_CHECKOUT,
    hermes_agent_checkout,
)


@dataclass(frozen=True)
class HermesAgentVersion:
    """Immutable metadata for one shipped Hermes Agent version."""

    label: str
    upstream_tag: str
    checkout_path: Path
    venv_python: Path | None
    redaction_default_on: bool
    has_kanban: bool
    has_heartbeat_reclaim: bool
    has_zombie_detection: bool
    has_pluggable_providers_dir: bool


V012 = HermesAgentVersion(
    label="v0.12",
    upstream_tag="v2026.4.30",
    checkout_path=V012_FALLBACK_CHECKOUT,
    venv_python=None,
    redaction_default_on=False,
    has_kanban=False,
    has_heartbeat_reclaim=False,
    has_zombie_detection=False,
    has_pluggable_providers_dir=False,
)

V013 = HermesAgentVersion(
    label="v0.13",
    upstream_tag="v2026.5.7",
    checkout_path=DEFAULT_AGENT_CHECKOUT,
    venv_python=None,
    redaction_default_on=True,
    has_kanban=True,
    has_heartbeat_reclaim=True,
    has_zombie_detection=True,
    has_pluggable_providers_dir=True,
)

KNOWN_VERSIONS: tuple[HermesAgentVersion, ...] = (V012, V013)


def active_version() -> HermesAgentVersion | None:
    """Return the registry entry whose ``checkout_path`` matches the
    currently-resolved Hermes Agent checkout, or ``None`` if the operator
    has pointed ``HERMES_AGENT_CHECKOUT`` at a path we don't recognize
    (e.g. a custom fork or a forensic clone).
    """
    active = hermes_agent_checkout().resolve(strict=False)
    for v in KNOWN_VERSIONS:
        if v.checkout_path.resolve(strict=False) == active:
            return v
    return None


__all__ = ["HermesAgentVersion", "V012", "V013", "KNOWN_VERSIONS", "active_version"]
