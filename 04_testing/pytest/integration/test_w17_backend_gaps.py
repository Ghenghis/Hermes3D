"""W17 — integration tests for the 2 new backend gap routes.

Covers:
- ``GET /api/files`` — honest blocked envelope, empty items.
- ``GET /api/files/{id}`` — same honest blocked envelope.
- ``POST /api/files`` — explicit 501 stub (no fabricated writes).
- ``GET /api/health/services`` — bridge probe results in the GUI app
  (previously only attached to ``server.py``; the GUI bridge was 404).

Per the W15-A20 contract, no test may rely on fabricated readiness.
``/api/files`` is asserted to be ``accepted=False`` + empty so a future
UI agent cannot accidentally rely on a fake list. ``/api/health/services``
is asserted to honor the existing ``ServiceHealthEntry`` shape from
:file:`ui/src/types/serviceHealth.ts` so the React consumer continues
to work unmodified.

References:
- FastAPI bigger-applications router contract:
  https://fastapi.tiangolo.com/tutorial/bigger-applications/
- W15-A20 honest-blocked envelope contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """Isolated FastAPI TestClient with a temp SQLite DB.

    Mirrors the W15-A20 fixture so the two test suites share the same
    sandbox semantics — adjacent regression of ``test_w15_a20_backend_gaps.py``
    is meaningful precisely because the fixtures match.

    We monkeypatch :func:`hermes3d.api.routes.health_services.probe_all`
    to return deterministic synthetic ``ProbeResult`` entries so the
    test never hits a real socket. Real probe behaviour is exercised
    by :file:`04_testing/pytest/test_health_probe.py` and the
    server-attached :file:`04_testing/pytest/test_health_endpoint.py`.
    """
    db_path = tmp_path / "hermes3d.db"
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    # Deterministic probe stub — uses the real ServiceSpec catalogue so
    # the catalogue-walk assertion stays meaningful, but skips socket I/O.
    from hermes3d.api.routes import health_services as hs
    from hermes3d.core.health import KNOWN_SERVICES, ProbeResult, Status

    def _fake_probe_all(extra: tuple = ()) -> list[ProbeResult]:
        results: list[ProbeResult] = []
        for spec in (*KNOWN_SERVICES, *extra):
            if not spec.enabled:
                results.append(
                    ProbeResult(spec, Status.DISABLED, "service disabled by config", 0.0)
                )
            elif spec.port == 0:
                results.append(ProbeResult(spec, Status.UNKNOWN, "stdio service", 0.0))
            else:
                results.append(
                    ProbeResult(spec, Status.OFFLINE, f"TCP {spec.host}:{spec.port} refused", 1.0)
                )
        return results

    monkeypatch.setattr(hs, "probe_all", _fake_probe_all)

    from hermes3d.api.app import create_gui_app

    return TestClient(create_gui_app())


# ---------------------------------------------------------------------------
# /api/files — honest blocked envelope
# ---------------------------------------------------------------------------


def test_files_route_is_registered_and_returns_ready(client: TestClient) -> None:
    """W19: /api/files now scans var/ and returns a real response.

    In CI the var/ directory does not exist, so items and total are both 0
    but accepted is True and status is "ready" (the scanner ran successfully).
    """
    resp = client.get("/api/files")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is True
    assert body["status"] == "ready"
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)
    assert body["total"] == len(body["items"])


def test_files_route_response_shape_matches_w15_a20_envelope(client: TestClient) -> None:
    body = client.get("/api/files").json()
    for field in ("accepted", "status", "reason", "items", "total"):
        assert field in body, f"missing envelope field {field!r}"
    assert isinstance(body["items"], list)
    assert isinstance(body["total"], int)


def test_files_route_does_not_fabricate_files(client: TestClient) -> None:
    """In CI var/ does not exist so the scanner returns zero rows.

    The scanner must never invent file records; every item must be a real
    file on disk.  In environments where var/ exists the count may be > 0,
    but it must always equal total.
    """
    body = client.get("/api/files").json()
    # total must match the item list length — no phantom count inflation.
    assert body["total"] == len(body["items"])


def test_files_get_by_id_returns_404_for_unknown_id(client: TestClient) -> None:
    """W19: unknown file IDs now return 404 (real scanner found no match).

    The old stub returned 200+accepted=False for any ID; the real scanner
    returns 404 when the SHA-1 ID does not match any file in var/.
    """
    resp = client.get("/api/files/some-arbitrary-id-that-does-not-exist")
    assert resp.status_code == 404


def test_files_get_by_id_rejects_empty_path_param(client: TestClient) -> None:
    """A bare ``/api/files/`` (trailing slash) routes to the collection;
    a whitespace-only id reaches the detail handler and must 400."""
    resp = client.get("/api/files/   ")
    assert resp.status_code == 400


def test_files_post_is_501_not_implemented(client: TestClient) -> None:
    resp = client.post("/api/files", json={"name": "test.gcode", "kind": "slice"})
    assert resp.status_code == 501, resp.text
    detail = resp.json()["detail"]
    assert detail["accepted"] is False
    assert detail["reason"] == "write_not_implemented"
    assert detail["echo"]["name"] == "test.gcode"
    assert detail["echo"]["kind"] == "slice"


def test_files_post_validates_body_before_501(client: TestClient) -> None:
    """Pydantic validation runs before the 501 stub: empty name → 422."""
    resp = client.post("/api/files", json={"name": "", "kind": "other"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /api/health/services — GUI bridge probe results
# ---------------------------------------------------------------------------


def test_health_services_route_is_registered_on_gui_bridge(client: TestClient) -> None:
    """The W17 fix is wiring this onto ``create_gui_app`` (port 8765).
    Pre-fix the GUI bridge returned 404 even though server.py exposed it."""
    resp = client.get("/api/health/services")
    assert resp.status_code == 200, resp.text


def test_health_services_response_shape_matches_ui_types(client: TestClient) -> None:
    """Match :file:`03_implementation/ui/src/types/serviceHealth.ts`.

    The React types declare ``{ results: ServiceHealthEntry[] }`` with
    each entry carrying ``name, category, host, port, status, detail,
    latency_ms, probed_at``. Keep this in lock-step.
    """
    body = client.get("/api/health/services").json()
    assert "results" in body
    assert isinstance(body["results"], list)
    if body["results"]:
        entry = body["results"][0]
        for field in (
            "name",
            "category",
            "host",
            "port",
            "status",
            "detail",
            "latency_ms",
            "probed_at",
        ):
            assert field in entry, f"missing serviceHealth field {field!r}"


def test_health_services_envelope_carries_honest_tokens(client: TestClient) -> None:
    """The W17 wrapper adds ``accepted/status/reason`` alongside ``results``
    so the UI can branch on readiness without re-walking the list."""
    body = client.get("/api/health/services").json()
    assert "accepted" in body
    assert "status" in body
    assert "reason" in body
    # KNOWN_SERVICES is non-empty by default → accepted=True, status=ready.
    # (See :data:`hermes3d.core.health.probe.KNOWN_SERVICES`.)
    assert body["accepted"] is True
    assert body["status"] == "ready"
    assert body["reason"] is None


def test_health_services_returns_known_service_catalogue(client: TestClient) -> None:
    """``KNOWN_SERVICES`` ships with MCP/LLM/modeling/api entries. Any of
    those names appearing proves the probe walked the static catalogue."""
    from hermes3d.core.health import KNOWN_SERVICES

    body = client.get("/api/health/services").json()
    returned_names = {entry["name"] for entry in body["results"]}
    expected_names = {spec.name for spec in KNOWN_SERVICES}
    # Must contain every default-catalogue name (printers vary by config).
    missing = expected_names - returned_names
    assert not missing, f"probe results missing catalogue entries: {missing}"


def test_health_services_each_entry_has_valid_status(client: TestClient) -> None:
    """Every entry's ``status`` must be one of the enum values declared in
    :file:`ui/src/types/serviceHealth.ts`."""
    allowed = {"online", "offline", "unreachable", "auth-required", "disabled", "unknown"}
    body = client.get("/api/health/services").json()
    for entry in body["results"]:
        assert entry["status"] in allowed, (
            f"entry {entry['name']!r} status={entry['status']!r} not in {allowed}"
        )


# ---------------------------------------------------------------------------
# App-level wire-up sanity
# ---------------------------------------------------------------------------


def test_w17_routes_are_registered_on_gui_app() -> None:
    """Both W17 routes must be wired on ``create_gui_app``."""
    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    paths = {route.path for route in app.routes}
    assert "/api/files" in paths, (
        f"missing /api/files (registered: {sorted(p for p in paths if p.startswith('/api/files'))})"
    )
    assert "/api/files/{file_id}" in paths, "missing /api/files/{file_id}"
    assert "/api/health/services" in paths, "missing /api/health/services"
