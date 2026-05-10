"""DeepSeek provider adapter substrate for Phase 3.4 probes."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from decimal import Decimal

import httpx

from hermes3d.gateways.llm import LLMCaller
from hermes3d.gateways.probe import ProbeCaller, ProbeOutcome
from hermes3d.gateways.redaction import redact_text
from hermes3d.orchestration.types import (
    LLMRequest,
    LLMResponse,
    ProviderConfig,
    ProviderProbeResult,
)


def build_probe_request(config: ProviderConfig) -> tuple[str, str, dict[str, str]]:
    """Construct the DeepSeek probe request.

    Squad G follow-up (Discovery audit Agent #3, 2026-05-09): the original
    ``os.environ[config.api_key_env]`` raised bare ``KeyError`` when the env
    var was missing, which surfaced as an opaque HTTP 500 with the env
    variable NAME in the traceback. Convert to an explicit ``RuntimeError``
    so callers see "DeepSeek API key not configured" instead of leaking
    the variable name (low-risk info disclosure).
    """
    method = "GET"
    url = f"{config.base_url.rstrip('/')}/{config.probe_path.lstrip('/')}"
    key = os.environ.get(config.api_key_env)
    if not key:
        raise RuntimeError(
            "DeepSeek provider is not configured: API key env variable is unset. "
            "Set the configured key in the private env file before invoking the probe."
        )
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    return method, url, headers


def parse_probe_response(status: int, body: str) -> ProviderProbeResult:
    response_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    excerpt = redact_text(body)[:200]
    success = False
    try:
        payload = json.loads(body)
        success = (
            200 <= status < 300
            and isinstance(payload, dict)
            and payload.get("object") == "list"
            and isinstance(payload.get("data"), list)
            and len(payload["data"]) > 0
        )
    except (TypeError, json.JSONDecodeError):
        success = False
    return ProviderProbeResult(
        provider_id="deepseek",
        http_status=status,
        latency_ms=0,
        redacted_excerpt=excerpt,
        response_sha256=response_sha256,
        probed_at_utc=_now_iso(),
        success=success,
    )


def probe_caller(config: ProviderConfig) -> ProbeCaller:
    def _caller(active_config: ProviderConfig) -> ProbeOutcome:
        method, url, headers = build_probe_request(active_config)
        start = time.monotonic_ns()
        with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
            response = client.request(method, url, headers=headers)
        latency_ms = (time.monotonic_ns() - start) // 1_000_000
        return ProbeOutcome(
            http_status=response.status_code,
            latency_ms=int(latency_ms),
            body=response.text,
        )

    return _caller


def completion_caller(config: ProviderConfig) -> LLMCaller:
    def _caller(request: LLMRequest) -> LLMResponse:
        url = f"{config.base_url.rstrip('/')}/{config.completion_path.lstrip('/')}"
        # Squad G follow-up: explicit RuntimeError instead of bare KeyError
        # (Discovery audit Agent #3 2026-05-09).
        key = os.environ.get(config.api_key_env)
        if not key:
            raise RuntimeError(
                "DeepSeek provider is not configured: API key env variable is unset. "
                "Set the configured key in the private env file before invoking completion."
            )
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        model = (
            os.environ.get("HERMES3D_DEEPSEEK_MODEL")
            or os.environ.get("DEEPSEEK_MODEL")
            or "deepseek-v4-pro"
        )
        body = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_completion_tokens,
        }
        if model == "deepseek-v4-pro":
            body["thinking"] = {"type": "enabled"}
            body["reasoning_effort"] = "high"
        with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
            response = client.post(url, headers=headers, json=body)
        parsed = response.json()
        return LLMResponse(
            redacted_text=str(parsed["choices"][0]["message"]["content"]),
            tokens_in=int(parsed["usage"]["prompt_tokens"]),
            tokens_out=int(parsed["usage"]["completion_tokens"]),
            cost_usd_estimate=Decimal("0"),
        )

    return _caller


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_probe_request", "parse_probe_response", "probe_caller", "completion_caller"]
