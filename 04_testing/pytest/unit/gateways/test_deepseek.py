"""DeepSeek provider adapter tests for Phase 3.4-B."""

from __future__ import annotations

import json

import pytest
from hermes3d.gateways.providers import deepseek
from hermes3d.orchestration.types import LLMRequest, ProviderConfig


def _config() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://api.deepseek.com/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="HERMES3D_DEEPSEEK_API_KEY",
    )


def test_build_probe_request_uses_env_key_and_probe_url(monkeypatch) -> None:
    monkeypatch.setenv("HERMES3D_DEEPSEEK_API_KEY", "test123")

    method, url, headers = deepseek.build_probe_request(_config())

    assert method == "GET"
    assert url == "https://api.deepseek.com/v1/models"
    assert headers["Authorization"] == "Bearer test123"
    assert headers["Accept"] == "application/json"


def test_build_probe_request_missing_env_raises(monkeypatch) -> None:
    """Squad G follow-up (2026-05-09 Discovery audit): explicit RuntimeError
    on missing env (was bare KeyError that leaked the env variable name
    in tracebacks)."""
    monkeypatch.delenv("HERMES3D_DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="DeepSeek provider is not configured"):
        deepseek.build_probe_request(_config())


def test_completion_caller_missing_env_raises(monkeypatch) -> None:
    """Same Squad G follow-up applied to completion_caller."""
    monkeypatch.delenv("HERMES3D_DEEPSEEK_API_KEY", raising=False)
    caller = deepseek.completion_caller(_config())
    request = LLMRequest(prompt="hello", max_completion_tokens=10, token_id="test-token-id")
    with pytest.raises(RuntimeError, match="DeepSeek provider is not configured"):
        caller(request)


def test_parse_probe_response_accepts_list_object_with_non_empty_data() -> None:
    body = json.dumps({"object": "list", "data": [{"id": "deepseek-v4-pro", "object": "model"}]})

    result = deepseek.parse_probe_response(200, body)

    assert result.provider_id == "deepseek"
    assert result.http_status == 200
    assert result.latency_ms == 0
    assert result.success is True
    assert result.response_sha256


def test_parse_probe_response_rejects_malformed_and_redacts_secrets() -> None:
    result = deepseek.parse_probe_response(
        200,
        '{"object":"list","error":"bad","Authorization":"Bearer abcdefghijklmnop"}',
    )
    malformed = deepseek.parse_probe_response(200, "not json")

    assert result.success is False
    assert "abcdefghijklmnop" not in result.redacted_excerpt
    assert malformed.success is False


def test_completion_caller_defaults_to_deepseek_v4_pro(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setenv("HERMES3D_DEEPSEEK_API_KEY", "test123")
    monkeypatch.delenv("HERMES3D_DEEPSEEK_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    class _Response:
        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _Response()

    monkeypatch.setattr(deepseek.httpx, "Client", _Client)

    response = deepseek.completion_caller(_config())(LLMRequest(prompt="hello", max_completion_tokens=8, token_id="tok"))

    assert response.redacted_text == "ok"
    assert captured["json"]["model"] == "deepseek-v4-pro"
    assert captured["json"]["thinking"] == {"type": "enabled"}
    assert captured["json"]["reasoning_effort"] == "high"
