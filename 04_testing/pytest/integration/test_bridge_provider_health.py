"""Bridge provider-health route integration coverage."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from hermes3d.orchestration.bridge import BridgeState, create_bridge_app
from hermes3d.orchestration.ledger import LedgerEvent, OrchestrationLedger
from starlette.testclient import TestClient


def _setup(tmp_path):
    ledger = OrchestrationLedger(tmp_path / "events.sqlite3")
    state = BridgeState(ledger=ledger)
    app = create_bridge_app(state)
    client = TestClient(app, client=("127.0.0.1", 50000))
    return client, ledger


def _append_probe_event(
    ledger: OrchestrationLedger,
    *,
    provider_id: str,
    verdict: str,
    http_status: int,
    latency_ms: int,
    ts_utc: str,
) -> None:
    ledger.append(
        LedgerEvent(
            ts_utc=ts_utc,
            run_id=f"probe-{provider_id}",
            agent_id="probe-test",
            tool="provider.probe",
            inputs_sha=hashlib.sha256(provider_id.encode()).hexdigest(),
            outputs_sha=hashlib.sha256(f"{http_status}".encode()).hexdigest(),
            verdict=verdict,
            message=(
                f"provider={provider_id} status={http_status} latency_ms={latency_ms} excerpt=ok"
            ),
        )
    )


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def test_bridge_returns_idle_when_no_probes_yet(tmp_path) -> None:
    client, _ = _setup(tmp_path)

    r = client.get("/api/providers/health")

    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["providers"], list)
    # ADR-015: lm_studio + hipfire are now first-class entries in
    # llm_policy.yaml alongside the original minimax + deepseek pair.
    # Assert the cloud pair is still present rather than locking the
    # exact length, so future local providers don't break this gate.
    ids = {p["provider_id"] for p in body["providers"]}
    assert {"minimax", "deepseek"}.issubset(ids)
    for provider in body["providers"]:
        assert provider["status"] == "idle"
        assert provider["last_probe_utc"] is None
        assert provider["stale"] is False


def test_bridge_returns_green_for_recent_pass(tmp_path) -> None:
    client, ledger = _setup(tmp_path)
    _append_probe_event(
        ledger,
        provider_id="minimax",
        verdict="pass",
        http_status=200,
        latency_ms=142,
        ts_utc=_iso(datetime.now(UTC)),
    )

    r = client.get("/api/providers/health")
    body = r.json()
    minimax = next(p for p in body["providers"] if p["provider_id"] == "minimax")
    assert minimax["status"] == "green"
    assert minimax["http_status"] == 200
    assert minimax["latency_ms"] == 142
    assert minimax["stale"] is False
    deepseek = next(p for p in body["providers"] if p["provider_id"] == "deepseek")
    assert deepseek["status"] == "idle"


def test_bridge_returns_amber_for_stale_pass(tmp_path) -> None:
    client, ledger = _setup(tmp_path)
    old_ts = _iso(datetime.now(UTC) - timedelta(minutes=30))
    _append_probe_event(
        ledger,
        provider_id="minimax",
        verdict="pass",
        http_status=200,
        latency_ms=142,
        ts_utc=old_ts,
    )

    r = client.get("/api/providers/health")
    minimax = next(p for p in r.json()["providers"] if p["provider_id"] == "minimax")
    assert minimax["status"] == "amber"
    assert minimax["stale"] is True


def test_bridge_returns_red_for_recent_fail(tmp_path) -> None:
    client, ledger = _setup(tmp_path)
    _append_probe_event(
        ledger,
        provider_id="minimax",
        verdict="fail",
        http_status=500,
        latency_ms=42,
        ts_utc=_iso(datetime.now(UTC)),
    )

    r = client.get("/api/providers/health")
    minimax = next(p for p in r.json()["providers"] if p["provider_id"] == "minimax")
    assert minimax["status"] == "red"
    assert minimax["http_status"] == 500
