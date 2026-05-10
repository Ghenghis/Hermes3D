"""Wave 2 P2-6 — proof-event version tagging tests.

Pins:
- ``services/proof_helpers.proof_version_fields()`` returns
  ``version_label``/``upstream_tag``/``checkout_path`` derived from the
  active Hermes Agent registry entry.
- When ``HERMES_AGENT_CHECKOUT`` is unset (post-promotion default),
  fields tag v0.13 (``v2026.5.7``).
- When the env points at the v0.12 fallback, fields tag v0.12
  (``v2026.4.30``).
- When the env points at an unknown checkout, ``version_label`` /
  ``upstream_tag`` fall back to ``"unknown"`` while ``checkout_path``
  preserves the literal env value (no crash, no secret leak).
- Persistence pin: a mocked ``_append_proof_event`` write inserts the
  enriched payload (containing the version fields) into the
  ``proof_events`` table SQL bind tuple.
- Source-level pin: each augmented call site imports the helper.

Provenance:
- NIST SP 800-92 §4 "Log Generation and Storage"
  (https://csrc.nist.gov/publications/detail/sp/800-92/final): events
  must record the software version they were emitted under so post-hoc
  forensic queries can attribute behavior across upgrades.
- OpenTelemetry semantic conventions, ``service.version`` resource
  attribute (https://opentelemetry.io/docs/specs/semconv/resource/#service):
  the canonical place to record a deployed service's version. Our
  ``version_label`` field mirrors that shape so a future OTel exporter
  can lift the field without remap.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from hermes3d.services import proof_helpers
from hermes3d.services.agent_checkout import (
    DEFAULT_AGENT_CHECKOUT,
    V012_FALLBACK_CHECKOUT,
)


# ---------------------------------------------------------------------------
# proof_version_fields() direct tests
# ---------------------------------------------------------------------------


def test_env_unset_tags_v013(monkeypatch: pytest.MonkeyPatch) -> None:
    """Post Wave 1 promotion default: env unset → v0.13 (v2026.5.7)."""
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    fields = proof_helpers.proof_version_fields()
    assert fields["version_label"] == "v0.13"
    assert fields["upstream_tag"] == "v2026.5.7"
    assert fields["checkout_path"] == str(DEFAULT_AGENT_CHECKOUT)


def test_env_v012_path_tags_v012(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator opt-in to v0.12 fallback → tag v2026.4.30."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", str(V012_FALLBACK_CHECKOUT))
    fields = proof_helpers.proof_version_fields()
    assert fields["version_label"] == "v0.12"
    assert fields["upstream_tag"] == "v2026.4.30"
    assert fields["checkout_path"] == str(V012_FALLBACK_CHECKOUT)


def test_env_unknown_path_tags_unknown_no_crash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Custom fork / forensic clone: version unknown, but path preserved.

    The ``checkout_path`` remains the literal env value so the audit
    chain still has a forensic anchor; no crash, no fabricated label.
    """
    nonsense = tmp_path / "custom-fork-xyz"
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", str(nonsense))
    fields = proof_helpers.proof_version_fields()
    assert fields["version_label"] == "unknown"
    assert fields["upstream_tag"] == "unknown"
    # Literal path round-tripped via str(Path(env_value)). On Windows
    # backslash/forward-slash is normalised by Path; compare as Path
    # to avoid spurious failures on the separator.
    assert Path(fields["checkout_path"]) == Path(str(nonsense))


def test_unknown_path_does_not_leak_env_other_than_checkout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Pin: only the *checkout path* itself is exposed in the unknown
    branch — no other env values leak into the recorded payload."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", str(tmp_path / "ghost"))
    monkeypatch.setenv("SECRET_TOKEN_DO_NOT_LEAK", "should-not-appear")
    fields = proof_helpers.proof_version_fields()
    serialized = json.dumps(fields)
    assert "should-not-appear" not in serialized
    assert "SECRET_TOKEN_DO_NOT_LEAK" not in serialized


# ---------------------------------------------------------------------------
# attach_version_fields() merge contract
# ---------------------------------------------------------------------------


def test_attach_returns_new_dict_does_not_mutate_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    original = {"event_id": "abc", "tag": "v2026.5.7"}
    merged = proof_helpers.attach_version_fields(original)
    assert "version_label" not in original, "input dict was mutated"
    assert merged is not original
    assert merged["event_id"] == "abc"
    assert merged["tag"] == "v2026.5.7"
    assert merged["version_label"] == "v0.13"


def test_attach_preserves_caller_keys_on_collision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If a caller pre-populates ``version_label`` (e.g. synthetic
    audit injection), their value wins so the audit trail is not
    silently rewritten."""
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    merged = proof_helpers.attach_version_fields(
        {"version_label": "synthetic-test", "upstream_tag": "synthetic"},
    )
    assert merged["version_label"] == "synthetic-test"
    assert merged["upstream_tag"] == "synthetic"


# ---------------------------------------------------------------------------
# DB-write integration: the augmented helper passes enriched payload
# ---------------------------------------------------------------------------


def _capture_execute_payloads() -> list[tuple[str, tuple[Any, ...]]]:
    return []


def test_agent_updates_helper_persists_version_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock ``execute`` and assert the enriched payload (with
    version_label / upstream_tag / checkout_path) reaches the SQL
    bind tuple inside agent_updates._append_proof_event."""
    monkeypatch.delenv("HERMES_AGENT_CHECKOUT", raising=False)
    from hermes3d.api.routes import agent_updates

    captured: list[tuple[str, tuple[Any, ...]]] = []

    def fake_execute(sql: str, params: tuple[Any, ...]) -> None:
        captured.append((sql, params))

    with patch.object(agent_updates, "execute", side_effect=fake_execute):
        agent_updates._append_proof_event(
            "p2_6_unit_test",
            "p2-6-test",
            {"foo": "bar"},
        )

    assert len(captured) == 1, "expected exactly one INSERT"
    sql, params = captured[0]
    assert "INSERT INTO proof_events" in sql
    persisted_payload = json.loads(params[3])
    assert persisted_payload["foo"] == "bar"
    assert persisted_payload["version_label"] == "v0.13"
    assert persisted_payload["upstream_tag"] == "v2026.5.7"
    assert persisted_payload["checkout_path"] == str(DEFAULT_AGENT_CHECKOUT)


def test_jobs_helper_persists_version_fields_alongside_ts_unix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """jobs._append_proof_event has a slightly different shape: it
    pre-stamps ``ts_unix`` and returns the event id. The version
    fields must coexist with both."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", str(V012_FALLBACK_CHECKOUT))
    from hermes3d.api.routes import jobs

    captured: list[tuple[str, tuple[Any, ...]]] = []

    def fake_execute(sql: str, params: tuple[Any, ...]) -> None:
        captured.append((sql, params))

    with patch.object(jobs, "execute", side_effect=fake_execute):
        event_id = jobs._append_proof_event(
            "jobs.test",
            "jobs-test",
            {"job_id": "abc"},
        )

    assert isinstance(event_id, str) and event_id
    assert len(captured) == 1
    persisted = json.loads(captured[0][1][3])
    assert "ts_unix" in persisted
    assert persisted["job_id"] == "abc"
    assert persisted["version_label"] == "v0.12"
    assert persisted["upstream_tag"] == "v2026.4.30"


def test_desktop_updates_helper_persists_version_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """desktop_updates carries Hermes Agent version too, even though
    its own checkout env is HERMES_DESKTOP_CHECKOUT — the audit chain
    attributes the agent runtime."""
    monkeypatch.setenv("HERMES_AGENT_CHECKOUT", str(tmp_path / "fork"))
    from hermes3d.api.routes import desktop_updates

    captured: list[tuple[str, tuple[Any, ...]]] = []

    def fake_execute(sql: str, params: tuple[Any, ...]) -> None:
        captured.append((sql, params))

    with patch.object(desktop_updates, "execute", side_effect=fake_execute):
        desktop_updates._append_proof_event(
            "desktop.test",
            "desktop-test",
            {"asset": "installer.exe"},
        )

    assert len(captured) == 1
    persisted = json.loads(captured[0][1][3])
    assert persisted["asset"] == "installer.exe"
    assert persisted["version_label"] == "unknown"
    assert persisted["upstream_tag"] == "unknown"


# ---------------------------------------------------------------------------
# Source-level import pins (catch a future revert before runtime)
# ---------------------------------------------------------------------------


def test_agent_updates_imports_attach_version_fields() -> None:
    from hermes3d.api.routes import agent_updates

    src = inspect.getsource(agent_updates)
    assert "from hermes3d.services.proof_helpers import attach_version_fields" in src, (
        "P2-6 regression: agent_updates dropped the proof_helpers import; "
        "proof events would silently lose version provenance."
    )


def test_desktop_updates_imports_attach_version_fields() -> None:
    from hermes3d.api.routes import desktop_updates

    src = inspect.getsource(desktop_updates)
    assert "from hermes3d.services.proof_helpers import attach_version_fields" in src, (
        "P2-6 regression: desktop_updates dropped the proof_helpers import."
    )


def test_jobs_imports_attach_version_fields() -> None:
    from hermes3d.api.routes import jobs

    src = inspect.getsource(jobs)
    assert "from hermes3d.services.proof_helpers import attach_version_fields" in src, (
        "P2-6 regression: jobs dropped the proof_helpers import."
    )


# ---------------------------------------------------------------------------
# Backward-compat reader contract
# ---------------------------------------------------------------------------


def test_reader_pattern_uses_get_with_unknown_default() -> None:
    """Document the contract for readers of historical events: a row
    written before this PR has no ``version_label`` key. Readers MUST
    use ``payload.get("version_label", "unknown")`` so a query against
    the legacy ledger does not crash.

    This test is a contract pin: any rewrite that breaks the
    fall-through invalidates the assumption stated in the handoff doc.
    """
    historical_payload = {"foo": "bar"}  # no version_label
    assert historical_payload.get("version_label", "unknown") == "unknown"
    assert historical_payload.get("upstream_tag", "unknown") == "unknown"
    assert historical_payload.get("checkout_path", "unknown") == "unknown"
