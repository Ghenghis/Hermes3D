"""Phase 3.3 redaction contract tests.

P1-8 F3 (2026-05-09): added pattern coverage for ALLCAPS env-style
``KEY=VALUE`` pairs and bare URL query-strings (``?token=`` /
``&access_token=``) that the legacy ``hermes3d.api.routes.agent_updates``
local ``SECRET_RE`` caught but ``redact_text`` originally missed.

References:
- OWASP A09:2021 Security Logging and Monitoring Failures —
  https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/
- Google re2 syntax (Python ``re`` is a near-subset) —
  https://github.com/google/re2/wiki/Syntax
"""

from __future__ import annotations

import pytest
from hermes3d.gateways.redaction import redact_text


def test_api_keys_are_masked() -> None:
    redacted = redact_text("sk-abcdefghijklmnopqrstuvwxyz and sk-ant-abcdefghijklmnopqrstuvwxyz")

    assert "sk-abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "sk-ant-abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "sk-***" in redacted
    assert "sk-ant-***" in redacted


def test_bearer_tokens_are_masked() -> None:
    redacted = redact_text("Authorization: Bearer abcdefghijklmnop")

    assert "abcdefghijklmnop" not in redacted
    assert "Authorization: ***" in redacted


def test_jwts_are_masked() -> None:
    redacted = redact_text("eyJabc.eyJdef.signature")

    assert redacted == "<JWT>"


def test_public_ipv4_masked_and_private_ipv4_kept() -> None:
    redacted = redact_text("8.8.8.8 192.168.0.24 10.1.2.3 172.16.4.5 127.0.0.1")

    assert "<IP>" in redacted
    assert "8.8.8.8" not in redacted
    assert "192.168.0.24" in redacted
    assert "10.1.2.3" in redacted
    assert "172.16.4.5" in redacted
    assert "127.0.0.1" in redacted


def test_paths_are_masked() -> None:
    redacted = redact_text(r"C:\Users\Admin\secret.txt /home/admin/secret.txt")

    assert "<WINPATH>" in redacted
    assert "<POSIXPATH>" in redacted
    assert "secret.txt" not in redacted


def test_header_values_are_masked() -> None:
    redacted = redact_text("X-Api-Key: abcdefgh Authorization: qwertyuiop")

    assert "abcdefgh" not in redacted
    assert "qwertyuiop" not in redacted
    assert "X-Api-Key: ***" in redacted
    assert "Authorization: ***" in redacted


def test_redaction_is_idempotent() -> None:
    first = redact_text("Bearer abcdefghijklmnop admin@example.com")
    second = redact_text(first)

    assert second == first


# ---------------------------------------------------------------------------
# P1-8 F3 hardening: ALLCAPS env-style KEY=VALUE coverage
# (subsumes the local ``SECRET_RE`` formerly in agent_updates.py)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected_field",
    [
        ("MY_API_KEY=fake_value_for_test", "MY_API_KEY"),
        ("ANTHROPIC_TOKEN=tok_abc_def", "ANTHROPIC_TOKEN"),
        ("OPENAI_API_KEY=fakefakefakefake", "OPENAI_API_KEY"),
        ("GITHUB_TOKEN=ghp_synthetic_test_value", "GITHUB_TOKEN"),
        ("PASSWORD=hunter2", "PASSWORD"),
        ("CLIENT_SECRET=foo_synthetic", "CLIENT_SECRET"),
        ("AUTH_TOKEN=bearerlike_value", "AUTH_TOKEN"),
        ("AWS_CREDENTIAL=blob_value", "AWS_CREDENTIAL"),
        ("PWD=fake_pwd", "PWD"),
        ("PASSWD=fake_passwd", "PASSWD"),
    ],
)
def test_env_style_secret_kv_is_redacted(raw: str, expected_field: str) -> None:
    redacted = redact_text(raw)

    # Field name preserved, value replaced with ``<redacted>``.
    assert redacted.startswith(f"{expected_field}=")
    assert "<redacted>" in redacted, f"value not redacted for {raw!r}: got {redacted!r}"
    # Original value substring should be gone.
    original_value = raw.split("=", 1)[1]
    assert original_value not in redacted, f"original value still present in {redacted!r}"


@pytest.mark.parametrize(
    "raw",
    [
        # Prose-shaped — does NOT end in a pinned secret suffix.
        "MAYBE_CHECKED=true",
        "BLOCK_RE=ignored",
        "no_secret_here=just_data",
        "REGULAR_VAR=value",
        # ``CHECKED`` is the suffix, not a secret token.
        "WAS_CHECKED=ok",
    ],
)
def test_env_style_non_secret_kv_is_not_redacted(raw: str) -> None:
    """Pinned suffix list keeps prose untouched."""
    redacted = redact_text(raw)

    assert redacted == raw, f"prose was incorrectly redacted: {raw!r} -> {redacted!r}"


# ---------------------------------------------------------------------------
# P1-8 F3 hardening: bare URL query-string secrets without an ``https?://``
# prefix (the legacy ``_URL_WITH_SECRET_RE`` only matched full URLs).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, leading",
    [
        ("?token=abcdefghij", "?token="),
        ("/api/v1?token=abcdef123", "?token="),
        ("/api/v1?api_key=secret_value", "?api_key="),
        ("&access_token=tk123", "&access_token="),
        ("path?secret=abc&other=def", "?secret="),
        ("path?token=abc&access_token=def", "?token="),
        ("logs/path?password=hunter2", "?password="),
    ],
)
def test_bare_query_string_secret_is_redacted(raw: str, leading: str) -> None:
    redacted = redact_text(raw)

    assert leading in redacted, f"key prefix lost: {redacted!r}"
    assert "<redacted>" in redacted, f"value not redacted for {raw!r}: got {redacted!r}"


def test_full_url_query_secret_still_uses_url_pattern() -> None:
    """A full ``https?://`` URL takes the URL pattern, not the bare-query
    pattern. Confirms the order-of-operations contract.
    """
    redacted = redact_text("https://api.example.com/v1?token=abc&other=xyz")

    # ``_URL_WITH_SECRET_RE`` collapses the entire query into ``<redacted-query>``.
    assert "?<redacted-query>" in redacted
    assert "abc" not in redacted


def test_bearer_outside_authorization_header_is_redacted() -> None:
    """Bare ``Bearer xxx`` in any context (URL, log line) must be redacted."""
    redacted = redact_text("dispatch sent Bearer myToken_synthetic over the wire")

    assert "myToken_synthetic" not in redacted
    assert "Bearer ***" in redacted


def test_mixed_case_env_secret_is_redacted() -> None:
    """``apikey=val`` (lowercase) — the case-insensitive flag must catch it."""
    redacted = redact_text("apikey=lowercaseval_synthetic")

    assert "lowercaseval_synthetic" not in redacted
    assert "<redacted>" in redacted


# ---------------------------------------------------------------------------
# P1-8 F3 fuzz / no-regression gate: every input the legacy ``SECRET_RE``
# redacted, the new ``redact_text`` must ALSO redact (at least the same
# substring or a larger range). This is the consolidation safety net —
# without this passing we cannot delete the local SECRET_RE.
# ---------------------------------------------------------------------------


# Frozen copy of the legacy ``SECRET_RE`` from agent_updates.py @ pre-F3
# tip, kept inline so the test does not depend on git history.
_LEGACY_SECRET_RE_PATTERN = (
    r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"
    r"|([?&](?:token|key|api_key|access_token)=)[^&\s]+"
    r"|([A-Za-z0-9_]*KEY=)[^\s]+"
)


def _legacy_redact(value: str) -> str:
    import re

    legacy = re.compile(_LEGACY_SECRET_RE_PATTERN)
    return legacy.sub(
        lambda match: f"{match.group(1) or match.group(2) or match.group(3) or ''}[REDACTED]",
        value,
    )


@pytest.mark.parametrize(
    "raw",
    [
        # ---- Bearer family ----
        "Bearer abcdefghij",
        "bearer abcdefghij",
        "Authorization: Bearer eyJabc.eyJdef.signature",
        "log line: Bearer myTOK_synthetic_value",
        # ---- bare query-string family ----
        "GET /api?token=secret_value",
        "POST /v1?api_key=mykey_test",
        "curl x.io?access_token=tk123",
        "/path?key=zzz",
        "/path?token=v1&access_token=v2",
        "?token=Z",
        # ---- ALLCAPS_KEY= family ----
        "MY_API_KEY=fake_value_for_test",
        "OPENAI_API_KEY=sk_synthetic_1234",
        "ANTHROPIC_API_KEY=sk-ant-synthetic-1234",
        "a_KEY=b",
        "GITHUB_KEY=gh_synthetic",
        "apikey=lowercaseval",  # case-insensitive KEY suffix in legacy
        # ---- mixed prose with embedded secrets ----
        "before MY_API_KEY=fake_value after",
        "GET /api?token=secret123 HTTP/1.1",
        "echo $BEARER_KEY=zzz",
        "header X-API-KEY=val123 trailing",
        # ---- bonus: legacy patterns that include a path/url tail ----
        "/path?token=zzz&extra=stuff",
        # ---- inputs that should be untouched by both ----
        "MAYBE_CHECKED=true",
        "BLOCK_RE=ignored",
        "no_secret_here=just_data",
        "RegularText",
        "safe_value=hello",
        "DATABASE_URL=postgres://example",
        # ---- corner cases ----
        "?token=",  # empty value — legacy still leaves the prefix only
        "Bearer ",  # bearer with no token (insufficient char run)
        # ---- non-ASCII / multi-line ----
        "log line 1\nMY_API_KEY=val_a\nlog line 3",
        # ---- lots of secrets in one line ----
        "Bearer abcdefghij ?token=zzz MY_API_KEY=fake",
    ],
)
def test_redact_text_no_regression_vs_legacy_secret_re(raw: str) -> None:
    """For every input the legacy ``SECRET_RE`` redacts, the new
    ``redact_text`` must ALSO produce a redacted output (different from
    input). The replacement TOKENS may differ — the contract is "secret
    no longer present in cleartext", not byte-equality.
    """
    legacy_out = _legacy_redact(raw)
    new_out = redact_text(raw)

    legacy_changed = legacy_out != raw
    new_changed = new_out != raw

    if legacy_changed and not new_changed:
        pytest.fail(
            "F3 regression: legacy SECRET_RE redacted but redact_text did not.\n"
            f"  raw    : {raw!r}\n"
            f"  legacy : {legacy_out!r}\n"
            f"  new    : {new_out!r}"
        )

    # When BOTH redact, ensure the new output really did remove the
    # secret tail (not just rewrite the prefix). Approximate test: the
    # redacted output must contain ``<redacted>``, ``[REDACTED]``-style,
    # or one of the existing redact_text tokens (``***``, ``<JWT>``,
    # ``<TOKEN>``, ``<B64>``, ``<EMAIL>``, ``<IP>``, ``<URL>``,
    # ``<WINPATH>``, ``<POSIXPATH>``, ``<redacted-query>``).
    if legacy_changed:
        markers = [
            "<redacted>",
            "***",
            "<JWT>",
            "<TOKEN>",
            "<B64>",
            "<EMAIL>",
            "<IP>",
            "<WINPATH>",
            "<POSIXPATH>",
            "<redacted-query>",
        ]
        assert any(m in new_out for m in markers), (
            f"redact_text changed output but no redaction marker found in {new_out!r}"
        )
