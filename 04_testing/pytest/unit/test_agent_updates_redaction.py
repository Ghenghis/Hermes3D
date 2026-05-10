"""P1-8 F3 (2026-05-09): consolidation pin for ``agent_updates`` redaction.

Earlier ``hermes3d.api.routes.agent_updates`` carried its own
``SECRET_RE`` regex and ``_redact()`` helper. That local pattern was
*materially weaker* than ``hermes3d.gateways.redaction.redact_text``:

- no JWT shape (``eyJ...``)
- no Anthropic / OpenAI key shape (``sk-ant-...`` / ``sk-...``)
- no ``Authorization: Bearer ...`` header redaction
- no JSON ``"token": "..."`` field redaction
- no email / IPv4 / Windows-path / POSIX-path masking
- no base64 / long-token blob redaction

The F3 fix (a) hardens ``redact_text`` to subsume the three shapes the
local ``SECRET_RE`` *did* catch (``Bearer xxx``, ``?token=val`` /
``&access_token=val``, ``ALLCAPS_KEY=val``) and (b) deletes the local
helpers so this module routes 100% of secret masking through the
single hardened chain. This file pins both halves so a future refactor
cannot silently re-introduce the asymmetry.

References:
- OWASP A09:2021 Security Logging and Monitoring Failures —
  https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/
- Google re2 syntax (Python ``re`` is a near-subset) —
  https://github.com/google/re2/wiki/Syntax
- Sentry data-management single-redaction-hook pattern —
  https://docs.sentry.io/platforms/python/data-management/sensitive-data/
"""

from __future__ import annotations

import inspect
import re

import pytest

from hermes3d.api.routes import agent_updates
from hermes3d.gateways.redaction import redact_text


# ---------------------------------------------------------------------------
# Source-level pin: the local SECRET_RE + _redact must be gone.
# ---------------------------------------------------------------------------


def test_agent_updates_module_has_no_local_secret_re() -> None:
    """The module-level ``SECRET_RE`` symbol must not exist any more."""
    assert not hasattr(agent_updates, "SECRET_RE"), (
        "F3 regression: agent_updates.SECRET_RE re-introduced. The local "
        "regex was deleted to route all redaction through redact_text."
    )


def test_agent_updates_module_has_no_local_redact_helper() -> None:
    """The module-level ``_redact`` helper must not exist any more."""
    assert not hasattr(agent_updates, "_redact"), (
        "F3 regression: agent_updates._redact re-introduced. The local "
        "helper was deleted to route all redaction through redact_text."
    )


def test_agent_updates_imports_redact_text() -> None:
    """``redact_text`` must be importable on the module."""
    assert hasattr(agent_updates, "redact_text"), (
        "F3 regression: agent_updates.redact_text import is missing. "
        "Every redaction call site depends on it being in scope."
    )
    # And it must be the same function object as the gateway export
    # (catches the case where someone redefined a local stub).
    assert agent_updates.redact_text is redact_text, (
        "F3 regression: agent_updates.redact_text is shadowed by a "
        "module-local definition; consolidation is broken."
    )


def test_agent_updates_source_has_no_secret_re_or_redact_call() -> None:
    """Source-level pin: ``SECRET_RE`` must not appear in source text
    (except in our explanatory historical comment), and there must be
    no bare ``_redact(...)`` call on RHS — every redaction MUST go
    through ``redact_text(...)``.
    """
    src = inspect.getsource(agent_updates)

    # Allow ONLY the historical comment lines that mention the deleted
    # symbol; reject any executable usage. We strip lines that are
    # clearly comments (start with optional whitespace + ``#``).
    code_only = "\n".join(
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "SECRET_RE" not in code_only, (
        "F3 regression: SECRET_RE re-introduced in executable code "
        "(allowed only inside historical comments)."
    )

    # No bare ``_redact(`` call (the function is gone). The substring
    # ``redact_text(`` is fine — that's the gateway helper; we just
    # need to ensure the legacy local helper isn't called any more.
    # Use a regex with negative lookbehind so ``redact_text(`` does
    # NOT match (it has 'redact_text' before the '(' which is not
    # ``_redact``).
    legacy_call_re = re.compile(r"(?<![_a-zA-Z0-9])_redact\(")
    matches = legacy_call_re.findall(code_only)
    assert not matches, (
        f"F3 regression: legacy _redact() call site(s) found: {len(matches)}"
    )


# ---------------------------------------------------------------------------
# Behavioural pin: every shape the legacy SECRET_RE caught is now
# masked end-to-end through redact_text — covered by the corpus in
# tests/unit/gateways/test_redaction.py. This file additionally pins
# the public-facing surface of agent_updates (``_proof_summary`` /
# ``_run_git`` error path) so a refactor that silently dropped the
# import would fail here too.
# ---------------------------------------------------------------------------


def test_proof_summary_redacts_check_output_via_redact_text() -> None:
    """``_proof_summary`` should funnel each ``check.output`` through
    ``redact_text`` and truncate to 180 chars (``output_head``).
    """
    secret_payload = (
        "MY_API_KEY=fake_value_for_test "
        "Bearer abcdefghij1234 "
        "?token=zzz_synthetic"
    )
    payload = {
        "checks": [
            {
                "name": "stub gate",
                "status": "fail",
                "output": secret_payload,
            }
        ]
    }
    summary = agent_updates._proof_summary(payload)

    head = summary["checks"][0]["output_head"]
    # The original secrets must not survive in cleartext.
    assert "fake_value_for_test" not in head
    assert "abcdefghij1234" not in head
    assert "zzz_synthetic" not in head
    # Length cap honoured.
    assert len(head) <= 180


def test_proof_summary_redacts_steps_check_output_via_redact_text() -> None:
    """The same redaction must apply to the ``steps[*].checks`` shape."""
    payload = {
        "steps": [
            {
                "tag": "v2026.5.8",
                "ok": False,
                "checks": [
                    {
                        "name": "stub",
                        "status": "fail",
                        "output": "OPENAI_API_KEY=fake_synthetic_value_zzzz",
                    }
                ],
            }
        ]
    }
    summary = agent_updates._proof_summary(payload)

    step_check = summary["steps"][0]["checks"][0]
    assert "fake_synthetic_value_zzzz" not in step_check["output_head"]
    assert len(step_check["output_head"]) <= 180


@pytest.mark.parametrize(
    "raw, must_not_contain",
    [
        ("MY_API_KEY=fake_value_for_test", "fake_value_for_test"),
        ("Bearer abcdefghij_synthetic", "abcdefghij_synthetic"),
        ("/v1?token=tok_synthetic", "tok_synthetic"),
        ("call &access_token=tk_synthetic", "tk_synthetic"),
        ("Authorization: Bearer eyJabc.eyJdef.signature", "eyJabc.eyJdef.signature"),
    ],
)
def test_redact_text_handles_legacy_secret_shapes(raw: str, must_not_contain: str) -> None:
    """Every shape the legacy ``SECRET_RE`` caught must still be
    masked via ``redact_text``."""
    out = redact_text(raw)

    assert must_not_contain not in out, (
        f"F3 regression: redact_text leaked {must_not_contain!r} in {out!r}"
    )
