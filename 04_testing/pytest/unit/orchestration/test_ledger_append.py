"""Phase 3.1-B append-only orchestration ledger."""

from __future__ import annotations

import sqlite3

from hermes3d.orchestration.ledger import LedgerEvent, OrchestrationLedger


def _event(message: str = "accepted") -> LedgerEvent:
    return LedgerEvent(
        ts_utc="2026-05-01T12:00:00Z",
        run_id="run-1",
        agent_id="agent-a",
        tool="printer.poll",
        inputs_sha="in-sha",
        outputs_sha="out-sha",
        verdict="pass",
        message=message,
    )


def test_ledger_appends_events_and_computes_stable_rollup(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    ledger = OrchestrationLedger(db_path)

    first_id = ledger.append(_event("first"))
    second_id = ledger.append(_event("second"))

    assert (first_id, second_id) == (1, 2)
    assert [event.message for event in ledger.events()] == ["first", "second"]
    assert ledger.stable_sha() == OrchestrationLedger(db_path).stable_sha()


def test_stable_rollup_changes_when_new_event_is_appended(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    ledger.append(_event("first"))
    before = ledger.stable_sha()

    ledger.append(_event("second"))

    assert ledger.stable_sha() != before


def test_ledger_schema_matches_required_columns(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    OrchestrationLedger(db_path)
    with sqlite3.connect(db_path) as conn:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(events)")]

    assert columns == [
        "ts_utc",
        "run_id",
        "agent_id",
        "tool",
        "inputs_sha",
        "outputs_sha",
        "verdict",
        "message",
    ]


def test_ledger_exposes_no_update_or_delete_helpers(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")

    assert not hasattr(ledger, "update")
    assert not hasattr(ledger, "delete")
    assert not hasattr(ledger, "remove")
