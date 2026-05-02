"""Provider policy loading helpers for Phase 3.4 probes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import jsonschema
import yaml

from hermes3d.gateways.llm import DEFAULT_POLICY_PATH, DEFAULT_SCHEMA_PATH
from hermes3d.orchestration.types import ProviderConfig


@dataclass(frozen=True)
class ProbePolicy:
    providers: dict[str, ProviderConfig]
    probe_freshness_minutes: int
    probe_budget_usd_per_day: Decimal
    probe_rate_per_minute: int


def load_provider_configs(
    policy_path: Path | str = DEFAULT_POLICY_PATH,
    schema_path: Path | str = DEFAULT_SCHEMA_PATH,
) -> dict[str, ProviderConfig]:
    policy = _load_validated_policy(policy_path=policy_path, schema_path=schema_path)
    providers = policy.get("providers") or {}
    return {str(provider_id): _provider_config(config) for provider_id, config in providers.items()}


def load_probe_policy(
    policy_path: Path | str = DEFAULT_POLICY_PATH,
    schema_path: Path | str = DEFAULT_SCHEMA_PATH,
) -> ProbePolicy:
    policy = _load_validated_policy(policy_path=policy_path, schema_path=schema_path)
    return ProbePolicy(
        providers=load_provider_configs(policy_path=policy_path, schema_path=schema_path),
        probe_freshness_minutes=int(policy.get("probe_freshness_minutes", 15)),
        probe_budget_usd_per_day=Decimal(str(policy.get("probe_budget_usd_per_day", "0.10"))),
        probe_rate_per_minute=int(policy.get("probe_rate_per_minute", 1)),
    )


def _load_validated_policy(
    *,
    policy_path: Path | str,
    schema_path: Path | str,
) -> dict[str, object]:
    policy = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    jsonschema.validate(policy, schema)
    return policy


def _provider_config(config: object) -> ProviderConfig:
    if not isinstance(config, dict):
        raise TypeError("provider config must be a mapping")
    return ProviderConfig(
        base_url=str(config["base_url"]),
        probe_path=str(config["probe_path"]),
        completion_path=str(config["completion_path"]),
        api_key_env=str(config["api_key_env"]),
        cost_cap_usd_per_run=_optional_decimal(config.get("cost_cap_usd_per_run")),
        cost_cap_usd_per_day=_optional_decimal(config.get("cost_cap_usd_per_day")),
    )


def _optional_decimal(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))


__all__ = ["load_provider_configs", "load_probe_policy", "ProbePolicy", "ProviderConfig"]
