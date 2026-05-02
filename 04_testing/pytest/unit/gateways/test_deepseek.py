"""DeepSeek provider adapter tests for Phase 3.4-B."""

from __future__ import annotations

import json

import pytest
from hermes3d.gateways.providers import deepseek
from hermes3d.orchestration.types import ProviderConfig


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
    monkeypatch.delenv("HERMES3D_DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(KeyError):
        deepseek.build_probe_request(_config())


def test_parse_probe_response_accepts_list_object_with_non_empty_data() -> None:
    body = json.dumps({"object": "list", "data": [{"id": "deepseek-chat", "object": "model"}]})

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
