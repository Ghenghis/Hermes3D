"""LMStudioClient + select_provider_with_fallback coverage (ADR-015).

LM Studio is the new default local LLM provider. ``LMStudioClient`` is a
thin façade around LM Studio's OpenAI-compat ``/v1`` server that mirrors
``OllamaClient``'s public surface so callers can swap with a one-line
import change.

The tests here cover three layers:

1. ``LMStudioClient`` happy path + connection failure (mocked at the
   urllib level — no real port required).
2. ``select_provider_with_fallback`` walks the chain when LM Studio is
   down, falls back to Ollama, and respects the ``HERMES3D_LLM_PROVIDER``
   pin.
3. A live integration test, marked ``integration`` and skipped when
   nothing is listening on :1234.
"""

from __future__ import annotations

import io
import json
import socket
from typing import Any
from urllib.error import URLError

import pytest
from hermes3d.core.llm.lmstudio_client import (
    LMStudioClient,
    LMStudioResponse,
    LMStudioUnavailable,
)
from hermes3d.core.llm.providers import (
    DEFAULT_PROVIDER_CHAIN,
    BaseLLMClient,
    LLMProvider,
    LMStudioProvider,
    OllamaProvider,
    ProviderConfig,
    ProviderUnavailable,
    select_provider_with_fallback,
)

# ---------------------------------------------------------------------------
# helpers — fake urlopen for unit-level mocking of LMStudioClient
# ---------------------------------------------------------------------------


class _FakeResponse(io.BytesIO):
    """Minimal context-manager wrapper around bytes for urlopen()."""

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _ok(payload: dict[str, Any]) -> _FakeResponse:
    return _FakeResponse(json.dumps(payload).encode("utf-8"))


# ---------------------------------------------------------------------------
# LMStudioClient — health probe
# ---------------------------------------------------------------------------


def test_lmstudio_client_available_true(monkeypatch):
    seen: dict[str, Any] = {}

    def _fake(req, timeout):  # noqa: ARG001
        seen["url"] = req.full_url
        return _ok({"data": [{"id": "local-model"}]})

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    client = LMStudioClient(base_url="http://127.0.0.1:1234/v1")
    assert client.available() is True
    assert seen["url"].endswith("/v1/models")


def test_lmstudio_client_available_false_on_connection_refused(monkeypatch):
    def _fake(req, timeout):  # noqa: ARG001
        raise URLError(socket.gaierror(111, "Connection refused"))

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    client = LMStudioClient()
    assert client.available() is False


# ---------------------------------------------------------------------------
# LMStudioClient — list_models
# ---------------------------------------------------------------------------


def test_lmstudio_client_list_models(monkeypatch):
    def _fake(req, timeout):  # noqa: ARG001
        return _ok(
            {
                "data": [
                    {"id": "Hermes-4-14B-FP8"},
                    {"id": "qwen2.5-coder-32b-instruct"},
                ]
            }
        )

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    client = LMStudioClient()
    assert client.list_models() == ["Hermes-4-14B-FP8", "qwen2.5-coder-32b-instruct"]


# ---------------------------------------------------------------------------
# LMStudioClient — generate / chat
# ---------------------------------------------------------------------------


def test_lmstudio_client_generate_happy(monkeypatch):
    seen: dict[str, Any] = {}

    def _fake(req, timeout):  # noqa: ARG001
        seen["url"] = req.full_url
        seen["body"] = req.data
        return _ok(
            {
                "model": "local-model",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 5,
                    "completion_tokens": 1,
                    "total_tokens": 6,
                },
            }
        )

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    client = LMStudioClient(model="local-model")
    resp = client.generate("ping", system="be brief")
    assert isinstance(resp, LMStudioResponse)
    assert resp.text == "ok"
    assert resp.model == "local-model"
    assert resp.prompt_tokens == 5 and resp.completion_tokens == 1
    assert seen["url"].endswith("/v1/chat/completions")
    body = json.loads(seen["body"].decode("utf-8"))
    assert body["stream"] is False
    assert body["messages"][0] == {"role": "system", "content": "be brief"}
    assert body["messages"][1] == {"role": "user", "content": "ping"}


def test_lmstudio_client_generate_raises_when_unreachable(monkeypatch):
    def _fake(req, timeout):  # noqa: ARG001
        raise URLError("connection refused")

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    with pytest.raises(LMStudioUnavailable):
        LMStudioClient().generate("ping")


def test_lmstudio_client_generate_raises_on_non_json(monkeypatch):
    def _fake(req, timeout):  # noqa: ARG001
        return _FakeResponse(b"<html>nope</html>")

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    with pytest.raises(LMStudioUnavailable):
        LMStudioClient().generate("ping")


def test_lmstudio_client_chat_passes_messages_through(monkeypatch):
    captured: dict[str, Any] = {}

    def _fake(req, timeout):  # noqa: ARG001
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return _ok({"choices": [{"message": {"content": "yo"}}]})

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    client = LMStudioClient(model="m")
    msgs = [{"role": "user", "content": "hi"}]
    resp = client.chat(msgs, max_tokens=64)
    assert resp.text == "yo"
    assert captured["body"]["messages"] == msgs
    assert captured["body"]["max_tokens"] == 64


def test_lmstudio_client_json_chat_extracts_object(monkeypatch):
    def _fake(req, timeout):  # noqa: ARG001
        return _ok(
            {
                "choices": [
                    {
                        "message": {
                            "content": '```json\n{"plan": "ok", "steps": 1}\n```',
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    client = LMStudioClient()
    resp = client.json_chat([{"role": "user", "content": "go"}], required_keys=("plan",))
    assert resp.parsed_json == {"plan": "ok", "steps": 1}


def test_lmstudio_client_json_chat_missing_required_key_raises(monkeypatch):
    def _fake(req, timeout):  # noqa: ARG001
        return _ok({"choices": [{"message": {"content": '{"a": 1}'}}]})

    monkeypatch.setattr("hermes3d.core.llm.lmstudio_client.urlrequest.urlopen", _fake)
    with pytest.raises(LMStudioUnavailable):
        LMStudioClient().json_chat([{"role": "user", "content": "go"}], required_keys=("plan",))


# ---------------------------------------------------------------------------
# select_provider_with_fallback — chain ordering + skip semantics
# ---------------------------------------------------------------------------


def test_select_with_fallback_prefers_lm_studio_when_healthy(monkeypatch):
    """LM Studio is reachable; chain stops at the first hit (no Ollama call)."""
    monkeypatch.delenv("HERMES3D_LLM_PROVIDER", raising=False)

    def _available(self) -> bool:
        return isinstance(self, LMStudioProvider)

    monkeypatch.setattr(BaseLLMClient, "available", _available)
    client = select_provider_with_fallback()
    assert isinstance(client, LMStudioProvider)


def test_select_with_fallback_falls_back_to_ollama_when_lm_studio_down(monkeypatch):
    monkeypatch.delenv("HERMES3D_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("HERMES3D_AMD_NODE", raising=False)

    def _available(self) -> bool:
        return isinstance(self, OllamaProvider)

    monkeypatch.setattr(BaseLLMClient, "available", _available)
    client = select_provider_with_fallback()
    assert isinstance(client, OllamaProvider)


def test_select_with_fallback_skips_hipfire_when_env_unset(monkeypatch):
    """Hipfire's ProviderUnavailable on construct must be skipped silently."""
    monkeypatch.delenv("HERMES3D_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("HERMES3D_AMD_NODE", raising=False)

    # Force LM Studio + Ollama to look down so the chain reaches Hipfire.
    monkeypatch.setattr(BaseLLMClient, "available", lambda self: False)
    with pytest.raises(ProviderUnavailable, match="no provider in chain"):
        select_provider_with_fallback()


def test_select_with_fallback_honors_explicit_pin(monkeypatch):
    """When HERMES3D_LLM_PROVIDER is set, the chain is bypassed."""
    monkeypatch.setenv("HERMES3D_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("HERMES3D_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("HERMES3D_LLM_MODEL", raising=False)
    monkeypatch.delenv("HERMES3D_LLM_API_KEY", raising=False)

    client = select_provider_with_fallback()
    assert isinstance(client, OllamaProvider)


def test_default_provider_chain_order_is_documented():
    """ADR-015 §1: lm_studio → ollama → hipfire."""
    assert DEFAULT_PROVIDER_CHAIN == (
        LLMProvider.LMSTUDIO,
        LLMProvider.OLLAMA,
        LLMProvider.HIPFIRE,
    )


# ---------------------------------------------------------------------------
# LMStudioProvider conformance — happy path through select_provider
# ---------------------------------------------------------------------------


def test_lmstudio_provider_constructs_via_select_provider():
    cfg = ProviderConfig(
        provider=LLMProvider.LMSTUDIO,
        base_url="http://127.0.0.1:1234/v1",
        model="local-model",
    )
    from hermes3d.core.llm.providers import select_provider

    client = select_provider(cfg)
    assert isinstance(client, LMStudioProvider)
    assert client.config.base_url == "http://127.0.0.1:1234/v1"


# ---------------------------------------------------------------------------
# Live integration — skipped unless LM Studio is actually listening on :1234.
# ---------------------------------------------------------------------------


def _lm_studio_is_live() -> bool:
    """Return True iff a service is bound to 127.0.0.1:1234 right now.

    We *only* probe with a TCP connect — we do NOT issue an LLM request,
    so this stays cheap and never produces a billed token (LM Studio is
    free anyway, but the discipline matters for future remote setups).
    """
    try:
        with socket.create_connection(("127.0.0.1", 1234), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not _lm_studio_is_live(), reason="LM Studio not running on :1234")
def test_lmstudio_client_live_health_probe():
    """Hits the real LM Studio /v1/models endpoint when available."""
    client = LMStudioClient()
    assert client.available() is True
    models = client.list_models()
    # If LM Studio is up but no model is loaded, list_models() returns [].
    assert isinstance(models, list)
