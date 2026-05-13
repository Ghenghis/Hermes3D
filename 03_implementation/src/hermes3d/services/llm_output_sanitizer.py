"""Shared cleanup for reasoning-aloud LLM responses."""

from __future__ import annotations

import re


def sanitize_reasoning_output(text: str | None) -> str:
    """Strip reasoning wrappers and whole-document fences from provider text."""

    if not text:
        return ""
    cleaned = str(text)
    cleaned = re.sub(r"<think>.*?</think>\s*", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    fence_match = re.match(
        r"\s*```(?:markdown|md)?\s*\n(.*?)\n```\s*\Z",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fence_match:
        cleaned = fence_match.group(1)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
