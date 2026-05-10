"""Shared OpenAI-compatible runtime helpers for Hermes3D agent surfaces."""

from __future__ import annotations

import ipaddress
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SELF_BRIDGE_PORTS = {8765, 8642}
DEFAULT_AGENT_MODEL = "hermes-agent"


def private_env() -> dict[str, str]:
    env_path = Path(os.environ.get("HERMES3D_ENV_FILE", r"G:\private\.env"))
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    try:
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
    except OSError:
        return {}
    return values


def env_value(name: str, private_values: dict[str, str] | None = None, default: str = "") -> str:
    if private_values is None:
        private_values = private_env()
    return os.environ.get(name) or private_values.get(name) or default


def trusted_runtime_url(private_values: dict[str, str] | None = None) -> str | None:
    value = env_value("HERMES3D_AGENT_RUNTIME_URL", private_values).strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    try:
        host = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return None
    if host.is_loopback and parsed.port in SELF_BRIDGE_PORTS:
        return None
    if host.is_loopback or host.is_private or host.is_link_local:
        return value.rstrip("/")
    return None


def configured_runtime_model(private_values: dict[str, str] | None = None, fallback: str = DEFAULT_AGENT_MODEL) -> str:
    return env_value("HERMES3D_AGENT_RUNTIME_MODEL", private_values, fallback).strip() or fallback


def chat_completions_url(runtime_url: str) -> str:
    base = runtime_url.rstrip("/")
    return f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"


def models_url(runtime_url: str) -> str:
    base = runtime_url.rstrip("/")
    return f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"


def runtime_request_body(payload: dict[str, Any], private_values: dict[str, str] | None = None) -> dict[str, Any]:
    """Map Hermes persona model aliases onto the configured concrete local model."""
    resolved_model = configured_runtime_model(private_values, str(payload.get("model") or DEFAULT_AGENT_MODEL))
    return {**payload, "model": resolved_model}


def runtime_probe(private_values: dict[str, str] | None = None, timeout: float = 1.5) -> dict[str, Any]:
    runtime_url = trusted_runtime_url(private_values)
    configured_model = configured_runtime_model(private_values, "")
    if not runtime_url:
        return {
            "ready": False,
            "status": "not_configured",
            "reason": "Set HERMES3D_AGENT_RUNTIME_URL to a trusted local/private OpenAI-compatible runtime that is not this bridge.",
            "runtime_url": None,
            "model": configured_model or None,
            "models": [],
            "latency_ms": None,
        }
    started = time.perf_counter()
    try:
        request = urllib.request.Request(models_url(runtime_url), headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
            http_status = int(response.status)
    except urllib.error.HTTPError as exc:
        return {
            "ready": False,
            "status": "unreachable",
            "reason": f"Configured agent runtime models probe failed with HTTP {exc.code}.",
            "runtime_url": runtime_url,
            "model": configured_model or None,
            "models": [],
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }
    except Exception as exc:
        return {
            "ready": False,
            "status": "unreachable",
            "reason": f"Configured agent runtime models probe failed: {type(exc).__name__}.",
            "runtime_url": runtime_url,
            "model": configured_model or None,
            "models": [],
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }
    models = _model_ids(payload)
    resolved_model = configured_model or _first_chat_model(models) or DEFAULT_AGENT_MODEL
    if configured_model and models and configured_model not in models:
        return {
            "ready": False,
            "status": "model_missing",
            "reason": f"Configured agent runtime responded HTTP {http_status}, but model {configured_model} was not listed.",
            "runtime_url": runtime_url,
            "model": configured_model,
            "models": models[:50],
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }
    return {
        "ready": True,
        "status": "ready",
        "reason": f"Configured local/private agent runtime responded HTTP {http_status} with model {resolved_model}.",
        "runtime_url": runtime_url,
        "model": resolved_model,
        "models": models[:50],
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }


def _model_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    candidates = payload.get("data")
    if not isinstance(candidates, list):
        candidates = payload.get("models")
    if not isinstance(candidates, list):
        return []
    model_ids: list[str] = []
    for item in candidates:
        if isinstance(item, dict):
            value = item.get("id") or item.get("model") or item.get("name")
        else:
            value = item
        if isinstance(value, str) and value.strip():
            model_ids.append(value.strip())
    return model_ids


def _first_chat_model(models: list[str]) -> str | None:
    for model in models:
        lowered = model.lower()
        if "embedding" not in lowered and "reranker" not in lowered:
            return model
    return models[0] if models else None
