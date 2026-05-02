"""Prompt sanitizer for the Phase 3.3 offline LLM gateway."""

from __future__ import annotations

import re

from .llm_redactor import redact_text

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WIN_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s\"'<>]+")
_POSIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|root|Users)/[^\s\"'<>]+")
_SECRET_HINT_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._\-+/=]{8,})\b",
    re.IGNORECASE,
)
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_prompt(prompt: str, *, prompt_max_bytes: int) -> str:
    """Return UTF-8 safe, bounded prompt text with local details stripped."""

    if prompt_max_bytes < 1:
        raise ValueError("prompt_max_bytes must be positive")

    safe = prompt.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    safe = _CONTROL_RE.sub(" ", safe)
    safe = _WIN_PATH_RE.sub(" ", safe)
    safe = _POSIX_PATH_RE.sub(" ", safe)
    safe = _SECRET_HINT_RE.sub(" ", safe)
    safe = redact_text(safe)
    safe = _WHITESPACE_RE.sub(" ", safe).strip()
    return _truncate_utf8(safe, prompt_max_bytes)


def _truncate_utf8(value: str, max_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip()
