"""Provider-registry routing loader.

Loads ``02_architecture/policies/provider-registry/routing.yaml`` and exposes
two routing modes that the rest of Hermes3D-OS can honour:

- ``local_private`` — strict local routing (LM Studio default, Ollama fallback,
  no cloud providers permitted). This is the privacy-preserving mode.
- ``hybrid``        — mixed routing: cloud architect (anthropic/claude) +
  cloud implementation (minimax/deepseek) + local fallback (lmstudio/ollama).

Selection is via the ``HERMES3D_ROUTING_MODE`` env var. Unknown modes fall
back to ``local_private`` (privacy-by-default).

The schema is ``hermes.routing.v1``. PyYAML is required (already a Hermes3D
dependency). When the file is missing the loader returns sensible defaults so
older deployments continue to function.

This module is intentionally side-effect-free: import it anywhere; nothing
runs until you call ``get_routing_config`` or ``select_provider_for``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROUTING_SCHEMA = "hermes.routing.v1"
DEFAULT_MODE = "local_private"

#: Repository root probe — used to locate the policy file.
#:
#: ``__file__`` is ``…/03_implementation/src/hermes3d/core/llm/registry_loader.py``;
#: walking five levels up lands on the repo root, which contains
#: ``02_architecture/``.
def _default_routing_path() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[5]
    return repo_root / "02_architecture" / "policies" / "provider-registry" / "routing.yaml"


_DEFAULT_ROUTING: dict[str, Any] = {
    "schema": ROUTING_SCHEMA,
    "local_private": {
        "default": "lmstudio",
        "fallback": "ollama",
        "cloud_allowed": False,
    },
    "hybrid": {
        "architect": "anthropic/claude",
        "implementation": "minimax",
        "budget_implementation": "deepseek",
        "fallback": "siliconflow",
        "local_default": "lmstudio",
        "local_fallback": "ollama",
    },
}


@dataclass(frozen=True)
class RoutingConfig:
    """Resolved routing configuration for one mode."""

    mode: str
    primary: str
    fallback: str
    cloud_allowed: bool
    failover_order: tuple[str, ...]
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "primary": self.primary,
            "fallback": self.fallback,
            "cloud_allowed": self.cloud_allowed,
            "failover_order": list(self.failover_order),
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return dict(_DEFAULT_ROUTING)
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return dict(_DEFAULT_ROUTING)
    if not isinstance(loaded, dict):
        return dict(_DEFAULT_ROUTING)
    return loaded


def get_routing_mode(env: dict[str, str] | None = None) -> str:
    """Return the active routing mode name.

    Honours ``HERMES3D_ROUTING_MODE`` (case-insensitive). Unknown values fall
    back to ``local_private`` to preserve privacy by default.
    """
    src = env if env is not None else os.environ
    raw = (src.get("HERMES3D_ROUTING_MODE") or DEFAULT_MODE).strip().lower()
    if raw not in {"local_private", "hybrid"}:
        return DEFAULT_MODE
    return raw


def get_routing_config(
    *,
    mode: str | None = None,
    routing_path: Path | None = None,
    env: dict[str, str] | None = None,
) -> RoutingConfig:
    """Resolve the routing configuration for the requested (or env) mode."""
    chosen = mode or get_routing_mode(env=env)
    path = routing_path or _default_routing_path()
    raw = _load_yaml(path)

    if chosen == "local_private":
        section = dict(_DEFAULT_ROUTING["local_private"])
        section.update(raw.get("local_private") or {})
        primary = str(section.get("default", "lmstudio"))
        fallback = str(section.get("fallback", "ollama"))
        cloud_allowed = bool(section.get("cloud_allowed", False))
        failover = (primary, fallback)
        return RoutingConfig(
            mode=chosen,
            primary=primary,
            fallback=fallback,
            cloud_allowed=cloud_allowed,
            failover_order=failover,
            raw=section,
        )

    # hybrid
    section = dict(_DEFAULT_ROUTING["hybrid"])
    section.update(raw.get("hybrid") or {})
    primary = str(section.get("implementation", "minimax"))
    fallback = str(section.get("fallback", "siliconflow"))
    failover_order = (
        primary,
        str(section.get("budget_implementation", "deepseek")),
        fallback,
        str(section.get("local_default", "lmstudio")),
        str(section.get("local_fallback", "ollama")),
    )
    return RoutingConfig(
        mode=chosen,
        primary=primary,
        fallback=fallback,
        cloud_allowed=True,
        failover_order=failover_order,
        raw=section,
    )


# Mapping from registry provider names to the ``LLMProvider`` enum values
# Hermes3D's ``providers.py`` ships today. Names not in this map fall through
# to whatever the caller's default is (typically OLLAMA), so the loader stays
# forward-compatible with future provider additions.
PROVIDER_NAME_TO_ENUM = {
    "lmstudio": "lmstudio",
    "ollama": "ollama",
    "anthropic/claude": "openrouter",  # closest existing route; ADR-017 §wiring
    "minimax": "openrouter",
    "deepseek": "openrouter",
    "siliconflow": "openrouter",
    "vllm": "vllm",
    "llamacpp": "llamacpp",
    "openrouter": "openrouter",
}


def resolve_provider_enum_value(registry_name: str, default: str = "ollama") -> str:
    """Resolve a registry provider name to a ``LLMProvider`` enum value.

    Falls back to ``default`` (``ollama``) when the name isn't mapped.
    """
    return PROVIDER_NAME_TO_ENUM.get(registry_name, default)


__all__ = [
    "DEFAULT_MODE",
    "PROVIDER_NAME_TO_ENUM",
    "ROUTING_SCHEMA",
    "RoutingConfig",
    "get_routing_config",
    "get_routing_mode",
    "resolve_provider_enum_value",
]
