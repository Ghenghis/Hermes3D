"""W21-A4 MVP-1 — unit tests for ``hermes3d.config.env_loader``.

Mission: prove the env-file loader honors its contract:
  1. Reads KEY=value pairs from a real .env file.
  2. Skips lines that are blank, comments, malformed, or have non-identifier keys.
  3. Strips surrounding single/double quotes on values.
  4. Honors ``override=False`` semantics (existing env wins).
  5. Honors ``HERMES3D_ENV_FILES`` override.
  6. Never logs values — return report only contains key NAMES.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from hermes3d.config.env_loader import (
    DEFAULT_ENV_FILES,
    _candidate_files,
    _parse_env_file,
    load_at_startup,
)

# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------


def test_parse_simple_key_value(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("FOO=bar\nBAZ=qux\n", encoding="utf-8")
    parsed = _parse_env_file(env)
    assert parsed == {"FOO": "bar", "BAZ": "qux"}


def test_parse_strips_double_quoted_value(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text('FOO="has spaces"\n', encoding="utf-8")
    parsed = _parse_env_file(env)
    assert parsed == {"FOO": "has spaces"}


def test_parse_strips_single_quoted_value(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("FOO='single-quoted'\n", encoding="utf-8")
    parsed = _parse_env_file(env)
    assert parsed == {"FOO": "single-quoted"}


def test_parse_skips_comments_and_blank(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("# header\n\nFOO=bar\n# trailing\n", encoding="utf-8")
    parsed = _parse_env_file(env)
    assert parsed == {"FOO": "bar"}


def test_parse_trims_inline_comment_only_when_unquoted(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text(
        'NOTE=hello # trailing\nQUOTED="value # not a comment"\n',
        encoding="utf-8",
    )
    parsed = _parse_env_file(env)
    assert parsed["NOTE"] == "hello"
    assert parsed["QUOTED"] == "value # not a comment"


def test_parse_rejects_non_identifier_keys(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("BAD-KEY=value\nGOOD_KEY=value\n", encoding="utf-8")
    parsed = _parse_env_file(env)
    assert "BAD-KEY" not in parsed
    assert parsed["GOOD_KEY"] == "value"


def test_parse_handles_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.env"
    parsed = _parse_env_file(missing)
    assert parsed == {}


# ---------------------------------------------------------------------------
# load_at_startup behavior
# ---------------------------------------------------------------------------


def test_load_at_startup_applies_new_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A fresh env var must be applied to os.environ."""
    env = tmp_path / ".env"
    env.write_text("W21_A4_TEST_NEW_KEY=sentinel_value\n", encoding="utf-8")
    monkeypatch.delenv("W21_A4_TEST_NEW_KEY", raising=False)

    report = load_at_startup(candidates=[env])
    assert "W21_A4_TEST_NEW_KEY" in report["applied"]
    assert os.environ.get("W21_A4_TEST_NEW_KEY") == "sentinel_value"


def test_load_at_startup_respects_existing_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a key is already set, the file MUST NOT override it (contract)."""
    env = tmp_path / ".env"
    env.write_text("W21_A4_TEST_EXISTING=from_file\n", encoding="utf-8")
    monkeypatch.setenv("W21_A4_TEST_EXISTING", "from_env")

    report = load_at_startup(candidates=[env])
    assert "W21_A4_TEST_EXISTING" in report["skipped_set"]
    assert os.environ["W21_A4_TEST_EXISTING"] == "from_env"


def test_load_at_startup_override_true_replaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """override=True must overwrite an existing env entry."""
    env = tmp_path / ".env"
    env.write_text("W21_A4_TEST_OVERRIDE=from_file\n", encoding="utf-8")
    monkeypatch.setenv("W21_A4_TEST_OVERRIDE", "from_env")

    report = load_at_startup(candidates=[env], override=True)
    assert "W21_A4_TEST_OVERRIDE" in report["applied"]
    assert os.environ["W21_A4_TEST_OVERRIDE"] == "from_file"


def test_load_at_startup_records_missing_files(tmp_path: Path) -> None:
    missing = tmp_path / "absent.env"
    report = load_at_startup(candidates=[missing])
    assert str(missing) in report["files_missing"]
    assert report["applied"] == []


def test_load_at_startup_honors_HERMES3D_ENV_FILES(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_a = tmp_path / "a.env"
    env_b = tmp_path / "b.env"
    env_a.write_text("W21_A4_FROM_A=from_a\n", encoding="utf-8")
    env_b.write_text("W21_A4_FROM_B=from_b\n", encoding="utf-8")
    monkeypatch.delenv("W21_A4_FROM_A", raising=False)
    monkeypatch.delenv("W21_A4_FROM_B", raising=False)
    monkeypatch.setenv("HERMES3D_ENV_FILES", f"{env_a};{env_b}")

    # candidate_files reads the env var; the resolved list must be those two.
    resolved = _candidate_files()
    assert resolved == [env_a, env_b]

    report = load_at_startup()
    assert "W21_A4_FROM_A" in report["applied"]
    assert "W21_A4_FROM_B" in report["applied"]
    assert os.environ["W21_A4_FROM_A"] == "from_a"
    assert os.environ["W21_A4_FROM_B"] == "from_b"


def test_load_at_startup_returns_keys_only_never_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Critical security property: the report must NEVER carry the
    secret value, only the key name. This guards against logs leaking
    credentials when verbose logging is enabled in production."""
    env = tmp_path / ".env"
    env.write_text("SECRET_VALUE=super_secret_payload_DO_NOT_LEAK\n", encoding="utf-8")
    monkeypatch.delenv("SECRET_VALUE", raising=False)

    report = load_at_startup(candidates=[env])
    flat = repr(report)
    assert "super_secret_payload_DO_NOT_LEAK" not in flat
    assert "SECRET_VALUE" in report["applied"]


# ---------------------------------------------------------------------------
# Default file list sanity
# ---------------------------------------------------------------------------


def test_default_env_files_includes_private_secret_path() -> None:
    """Per the operator secret-storage convention, G:\\private\\.env must be
    in the default lookup list. The 2026-05-03 .env.txt screenshot incident
    documented why .env files MUST live outside the repo."""
    assert any(r"G:\private" in candidate for candidate in DEFAULT_ENV_FILES)
