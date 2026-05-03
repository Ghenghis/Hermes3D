"""Schema security tests for `config/llm_policy.schema.json`.

Targets the specific bypass found in PR #40 audit (Codex, 2026-05-03):
when `providers.additionalProperties` was set to `true`, an unknown provider
name (e.g. `evil`) could supply a public-HTTP `base_url` like
`http://api.example.com/v1` and slip past validation that the named
providers (`minimax`, `deepseek`, `lm_studio`, `hipfire`) reject via the
`base_url` pattern restriction.

Fix: `providers.additionalProperties` now references `#/definitions/providerConfig`
so unknown provider names inherit the same URL/schema rules.

These tests pin that fix in place: any future regression that relaxes
`additionalProperties` back to `true` (or removes the `$ref`) will fail
this suite at PR time.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "03_implementation" / "config" / "llm_policy.schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base_policy() -> dict:
    """A minimally valid policy for the fixture providers — modify and revalidate."""
    return {
        "default_mode": "template",
        "fallback_mode": "template",
        "provider_allowlist": ["minimax"],
        "cost_cap_usd_per_run": 0.10,
        "cost_cap_usd_per_day": 1.0,
        "timeout_seconds": 30,
        "prompt_max_bytes": 8192,
        "retry_max": 1,
        "rate_per_second": 1,
        "input_usd_per_token": 0.000001,
        "output_usd_per_token": 0.000002,
        "providers": {
            "minimax": {
                "base_url": "https://api.minimaxi.com/v1",
                "probe_path": "/models",
                "completion_path": "/chat/completions",
                "api_key_env": "HERMES3D_MINIMAX_API_KEY",
            }
        },
    }


def test_named_provider_accepts_https_base_url(schema):
    policy = _base_policy()
    jsonschema.validate(policy, schema)  # baseline: must pass


def test_named_provider_rejects_public_http_base_url(schema):
    policy = _base_policy()
    policy["providers"]["minimax"]["base_url"] = "http://api.example.com/v1"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(policy, schema)


def test_unknown_provider_name_with_public_http_base_url_is_REJECTED(schema):
    """Schema-bypass closure (Codex audit 2026-05-03, PR #40 P1).

    If a future regression sets `providers.additionalProperties: true`
    again, this test fails — preventing the schema from silently allowing
    `providers.evil.base_url=http://api.example.com/v1`.
    """
    policy = _base_policy()
    policy["providers"]["evil"] = {
        "base_url": "http://api.example.com/v1",
        "probe_path": "/models",
        "completion_path": "/chat/completions",
        "api_key_env": "HERMES3D_EVIL_API_KEY",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(policy, schema)


def test_unknown_provider_name_with_loopback_base_url_is_accepted(schema):
    """Future local backends (vllm, llamacpp, ollama) are allowed.

    They inherit `providerConfig` rules — loopback / RFC1918 only when
    using HTTP. Outright HTTPS public URLs are also accepted.
    """
    policy = _base_policy()
    policy["providers"]["vllm"] = {
        "base_url": "http://localhost:8000",
        "probe_path": "/v1/models",
        "completion_path": "/v1/chat/completions",
        "api_key_env": "HERMES3D_NULL_API_KEY",
    }
    jsonschema.validate(policy, schema)


def test_unknown_provider_missing_required_fields_is_REJECTED(schema):
    """Unknown providers must satisfy required fields, not just any object."""
    policy = _base_policy()
    policy["providers"]["misconfigured"] = {
        "base_url": "http://localhost:9000"
        # missing probe_path, completion_path, api_key_env
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(policy, schema)


def test_providers_additionalProperties_is_locked_to_providerConfig_ref(schema):
    """Static guard: `additionalProperties` must remain a `$ref` to providerConfig.

    Catches regressions to `additionalProperties: true` at the schema level
    even before runtime validation runs.
    """
    providers_schema = schema["properties"]["providers"]
    add_props = providers_schema.get("additionalProperties")
    assert isinstance(add_props, dict), (
        "providers.additionalProperties must be an object referencing providerConfig "
        "(was: " + repr(add_props) + ")"
    )
    assert add_props.get("$ref") == "#/definitions/providerConfig", (
        "providers.additionalProperties must $ref #/definitions/providerConfig "
        "to prevent schema bypass; saw: " + repr(add_props)
    )
