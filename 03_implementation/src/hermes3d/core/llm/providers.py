"""LLM provider abstraction.

Hermes3D-OS is local-first by default but supports multiple backends so the
fleet brain can keep running even if one provider is down. All providers share
the same shape (``generate(prompt) -> ProviderResult``) and the same JSON
extraction helper, so every agentic module (multi_agent, failure_predictor,
quality_scorer, etc.) is provider-agnostic.

Supported backends (offline-tested):
- ``lmstudio``     : http://127.0.0.1:1234   (default, LM Studio OpenAI-compat)
- ``ollama``       : http://127.0.0.1:11434  (fallback, fully local)
- ``vllm``         : http://127.0.0.1:8000   (vLLM OpenAI-compat server)
- ``llamacpp``     : http://127.0.0.1:8080   (llama.cpp ``server`` binary)
- ``hipfire``      : http://127.0.0.1:11435  (optional AMD-node helper, gated
                                              by ``HERMES3D_AMD_NODE=1``)
- ``openrouter``   : https://openrouter.ai/api/v1  (optional, requires key)

Selection happens via ``HERMES3D_LLM_PROVIDER`` env var (default: ``lmstudio``)
or programmatically via ``select_provider``. See ADR-015 for the local-first
provider chain rationale (LM Studio default + Ollama fallback + Hipfire opt-in).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"
    VLLM = "vllm"
    LLAMACPP = "llamacpp"
    HIPFIRE = "hipfire"
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
    def from_env(cls) -> ProviderConfig:
        # Default switched from "ollama" to "lmstudio" per ADR-015 (LM Studio
        # ships a discoverable on-ramp + tool-calling friendly UI; Ollama is
        # still a first-class fallback via select_provider_with_fallback).
        provider = LLMProvider(os.getenv("HERMES3D_LLM_PROVIDER", "lmstudio").lower())
        defaults = {
            LLMProvider.OLLAMA: ("http://127.0.0.1:11434", "qwen2.5-coder:7b"),
            LLMProvider.LMSTUDIO: ("http://127.0.0.1:1234/v1", "local-model"),
            LLMProvider.VLLM: ("http://127.0.0.1:8000/v1", "Qwen/Qwen2.5-7B-Instruct"),
            LLMProvider.LLAMACPP: ("http://127.0.0.1:8080", "llama"),
            LLMProvider.HIPFIRE: ("http://127.0.0.1:11435/v1", "local-model"),
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
    """LM Studio's OpenAI-compatible server (default at :1234/v1).

    Inherits the standard health probe (``GET /v1/models``) and the
    non-streaming chat-completions call from ``_OpenAICompatProvider``.
    Adds optional streaming + tool-calling helpers used by agentic modules
    that need richer control surface.

    LM Studio is the Hermes3D-OS default local provider per ADR-015: it
    ships a discoverable model picker + GUI install flow, while still
    speaking the same OpenAI-compat API every other backend in this
    module uses.
    """

    def stream(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> Iterator[str]:
        """Yield partial chunks from /v1/chat/completions with stream=true.

        Each yielded value is the delta ``content`` substring, so the
        caller can concatenate them or render them as a typewriter feed.
        Errors are normalized to ``ProviderUnavailable`` like ``generate``.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "stream": True,
        }
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        try:
            with httpx.stream(
                "POST",
                f"{self.config.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
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
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"lmstudio stream unreachable at {self.config.base_url}: {exc}"
            ) from exc

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        tool_choice: str | dict[str, Any] = "auto",
    ) -> dict[str, Any]:
        """OpenAI-compat tool-calling roundtrip.

        Returns the raw API response so the caller can inspect any
        ``tool_calls`` on ``choices[0].message`` and dispatch them.
        """
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "stream": False,
            "tools": tools,
            "tool_choice": tool_choice,
        }
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                resp = client.post(
                    f"{self.config.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(
                f"lmstudio tool-call unreachable at {self.config.base_url}: {exc}"
            ) from exc


class VLLMProvider(_OpenAICompatProvider):
    pass


class HipfireProvider(_OpenAICompatProvider):
    """Optional AMD-node Hipfire helper (OpenAI-compat at :11435/v1).

    Hipfire is the on-box AMD inference helper used on the dedicated AMD
    workstation in the lab. It is **not** a default: instantiation refuses
    unless ``HERMES3D_AMD_NODE=1`` is set in the environment. This guard
    keeps a stray ``HERMES3D_LLM_PROVIDER=hipfire`` from silently routing
    a developer laptop's traffic to a port that won't answer.
    """

    def __init__(self, config: ProviderConfig) -> None:
        if os.environ.get("HERMES3D_AMD_NODE") != "1":
            raise ProviderUnavailable(
                "Hipfire selected but HERMES3D_AMD_NODE is not set to '1'. "
                "This provider is restricted to the AMD inference node."
            )
        super().__init__(config)


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
    LLMProvider.HIPFIRE: HipfireProvider,
    LLMProvider.OPENROUTER: OpenRouterProvider,
}


def select_provider(config: ProviderConfig | None = None) -> BaseLLMClient:
    """Construct the configured provider. Read env if ``config`` omitted."""
    cfg = config or ProviderConfig.from_env()
    cls = _PROVIDER_REGISTRY[cfg.provider]
    return cls(cfg)


# Default chain consumed by ``select_provider_with_fallback`` per ADR-015 §1.
# Order: lm_studio → ollama → hipfire (the latter only constructs when
# ``HERMES3D_AMD_NODE=1``; it is silently skipped otherwise).
DEFAULT_PROVIDER_CHAIN: tuple[LLMProvider, ...] = (
    LLMProvider.LMSTUDIO,
    LLMProvider.OLLAMA,
    LLMProvider.HIPFIRE,
)


def _config_for(provider: LLMProvider) -> ProviderConfig:
    """Build a ProviderConfig for a chain member using its baked-in default
    base URL + model. Used by ``select_provider_with_fallback`` to walk the
    chain without forcing the caller to pre-build configs for every entry.
    """
    defaults: dict[LLMProvider, tuple[str, str]] = {
        LLMProvider.OLLAMA: ("http://127.0.0.1:11434", "qwen2.5-coder:7b"),
        LLMProvider.LMSTUDIO: ("http://127.0.0.1:1234/v1", "local-model"),
        LLMProvider.VLLM: ("http://127.0.0.1:8000/v1", "Qwen/Qwen2.5-7B-Instruct"),
        LLMProvider.LLAMACPP: ("http://127.0.0.1:8080", "llama"),
        LLMProvider.HIPFIRE: ("http://127.0.0.1:11435/v1", "local-model"),
        LLMProvider.OPENROUTER: (
            "https://openrouter.ai/api/v1",
            "qwen/qwen-2.5-coder-32b-instruct",
        ),
    }
    base_url, model = defaults[provider]
    return ProviderConfig(
        provider=provider,
        base_url=base_url,
        model=model,
        api_key=os.getenv("HERMES3D_LLM_API_KEY"),
        timeout_seconds=float(os.getenv("HERMES3D_LLM_TIMEOUT", "60")),
        temperature=float(os.getenv("HERMES3D_LLM_TEMPERATURE", "0.2")),
    )


def select_provider_with_fallback(
    chain: tuple[LLMProvider, ...] | None = None,
    *,
    require_health: bool = True,
) -> BaseLLMClient:
    """Walk a provider chain and return the first reachable backend.

    Resolution order (per ADR-015 §1):

      1. ``HERMES3D_LLM_PROVIDER`` is honored if set — that single provider
         is returned directly via :func:`select_provider`. (No silent
         fallback when the operator pinned a provider.)
      2. Otherwise, walk ``chain`` (default: ``DEFAULT_PROVIDER_CHAIN``).
         For each entry, try to construct the client. Skip silently on
         :class:`ProviderUnavailable` (e.g., Hipfire's env gate). When
         ``require_health`` is true, also call ``available()`` and skip if
         the backend isn't reachable on its loopback port.
      3. If every entry in the chain is unreachable, raise
         ``ProviderUnavailable`` with a summary of what was tried.

    Streaming + tool-calling consumers should still construct the
    LM Studio client directly — this helper is for the agentic modules
    (multi_agent, repair_agent, failure_predictor) that currently call
    :func:`select_provider` with no fallback.
    """
    if os.getenv("HERMES3D_LLM_PROVIDER"):
        # Explicit pin: caller wants a specific provider; don't second-guess.
        return select_provider()

    chain = chain or DEFAULT_PROVIDER_CHAIN
    attempts: list[str] = []
    for provider in chain:
        try:
            client = select_provider(_config_for(provider))
        except ProviderUnavailable as exc:
            attempts.append(f"{provider.value}: refused at construct ({exc})")
            continue
        if not require_health:
            return client
        if client.available():
            return client
        attempts.append(f"{provider.value}: unreachable at {client.config.base_url}")
    raise ProviderUnavailable("no provider in chain is reachable: " + "; ".join(attempts))


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
    "DEFAULT_PROVIDER_CHAIN",
    "BaseLLMClient",
    "HipfireProvider",
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
    "select_provider_with_fallback",
]
