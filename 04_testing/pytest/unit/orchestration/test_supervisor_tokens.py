"""Phase 3.1-B offline supervisor token rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hermes3d.orchestration import (
    Err,
    OfflineSupervisor,
    OrchestrationLedger,
    PollRequest,
    PrinterMirror,
)


def _request(tool: str = "printer.poll") -> PollRequest:
    return PollRequest(
        run_id="run-1",
        agent_id="agent-a",
        printer_id="printer-1",
        tool=tool,
        inputs={"requested": "mirror"},
    )


def _mirror(request: PollRequest) -> PrinterMirror:
    return PrinterMirror(
        printer_id=request.printer_id,
        name="Voron 2.4",
        status="ready",
        state="idle",
        progress=0.0,
    )


def test_tokenless_dispatch_is_refused(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    supervisor = OfflineSupervisor(ledger=ledger)

    result = supervisor.dispatch_poll(_request(), handler=_mirror)

    assert isinstance(result.result, Err)
    assert result.result.code == "no_token"
    assert result.token_id is None
    assert ledger.events()[0].verdict == "fail"


def test_expired_token_is_refused(tmp_path):
    now = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    token = supervisor.issue_token(
        agent_id="agent-a",
        tools=frozenset({"printer.poll"}),
        ttl_seconds=1,
        now_utc=now,
    )

    result = supervisor.dispatch_poll(
        _request(),
        token=token,
        handler=_mirror,
        now_utc=now + timedelta(seconds=2),
    )

    assert isinstance(result.result, Err)
    assert result.result.code == "token_expired"


def test_unauthorized_tool_is_refused(tmp_path):
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    token = supervisor.issue_token(
        agent_id="agent-a",
        tools=frozenset({"printer.poll"}),
    )

    result = supervisor.dispatch_poll(
        _request(tool="printer.write"),
        token=token,
        handler=_mirror,
    )

    assert isinstance(result.result, Err)
    assert result.result.code == "tool_not_authorized"


def test_unregistered_poll_tool_is_refused_after_token_validation(tmp_path):
    supervisor = OfflineSupervisor(
        ledger=OrchestrationLedger(tmp_path / "events.sqlite3"),
        registered_tools=frozenset({"planner.plan", "gen3d.generate"}),
    )
    token = supervisor.issue_token(
        agent_id="agent-a",
        tools=frozenset({"printer.poll"}),
    )

    result = supervisor.dispatch_poll(_request(), token=token, handler=_mirror)

    assert isinstance(result.result, Err)
    assert result.result.code == "tool_unregistered"
    assert supervisor.ledger is not None
    assert supervisor.ledger.events()[0].tool == "printer.poll"
    assert supervisor.ledger.events()[0].verdict == "fail"


def test_authorized_dispatch_consumes_token_and_reuses_printer_mutex(tmp_path):
    supervisor = OfflineSupervisor(ledger=OrchestrationLedger(tmp_path / "events.sqlite3"))
    token = supervisor.issue_token(
        agent_id="agent-a",
        tools=frozenset({"printer.poll"}),
    )

    accepted = supervisor.dispatch_poll(_request(), token=token, handler=_mirror)
    replay = supervisor.dispatch_poll(_request(), token=token, handler=_mirror)

    assert not isinstance(accepted.result, Err)
    assert accepted.token_id == token.token_id
    assert isinstance(replay.result, Err)
    assert replay.result.code == "token_unknown"
    assert supervisor.mutex_for("printer-1") is supervisor.mutex_for("printer-1")
