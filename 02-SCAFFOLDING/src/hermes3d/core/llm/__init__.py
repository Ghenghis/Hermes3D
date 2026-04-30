"""Hermes3D local LLM bridges (Ollama-first)."""
from .ollama_client import (
    DEFAULT_BASE_URL, DEFAULT_MODEL,
    OllamaClient, OllamaResponse, OllamaUnavailable,
)

__all__ = [
    "DEFAULT_BASE_URL", "DEFAULT_MODEL",
    "OllamaClient", "OllamaResponse", "OllamaUnavailable",
]
