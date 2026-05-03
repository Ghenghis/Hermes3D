"""Tests for hermes3d.core.llm.registry_loader (provider-registry routing).

Covers:
- routing-mode env-var resolution (default, explicit, unknown -> default)
- local_private: lmstudio primary, ollama fallback, cloud_allowed=False
- hybrid: minimax primary + multi-step failover order
- routing.yaml file presence is *not* required (loader returns defaults)
- ProviderConfig.from_env honours HERMES3D_ROUTING_MODE when no explicit
  HERMES3D_LLM_PROVIDER is set.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Strip the LLM/routing env so each test starts clean."""
    for var in (
        "HERMES3D_LLM_PROVIDER",
        "HERMES3D_LLM_BASE_URL",
        "HERMES3D_LLM_MODEL",
        "HERMES3D_LLM_API_KEY",
        "HERMES3D_LLM_TIMEOUT",
        "HERMES3D_LLM_TEMPERATURE",
        "HERMES3D_ROUTING_MODE",
    ):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------------------
# get_routing_mode
# ---------------------------------------------------------------------------
def test_get_routing_mode_defaults_to_local_private():
    from hermes3d.core.llm.registry_loader import DEFAULT_MODE, get_routing_mode

    assert DEFAULT_MODE == "local_private"
    assert get_routing_mode(env={}) == "local_private"


def test_get_routing_mode_honours_env_hybrid():
    from hermes3d.core.llm.registry_loader import get_routing_mode

    assert get_routing_mode(env={"HERMES3D_ROUTING_MODE": "hybrid"}) == "hybrid"


def test_get_routing_mode_unknown_falls_back_to_default():
    from hermes3d.core.llm.registry_loader import get_routing_mode

    assert get_routing_mode(env={"HERMES3D_ROUTING_MODE": "wide_open"}) == "local_private"


def test_get_routing_mode_is_case_insensitive():
    from hermes3d.core.llm.registry_loader import get_routing_mode

    assert get_routing_mode(env={"HERMES3D_ROUTING_MODE": "HYBRID"}) == "hybrid"


# ---------------------------------------------------------------------------
# get_routing_config — local_private
# ---------------------------------------------------------------------------
def test_local_private_routing_uses_lmstudio_then_ollama():
    from hermes3d.core.llm.registry_loader import get_routing_config

    cfg = get_routing_config(mode="local_private")
    assert cfg.mode == "local_private"
    assert cfg.primary == "lmstudio"
    assert cfg.fallback == "ollama"
    assert cfg.cloud_allowed is False
    assert cfg.failover_order == ("lmstudio", "ollama")


def test_local_private_routing_loads_from_disk(tmp_path: Path):
    from hermes3d.core.llm.registry_loader import get_routing_config

    routing = tmp_path / "routing.yaml"
    routing.write_text(
        "schema: hermes.routing.v1\n"
        "local_private:\n"
        "  default: ollama\n"
        "  fallback: lmstudio\n"
        "  cloud_allowed: false\n",
        encoding="utf-8",
    )
    cfg = get_routing_config(mode="local_private", routing_path=routing)
    assert cfg.primary == "ollama"
    assert cfg.fallback == "lmstudio"
    assert cfg.cloud_allowed is False


def test_local_private_falls_back_to_defaults_when_file_missing(tmp_path: Path):
    from hermes3d.core.llm.registry_loader import get_routing_config

    cfg = get_routing_config(mode="local_private", routing_path=tmp_path / "absent.yaml")
    assert cfg.primary == "lmstudio"
    assert cfg.fallback == "ollama"


# ---------------------------------------------------------------------------
# get_routing_config — hybrid
# ---------------------------------------------------------------------------
def test_hybrid_routing_failover_order():
    from hermes3d.core.llm.registry_loader import get_routing_config

    cfg = get_routing_config(mode="hybrid")
    assert cfg.mode == "hybrid"
    assert cfg.primary == "minimax"
    assert cfg.cloud_allowed is True
    # implementation -> budget_implementation -> fallback -> local_default -> local_fallback
    assert cfg.failover_order == (
        "minimax",
        "deepseek",
        "siliconflow",
        "lmstudio",
        "ollama",
    )


def test_hybrid_routing_overrides_via_yaml(tmp_path: Path):
    from hermes3d.core.llm.registry_loader import get_routing_config

    routing = tmp_path / "routing.yaml"
    routing.write_text(
        "schema: hermes.routing.v1\n"
        "hybrid:\n"
        "  architect: anthropic/claude\n"
        "  implementation: openai\n"
        "  budget_implementation: deepseek\n"
        "  fallback: groq\n"
        "  local_default: lmstudio\n"
        "  local_fallback: ollama\n",
        encoding="utf-8",
    )
    cfg = get_routing_config(mode="hybrid", routing_path=routing)
    assert cfg.primary == "openai"
    assert cfg.failover_order[2] == "groq"


# ---------------------------------------------------------------------------
# resolve_provider_enum_value
# ---------------------------------------------------------------------------
def test_resolve_provider_enum_known_names():
    from hermes3d.core.llm.registry_loader import resolve_provider_enum_value

    assert resolve_provider_enum_value("lmstudio") == "lmstudio"
    assert resolve_provider_enum_value("ollama") == "ollama"
    assert resolve_provider_enum_value("vllm") == "vllm"


def test_resolve_provider_enum_unknown_falls_back():
    from hermes3d.core.llm.registry_loader import resolve_provider_enum_value

    assert resolve_provider_enum_value("definitely_not_a_provider") == "ollama"
    assert (
        resolve_provider_enum_value("definitely_not_a_provider", default="vllm") == "vllm"
    )


def test_resolve_provider_enum_cloud_names_route_through_openrouter():
    from hermes3d.core.llm.registry_loader import resolve_provider_enum_value

    # Cloud provider names not in the LLMProvider enum must funnel into a
    # supported transport (openrouter), per ADR-017 wiring §1.
    assert resolve_provider_enum_value("minimax") == "openrouter"
    assert resolve_provider_enum_value("deepseek") == "openrouter"
    assert resolve_provider_enum_value("siliconflow") == "openrouter"
    assert resolve_provider_enum_value("anthropic/claude") == "openrouter"


# ---------------------------------------------------------------------------
# Wiring: ProviderConfig.from_env honours routing mode
# ---------------------------------------------------------------------------
def test_provider_config_from_env_uses_local_private_default(monkeypatch):
    from hermes3d.core.llm.providers import LLMProvider, ProviderConfig

    # No explicit HERMES3D_LLM_PROVIDER, default mode = local_private,
    # primary = lmstudio.
    cfg = ProviderConfig.from_env()
    assert cfg.provider == LLMProvider.LMSTUDIO


def test_provider_config_from_env_explicit_overrides_routing(monkeypatch):
    from hermes3d.core.llm.providers import LLMProvider, ProviderConfig

    monkeypatch.setenv("HERMES3D_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("HERMES3D_ROUTING_MODE", "hybrid")
    cfg = ProviderConfig.from_env()
    # Explicit env beats routing mode.
    assert cfg.provider == LLMProvider.OLLAMA


def test_provider_config_from_env_hybrid_routes_to_openrouter(monkeypatch):
    from hermes3d.core.llm.providers import LLMProvider, ProviderConfig

    monkeypatch.setenv("HERMES3D_ROUTING_MODE", "hybrid")
    cfg = ProviderConfig.from_env()
    # hybrid primary = minimax, which maps to LLMProvider.OPENROUTER.
    assert cfg.provider == LLMProvider.OPENROUTER


# ---------------------------------------------------------------------------
# Schema sanity
# ---------------------------------------------------------------------------
def test_shipped_routing_yaml_parseable():
    """The routing.yaml committed under 02_architecture/policies/ parses."""
    import yaml

    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    routing = repo_root / "02_architecture" / "policies" / "provider-registry" / "routing.yaml"
    if not routing.exists():
        pytest.skip("routing.yaml not present in this checkout")
    parsed = yaml.safe_load(routing.read_text(encoding="utf-8"))
    assert parsed["schema"] == "hermes.routing.v1"
    assert parsed["local_private"]["default"] == "lmstudio"
    assert parsed["local_private"]["fallback"] == "ollama"
    assert parsed["hybrid"]["architect"] == "anthropic/claude"
    assert parsed["hybrid"]["implementation"] == "minimax"
    assert parsed["hybrid"]["budget_implementation"] == "deepseek"
    assert parsed["hybrid"]["fallback"] == "siliconflow"
