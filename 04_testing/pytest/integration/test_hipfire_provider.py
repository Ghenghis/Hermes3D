"""HipfireProvider integration coverage (ADR-015).

Hipfire is the optional AMD-node inference helper. The HipfireProvider class
must:

- Refuse to instantiate when HERMES3D_AMD_NODE is unset / != "1" (so a stray
  HERMES3D_LLM_PROVIDER=hipfire on a non-AMD host doesn't silently route
  traffic to a port that won't answer).
- Speak the OpenAI-compat protocol on :11435/v1 like LM Studio does, when
  the env gate is satisfied.
- Be select_provider()-able through the registry once the gate passes.

These tests use httpx's MockTransport so we never touch a real port.
"""

from __future__ import annotations

import httpx
import pytest
from hermes3d.core.llm.providers import (
    HipfireProvider,
    LLMProvider,
    ProviderConfig,
    ProviderUnavailable,
    select_provider,
)

_HIPFIRE_BASE = "http://127.0.0.1:11435/v1"


def _config() -> ProviderConfig:
    return ProviderConfig(
        provider=LLMProvider.HIPFIRE,
        base_url=_HIPFIRE_BASE,
        model="local-model",
    )


# ---------------------------------------------------------------------------
# Env-gate guard
# ---------------------------------------------------------------------------


def test_hipfire_refuses_without_env_gate(monkeypatch):
    """HERMES3D_AMD_NODE unset => ProviderUnavailable at construction."""
    monkeypatch.delenv("HERMES3D_AMD_NODE", raising=False)
    with pytest.raises(ProviderUnavailable, match="HERMES3D_AMD_NODE"):
        HipfireProvider(_config())


def test_hipfire_refuses_when_env_gate_is_zero(monkeypatch):
    """Anything other than the literal '1' must not enable Hipfire."""
    monkeypatch.setenv("HERMES3D_AMD_NODE", "0")
    with pytest.raises(ProviderUnavailable):
        HipfireProvider(_config())


def test_hipfire_refuses_when_env_gate_is_truthy_but_not_one(monkeypatch):
    monkeypatch.setenv("HERMES3D_AMD_NODE", "true")
    with pytest.raises(ProviderUnavailable):
        HipfireProvider(_config())


def test_select_provider_refuses_hipfire_without_env(monkeypatch):
    monkeypatch.delenv("HERMES3D_AMD_NODE", raising=False)
    with pytest.raises(ProviderUnavailable):
        select_provider(_config())


# ---------------------------------------------------------------------------
# Happy path (env gate satisfied)
# ---------------------------------------------------------------------------


def test_hipfire_constructs_when_env_set(monkeypatch):
    monkeypatch.setenv("HERMES3D_AMD_NODE", "1")
    provider = HipfireProvider(_config())
    assert provider.config.provider == LLMProvider.HIPFIRE
    assert provider.config.base_url == _HIPFIRE_BASE


def test_select_provider_returns_hipfire_when_env_set(monkeypatch):
    monkeypatch.setenv("HERMES3D_AMD_NODE", "1")
    provider = select_provider(_config())
    assert isinstance(provider, HipfireProvider)


def test_hipfire_health_probes_v1_models(monkeypatch):
    """Health probe hits GET /v1/models — same path as LM Studio."""
    monkeypatch.setenv("HERMES3D_AMD_NODE", "1")
    seen: dict[str, str] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"data": [{"id": "local-model"}]})

    transport = httpx.MockTransport(_handler)

    provider = HipfireProvider(_config())
    # Patch the httpx.Client used by health() to use our mock transport.
    real_client = httpx.Client

    class _PatchedClient(real_client):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", _PatchedClient)
    result = provider.health()
    assert seen["method"] == "GET"
    assert seen["url"].endswith("/v1/models")
    assert result["data"][0]["id"] == "local-model"


def test_hipfire_generate_happy_path(monkeypatch):
    """generate() POSTs to /v1/chat/completions and unpacks the content."""
    monkeypatch.setenv("HERMES3D_AMD_NODE", "1")
    seen: dict[str, object] = {}

    def _handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        body = request.read().decode("utf-8")
        seen["body"] = body
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "hipfire-ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            },
        )

    transport = httpx.MockTransport(_handler)
    real_client = httpx.Client

    class _PatchedClient(real_client):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", _PatchedClient)

    provider = HipfireProvider(_config())
    result = provider.generate("ping", system="be brief")
    assert result.text == "hipfire-ok"
    assert result.provider == LLMProvider.HIPFIRE
    assert seen["method"] == "POST"
    assert seen["url"].endswith("/v1/chat/completions")
    assert b'"role": "system"' in seen["body"].encode() or b"role" in seen["body"].encode()
