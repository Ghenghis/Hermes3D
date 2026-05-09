"""MiniMax provider adapter tests for Phase 3.4-B."""

from __future__ import annotations

import json

import pytest
from hermes3d.gateways.providers import minimax
from hermes3d.orchestration.types import LLMRequest, ProviderConfig


def _config() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://api.minimax.io/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="HERMES3D_MINIMAX_API_KEY",
    )


def test_build_probe_request_uses_env_key_and_probe_url(monkeypatch) -> None:
    monkeypatch.setenv("HERMES3D_MINIMAX_API_KEY", "test123")
    monkeypatch.delenv("HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_TOKEN_PLAN_API_KEY", raising=False)

    method, url, headers = minimax.build_probe_request(_config())

    assert method == "GET"
    assert url == "https://api.minimax.io/v1/models"
    assert headers["Authorization"] == "Bearer test123"
    assert headers["Accept"] == "application/json"


def test_build_probe_request_missing_env_raises(monkeypatch) -> None:
    monkeypatch.delenv("HERMES3D_MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_TOKEN_PLAN_API_KEY", raising=False)
    monkeypatch.delenv("HERMES3D_MINIMAX_HIGHSPEED_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_HIGHSPEED_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)

    with pytest.raises(KeyError):
        minimax.build_probe_request(_config())


def test_build_probe_request_prefers_token_plan_key(monkeypatch) -> None:
    monkeypatch.setenv("HERMES3D_MINIMAX_TOKEN_PLAN_API_KEY", "token-plan-key")
    monkeypatch.setenv("HERMES3D_MINIMAX_API_KEY", "standard-key")

    _method, _url, headers = minimax.build_probe_request(_config())

    assert headers["Authorization"] == "Bearer token-plan-key"


def test_parse_probe_response_accepts_non_empty_data_list() -> None:
    body = json.dumps({"data": [{"id": "MiniMax-M2.7-highspeed", "object": "model"}]})

    result = minimax.parse_probe_response(200, body)

    assert result.provider_id == "minimax"
    assert result.http_status == 200
    assert result.latency_ms == 0
    assert result.success is True
    assert result.response_sha256


def test_parse_probe_response_rejects_malformed_and_redacts_secrets() -> None:
    result = minimax.parse_probe_response(
        200,
        '{"error":"not json", "Authorization":"Bearer abcdefghijklmnop"}',
    )
    malformed = minimax.parse_probe_response(200, "not json")

    assert result.success is False
    assert "abcdefghijklmnop" not in result.redacted_excerpt
    assert malformed.success is False


def test_completion_caller_uses_highspeed_model_and_openai_token_field(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setenv("HERMES3D_MINIMAX_API_KEY", "test123")
    monkeypatch.delenv("HERMES3D_MINIMAX_MODEL", raising=False)
    monkeypatch.delenv("MINIMAX_MODEL", raising=False)

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

    monkeypatch.setattr(minimax.httpx, "Client", _Client)

    response = minimax.completion_caller(_config())(LLMRequest(prompt="hello", max_completion_tokens=8, token_id="tok"))

    assert response.redacted_text == "ok"
    assert captured["json"]["model"] == "MiniMax-M2.7-highspeed"
    assert captured["json"]["max_completion_tokens"] == 8
    assert "max_tokens" not in captured["json"]
