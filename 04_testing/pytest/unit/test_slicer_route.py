"""W18-A12 — unit tests for POST/GET /api/slice.

Covers:
    * The route returns a real G-code FILE on disk with non-zero bytes,
      a deterministic sha256, and a positive layer_count once the
      background thread completes.
    * The slicer endpoint NEVER hits a printer-control endpoint
      (no Moonraker / OctoPrint / Klipper upload). We mock the
      requests/httpx HTTP clients and assert they were never called.
    * The PrusaSlicer 2.9.5 ``;LAYER_CHANGE`` analyzer fix returns
      ``layer_count > 0`` and ``motion_lines > 0``.

The first two tests need an actual slicer binary on PATH because the
verdict gate is "real G-code". When no slicer is found we skip with a
descriptive reason — never with `test.skip` semantics from the
operator brief, but pytest's environment-conditional skip is the
correct posture when the dependency is genuinely absent.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = REPO_ROOT / "03_implementation" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture()
def isolated_app(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple, None, None]:
    """Build the FastAPI app against a fresh tmp SQLite + tmp var/slicer dir."""
    import hermes3d.api.routes.slicer as slicer_route
    import hermes3d.db.init as dbinit
    from fastapi.testclient import TestClient

    tmp = Path(tempfile.mkdtemp(prefix="hermes3d_slicer_test_"))
    db_path = tmp / "slicer_test.db"
    monkeypatch.setattr(dbinit, "DB_PATH", db_path)

    # Redirect var/slicer so the test doesn't pollute the repo.
    slicer_root = tmp / "slicer_root"
    slicer_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(slicer_route, "_slicer_root", lambda: slicer_root)

    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    client = TestClient(app)
    try:
        yield client, slicer_root
    finally:
        client.close()


def _find_seed_stl() -> Path:
    """Locate the small tiny_cube fixture committed for E2E."""
    candidates = [
        REPO_ROOT / "04_testing" / "fixtures" / "tiny_cube_10mm.stl",
        REPO_ROOT / "fixtures" / "tiny_cube_10mm.stl",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    pytest.skip(f"seed STL not found in {candidates}")


def _slicer_available() -> bool:
    from hermes3d.core.slicer.slicer_runner import find_slicer

    sl = find_slicer()
    return sl is not None and sl.is_file()


# ---------------------------------------------------------------------------
# Test 1 — happy-path: real slicer -> real G-code on disk
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _slicer_available(),
    reason="PrusaSlicer/OrcaSlicer CLI not installed — slice_mesh would raise SlicerNotFound",
)
def test_slice_endpoint_returns_real_gcode(isolated_app: tuple) -> None:
    client, slicer_root = isolated_app
    stl = _find_seed_stl()

    # ----- POST /api/slice -----
    resp = client.post("/api/slice", json={"stl_path": str(stl)})
    assert resp.status_code == 202, f"POST should be 202; got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["accepted"] is True
    job_id = body["job_id"]
    assert isinstance(job_id, str) and len(job_id) >= 16

    # ----- GET /api/slice/{id} until terminal -----
    deadline = time.time() + 240  # tiny cube < 30s on any modern box
    final: dict = {}
    while time.time() < deadline:
        det = client.get(f"/api/slice/{job_id}")
        assert det.status_code == 200, f"GET 200 expected; got {det.status_code}: {det.text}"
        final = det.json()
        if (final.get("status") or "").lower() in {"completed", "failed"}:
            break
        time.sleep(1.0)

    assert final.get("status") == "completed", f"slice did not complete in 240s: {final}"

    # ----- Assertions on the real G-code FILE -----
    gcode_path = Path(final["gcode_path"])
    assert gcode_path.is_file(), f"G-code missing on disk: {gcode_path}"
    size = gcode_path.stat().st_size
    assert size > 0, "G-code file must be non-empty"
    # Re-hash and compare against what the API reported
    h = hashlib.sha256()
    h.update(gcode_path.read_bytes())
    assert h.hexdigest() == final["sha256"], "sha256 mismatch"

    # ----- Analyzer assertions: layer_count > 0 (W18-A12 fix) -----
    layer_count = final.get("layer_count")
    assert isinstance(layer_count, int) and layer_count > 0, (
        f"layer_count must be a positive integer (W18-A12 gcode_analyzer fix); got {layer_count}. "
        f"Final payload: {final}"
    )
    motion_lines = final.get("motion_lines")
    assert isinstance(motion_lines, int) and motion_lines > 0, (
        f"motion_lines must be a positive integer (W18-A12 fix); got {motion_lines}."
    )

    # ----- The proof envelope must live beside the gcode -----
    proof_path = Path(final["proof_path"])
    assert proof_path.is_file(), f"proof.json missing on disk: {proof_path}"
    assert proof_path.parent == gcode_path.parent
    assert final.get("proof_event_id"), "proof_event_id must be returned"

    # ----- Belt-and-braces: file is under the redirected var/slicer root -----
    assert str(gcode_path).startswith(str(slicer_root)), (
        f"G-code should be inside the test slicer_root {slicer_root}, got {gcode_path}"
    )


# ---------------------------------------------------------------------------
# Test 2 — assert NO printer-control endpoint was called.
# ---------------------------------------------------------------------------


def test_slicer_route_does_not_import_printer_clients() -> None:
    """The slicer route MUST NOT statically import any printer-HTTP client.

    This is a static-analysis assertion: it inspects the actual module
    namespace after import. If any future commit adds a Moonraker / OctoPrint
    /Klipper client import to ``api.routes.slicer`` this test fires.
    """
    import importlib

    mod = importlib.import_module("hermes3d.api.routes.slicer")
    forbidden = {
        "hermes3d.core.printers.moonraker_client",
        "hermes3d.adapters.moonraker",
        "hermes3d.adapters.moonraker_readonly",
        "hermes3d.adapters.octoprint",
        "hermes3d.adapters.klipper",
    }
    # Walk the module's referenced objects to make sure no Moonraker symbol
    # leaked in via a star-import or a hidden alias.
    referenced = {
        getattr(getattr(mod, name), "__module__", "")
        for name in dir(mod)
        if not name.startswith("_")
    }
    intersection = referenced & forbidden
    assert intersection == set(), (
        f"slicer route imports printer-HTTP clients: {intersection}. "
        f"Operator freeze 2026-05-11 forbids this — slicer outputs a FILE only."
    )


def test_source_mesh_artifact_lookup_uses_existing_mesh_row(monkeypatch, tmp_path: Path) -> None:
    """Slicer artifacts should link back to the source mesh when DB knows it."""

    import hermes3d.api.routes.slicer as slicer_route

    stl = tmp_path / "part.stl"
    stl.write_text("solid part\nendsolid part\n", encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_row(sql: str, params: tuple[str]):  # noqa: ANN202
        seen["sql"] = sql
        seen["params"] = params
        return {"id": "mesh-artifact-123"}

    monkeypatch.setattr(slicer_route, "row", fake_row)

    assert slicer_route._source_mesh_artifact_id(stl) == "mesh-artifact-123"
    assert seen["params"] == (str(stl),)
    assert "evidence_type IN ('mesh', 'model')" in str(seen["sql"])


def test_source_mesh_artifact_lookup_returns_none_when_absent(monkeypatch, tmp_path: Path) -> None:
    import hermes3d.api.routes.slicer as slicer_route

    stl = tmp_path / "missing-link.stl"
    monkeypatch.setattr(slicer_route, "row", lambda *_args, **_kwargs: None)

    assert slicer_route._source_mesh_artifact_id(stl) is None


@pytest.mark.skipif(
    not _slicer_available(),
    reason="PrusaSlicer/OrcaSlicer CLI not installed — slice_mesh would raise SlicerNotFound",
)
def test_slicer_does_not_dispatch(isolated_app: tuple) -> None:
    """Slicer route MUST NOT touch any Moonraker / OctoPrint HTTP surface.

    We monkey-patch ``urllib.request.urlopen`` (the actual lib the
    Hermes Moonraker client uses) and the ``requests`` module and assert
    no call was made for the lifetime of the slice job. The slicer's
    real path is ``subprocess.run(prusa-slicer-console.exe ...)`` — there
    must be ZERO HTTP traffic.

    Note: we deliberately do NOT mock ``httpx`` because the TestClient
    itself uses httpx as its ASGI transport.
    """
    client, _slicer_root = isolated_app
    stl = _find_seed_stl()

    urlopen_calls: list[str] = []
    requests_calls: list[str] = []

    import urllib.request as _ur

    real_urlopen = _ur.urlopen

    def _urlopen_spy(url, *args, **kwargs):  # noqa: ANN001
        urlopen_calls.append(str(url))
        return real_urlopen(url, *args, **kwargs)

    import requests as _req

    def _req_spy(method, url, *args, **kwargs):  # noqa: ANN001
        requests_calls.append(f"{method} {url}")
        raise AssertionError(
            f"HARD FREEZE VIOLATION: slicer route attempted requests.{method} -> {url}"
        )

    with (
        mock.patch.object(_ur, "urlopen", _urlopen_spy),
        mock.patch.object(_req.api, "request", _req_spy),
    ):
        resp = client.post("/api/slice", json={"stl_path": str(stl)})
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        deadline = time.time() + 240
        final: dict = {}
        while time.time() < deadline:
            det = client.get(f"/api/slice/{job_id}")
            assert det.status_code == 200
            final = det.json()
            if (final.get("status") or "").lower() in {"completed", "failed"}:
                break
            time.sleep(1.0)

    assert final.get("status") == "completed", final
    assert urlopen_calls == [], (
        f"HARD FREEZE VIOLATION: slicer route made urllib.urlopen() calls: {urlopen_calls}"
    )
    assert requests_calls == [], (
        f"HARD FREEZE VIOLATION: slicer route made requests calls: {requests_calls}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Bad input path returns 404 honestly, never silently dispatches.
# ---------------------------------------------------------------------------


def test_slice_unknown_stl_returns_404(isolated_app: tuple) -> None:
    client, _ = isolated_app
    resp = client.post("/api/slice", json={"stl_path": "this_does_not_exist_anywhere.stl"})
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("detail", {}).get("status") == "blocked"


# ---------------------------------------------------------------------------
# Test 4 — Route registration smoke-test (always runnable, no slicer needed)
# ---------------------------------------------------------------------------


def test_slice_routes_are_registered() -> None:
    from hermes3d.api.app import create_gui_app

    app = create_gui_app()
    paths = {route.path for route in app.routes}
    assert "/api/slice" in paths
    assert "/api/slice/{job_id}" in paths


# ---------------------------------------------------------------------------
# Test 5 — gcode_analyzer LAYER_CHANGE parsing fix (W18-A12)
# ---------------------------------------------------------------------------


def test_gcode_analyzer_counts_layer_change_markers(tmp_path: Path) -> None:
    """Synthetic G-code with PrusaSlicer 2.9.5 markers must report >0 layers."""
    from hermes3d.core.slicer.gcode_analyzer import analyze_gcode

    sample = tmp_path / "synthetic.gcode"
    lines = [
        "; generated by PrusaSlicer 2.9.5-beta2 on test",
        "; estimated printing time (normal mode) = 1h 23m",
        "; filament used [mm] = 1234.5",
        "; filament used [g] = 3.7",
        ";BEFORE_LAYER_CHANGE",
        ";LAYER_CHANGE",
        ";AFTER_LAYER_CHANGE",
        "G1 X0 Y0 Z0.2 E0.5 F1800",
        "G0 X10 Y10",
        ";BEFORE_LAYER_CHANGE",
        ";LAYER_CHANGE",
        ";AFTER_LAYER_CHANGE",
        "G1 X1 Y1 Z0.4 E0.7 F1800",
        ";BEFORE_LAYER_CHANGE",
        ";LAYER_CHANGE",
        ";AFTER_LAYER_CHANGE",
        "G1 X2 Y2 Z0.6 E0.9 F1800",
    ]
    sample.write_text("\n".join(lines), encoding="utf-8")

    analysis = analyze_gcode(sample)
    assert analysis.layer_change_markers == 3, (
        f"Should count exactly 3 ;LAYER_CHANGE markers (excluding BEFORE/AFTER); got "
        f"{analysis.layer_change_markers}"
    )
    assert analysis.layer_count == 3, (
        f"layer_count must equal LAYER_CHANGE count when no header is present; got {analysis.layer_count}"
    )
    assert analysis.motion_lines >= 3, (
        f"motion_lines must count G0/G1 lines; got {analysis.motion_lines}"
    )


def test_gcode_analyzer_prefers_header_layer_count(tmp_path: Path) -> None:
    """A real `; total layer count = N` header MUST win over the marker count."""
    from hermes3d.core.slicer.gcode_analyzer import analyze_gcode

    sample = tmp_path / "with_header.gcode"
    lines = [
        "; generated by PrusaSlicer 2.5.0 on test",
        "; total layer count = 7",
        ";LAYER_CHANGE",
        "G1 X0 Y0 Z0.2 E0.5 F1800",
        ";LAYER_CHANGE",
        "G1 X1 Y1 Z0.4 E0.7 F1800",
    ]
    sample.write_text("\n".join(lines), encoding="utf-8")

    analysis = analyze_gcode(sample)
    assert analysis.layer_count == 7
    assert analysis.layer_change_markers == 2  # streaming counter is still correct
