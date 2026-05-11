"""W18-A18 — backend timeout fix integration tests.

Operator audit on 2026-05-11 reproduced two cold-start timeouts on the
GUI bridge port 8765 even after PR #244 (W18-A13) landed the
honest-blocked banners:

* ``GET /api/health/services`` actually hung > 60 s before returning,
  because ``hermes3d.core.health.probe.probe_all`` ran probes
  **sequentially** across all known services + per-printer Moonraker
  specs. DNS resolution on ``*.local`` hostnames is not bounded by
  ``socket.settimeout()`` and inflates the sequential cost past any
  reasonable FE budget.

* ``GET /api/source-os/modules`` took ~19 s because
  ``modules.list_modules`` called ``_module_response`` sequentially for
  ~60 module rows and several runtime-probe kinds
  (``python_import``, ``moonraker_fleet``, ``local_http_health``, etc.)
  always spawn subprocesses or hit the network regardless of the
  ``live=False`` flag.

These tests assert the actual backend root-cause fixes — they exercise
the live FastAPI handlers in-process through ``TestClient`` and time
the response wall-clock against the operator's < 5 s budget. The
target is real-data responses, never faked status; the unreachable
verdict for printers we cannot connect to **is** the honest output.

Operator-freeze contract: no printer hardware writes are exercised.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Spin up a fresh FastAPI GUI app with isolated temp DB + cleared caches.

    Each test starts with empty caches so timing reflects a true cold
    request, not a probe-cache hit from a previous test.
    """
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "w18_a18.db"

    import hermes3d.db.init as dbinit
    import hermes3d.db.load_modules as lm

    monkeypatch.setattr(dbinit, "DB_PATH", db_path)
    monkeypatch.setattr(lm, "DB_PATH", db_path)

    import hermes3d.api.routes.apps as apps_route
    import hermes3d.api.routes.modules as modules_route

    monkeypatch.setattr(apps_route, "_APPS_SYNCED", False)
    monkeypatch.setattr(modules_route, "_MODULES_SYNCED", False)
    monkeypatch.setattr(modules_route, "_RUNTIME_RESPONSE_CACHE", {})
    monkeypatch.setattr(modules_route, "_MODULE_LIST_CACHE", {})
    monkeypatch.setattr(modules_route, "_MODULE_RUNTIME_PROBE_CACHE", {})

    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    return TestClient(app)


# -----------------------------------------------------------------------------
# /api/health/services — backend root cause: sequential probes
# -----------------------------------------------------------------------------


def test_health_services_returns_200_under_5s_cold(client: TestClient) -> None:
    """Cold call to /api/health/services completes in < 5 s.

    Pre-W18-A18: the operator measured > 60 s. Post-fix, parallel
    ``probe_all`` with a 3.5 s overall budget keeps the response under
    the 5 s FE timeout. The status field is real and may include
    ``unreachable`` for probes that exceeded the budget — that is the
    honest-blocked verdict, not faked.
    """
    start = time.perf_counter()
    response = client.get("/api/health/services")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200, response.text
    assert elapsed < 5.0, f"cold /api/health/services took {elapsed:.3f}s (>5s budget)"


def test_health_services_returns_real_status_per_probe(client: TestClient) -> None:
    """Each result row carries a real status value from probe execution.

    The W18-A18 fix MUST NOT downgrade probes that actually completed
    to a placeholder. Status values must come from the
    :class:`hermes3d.core.health.probe.Status` enum (``online``,
    ``offline``, ``unreachable``, ``auth-required``, ``disabled``,
    ``unknown``) — no ``"ok"`` / ``"failed"`` fabrications.
    """
    valid_statuses = {
        "online",
        "offline",
        "unreachable",
        "auth-required",
        "disabled",
        "unknown",
    }
    response = client.get("/api/health/services")
    assert response.status_code == 200
    body = response.json()
    assert body.get("accepted") is True
    assert body.get("status") == "ready"
    results = body.get("results")
    assert isinstance(results, list) and results, "expected non-empty probe results"
    for entry in results:
        assert entry.get("status") in valid_statuses, entry
        # Each entry MUST carry the spec metadata — no rows from
        # placeholder-only responses lacking a name/category/host/port.
        for key in ("name", "category", "host", "port", "detail", "latency_ms"):
            assert key in entry, f"missing {key!r} in {entry!r}"


def test_health_services_parallel_probe_under_budget(client: TestClient) -> None:
    """Even when many specs (KNOWN + per-printer) are present, the
    overall probe budget keeps the response inside the 5 s window.

    This is the regression guard against re-introducing the sequential
    list-comprehension pattern in ``probe_all``. We don't mock probes
    here — we want the *real* parallel path exercised end-to-end.
    """
    # Warm one request to confirm baseline, then re-cold via cache clear.
    client.get("/api/health/services")
    start = time.perf_counter()
    response = client.get("/api/health/services")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    # Warm requests should be just as fast (probes still re-run; this
    # endpoint deliberately does not cache liveness signals).
    assert elapsed < 5.0, f"warm /api/health/services took {elapsed:.3f}s"


# -----------------------------------------------------------------------------
# /api/source-os/modules — backend root cause: serial per-module probe
# -----------------------------------------------------------------------------


def test_source_os_modules_returns_200_under_5s_cold(client: TestClient) -> None:
    """Cold call to /api/source-os/modules completes in < 5 s.

    Pre-W18-A18: operator measured ~19 s because ``_module_response``
    ran sequentially across ~60 module rows. Post-fix, a
    ``ThreadPoolExecutor`` fans the per-module probes out 32-way and
    caches the result by ``module_id`` for the next call within the
    TTL window.

    The build budget is generous — production payload size is 60+ rows
    and the test environment may share CPU with adjacent test runs —
    so we assert < 5 s, the operator's stated FE budget.
    """
    start = time.perf_counter()
    response = client.get("/api/source-os/modules")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200, response.text
    assert elapsed < 5.0, f"cold /api/source-os/modules took {elapsed:.3f}s (>5s budget)"


def test_source_os_modules_returns_real_non_empty_data(client: TestClient) -> None:
    """Every module row carries real registry data — no fabricated rows.

    The W18-A18 fix MUST preserve the contract that the response is
    the actual SQLite ``modules`` table joined with provider rows. A
    parallelism bug that swapped real data for a placeholder would be
    caught by this assertion.
    """
    response = client.get("/api/source-os/modules")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list) and body, "expected non-empty modules list"
    for mod in body:
        # display + section + launchKind come from the registry; if any
        # are blank the registry didn't actually sync.
        assert mod.get("id"), mod
        assert mod.get("display"), mod
        assert mod.get("section"), mod
        # runtime envelope is always present, even when blocked.
        runtime = mod.get("runtime")
        assert isinstance(runtime, dict), mod
        assert "status" in runtime, runtime


def test_source_os_modules_cache_hit_is_instant(client: TestClient) -> None:
    """Second call within TTL window returns from cache in < 1 s.

    Validates the response cache wired in W18-A18. The cold call may
    pay the full probe cost; the warm call must be near-instant.
    """
    client.get("/api/source-os/modules")  # populate cache
    start = time.perf_counter()
    response = client.get("/api/source-os/modules")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 1.0, f"cached /api/source-os/modules took {elapsed:.3f}s"


def test_canonical_modules_endpoint_also_under_5s(client: TestClient) -> None:
    """The canonical ``/api/modules`` endpoint (which ``/api/source-os/modules``
    delegates to) must also be < 5 s on cold. This guards against a
    regression where the source-os alias is fast but ``/api/modules``
    is slow — they share the same handler.
    """
    start = time.perf_counter()
    response = client.get("/api/modules")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed < 5.0, f"cold /api/modules took {elapsed:.3f}s (>5s budget)"


# -----------------------------------------------------------------------------
# Unit-level regression: probe_all is parallel, not sequential
# -----------------------------------------------------------------------------


def test_probe_all_runs_in_parallel() -> None:
    """``probe_all`` must finish in roughly the slowest single probe,
    not the sum of probe times — the regression guard against
    re-introducing the sequential list comprehension.

    We register five fake specs that each sleep 1 s in ``probe_one``;
    the parallel implementation must finish in < 2 s (worst slow
    probe + thread-pool overhead), not 5+ s.
    """
    import hermes3d.core.health.probe as probe_mod
    from hermes3d.core.health.probe import (
        ProbeResult,
        ServiceSpec,
        Status,
        probe_all,
    )

    fake_specs = tuple(ServiceSpec(f"slow_{i}", "127.0.0.1", 65000 + i, "api") for i in range(5))

    def _slow_probe(spec: ServiceSpec, timeout_s: float = 2.0) -> ProbeResult:
        time.sleep(1.0)
        return ProbeResult(spec, Status.ONLINE, "fake slow probe", 1000.0)

    # Swap KNOWN_SERVICES and probe_one to deterministic slow probes.
    original_known = probe_mod.KNOWN_SERVICES
    original_probe_one = probe_mod.probe_one
    probe_mod.KNOWN_SERVICES = fake_specs  # type: ignore[misc]
    probe_mod.probe_one = _slow_probe  # type: ignore[assignment]
    try:
        start = time.perf_counter()
        results = probe_all()
        elapsed = time.perf_counter() - start
    finally:
        probe_mod.KNOWN_SERVICES = original_known  # type: ignore[misc]
        probe_mod.probe_one = original_probe_one  # type: ignore[assignment]

    assert len(results) == 5
    assert all(r.status == Status.ONLINE for r in results)
    # Sequential would be ~5 s; parallel must be ~1 s + overhead.
    assert elapsed < 2.5, f"probe_all took {elapsed:.3f}s for 5 × 1 s probes — parallelism broken?"


def test_probe_all_overall_budget_downgrades_stuck_probes() -> None:
    """A probe that exceeds the overall budget must return
    :class:`Status.UNREACHABLE`, never invent a fake online verdict.
    """
    import hermes3d.core.health.probe as probe_mod
    from hermes3d.core.health.probe import (
        PROBE_ALL_DEADLINE_S,
        ProbeResult,
        ServiceSpec,
        Status,
        probe_all,
    )

    fake_specs = (
        ServiceSpec("never_returns", "127.0.0.1", 65500, "api"),
        ServiceSpec("fast", "127.0.0.1", 65501, "api"),
    )

    def _mixed_probe(spec: ServiceSpec, timeout_s: float = 2.0) -> ProbeResult:
        if spec.name == "never_returns":
            time.sleep(PROBE_ALL_DEADLINE_S + 2.0)
        return ProbeResult(spec, Status.ONLINE, "fast", 10.0)

    original_known = probe_mod.KNOWN_SERVICES
    original_probe_one = probe_mod.probe_one
    probe_mod.KNOWN_SERVICES = fake_specs  # type: ignore[misc]
    probe_mod.probe_one = _mixed_probe  # type: ignore[assignment]
    try:
        start = time.perf_counter()
        results = probe_all()
        elapsed = time.perf_counter() - start
    finally:
        probe_mod.KNOWN_SERVICES = original_known  # type: ignore[misc]
        probe_mod.probe_one = original_probe_one  # type: ignore[assignment]

    assert len(results) == 2
    # The overall budget must bound wall-clock latency.
    assert elapsed < PROBE_ALL_DEADLINE_S + 1.0, (
        f"probe_all exceeded budget: {elapsed:.3f}s vs deadline {PROBE_ALL_DEADLINE_S}s"
    )
    # The stuck probe is honest-unreachable, not faked online.
    stuck = next(r for r in results if r.spec.name == "never_returns")
    assert stuck.status == Status.UNREACHABLE, stuck
    fast = next(r for r in results if r.spec.name == "fast")
    assert fast.status == Status.ONLINE, fast
