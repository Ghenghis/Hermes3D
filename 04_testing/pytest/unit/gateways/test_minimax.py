"""MiniMax provider adapter tests for Phase 3.4-B."""

from __future__ import annotations

import json

import pytest
from hermes3d.gateways.providers import minimax
from hermes3d.orchestration.types import ProviderConfig


def _config() -> ProviderConfig:
    return ProviderConfig(
        base_url="https://api.minimax.io/v1",
        probe_path="/models",
        completion_path="/chat/completions",
        api_key_env="HERMES3D_MINIMAX_API_KEY",
    )


def test_build_probe_request_uses_env_key_and_probe_url(monkeypatch) -> None:
    monkeypatch.setenv("HERMES3D_MINIMAX_API_KEY", "test123")

    method, url, headers = minimax.build_probe_request(_config())

    assert method == "GET"
    assert url == "https://api.minimax.io/v1/models"
    assert headers["Authorization"] == "Bearer test123"
    assert headers["Accept"] == "application/json"


def test_build_probe_request_missing_env_raises(monkeypatch) -> None:
    monkeypatch.delenv("HERMES3D_MINIMAX_API_KEY", raising=False)

    with pytest.raises(KeyError):
        minimax.build_probe_request(_config())


def test_parse_probe_response_accepts_non_empty_data_list() -> None:
    body = json.dumps({"data": [{"id": "abab6.5s-chat", "object": "model"}]})

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
