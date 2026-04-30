"""Ollama bridge — local LLM client.

Status: runnable (graceful when Ollama isn't running)
Contract: 00_overview/contract/MASTER_CONTRACT.md §32 (Local LLM)

Talks to a locally-running Ollama instance (default: http://localhost:11434)
using Ollama's HTTP API. No external services, no API keys, no telemetry —
matches the user's "fully local + anonymous" preference.

Public surface:
  OllamaClient(base_url, model)        – wraps /api/generate and /api/chat
  generate(prompt) -> str              – single-prompt completion
  chat(messages) -> str                – chat-format completion
  json_chat(messages, schema) -> dict  – structured output (asks the model
                                          to return JSON; validates shape)
  available() -> bool                  – is Ollama reachable?
  list_models() -> list[str]           – which models are pulled

Used by: multi-agent system (critic/optimizer), failure predictor, future
"explain this dispatch decision" surface in the Gradio UI.

Note: the agentic features in this kit work WITHOUT Ollama. The LLM is
optional — when unavailable, the system falls back to the deterministic
scoring functions.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import socket
from dataclasses import dataclass, field
from typing import Any, Iterable
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


log = logging.getLogger(__name__)


DEFAULT_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")


@dataclass
class OllamaResponse:
    text: str
    model: str
    eval_count: int = 0
    prompt_eval_count: int = 0
    total_duration_ns: int = 0
    parsed_json: dict[str, Any] | None = None

    @property
    def total_duration_s(self) -> float:
        return self.total_duration_ns / 1e9


# =============================================================================


class OllamaUnavailable(RuntimeError):
    """Raised when Ollama isn't reachable. Callers should fall back to
    deterministic logic."""


class OllamaClient:
    def __init__(
        self, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL, timeout_s: float = 60.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    # ---- HTTP plumbing ---------------------------------------------------

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlrequest.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
        except (HTTPError, URLError, socket.timeout) as exc:
            raise OllamaUnavailable(f"Ollama request to {url} failed: {exc}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaUnavailable(f"Ollama returned non-JSON: {exc}")

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            with urlrequest.urlopen(url, timeout=self.timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, socket.timeout) as exc:
            raise OllamaUnavailable(f"Ollama GET {url} failed: {exc}")
        except json.JSONDecodeError as exc:
            raise OllamaUnavailable(f"Ollama returned non-JSON: {exc}")

    # ---- Public API ------------------------------------------------------

    def available(self) -> bool:
        try:
            self.list_models()
            return True
        except OllamaUnavailable:
            return False

    def list_models(self) -> list[str]:
        data = self._get("/api/tags")
        return [m["name"] for m in data.get("models", [])]

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> OllamaResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        if system:
            payload["system"] = system
        d = self._post("/api/generate", payload)
        return OllamaResponse(
            text=d.get("response", ""),
            model=d.get("model", self.model),
            eval_count=int(d.get("eval_count", 0)),
            prompt_eval_count=int(d.get("prompt_eval_count", 0)),
            total_duration_ns=int(d.get("total_duration", 0)),
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> OllamaResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        d = self._post("/api/chat", payload)
        return OllamaResponse(
            text=d.get("message", {}).get("content", ""),
            model=d.get("model", self.model),
            eval_count=int(d.get("eval_count", 0)),
            prompt_eval_count=int(d.get("prompt_eval_count", 0)),
            total_duration_ns=int(d.get("total_duration", 0)),
        )

    def json_chat(
        self,
        messages: list[dict[str, str]],
        *,
        required_keys: Iterable[str] = (),
        temperature: float = 0.0,
    ) -> OllamaResponse:
        """Ask the model to reply with JSON only; parse + validate.

        Adds a system-level JSON guard message; tolerant of preamble or
        markdown fencing. Validates that all ``required_keys`` are present.
        """
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
            raise OllamaUnavailable(f"Ollama replied with non-object JSON: {resp.text[:200]}")
        for k in required_keys:
            if k not in parsed:
                raise OllamaUnavailable(f"Ollama JSON missing required key {k!r}: {parsed}")
        resp.parsed_json = parsed
        return resp


def _extract_json(text: str) -> Any:
    """Extract a JSON value from possibly-noisy text.

    Handles:
      - ```json ... ``` fenced blocks
      - leading/trailing prose
      - raw JSON
    """
    stripped = text.strip()
    # Markdown fence
    if stripped.startswith("```"):
        # remove first line + trailing ```
        lines = stripped.splitlines()
        if lines[0].lstrip("`").strip().lower().startswith("json"):
            inner = "\n".join(lines[1:])
        else:
            inner = "\n".join(lines[1:])
        if inner.rstrip().endswith("```"):
            inner = inner.rstrip()[:-3]
        stripped = inner.strip()
    # Direct parse
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # Find first { ... } or [ ... ] block
    for opener, closer in (("{", "}"), ("[", "]")):
        i = stripped.find(opener)
        j = stripped.rfind(closer)
        if 0 <= i < j:
            try:
                return json.loads(stripped[i : j + 1])
            except json.JSONDecodeError:
                continue
    raise OllamaUnavailable(f"could not extract JSON from: {text[:200]}")


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_MODEL",
    "OllamaClient",
    "OllamaResponse",
    "OllamaUnavailable",
]
