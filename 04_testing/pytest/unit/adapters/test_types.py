"""Phase 1 Task 14 — adapter types per ADR-008."""

from __future__ import annotations

from hermes3d.adapters.types import (
    Action,
    AdapterResult,
    AdapterState,
    ArtifactRef,
    CapabilityFlag,
    Confirmation,
    DetectResult,
    DryRunResult,
    ExecuteResult,
    HealthResult,
    LaunchResult,
    LogEntry,
    ProofRef,
    ValidateResult,
)


def test_adapter_state_has_8_canonical_states():
    expected = {
        "uninstalled",
        "detected",
        "configured",
        "ready",
        "connecting",
        "connected",
        "degraded",
        "error",
    }
    assert {s.value for s in AdapterState} == expected


def test_capability_flag_closed_enum():
    expected = {
        "cli",
        "gui",
        "headless_smoke",
        "usb",
        "websocket",
        "rest_api",
        "mcp",
        "dock_iframe",
        "streaming_logs",
        "dry_run_supported",
        "e_stop",
        "read_only",
    }
    assert {c.value for c in CapabilityFlag} == expected


def test_confirmation_carries_all_required_fields():
    c = Confirmation(
        user="alice",
        ts_utc="2026-04-30T22:00:00Z",
        printer_id="t1-1",
        reason_text="manual park",
        dry_run_token="abc123",
        signed_token="hmac-deadbeef",
        policy_version="v4.1",
    )
    assert c.user == "alice"
    assert c.printer_id == "t1-1"
    assert c.dry_run_token == "abc123"
    assert c.signed_token == "hmac-deadbeef"
    assert c.policy_version == "v4.1"


def test_confirmation_allows_null_printer_id_for_non_printer_actions():
    """Some dangerous actions are not printer-specific (e.g. Blender Python execution)."""
    c = Confirmation(
        user="alice",
        ts_utc="2026-04-30T22:00:00Z",
        printer_id=None,
        reason_text="run safe Python",
        dry_run_token="x",
        signed_token="y",
        policy_version="v4.1",
    )
    assert c.printer_id is None


def test_adapter_result_carries_proof_metadata():
    r = AdapterResult(
        ok=True,
        adapter="moonraker",
        mode="detect",
        artifacts=(),
        logs=(),
        proof=ProofRef(
            timestamp_utc="2026-04-30T22:00:00Z",
            branch="develop",
            commit="abc123",
        ),
    )
    assert r.ok is True
    assert r.proof.commit == "abc123"
    assert r.error_code is None  # default


def test_adapter_result_carries_extended_error_fields():
    r = AdapterResult(
        ok=False,
        adapter="moonraker",
        mode="execute",
        artifacts=(),
        logs=(),
        proof=ProofRef(timestamp_utc="t", branch="b", commit="c"),
        error_code="ADAPTER.MOONRAKER.AUTH_REQUIRED",
        severity="error",
        recoverable=True,
        user_action_required="Set api_key in printers.user.toml",
    )
    assert r.error_code == "ADAPTER.MOONRAKER.AUTH_REQUIRED"
    assert r.severity == "error"
    assert r.recoverable is True


def test_log_entry_has_redactions_field():
    e = LogEntry(
        ts_utc="2026-04-30T22:00:00Z",
        severity="info",
        source="moonraker.http",
        code=None,
        msg="GET /server/info",
        redactions=("headers.authorization",),
    )
    assert "headers.authorization" in e.redactions


def test_action_carries_kind_and_payload():
    a = Action(kind="park", payload={"position": "home"})
    assert a.kind == "park"
    assert a.payload["position"] == "home"


def test_artifact_ref_basic():
    ar = ArtifactRef(path="staging/sliced.gcode", sha256="deadbeef")
    assert ar.path == "staging/sliced.gcode"
    assert ar.sha256 == "deadbeef"


def test_dry_run_result_provides_token():
    r = DryRunResult(ok=True, dry_run_token="tok-123", summary="would print 47 lines")
    assert r.dry_run_token == "tok-123"
    assert r.ok


def test_execute_result_basic():
    r = ExecuteResult(ok=True, artifacts=(), detail="paused")
    assert r.ok and r.detail == "paused"


def test_validate_health_launch_detect_results_basic():
    assert ValidateResult(ok=True, state=AdapterState.READY).ok
    assert HealthResult(ok=True, state=AdapterState.CONNECTED, latency_ms=12).latency_ms == 12
    assert LaunchResult(ok=True, mode="docked", pid=4242).pid == 4242
    assert DetectResult(found=True, state=AdapterState.DETECTED, detail="ok").found
