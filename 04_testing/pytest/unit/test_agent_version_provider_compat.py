"""Wave 4 P3-5 — provider compatibility matrix tests.

Pins the cross-version reachability of Hermes3D-side direct-probe
providers (Lane A in
``HERMES_AGENT_PROVIDER_COMPAT_MATRIX_2026-05-09.md``).

Pinned invariants:
- v0.12 has at least the v0.12 providers documented in the doc
  (minimax, deepseek).
- v0.13 has at least every provider v0.12 has, plus any new ones (none
  on this v0.12->v0.13 hop — surface stable).
- Every ``ProviderInfo.env_var_name`` is a public env-var NAME, never a
  literal token value (OWASP A02:2021 enforcement).
- Naming: env vars start with ``HERMES3D_`` for the canonical project
  convention; documented exceptions live below.
- ``providers_for(V012) != providers_for(V013)`` because the redaction
  default flips between the two even when the provider list itself is
  stable (per upstream issue #21193).
- Module paths under ``providers_for`` resolve to importable Python
  paths whose module file exists on disk under
  ``03_implementation/src/`` (FS check; no actual ``import`` to keep
  tests venv-agnostic).
"""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from hermes3d.services import agent_version_provider_compat as avpc
from hermes3d.services.agent_version_registry import V012, V013

# Module-relative path to the Hermes3D source tree (used by the FS-only
# import path check). This file lives at
# 04_testing/pytest/unit/test_agent_version_provider_compat.py
# so the source tree is two levels up + 03_implementation/src/.
_SRC_ROOT = Path(__file__).resolve().parents[3] / "03_implementation" / "src"


def _expected_v012_provider_names() -> set[str]:
    """Documented v0.12 provider names per the compat-matrix doc, §1."""
    return {"minimax", "deepseek"}


def _expected_v013_provider_names() -> set[str]:
    """Documented v0.13 provider names per the compat-matrix doc, §1.

    On the v0.12 -> v0.13 hop, no providers were added or removed.
    Surface stability per Stripe-style per-version-pin model.
    """
    return {"minimax", "deepseek"}


def test_v012_includes_documented_providers() -> None:
    """v0.12 row of the compat matrix lists at least the providers
    documented in the doc. Catches accidental row deletion."""
    names = {p.name for p in avpc.providers_for(V012)}
    expected = _expected_v012_provider_names()
    assert expected <= names, f"v0.12 missing providers: {expected - names}"


def test_v013_is_a_superset_of_v012() -> None:
    """v0.13 must contain every provider v0.12 has (no breaking
    removals across upstream major version)."""
    v012_names = {p.name for p in avpc.providers_for(V012)}
    v013_names = {p.name for p in avpc.providers_for(V013)}
    missing = v012_names - v013_names
    assert not missing, f"v0.13 dropped v0.12 providers: {missing}"


def test_v013_includes_documented_providers() -> None:
    """v0.13 row of the compat matrix lists at least the providers
    documented in the doc."""
    names = {p.name for p in avpc.providers_for(V013)}
    expected = _expected_v013_provider_names()
    assert expected <= names, f"v0.13 missing providers: {expected - names}"


def test_every_env_var_name_starts_with_hermes3d_prefix() -> None:
    """OWASP A02:2021: env-var NAMES are public; the value lives at
    G:\\private\\ outside the repo. Project naming convention requires
    ``HERMES3D_`` prefix on canonical names so operators can grep for
    project-owned env vars without false positives.

    Documented exceptions: none currently. Add the exception list here
    if a provider truly needs an unprefixed name (e.g.
    upstream-mandated naming). Each row is fail-open by ``startswith``.
    """
    documented_exceptions: set[str] = set()
    for record_version, providers in avpc.COMPAT:
        for p in providers:
            if p.env_var_name in documented_exceptions:
                continue
            assert p.env_var_name.startswith("HERMES3D_"), (
                f"{record_version.label}/{p.name}: env_var_name "
                f"{p.env_var_name!r} does not start with 'HERMES3D_' and "
                f"is not in the documented exception list. Either rename "
                f"the env var or add the exception with a justifying "
                f"comment in the test."
            )


def test_no_literal_token_value_in_compat() -> None:
    """OWASP A02:2021: no row may contain a literal token value.

    This regex catches the common provider-token shapes (Anthropic
    ``sk-ant-...``, OpenAI ``sk-...``, JWT ``eyJ...``, generic long
    base64 blobs >40 chars). If a maintainer accidentally pastes a key
    into the source, the test trips.
    """
    token_shapes = re.compile(
        r"sk-ant-[A-Za-z0-9_-]{16,}"
        r"|sk-[A-Za-z0-9]{20,}"
        r"|eyJ[A-Za-z0-9_-]+\.eyJ"
        r"|[A-Za-z0-9+/]{40,}={0,2}"
    )
    for _, providers in avpc.COMPAT:
        for p in providers:
            for field_name in (
                "name",
                "module_path",
                "env_var_name",
                "auth_header",
                "endpoint_url",
            ):
                value = getattr(p, field_name)
                assert not token_shapes.search(value), (
                    f"Field {field_name}={value!r} on provider {p.name} "
                    f"matches a token-shape regex. Suspected secret leak "
                    f"in source."
                )


def test_providers_for_v012_differs_from_v013() -> None:
    """Even when the provider name set is stable, the rows must still
    diverge across versions because v0.13 flipped the upstream redaction
    default ON (issue #21193). If they ever became byte-identical, the
    upstream redaction-default change would be silently lost.
    """
    v012 = avpc.providers_for(V012)
    v013 = avpc.providers_for(V013)
    assert v012 != v013, (
        "v0.12 and v0.13 provider rows are byte-identical — the "
        "upstream redaction-default flip (False -> True) is not being "
        "carried in the compat matrix."
    )


def test_v012_all_providers_redaction_default_off() -> None:
    """Pin: v0.12 ships with upstream redaction OFF
    (agent/redact.py:_REDACT_ENABLED defaults to ``""`` on v0.12).
    Catches a copy-paste flip back ON for v0.12.
    """
    for p in avpc.providers_for(V012):
        assert p.redaction_default_on is False, (
            f"v0.12/{p.name}: redaction_default_on must be False "
            f"(upstream agent/redact.py default is OFF on v0.12)."
        )


def test_v013_all_providers_redaction_default_on() -> None:
    """Pin: v0.13 ships with upstream redaction ON per upstream issue
    #21193. Catches a copy-paste flip back OFF for v0.13.
    """
    for p in avpc.providers_for(V013):
        assert p.redaction_default_on is True, (
            f"v0.13/{p.name}: redaction_default_on must be True "
            f"(upstream issue #21193 made redaction default-ON)."
        )


def test_module_paths_resolve_to_files_on_disk() -> None:
    """FS-only check that every ``ProviderInfo.module_path`` resolves
    to a real .py file under ``03_implementation/src/``. Does NOT
    actually ``import`` (tests must be venv-agnostic; the upstream
    Hermes Agent venv may not be on ``sys.path`` during this test
    run).
    """
    for _, providers in avpc.COMPAT:
        for p in providers:
            # "hermes3d.gateways.providers.minimax" -> "hermes3d/gateways/providers/minimax.py"
            relative = Path(*p.module_path.split(".")).with_suffix(".py")
            full = _SRC_ROOT / relative
            assert full.exists(), (
                f"module_path {p.module_path!r} for provider {p.name} "
                f"does not resolve to an existing file on disk: "
                f"expected {full}"
            )


def test_provider_info_is_frozen() -> None:
    """``ProviderInfo`` is a frozen dataclass. Mutating one row must
    not silently leak across callers."""
    sample = avpc.providers_for(V013)[0]
    with pytest.raises(FrozenInstanceError):
        sample.redaction_default_on = False  # type: ignore[misc]


def test_providers_for_unknown_version_returns_empty_tuple() -> None:
    """``providers_for()`` must return ``()`` for any
    ``HermesAgentVersion``-shaped value not in ``COMPAT``. This is the
    safe-fallback path when ``active_version()`` returned ``None``
    because the operator pointed ``HERMES_AGENT_CHECKOUT`` at a custom
    fork.
    """
    from hermes3d.services.agent_version_registry import HermesAgentVersion

    fake = HermesAgentVersion(
        label="v9.99",
        upstream_tag="v0000.0.0",
        checkout_path=Path("/nonexistent"),
        venv_python=None,
        redaction_default_on=False,
        has_kanban=False,
        has_heartbeat_reclaim=False,
        has_zombie_detection=False,
        has_pluggable_providers_dir=False,
    )
    assert avpc.providers_for(fake) == ()


def test_compat_is_a_tuple_of_tuples_not_lists() -> None:
    """Structural immutability: COMPAT and every per-version
    providers list is a tuple, not a list. Prevents an in-place
    .append() corrupting the matrix from another caller.
    """
    assert isinstance(avpc.COMPAT, tuple)
    for entry in avpc.COMPAT:
        assert isinstance(entry, tuple)
        assert len(entry) == 2
        _, providers = entry
        assert isinstance(providers, tuple)


def test_known_v012_endpoint_url_is_minimax_or_deepseek_v1() -> None:
    """Endpoint URLs are public; pin them so a typo (e.g. minimaxi.com
    vs minimax.io, c.f. PR #145 schema test) is caught at unit-test
    time, not in production."""
    by_name = {p.name: p for p in avpc.providers_for(V013)}
    assert by_name["minimax"].endpoint_url == "https://api.minimax.io/v1/models"
    assert by_name["deepseek"].endpoint_url == "https://api.deepseek.com/v1/models"


def test_auth_header_is_authorization_for_bearer_providers() -> None:
    """Both MiniMax and DeepSeek use the ``Authorization: Bearer ...``
    pattern. If a future provider needs ``X-Api-Key:`` instead, this
    test must be updated alongside the new row.
    """
    for _, providers in avpc.COMPAT:
        for p in providers:
            assert p.auth_header == "Authorization", (
                f"{p.name}: auth_header={p.auth_header!r}, expected "
                f"'Authorization' (Bearer scheme). If this provider "
                f"genuinely uses a different header (e.g. 'X-Api-Key'), "
                f"add it to a documented-exception set in this test."
            )
