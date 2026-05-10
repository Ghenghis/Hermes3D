"""Integration tests for the W6-9 PrinterSafetyGate (10 tests).

Tests the three explicit gates from the user's W6-9 brief 2026-05-09:

    1. camera-only — no live camera frame -> blocked
    2. plate clear — vision says "clear" with confidence >= 0.85
    3. no heat/start until proof — every command-route refuses on block

Default-deny posture is the load-bearing invariant: a freshly initialised
gate refuses every printer.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hermes3d.api.routes import printer_safety as printer_safety_route
from hermes3d.services.printer_safety_gate import PrinterSafetyGate

# --------------------------------------------------------------------------- #
# Fixtures — every test gets a brand-new gate so state doesn't leak.
# --------------------------------------------------------------------------- #


@pytest.fixture
def fixed_clock() -> "list[float]":
    """A list of length 1 used as a settable clock."""
    return [1_700_000_000.0]


@pytest.fixture
def gate(fixed_clock: "list[float]") -> PrinterSafetyGate:
    """Fresh gate per test with a clock we can step forward."""
    g = PrinterSafetyGate(clock=lambda: fixed_clock[0])
    return g


@pytest.fixture
def fastapi_client(monkeypatch: pytest.MonkeyPatch, gate: PrinterSafetyGate) -> TestClient:
    """Build a fresh FastAPI app that includes ONLY the safety router and
    routes the singleton lookup at the gate fixture above so every test
    is fully isolated."""
    monkeypatch.setattr(printer_safety_route, "_gate", lambda: gate)
    app = FastAPI()
    app.include_router(printer_safety_route.router)
    return TestClient(app)


# --------------------------------------------------------------------------- #
# 1. Default state — blocked, reasons name both missing pieces.
# --------------------------------------------------------------------------- #


def test_default_state_is_blocked_with_full_reasons(
    gate: PrinterSafetyGate,
) -> None:
    allow, reasons = asyncio.run(gate.is_safe_to_start("printer_a"))
    assert allow is False, "Fresh gate must default-deny"
    assert any("no camera bound" in r for r in reasons), reasons
    assert any("no camera frame" in r for r in reasons), reasons
    assert any("no plate classification" in r for r in reasons), reasons


# --------------------------------------------------------------------------- #
# 2. Camera frame alone is not enough — plate classification still missing.
# --------------------------------------------------------------------------- #


def test_camera_frame_alone_still_blocked(
    gate: PrinterSafetyGate, fixed_clock: "list[float]"
) -> None:
    async def _go() -> tuple[bool, list[str]]:
        await gate.bind_camera("printer_a", "cam_a")
        await gate.record_camera_frame("cam_a", fixed_clock[0])
        return await gate.is_safe_to_start("printer_a")

    allow, reasons = asyncio.run(_go())
    assert allow is False
    assert any("no plate classification ever" in r for r in reasons), reasons


# --------------------------------------------------------------------------- #
# 3. Obstructed plate is blocked.
# --------------------------------------------------------------------------- #


def test_obstructed_plate_is_blocked(gate: PrinterSafetyGate, fixed_clock: "list[float]") -> None:
    async def _go() -> tuple[bool, list[str]]:
        await gate.bind_camera("printer_a", "cam_a")
        await gate.record_camera_frame("cam_a", fixed_clock[0])
        await gate.record_plate_classification("cam_a", "obstructed", 0.99, fixed_clock[0])
        return await gate.is_safe_to_start("printer_a")

    allow, reasons = asyncio.run(_go())
    assert allow is False
    assert any("plate not clear" in r and "obstructed" in r for r in reasons), reasons


# --------------------------------------------------------------------------- #
# 4. Low-confidence "clear" is blocked.
# --------------------------------------------------------------------------- #


def test_clear_with_low_confidence_is_blocked(
    gate: PrinterSafetyGate, fixed_clock: "list[float]"
) -> None:
    async def _go() -> tuple[bool, list[str]]:
        await gate.bind_camera("printer_a", "cam_a")
        await gate.record_camera_frame("cam_a", fixed_clock[0])
        await gate.record_plate_classification("cam_a", "clear", 0.50, fixed_clock[0])
        return await gate.is_safe_to_start("printer_a")

    allow, reasons = asyncio.run(_go())
    assert allow is False
    assert any("confidence too low" in r for r in reasons), reasons


# --------------------------------------------------------------------------- #
# 5. Clear at high confidence with a fresh frame -> allow.
# --------------------------------------------------------------------------- #


def test_clear_high_confidence_allows(gate: PrinterSafetyGate, fixed_clock: "list[float]") -> None:
    async def _go() -> tuple[bool, list[str]]:
        await gate.bind_camera("printer_a", "cam_a")
        await gate.record_camera_frame("cam_a", fixed_clock[0])
        await gate.record_plate_classification("cam_a", "clear", 0.92, fixed_clock[0])
        return await gate.is_safe_to_start("printer_a")

    allow, reasons = asyncio.run(_go())
    assert allow is True, reasons
    assert reasons == []


# --------------------------------------------------------------------------- #
# 6. Camera frame goes stale -> blocked.
# --------------------------------------------------------------------------- #


def test_camera_stale_blocks(gate: PrinterSafetyGate, fixed_clock: "list[float]") -> None:
    async def _go() -> tuple[bool, list[str]]:
        await gate.bind_camera("printer_a", "cam_a")
        await gate.record_camera_frame("cam_a", fixed_clock[0])
        await gate.record_plate_classification("cam_a", "clear", 0.95, fixed_clock[0])
        # advance clock past camera freshness window (default 5s)
        fixed_clock[0] += 12.0
        return await gate.is_safe_to_start("printer_a")

    allow, reasons = asyncio.run(_go())
    assert allow is False
    assert any("camera stale" in r for r in reasons), reasons


# --------------------------------------------------------------------------- #
# 7. Plate classification goes stale -> blocked.
# --------------------------------------------------------------------------- #


def test_plate_classification_stale_blocks(
    gate: PrinterSafetyGate, fixed_clock: "list[float]"
) -> None:
    async def _go() -> tuple[bool, list[str]]:
        await gate.bind_camera("printer_a", "cam_a")
        await gate.record_plate_classification("cam_a", "clear", 0.95, fixed_clock[0])
        # advance clock past plate window (default 30s) but keep the camera fresh
        # so the only failure reason is plate-stale
        fixed_clock[0] += 45.0
        await gate.record_camera_frame("cam_a", fixed_clock[0])
        return await gate.is_safe_to_start("printer_a")

    allow, reasons = asyncio.run(_go())
    assert allow is False
    assert any("plate classification stale" in r for r in reasons), reasons


# --------------------------------------------------------------------------- #
# 8. State is isolated per printer_id — one printer's good state never leaks.
# --------------------------------------------------------------------------- #


def test_state_is_isolated_per_printer(gate: PrinterSafetyGate, fixed_clock: "list[float]") -> None:
    async def _go() -> "tuple[tuple[bool, list[str]], tuple[bool, list[str]]]":
        # printer_a gets full proof on cam_a
        await gate.bind_camera("printer_a", "cam_a")
        await gate.record_camera_frame("cam_a", fixed_clock[0])
        await gate.record_plate_classification("cam_a", "clear", 0.95, fixed_clock[0])
        # printer_b is bound to a DIFFERENT camera with no events
        await gate.bind_camera("printer_b", "cam_b")
        a_decision = await gate.is_safe_to_start("printer_a")
        b_decision = await gate.is_safe_to_start("printer_b")
        return a_decision, b_decision

    (a_allow, _), (b_allow, b_reasons) = asyncio.run(_go())
    assert a_allow is True
    assert b_allow is False
    assert any("no camera frame" in r for r in b_reasons), b_reasons


# --------------------------------------------------------------------------- #
# 9. Route tests — POST /start-print returns 403 when blocked, 200 when allowed.
# --------------------------------------------------------------------------- #


def test_routes_403_when_blocked_and_200_when_allowed(
    fastapi_client: TestClient, fixed_clock: "list[float]"
) -> None:
    # default-deny: every command route 403 with explicit blocked_by list
    for endpoint in (
        "/api/printers/printer_a/start-print",
        "/api/printers/printer_a/heat-extruder",
        "/api/printers/printer_a/heat-bed",
    ):
        r = fastapi_client.post(endpoint)
        assert r.status_code == 403, f"{endpoint} expected 403, got {r.status_code}"
        body = r.json()
        assert body["detail"]["ok"] is False
        assert body["detail"]["printer_id"] == "printer_a"
        assert isinstance(body["detail"]["blocked_by"], list)
        assert len(body["detail"]["blocked_by"]) >= 1

    # bind camera + record proof via the ingestion routes
    bind = fastapi_client.post(
        "/api/printers/printer_a/safety-events/bind-camera",
        json={"camera_id": "cam_a"},
    )
    assert bind.status_code == 200, bind.text

    frame = fastapi_client.post(
        "/api/printers/printer_a/safety-events/camera-frame",
        json={"camera_id": "cam_a", "ts_unix": fixed_clock[0]},
    )
    assert frame.status_code == 200, frame.text

    cls = fastapi_client.post(
        "/api/printers/printer_a/safety-events/plate-classification",
        json={
            "camera_id": "cam_a",
            "classification": "clear",
            "confidence": 0.95,
            "ts_unix": fixed_clock[0],
        },
    )
    assert cls.status_code == 200, cls.text

    state_resp = fastapi_client.get("/api/printers/printer_a/safety-state")
    assert state_resp.status_code == 200, state_resp.text
    state = state_resp.json()
    assert state["allow"] is True, state
    assert state["camera_fresh"] is True
    assert state["plate_classification"] == "clear"

    # now every command route should pass
    for endpoint in (
        "/api/printers/printer_a/start-print",
        "/api/printers/printer_a/heat-extruder",
        "/api/printers/printer_a/heat-bed",
    ):
        r = fastapi_client.post(endpoint)
        assert r.status_code == 200, f"{endpoint} expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        assert body["ok"] is True
        assert body["gated"] is True


# --------------------------------------------------------------------------- #
# 10. Concurrent calls — at most one per printer-millisecond passes the gate.
#
#     We fire 100 parallel start_print calls before any proof is recorded;
#     EVERY one must be refused. Then we record proof and fire another 100;
#     EVERY one must be allowed. No race in either direction.
# --------------------------------------------------------------------------- #


def test_concurrent_calls_have_no_race(gate: PrinterSafetyGate, fixed_clock: "list[float]") -> None:
    async def _go() -> tuple[list[bool], list[bool]]:
        # phase 1: nothing recorded -> everything blocked
        await gate.bind_camera("printer_a", "cam_a")
        results_blocked = await asyncio.gather(
            *(gate.is_safe_to_start("printer_a") for _ in range(100))
        )
        # phase 2: record proof -> everything allowed
        await gate.record_camera_frame("cam_a", fixed_clock[0])
        await gate.record_plate_classification("cam_a", "clear", 0.95, fixed_clock[0])
        results_allowed = await asyncio.gather(
            *(gate.is_safe_to_start("printer_a") for _ in range(100))
        )
        return [r[0] for r in results_blocked], [r[0] for r in results_allowed]

    blocked_decisions, allowed_decisions = asyncio.run(_go())
    # property 1: pre-proof everything is blocked, no leak
    assert all(d is False for d in blocked_decisions), "pre-proof leak detected"
    # property 2: post-proof everything is allowed, no spurious deny
    assert all(d is True for d in allowed_decisions), "post-proof spurious deny"
    # property 3: results are stable — count, not order, is what matters
    assert len(blocked_decisions) == 100
    assert len(allowed_decisions) == 100
