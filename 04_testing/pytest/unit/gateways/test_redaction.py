"""Phase 3.3 redaction contract tests."""

from __future__ import annotations

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
