"""Redaction helpers for Phase 3.3 LLM planner traces.

P1-8 F3 hardening (2026-05-09): ``redact_text`` now subsumes the local
``SECRET_RE`` formerly defined in
``hermes3d.api.routes.agent_updates`` (and several sibling routes). The
local pattern caught three shapes the original ``redact_text`` missed:

1. ``bare Bearer xxx`` — actually already covered by ``_BEARER_RE``,
   retained here for documentation symmetry.
2. ``?token=val`` / ``&access_token=val`` URL query secrets WITHOUT an
   ``https?://`` prefix (e.g. extracted from a log line that quoted only
   the query-string slice).
3. ``MY_API_KEY=value`` ALLCAPS env-style key/value pairs in subprocess
   output, ``git`` errors, etc.

The new ``_BARE_QUERY_SECRET_RE`` and ``_ENV_SECRET_KV_RE`` patterns
close those gaps. Both run AFTER the more-specific URL/header/JSON
patterns to avoid double-redaction.

References:
- OWASP A09:2021 Security Logging and Monitoring Failures —
  https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/
- Google re2 syntax (Python ``re`` is a near-subset) —
  https://github.com/google/re2/wiki/Syntax
"""

from __future__ import annotations

import json
import re
from typing import Any

SECRET_FIELD_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "client_secret",
        "password",
        "secret",
        "token",
    }
)

_ANTHROPIC_KEY_RE = re.compile(r"\bsk-ant-[A-Za-z0-9_-]{16,}\b")
_OPENAI_KEY_RE = re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{16,}\b")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._\-+/=]{8,}\b", re.IGNORECASE)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_WIN_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s\"'<>]+")
_POSIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|root|Users)/[^\s\"'<>]+")
_HEADER_SECRET_RE = re.compile(
    r"\b(?P<header>X-Api-Key|Authorization)\s*:\s*(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)
_JSON_SECRET_FIELD_RE = re.compile(
    r'("(?P<key>api_?key|authorization|bearer|client_secret|password|secret|token)"\s*:\s*)"[^"]*"',
    re.IGNORECASE,
)
_URL_WITH_SECRET_RE = re.compile(
    r"\bhttps?://[^\s\"'<>]*(?:token|api[_-]?key|secret|password|signature)=[^\s\"'<>]+",
    re.IGNORECASE,
)
# P1-8 F3: bare URL query-string secret without an ``https?://`` prefix.
# Captures the leading ``?`` or ``&`` plus the key name so the replacement
# can keep the field name visible (e.g. ``?token=<redacted>``) — this is
# how the legacy local ``SECRET_RE`` rendered the redaction. Field names
# are pinned to the same set the legacy pattern recognised.
_BARE_QUERY_SECRET_RE = re.compile(
    r"(?P<sep>[?&])(?P<key>token|access_token|api_key|apikey|key|secret|password|signature)="
    r"(?P<value>[^&\s\"'<>]+)",
    re.IGNORECASE,
)
# P1-8 F3: ALLCAPS-style env / KEY=VALUE pairs in subprocess output and
# logs. Pinned to a SUFFIX list so prose like ``MAYBE_CHECKED=true`` does
# NOT match — must end in one of the secret-suffix tokens (case-insensitive)
# immediately followed by ``=`` (with optional whitespace). The captured
# value runs to the next whitespace, end-of-string, or quote.
_ENV_SECRET_KV_RE = re.compile(
    r"(?P<name>\b[A-Za-z0-9_]*"
    r"(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|PWD|APIKEY|API_KEY|AUTH|CREDENTIAL|CREDENTIALS)"
    r")\s*=\s*"
    r"(?P<value>[^\s\"'<>]+)",
    re.IGNORECASE,
)
_BASE64_BLOB_RE = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{80,}={0,2}(?![A-Za-z0-9+/=])")
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9._\-]{257,}\b")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def redact_text(text: str) -> str:
    """Mask secrets and host-local details from text.

    Patterns run most-specific-first so that, for example, an
    ``Authorization: Bearer xxx`` header is consumed by
    ``_HEADER_SECRET_RE`` before the standalone ``_BEARER_RE`` sees it.
    The new P1-8 F3 patterns
    (``_BARE_QUERY_SECRET_RE`` / ``_ENV_SECRET_KV_RE``) run AFTER
    ``_URL_WITH_SECRET_RE`` so a full ``https://...?token=`` URL is
    rendered as ``...?<redacted-query>`` rather than getting the value
    pass swapped twice.
    """

    redacted = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    redacted = _ANTHROPIC_KEY_RE.sub("sk-ant-***", redacted)
    redacted = _OPENAI_KEY_RE.sub("sk-***", redacted)
    redacted = _BEARER_RE.sub("Bearer ***", redacted)
    redacted = _JWT_RE.sub("<JWT>", redacted)
    redacted = _HEADER_SECRET_RE.sub(lambda match: f"{match.group('header')}: ***", redacted)
    redacted = _JSON_SECRET_FIELD_RE.sub(lambda match: f'{match.group(1)}"***"', redacted)
    redacted = _URL_WITH_SECRET_RE.sub(_redact_url_query, redacted)
    # P1-8 F3 additions — run after URL/header/JSON so they only see
    # bare query-strings and env-style KEY=VALUE pairs that the
    # specific patterns above did not consume.
    redacted = _BARE_QUERY_SECRET_RE.sub(
        lambda match: f"{match.group('sep')}{match.group('key')}=<redacted>",
        redacted,
    )
    redacted = _ENV_SECRET_KV_RE.sub(
        lambda match: f"{match.group('name')}=<redacted>",
        redacted,
    )
    redacted = _EMAIL_RE.sub("<EMAIL>", redacted)
    redacted = _WIN_PATH_RE.sub("<WINPATH>", redacted)
    redacted = _POSIX_PATH_RE.sub("<POSIXPATH>", redacted)
    redacted = _IPV4_RE.sub(_redact_public_ipv4, redacted)
    redacted = _BASE64_BLOB_RE.sub("<B64>", redacted)
    return _LONG_TOKEN_RE.sub("<TOKEN>", redacted)


def redact_json(value: Any) -> Any:
    """Recursively redact JSON-like data."""

    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list | tuple):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            normalized_key = key_text.lower().replace("-", "_")
            result[key_text] = "***" if normalized_key in SECRET_FIELD_NAMES else redact_json(item)
        return result
    return value


def redacted_json_dumps(value: Any) -> str:
    """Return deterministic redacted JSON."""

    return json.dumps(redact_json(value), sort_keys=True, separators=(",", ":"))


def _redact_url_query(match: re.Match[str]) -> str:
    url = match.group(0)
    if "?" not in url:
        return "<URL>"
    return f"{url.split('?', 1)[0]}?<redacted-query>"


def _redact_public_ipv4(match: re.Match[str]) -> str:
    value = match.group(0)
    octets = value.split(".")
    if not _valid_ipv4_octets(octets):
        return value
    first = int(octets[0])
    second = int(octets[1])
    if first == 10 or first == 127:
        return value
    if first == 192 and second == 168:
        return value
    if first == 172 and 16 <= second <= 31:
        return value
    return "<IP>"


def _valid_ipv4_octets(octets: list[str]) -> bool:
    return len(octets) == 4 and all(octet.isdigit() and 0 <= int(octet) <= 255 for octet in octets)
