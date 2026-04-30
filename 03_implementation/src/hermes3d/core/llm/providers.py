"""LLM provider abstraction.

Hermes3D-OS is local-first by default but supports multiple backends so the
fleet brain can keep running even if one provider is down. All providers share
the same shape (``generate(prompt) -> ProviderResult``) and the same JSON
extraction helper, so every agentic module (multi_agent, failure_predictor,
quality_scorer, etc.) is provider-agnostic.

Supported backends (offline-tested):
- ``ollama``       : http://127.0.0.1:11434  (default, fully local)
- ``lmstudio``     : http://127.0.0.1:1234   (LM Studio's OpenAI-compat server)
- ``vllm``         : http://127.0.0.1:8000   (vLLM OpenAI-compat server)
- ``llamacpp``     : http://127.0.0.1:8080   (llama.cpp ``server`` binary)
- ``openrouter``   : https://openrouter.ai/api/v1  (optional, requires key)

Selection happens via ``HERMES3D_LLM_PROVIDER`` env var (default: ``ollama``)
or programmatically via ``select_provider``.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    VLLM = "vllm"
    LLAMACPP = "llamacpp"
    OPENROUTER = "openrouter"


class ProviderUnavailable(RuntimeError):
    """Raised when the chosen LLM backend cannot be reached."""


@dataclass
class ProviderResult:
    text: str
    provider: LLMProvider
    model: str
    elapsed_seconds: float
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    provider: LLMProvider
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 60.0
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        provider = LLMProvider(os.getenv("HERMES3D_LLM_PROVIDER", "ollama").lower())
        defaults = {
            LLMProvider.OLLAMA: ("http://127.0.0.1:11434", "qwen2.5-coder:7b"),
            LLMProvider.LMSTUDIO: ("http://127.0.0.1:1234/v1", "local-model"),
            LLMProvider.VLLM: ("http://127.0.0.1:8000/v1", "Qwen/Qwen2.5-7B-Instruct"),
            LLMProvider.LLAMACPP: ("http://127.0.0.1:8080", "llama"),
            LLMProvider.OPENROUTER: (
                "https://openrouter.ai/api/v1",
                "qwen/qwen-2.5-coder-32b-instruct",
            ),
        }
        base_url_default, model_default = defaults[provider]
        return cls(
            provider=provider,
            base_url=os.getenv("HERMES3D_LLM_BASE_URL", base_url_default),
            model=os.getenv("HERMES3D_LLM_MODEL", model_default),
            api_key=os.getenv("HERMES3D_LLM_API_KEY"),
            timeout_seconds=float(os.getenv("HERMES3D_LLM_TIMEOUT", "60")),
            temperature=float(os.getenv("HERMES3D_LLM_TEMPERATURE", "0.2")),
        )


class BaseLLMClient:
    """Common interface; concrete classes implement ``_call``."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def available(self) -> bool:
        try:
            self.health()
            return True
        except Exception:
            return False

    def health(self) -> dict[str, Any]:  # pragma: no cover - exercised in subclasses
        raise NotImplementedError

    def generate(self, prompt: str, *, system: str | None = None) -> ProviderResult:
        import time

        start = time.monotonic()
        try:
            text, raw = self._call(prompt, system=system)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"{self.config.provider.value} unreachable at {self.config.base_url}: {exc}"
            ) from exc
        elapsed = time.monotonic() - start
        return ProviderResult(
            text=text,
            provider=self.config.provider,
            model=self.config.model,
            elapsed_seconds=elapsed,
            raw=raw,
        )

    def _call(  # pragma: no cover - implemented by subclasses
        self, prompt: str, *, system: str | None
    ) -> tuple[str, dict[str, Any]]:
        raise NotImplementedError


class OllamaProvider(BaseLLMClient):
    def health(self) -> dict[str, Any]:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{self.config.base_url}/api/tags")
            resp.raise_for_status()
            return resp.json()

    def _call(self, prompt: str, *, system: str | None) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.config.temperature},
        }
        if system:
            payload["system"] = system
        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            resp = client.post(f"{self.config.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("response", ""), data


class _OpenAICompatProvider(BaseLLMClient):
    """Shared logic for any /v1/chat/completions backend (LM Studio, vLLM, OpenRouter)."""

    def health(self) -> dict[str, Any]:
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{self.config.base_url}/models", headers=headers)
            resp.raise_for_status()
            return resp.json()

    def _call(self, prompt: str, *, system: str | None) -> tuple[str, dict[str, Any]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            resp = client.post(
                f"{self.config.base_url}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
        text = ""
        choices = data.get("choices") or []
        if choices:
            msg = choices[0].get("message") or {}
            text = msg.get("content") or ""
        return text, data


class LMStudioProvider(_OpenAICompatProvider):
    pass


class VLLMProvider(_OpenAICompatProvider):
    pass


class LlamaCppProvider(BaseLLMClient):
    """llama.cpp's native ``server`` exposes /completion."""

    def health(self) -> dict[str, Any]:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{self.config.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    def _call(self, prompt: str, *, system: str | None) -> tuple[str, dict[str, Any]]:
        full = f"{system}\n\n{prompt}" if system else prompt
        payload = {"prompt": full, "temperature": self.config.temperature, "stream": False}
        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            resp = client.post(f"{self.config.base_url}/completion", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("content", ""), data


class OpenRouterProvider(_OpenAICompatProvider):
    """OpenRouter requires an API key; will refuse to instantiate without one."""

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_key:
            raise ProviderUnavailable("OpenRouter selected but HERMES3D_LLM_API_KEY is not set.")
        super().__init__(config)


_PROVIDER_REGISTRY: dict[LLMProvider, type[BaseLLMClient]] = {
    LLMProvider.OLLAMA: OllamaProvider,
    LLMProvider.LMSTUDIO: LMStudioProvider,
    LLMProvider.VLLM: VLLMProvider,
    LLMProvider.LLAMACPP: LlamaCppProvider,
    LLMProvider.OPENROUTER: OpenRouterProvider,
}


def select_provider(config: ProviderConfig | None = None) -> BaseLLMClient:
    """Construct the configured provider. Read env if ``config`` omitted."""
    cfg = config or ProviderConfig.from_env()
    cls = _PROVIDER_REGISTRY[cfg.provider]
    return cls(cfg)


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_FIRST_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> dict[str, Any]:
    """Robust JSON extractor for LLM output (handles fences, preamble, raw)."""
    if not text or not text.strip():
        raise ValueError("empty LLM response")

    candidates: list[str] = []
    for match in _JSON_BLOCK_RE.finditer(text):
        candidates.append(match.group(1).strip())
    if not candidates:
        m = _FIRST_OBJECT_RE.search(text)
        if m:
            candidates.append(m.group(0))
    candidates.append(text.strip())

    last_error: Exception | None = None
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
    raise ValueError(f"no JSON object found in LLM response: {last_error}")


__all__ = [
    "BaseLLMClient",
    "LLMProvider",
    "LMStudioProvider",
    "LlamaCppProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    "ProviderConfig",
    "ProviderResult",
    "ProviderUnavailable",
    "VLLMProvider",
    "extract_json",
    "select_provider",
]
