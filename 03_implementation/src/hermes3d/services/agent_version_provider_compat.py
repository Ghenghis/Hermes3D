"""Per-version provider compatibility table (Wave 4 P3-5).

Read by Hermes3D callers that need to dispatch a provider call to a
specific Hermes Agent version. Source of truth for the
``HERMES_AGENT_PROVIDER_COMPAT_MATRIX_2026-05-09.md`` doc.

Sibling to :mod:`hermes3d.services.agent_version_registry`. Where that
module says *what we know about each shipped agent version*, this
module says *which provider adapters are dispatchable on each version*.
The two are decoupled by design: P2-1 froze the registry's
``HermesAgentVersion`` dataclass and the ``KNOWN_VERSIONS`` tuple, so
adding a per-version provider list as a new field would break that
contract. We add a sibling table instead.

Stability model follows Stripe's per-version-pinning convention
(https://docs.stripe.com/api/versioning) — the ``COMPAT`` tuple is
frozen at module-import time. New providers or new versions get a new
entry; existing rows are never mutated. This protects callers from a
silent upstream rename: a renamed provider would simply fall off the
matrix and surface in a unit test, not a runtime AttributeError.

Security: per OWASP A02:2021 Cryptographic Failures
(https://owasp.org/Top10/2021/A02_2021-Cryptographic_Failures/), only
env-var NAMES are recorded here — the actual key values live outside
the repo (G:\\private\\) and are sourced via the operator's env file at
process start. ``test_no_literal_token_value_in_compat`` enforces that
no row contains a literal token shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from hermes3d.services.agent_version_registry import (
    V012,
    V013,
    HermesAgentVersion,
)


@dataclass(frozen=True)
class ProviderInfo:
    """Immutable per-provider record.

    All fields are public-safe metadata. ``env_var_name`` is the name of
    the environment variable Hermes3D reads — never the value. The
    value lives outside the repo and is loaded via the operator's
    private env file.
    """

    name: str
    module_path: str
    env_var_name: str
    auth_header: str
    endpoint_url: str
    redaction_default_on: bool


# Lane A: Hermes3D-side direct probe adapters
# (lives in 03_implementation/src/hermes3d/gateways/providers/<name>.py).
# These are invariant across Hermes Agent versions because they are
# Hermes3D code, not vendored from the upstream agent. The
# ``redaction_default_on`` field reflects the **upstream** redaction
# default for the matched HermesAgentVersion — Hermes3D's own
# ``gateways.redaction.redact_text`` is always-on regardless.

_MINIMAX = ProviderInfo(
    name="minimax",
    module_path="hermes3d.gateways.providers.minimax",
    env_var_name="HERMES3D_MINIMAX_API_KEY",
    auth_header="Authorization",
    endpoint_url="https://api.minimax.io/v1/models",
    redaction_default_on=False,  # set per-version below
)

_DEEPSEEK = ProviderInfo(
    name="deepseek",
    module_path="hermes3d.gateways.providers.deepseek",
    env_var_name="HERMES3D_DEEPSEEK_API_KEY",
    auth_header="Authorization",
    endpoint_url="https://api.deepseek.com/v1/models",
    redaction_default_on=False,  # set per-version below
)


def _with_redaction(p: ProviderInfo, redaction_on: bool) -> ProviderInfo:
    """Return a copy of ``p`` with ``redaction_default_on`` set."""
    return ProviderInfo(
        name=p.name,
        module_path=p.module_path,
        env_var_name=p.env_var_name,
        auth_header=p.auth_header,
        endpoint_url=p.endpoint_url,
        redaction_default_on=redaction_on,
    )


# v0.12: upstream redaction default OFF (agent/redact.py:_REDACT_ENABLED
# = os.getenv("HERMES_REDACT_SECRETS", "")).
_V012_PROVIDERS: tuple[ProviderInfo, ...] = (
    _with_redaction(_MINIMAX, redaction_on=False),
    _with_redaction(_DEEPSEEK, redaction_on=False),
)

# v0.13: upstream redaction default ON (agent/redact.py:_REDACT_ENABLED
# = os.getenv("HERMES_REDACT_SECRETS", "true")) per upstream issue
# #17691. No new providers added; surface stability per Stripe-style
# per-version-pin model.
_V013_PROVIDERS: tuple[ProviderInfo, ...] = (
    _with_redaction(_MINIMAX, redaction_on=True),
    _with_redaction(_DEEPSEEK, redaction_on=True),
)

COMPAT: tuple[tuple[HermesAgentVersion, tuple[ProviderInfo, ...]], ...] = (
    (V012, _V012_PROVIDERS),
    (V013, _V013_PROVIDERS),
)


def providers_for(version: HermesAgentVersion) -> tuple[ProviderInfo, ...]:
    """Return the providers reachable on ``version``.

    Returns an empty tuple when ``version`` is not a registered
    ``HermesAgentVersion`` (e.g. ``active_version()`` returned ``None``
    because the operator pointed ``HERMES_AGENT_CHECKOUT`` at a custom
    fork).
    """
    for v, ps in COMPAT:
        if v == version:
            return ps
    return ()


__all__ = ["ProviderInfo", "COMPAT", "providers_for"]
