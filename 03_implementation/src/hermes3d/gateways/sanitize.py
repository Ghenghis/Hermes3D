"""Prompt sanitizer for the Phase 3.3 LLM gateway."""

from __future__ import annotations

import re

from hermes3d.orchestration.types import Err, Ok, Result

from .redaction import redact_text

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WIN_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s\"'<>]+")
_POSIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|root|Users)/[^\s\"'<>]+")
_WHITESPACE_RE = re.compile(r"\s+")
_INJECTION_RE = re.compile(
    r"ignore (?:all )?previous instructions|"
    r"disregard (?:the )?(?:system|safety) (?:prompt|policy)|"
    r"you are now|"
    r"pretend (?:to be|you are)",
    re.IGNORECASE,
)
_ROLE_SENTINEL_RE = re.compile(
    r"^\s*(?:system|assistant|tool|function)\s*:|<\|system\|>|<\|assistant\|>",
    re.IGNORECASE | re.MULTILINE,
)
_DAG_SENTINEL_RE = re.compile(r'\{\s*"nodes"\s*:|"tool"\s*:\s*"printer\.write"', re.IGNORECASE)


def sanitize_prompt(prompt: str, *, prompt_max_bytes: int) -> Result[str]:
    """Return sanitized prompt text or a refusal error."""

    if prompt_max_bytes < 1:
        return Err("PromptTooLarge", "prompt_max_bytes must be positive")
    utf8_safe = prompt.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    if _INJECTION_RE.search(utf8_safe):
        return Err("PromptRejected", "injection_marker")
    if _ROLE_SENTINEL_RE.search(utf8_safe):
        return Err("PromptRejected", "role_or_system_sentinel")
    if _DAG_SENTINEL_RE.search(utf8_safe):
        return Err("PromptRejected", "dag_sentinel")

    sanitized = _CONTROL_RE.sub(" ", utf8_safe)
    sanitized = _WIN_PATH_RE.sub(" ", sanitized)
    sanitized = _POSIX_PATH_RE.sub(" ", sanitized)
    sanitized = redact_text(sanitized)
    sanitized = _WHITESPACE_RE.sub(" ", sanitized).strip()
    if len(sanitized.encode("utf-8")) > prompt_max_bytes:
        return Err("PromptTooLarge", "prompt exceeds prompt_max_bytes")
    return Ok(sanitized, "prompt sanitized")
