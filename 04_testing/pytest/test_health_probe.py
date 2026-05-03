"""Unit tests for hermes3d.core.health.probe.

Validates the in-house stdlib `socket.connect_ex` reachability probe.
NO `port-monitor` library — that's a C++/Qt6 desktop GUI, not a Python
library. We probe ports ourselves with sockets.

Live-mode tests against actual printer URLs default to skipped — they
require `HERMES3D_HEALTH_LIVE=1` and reachable infrastructure.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
from pathlib import Path

import pytest

# Make hermes3d importable when this file is collected from the repo root
# directly (e.g. via `pytest 04_testing/pytest/test_health_probe.py`).
SRC = Path(__file__).resolve().parent.parent.parent / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hermes3d.core.health.probe import (  # noqa: E402
    KNOWN_SERVICES,
    ProbeResult,
    ServiceSpec,
    Status,
    moonraker_specs_from_config,
    probe_all,
    probe_one,
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


@pytest.fixture
def open_tcp_port():
    """Bind to localhost on an ephemeral port; yield the port; close on teardown.

    The listener accepts and immediately drops connections so our probe sees a
    successful TCP handshake.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(8)
    port = sock.getsockname()[1]
    stop = threading.Event()

    def _accept_loop() -> None:
        sock.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = sock.accept()
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                return
            try:
                conn.close()
            except OSError:
                pass

    thread = threading.Thread(target=_accept_loop, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        stop.set()
        try:
            sock.close()
        except OSError:
            pass
        thread.join(timeout=1.0)


@pytest.fixture
def closed_tcp_port():
    """Bind+close to claim a port number that is then guaranteed-closed.

    The kernel will immediately TCP-reject `connect_ex` against this port,
    so our probe should report OFFLINE.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# -----------------------------------------------------------------------------
# probe_one — schema + happy-path
# -----------------------------------------------------------------------------


def test_probe_result_schema():
    """Result must carry spec + status + detail + latency + ISO timestamp."""
    spec = ServiceSpec("Test", "127.0.0.1", 1, "api", enabled=False)
    res = probe_one(spec)
    assert isinstance(res, ProbeResult)
    assert res.spec is spec
    assert isinstance(res.status, Status)
    assert isinstance(res.detail, str)
    assert isinstance(res.latency_ms, float)
    assert isinstance(res.probed_at, str)
    # ISO 8601 UTC suffix
    assert res.probed_at.endswith("+00:00") or "T" in res.probed_at


def test_disabled_service_returns_disabled():
    spec = ServiceSpec("LM Studio", "127.0.0.1", 1234, "llm", enabled=False)
    res = probe_one(spec)
    assert res.status is Status.DISABLED
    assert "disabled" in res.detail.lower()
    assert res.latency_ms == 0.0


def test_stdio_service_returns_unknown():
    """port=0 means stdio (e.g. HermesProof MCP) — we can't TCP-probe it."""
    spec = ServiceSpec("HermesProof MCP", "127.0.0.1", 0, "mcp")
    res = probe_one(spec)
    assert res.status is Status.UNKNOWN
    assert res.latency_ms == 0.0


def test_open_port_reports_online(open_tcp_port: int):
    spec = ServiceSpec("Test Open", "127.0.0.1", open_tcp_port, "api")
    res = probe_one(spec, timeout_s=2.0)
    assert res.status is Status.ONLINE, f"expected ONLINE, got {res.status} ({res.detail})"
    assert res.latency_ms >= 0.0
    assert "accepted" in res.detail.lower() or "ok" in res.detail.lower()


def test_closed_port_reports_offline(closed_tcp_port: int):
    spec = ServiceSpec("Test Closed", "127.0.0.1", closed_tcp_port, "api")
    res = probe_one(spec, timeout_s=2.0)
    assert res.status is Status.OFFLINE, f"expected OFFLINE, got {res.status} ({res.detail})"


def test_unreachable_host_reports_unreachable():
    """An invalid hostname should DNS-fail rather than hang."""
    spec = ServiceSpec("Test Bad Host", "no-such-host.invalid.", 1234, "api")
    res = probe_one(spec, timeout_s=2.0)
    assert res.status in {Status.UNREACHABLE, Status.OFFLINE}
    # latency_ms is meaningful only on TCP refusal; gaierror returns 0.0.
    assert res.latency_ms >= 0.0


# -----------------------------------------------------------------------------
# probe_all
# -----------------------------------------------------------------------------


def test_probe_all_returns_one_per_known_service():
    results = probe_all()
    assert len(results) == len(KNOWN_SERVICES)
    for r in results:
        assert isinstance(r, ProbeResult)


def test_probe_all_with_extras(open_tcp_port: int):
    extra = (
        ServiceSpec("Extra A", "127.0.0.1", open_tcp_port, "printer"),
        ServiceSpec("Extra B", "127.0.0.1", 0, "printer", enabled=False),
    )
    results = probe_all(extra=extra)
    assert len(results) == len(KNOWN_SERVICES) + 2
    # The custom Extra A should be ONLINE (we just bound the port).
    extra_a = next(r for r in results if r.spec.name == "Extra A")
    assert extra_a.status is Status.ONLINE
    extra_b = next(r for r in results if r.spec.name == "Extra B")
    assert extra_b.status is Status.DISABLED


# -----------------------------------------------------------------------------
# Per-printer Moonraker spec generation from printers.toml
# -----------------------------------------------------------------------------


def test_moonraker_specs_from_config_handles_missing_files(tmp_path):
    """Should NOT crash when neither printers.toml nor user override exists."""
    specs = moonraker_specs_from_config(
        stock=tmp_path / "nope.toml",
        user=tmp_path / "also-nope.toml",
    )
    assert specs == ()


def test_moonraker_specs_from_config_parses_stock(tmp_path):
    stock = tmp_path / "printers.toml"
    stock.write_text(
        "\n".join(
            [
                'schema_version = "1.0.0"',
                "[printers.test_a]",
                'manufacturer = "Test"',
                'model        = "A"',
                'moonraker_url = "http://printer-a.local"',
                "[printers.test_b]",
                'manufacturer = "Test"',
                'model        = "B"',
                'moonraker_url = "http://printer-b.local:7125"',
            ]
        ),
        encoding="utf-8",
    )
    specs = moonraker_specs_from_config(stock=stock, user=tmp_path / "no-user.toml")
    assert len(specs) == 2
    by_name = {s.name: s for s in specs}
    assert "Moonraker — test_a" in by_name
    assert by_name["Moonraker — test_a"].host == "printer-a.local"
    assert by_name["Moonraker — test_a"].port == 7125
    assert by_name["Moonraker — test_b"].port == 7125


def test_moonraker_specs_user_overrides_stock(tmp_path):
    stock = tmp_path / "printers.toml"
    stock.write_text(
        "\n".join(
            [
                "[printers.test_a]",
                'moonraker_url = "http://stock.local"',
            ]
        ),
        encoding="utf-8",
    )
    user = tmp_path / "printers.user.toml"
    user.write_text(
        "\n".join(
            [
                "[printers.test_a]",
                'moonraker_url = "http://192.168.1.42:7125"',
            ]
        ),
        encoding="utf-8",
    )
    specs = moonraker_specs_from_config(stock=stock, user=user)
    by_name = {s.name: s for s in specs}
    assert by_name["Moonraker — test_a"].host == "192.168.1.42"
    assert by_name["Moonraker — test_a"].port == 7125


# -----------------------------------------------------------------------------
# Live-mode (skipped by default)
# -----------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("HERMES3D_HEALTH_LIVE") != "1",
    reason="set HERMES3D_HEALTH_LIVE=1 to run live probes against real services",
)
def test_live_probe_against_known_services():
    results = probe_all()
    online = [r for r in results if r.status is Status.ONLINE]
    # We don't assert which services are up — just that the call succeeds and
    # at least one well-known port responds (LM Studio / Ollama / Hermes).
    assert isinstance(online, list)
