"""LM Studio bridge — local LLM client (OpenAI-compatible).

Status: runnable (graceful when LM Studio isn't running)
Contract: ADR-015 (Local LLM provider chain — LM Studio default + Ollama fallback)

Talks to a locally-running LM Studio instance (default:
``http://127.0.0.1:1234/v1``) via LM Studio's OpenAI-compatible HTTP API.
No external services, no API keys, no telemetry.

This module mirrors the public surface of ``ollama_client.py`` so callers
that today instantiate ``OllamaClient`` can switch by import:

    from hermes3d.core.llm.lmstudio_client import LMStudioClient
    client = LMStudioClient()                # uses HERMES3D_LM_STUDIO_BASE_URL
    if client.available():
        resp = client.generate("Tell me about FFF printers.")

It is intentionally a thin façade — the heavy lifting lives in
``LMStudioProvider`` (``providers.py``), which already supports streaming +
tool-calling per ADR-015 §1. Use ``LMStudioProvider`` directly when you
want those advanced surfaces; use ``LMStudioClient`` when you want a
drop-in replacement for ``OllamaClient``.

Recommended weights: ``NousResearch/Hermes-4-14B-FP8`` (see ADR-015 §References).
The class falls back to whatever model LM Studio's GUI has loaded if
``HERMES3D_LM_STUDIO_MODEL`` is unset.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

log = logging.getLogger(__name__)


DEFAULT_BASE_URL = os.environ.get("HERMES3D_LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
DEFAULT_MODEL = os.environ.get("HERMES3D_LM_STUDIO_MODEL", "local-model")
DEFAULT_TIMEOUT_S = float(os.environ.get("HERMES3D_LM_STUDIO_TIMEOUT", "30"))
HEALTH_TIMEOUT_S = float(os.environ.get("HERMES3D_LM_STUDIO_HEALTH_TIMEOUT", "5"))


@dataclass
class LMStudioResponse:
    """Mirror of OllamaResponse so callers can swap clients without
    rewriting downstream code."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = ""
    parsed_json: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class LMStudioUnavailable(RuntimeError):
    """Raised when LM Studio isn't reachable. Callers should fall back
    (typically to Ollama, then to deterministic logic)."""


class LMStudioClient:
    """Thin client targeting LM Studio's ``/v1/chat/completions`` server.

    Public surface intentionally matches ``OllamaClient`` so callers can
    swap with a one-line import change:

      ``available() -> bool``
      ``list_models() -> list[str]``
      ``generate(prompt, *, system=None, temperature=0.2, max_tokens=None)``
      ``chat(messages, *, temperature=0.2, max_tokens=None)``
      ``json_chat(messages, required_keys=(), temperature=0.0)``
      ``stream(prompt, *, system=None, temperature=0.2)`` (LM Studio extra)
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        # LM Studio's local server ignores the auth header; callers may
        # still pass a key when targeting an OpenAI-compat proxy.
        self.api_key = api_key

    # ---- HTTP plumbing ---------------------------------------------------

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(url, data=body, method="POST", headers=self._headers())
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except (TimeoutError, HTTPError, URLError) as exc:
            raise LMStudioUnavailable(f"LM Studio request to {url} failed: {exc}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LMStudioUnavailable(f"LM Studio returned non-JSON: {exc}")

    def _get(self, path: str, *, timeout_s: float | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        req = urlrequest.Request(url, headers=self._headers())
        try:
            with urlrequest.urlopen(req, timeout=timeout_s or self.timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (TimeoutError, HTTPError, URLError) as exc:
            raise LMStudioUnavailable(f"LM Studio GET {url} failed: {exc}")
        except json.JSONDecodeError as exc:
            raise LMStudioUnavailable(f"LM Studio returned non-JSON: {exc}")

    # ---- Public API ------------------------------------------------------

    def available(self) -> bool:
        """Health probe — short-timeout GET /v1/models. Never raises."""
        try:
            self._get("/models", timeout_s=HEALTH_TIMEOUT_S)
            return True
        except LMStudioUnavailable:
            return False

    def list_models(self) -> list[str]:
        """Return the list of model IDs LM Studio currently has loaded."""
        data = self._get("/models", timeout_s=HEALTH_TIMEOUT_S)
        return [m.get("id") for m in data.get("data", []) if m.get("id")]

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LMStudioResponse:
        """Single-prompt completion using /chat/completions."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> LMStudioResponse:
        """Chat-format completion."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        d = self._post("/chat/completions", payload)
        choices = d.get("choices") or []
        text = ""
        finish_reason = ""
        if choices:
            msg = choices[0].get("message") or {}
            text = msg.get("content") or ""
            finish_reason = choices[0].get("finish_reason") or ""
        usage = d.get("usage") or {}
        return LMStudioResponse(
            text=text,
            model=d.get("model", self.model),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            finish_reason=finish_reason,
            raw=d,
        )

    def json_chat(
        self,
        messages: list[dict[str, str]],
        *,
        required_keys: Iterable[str] = (),
        temperature: float = 0.0,
    ) -> LMStudioResponse:
        """Ask the model for JSON only; parse + validate required keys."""
        guard = {
            "role": "system",
            "content": (
                "You MUST respond with valid JSON ONLY. No prose, no "
                "markdown fencing. Required keys: "
                + (", ".join(required_keys) if required_keys else "(any)")
                + "."
            ),
        }
        msgs = [guard] + list(messages)
        resp = self.chat(msgs, temperature=temperature)
        parsed = _extract_json(resp.text)
        if not isinstance(parsed, dict):
            raise LMStudioUnavailable(f"LM Studio replied with non-object JSON: {resp.text[:200]}")
        for k in required_keys:
            if k not in parsed:
                raise LMStudioUnavailable(f"LM Studio JSON missing required key {k!r}: {parsed}")
        resp.parsed_json = parsed
        return resp

    def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
    ) -> Iterator[str]:
        """Yield content chunks from /chat/completions with stream=true."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        url = f"{self.base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(url, data=body, method="POST", headers=self._headers())
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_s) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:") :].strip()
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    chunk = delta.get("content")
                    if chunk:
                        yield chunk
        except (TimeoutError, HTTPError, URLError) as exc:
            raise LMStudioUnavailable(f"LM Studio stream {url} failed: {exc}")


def _extract_json(text: str) -> Any:
    """Extract a JSON value from possibly-noisy text."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner = "\n".join(lines[1:])
        if inner.rstrip().endswith("```"):
            inner = inner.rstrip()[:-3]
        stripped = inner.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        i = stripped.find(opener)
        j = stripped.rfind(closer)
        if 0 <= i < j:
            try:
                return json.loads(stripped[i : j + 1])
            except json.JSONDecodeError:
                continue
    raise LMStudioUnavailable(f"could not extract JSON from: {text[:200]}")


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_S",
    "HEALTH_TIMEOUT_S",
    "LMStudioClient",
    "LMStudioResponse",
    "LMStudioUnavailable",
]
