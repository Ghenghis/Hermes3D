"""Tests for GET /api/gen3d/providers and GET /api/gen3d/templates.

Lane 13 (H3D-CLAUDE-GEN3D): verifies that both new endpoints return real,
non-fake data structures — provider readiness sourced from Lane 04 proof and
live port probes; templates sourced from actual repo adapter schemas.

Tests mount only the generation router in a lightweight FastAPI app to avoid
DB lock contention from the full app startup. No live network connections are
made — port_reachable and _LANE04_PROOF_PATH are monkeypatched.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

# Ensure hermes3d is importable
_SRC = Path(__file__).resolve().parent.parent.parent / "03_implementation" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Skip entire module if FastAPI or starlette not available
fastapi_mod = pytest.importorskip("fastapi")
starlette_tc = pytest.importorskip("starlette.testclient")
TestClient = starlette_tc.TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_connect(db_path: Path):
    """Return a connect() factory that always uses db_path."""

    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    return _connect


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    """TestClient that mounts only the generation router, with an isolated DB.

    The DB is pre-initialised with the real schema (PRAGMA foreign_keys OFF
    during seed to avoid the inter-table dependency issue in init_db). All
    _common queries and ensure_db() are redirected to the test db.
    """
    import hermes3d.api.routes._common as common_mod

    db_file = tmp_path / "gen3d_test.db"

    # Build schema from the real schema.sql file, without the seed that has
    # FK constraints (we don't need roadmap/modules data for gen3d route tests)
    schema_file = (
        Path(__file__).resolve().parent.parent.parent
        / "03_implementation"
        / "src"
        / "hermes3d"
        / "db"
        / "schema.sql"
    )
    conn0 = sqlite3.connect(str(db_file))
    conn0.execute("PRAGMA foreign_keys = OFF")
    if schema_file.is_file():
        conn0.executescript(schema_file.read_text(encoding="utf-8"))
    conn0.commit()
    conn0.close()

    test_connect = _make_test_connect(db_file)

    # Patch _common so rows()/row()/execute() use the test DB
    monkeypatch.setattr(common_mod, "ensure_db", lambda: None)
    monkeypatch.setattr("hermes3d.db.init.connect", test_connect)
    monkeypatch.setattr(
        common_mod,
        "connect" if hasattr(common_mod, "connect") else "_connect",
        test_connect,
        raising=False,
    )

    # _common imports connect directly at module level; patch the name it uses
    import hermes3d.api.routes._common as _cm_reimport

    _cm_orig_connect = getattr(_cm_reimport, "connect", None)
    # The module does `from hermes3d.db.init import connect, init_db`
    # so we patch the names in the _common module namespace
    monkeypatch.setattr(_cm_reimport, "connect", test_connect, raising=True)
    monkeypatch.setattr(_cm_reimport, "init_db", lambda: None, raising=True)

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from hermes3d.api.routes import generation

    monkeypatch.setattr(
        generation,
        "_GEN3D_MODEL_MANIFEST_PATH",
        tmp_path / "missing-gen3d-model-manifest.json",
        raising=True,
    )
    monkeypatch.setenv("HERMES3D_COMFYUI_ROOT", str(tmp_path / "missing-ComfyUI"))

    app = FastAPI(title="gen3d-test")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(generation.router)

    with TestClient(app) as client:
        yield client


@pytest.fixture
def fake_proof_file(tmp_path):
    """Write a minimal Lane 04 proof JSON and return its path."""
    proof = {
        "$schema": "hermes3d://proof/gen3d_verify_v1",
        "lane": "H3D-CLAUDE-SOURCE-GEN3D",
        "generated_at_utc": "2026-05-06T22:29:10.948471+00:00",
        "providers": [
            {
                "id": "comfyui",
                "label": "ComfyUI",
                "kind": "python_runtime",
                "installed": False,
                "repo_reachable": {"reachable": True, "ref_count": 200},
                "pip_show": {"installed": False},
                "weights_present": {"any_present": False},
                "executable_present": {"present": False},
                "proof_gate_version": "gen3d-source-runtime-verifier-v1",
            },
            {
                "id": "trellis2",
                "label": "TRELLIS",
                "kind": "python_runtime",
                "installed": False,
                "repo_reachable": {"reachable": True, "ref_count": 2},
                "pip_show": {"installed": False},
                "weights_present": {"any_present": False},
                "executable_present": {"present": False},
                "proof_gate_version": "gen3d-source-runtime-verifier-v1",
            },
            {
                "id": "hunyuan3d",
                "label": "Hunyuan3D",
                "kind": "python_runtime",
                "installed": False,
                "repo_reachable": {"reachable": True, "ref_count": 1},
                "pip_show": {"installed": False},
                "weights_present": {"any_present": False},
                "executable_present": {"present": False},
                "proof_gate_version": "gen3d-source-runtime-verifier-v1",
            },
            {
                "id": "triposr",
                "label": "TripoSR",
                "kind": "python_runtime",
                "installed": False,
                "repo_reachable": {"reachable": True, "ref_count": 3},
                "pip_show": {"installed": False},
                "weights_present": {"any_present": False},
                "executable_present": {"present": False},
                "proof_gate_version": "gen3d-source-runtime-verifier-v1",
            },
            {
                "id": "bambustudio_bridge",
                "label": "Bambu Studio",
                "kind": "desktop_app",
                "installed": True,
                "repo_reachable": {"reachable": True, "ref_count": 15},
                "pip_show": {"installed": False},
                "weights_present": {"any_present": False},
                "executable_present": {"present": True},
                "proof_gate_version": "gen3d-source-runtime-verifier-v1",
            },
        ],
        "summary": {
            "installed": ["bambustudio_bridge"],
            "not_installed": ["comfyui", "trellis2", "hunyuan3d", "triposr"],
            "repo_reachable": ["comfyui", "trellis2", "hunyuan3d", "triposr", "bambustudio_bridge"],
            "weights_present": [],
            "total": 5,
        },
    }
    proof_path = tmp_path / "GEN3D_VERIFY_2026-05-06.json"
    proof_path.write_text(json.dumps(proof), encoding="utf-8")
    return proof_path


# ---------------------------------------------------------------------------
# /api/gen3d/providers tests
# ---------------------------------------------------------------------------


class TestGen3DProviders:
    def test_returns_list(self, app_client, fake_proof_file, monkeypatch):
        """Endpoint returns a list of provider objects."""
        import hermes3d.api.routes.generation as gen_mod

        monkeypatch.setattr(gen_mod, "_LANE04_PROOF_PATH", fake_proof_file)
        monkeypatch.setattr(gen_mod, "port_reachable", lambda url: False)

        res = app_client.get("/api/gen3d/providers")
        assert res.status_code == 200, res.text
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 4  # comfyui, trellis2, hunyuan3d, triposr + bambustudio

    def test_required_fields_present(self, app_client, fake_proof_file, monkeypatch):
        """Each provider entry has the required fields."""
        import hermes3d.api.routes.generation as gen_mod

        monkeypatch.setattr(gen_mod, "_LANE04_PROOF_PATH", fake_proof_file)
        monkeypatch.setattr(gen_mod, "port_reachable", lambda url: False)

        res = app_client.get("/api/gen3d/providers")
        data = res.json()
        for provider in data:
            for field in ("provider_id", "label", "readiness", "installed", "repo_reachable"):
                assert field in provider, f"Missing field {field!r} in {provider}"

    def test_comfyui_not_available_when_port_unreachable(
        self, app_client, fake_proof_file, monkeypatch
    ):
        """ComfyUI readiness is not_installed when port is unreachable and proof says not installed."""
        import hermes3d.api.routes.generation as gen_mod

        monkeypatch.setattr(gen_mod, "_LANE04_PROOF_PATH", fake_proof_file)
        monkeypatch.setattr(gen_mod, "port_reachable", lambda url: False)

        res = app_client.get("/api/gen3d/providers")
        data = res.json()
        comfyui = next((p for p in data if p["provider_id"] == "comfyui"), None)
        assert comfyui is not None
        assert comfyui["readiness"] in ("not_installed", "unavailable")
        assert comfyui["installed"] is False

    def test_comfyui_available_when_port_reachable(self, app_client, fake_proof_file, monkeypatch):
        """ComfyUI readiness is 'available' when the port probe succeeds."""
        import hermes3d.api.routes.generation as gen_mod

        monkeypatch.setattr(gen_mod, "_LANE04_PROOF_PATH", fake_proof_file)
        monkeypatch.setattr(gen_mod, "port_reachable", lambda url: True)

        res = app_client.get("/api/gen3d/providers")
        data = res.json()
        comfyui = next((p for p in data if p["provider_id"] == "comfyui"), None)
        assert comfyui is not None
        assert comfyui["readiness"] == "available"
        assert comfyui["live_reachable"] is True

    def test_bambustudio_installed_from_proof(self, app_client, fake_proof_file, monkeypatch):
        """Bambu Studio shows installed=True based on Lane 04 proof executable probe."""
        import hermes3d.api.routes.generation as gen_mod

        monkeypatch.setattr(gen_mod, "_LANE04_PROOF_PATH", fake_proof_file)
        monkeypatch.setattr(gen_mod, "port_reachable", lambda url: False)

        res = app_client.get("/api/gen3d/providers")
        data = res.json()
        bambu = next((p for p in data if p["provider_id"] == "bambustudio_bridge"), None)
        assert bambu is not None
        assert bambu["installed"] is True

    def test_model_manifest_marks_downloaded_weights_installed_not_running(
        self, app_client, fake_proof_file, tmp_path, monkeypatch
    ):
        """Downloaded HF weights are real installed evidence, but not service availability."""
        import hermes3d.api.routes.generation as gen_mod

        model_root = tmp_path / "models"
        hunyuan_dir = model_root / "hunyuan3d"
        triposr_dir = model_root / "triposr"
        trellis_dir = model_root / "trellis"
        for directory in (hunyuan_dir, triposr_dir, trellis_dir):
            directory.mkdir(parents=True)
            (directory / "weights.bin").write_bytes(b"weights")
        comfy_root = tmp_path / "ComfyUI"
        comfy_root.mkdir()
        (comfy_root / "main.py").write_text("print('comfy')", encoding="utf-8")

        manifest_path = tmp_path / "GEN3D_MODEL_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "repos": [
                        {
                            "repo_id": "tencent/Hunyuan3D-2.1",
                            "local_dir": str(hunyuan_dir),
                            "expected_file_count": 1,
                            "actual_file_count_without_hf_cache": 1,
                            "expected_bytes": 7,
                            "actual_bytes_without_hf_cache": 7,
                            "revision": "rev-hy",
                        },
                        {
                            "repo_id": "stabilityai/TripoSR",
                            "local_dir": str(triposr_dir),
                            "expected_file_count": 1,
                            "actual_file_count_without_hf_cache": 1,
                            "expected_bytes": 7,
                            "actual_bytes_without_hf_cache": 7,
                            "revision": "rev-tripo",
                        },
                        {
                            "repo_id": "microsoft/TRELLIS-image-large",
                            "local_dir": str(trellis_dir),
                            "expected_file_count": 1,
                            "actual_file_count_without_hf_cache": 1,
                            "expected_bytes": 7,
                            "actual_bytes_without_hf_cache": 7,
                            "revision": "rev-trellis",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(gen_mod, "_LANE04_PROOF_PATH", fake_proof_file)
        monkeypatch.setattr(gen_mod, "_GEN3D_MODEL_MANIFEST_PATH", manifest_path)
        monkeypatch.setenv("HERMES3D_COMFYUI_ROOT", str(comfy_root))
        monkeypatch.setattr(gen_mod, "port_reachable", lambda url: False)

        res = app_client.get("/api/gen3d/providers")
        data = res.json()

        for provider_id in ("comfyui", "hunyuan3d", "triposr", "trellis2"):
            provider = next(p for p in data if p["provider_id"] == provider_id)
            assert provider["installed"] is True
            assert provider["readiness"] == "installed_not_running"
            assert provider["model_proof_source"] == "GEN3D_MODEL_MANIFEST.json"

        hunyuan = next(p for p in data if p["provider_id"] == "hunyuan3d")
        assert hunyuan["weights_present"] is True
        assert hunyuan["model_evidence"]["revision"] == "rev-hy"

    def test_proof_source_field_reflects_file(self, app_client, fake_proof_file, monkeypatch):
        """proof_source field is set when proof file is present."""
        import hermes3d.api.routes.generation as gen_mod

        monkeypatch.setattr(gen_mod, "_LANE04_PROOF_PATH", fake_proof_file)
        monkeypatch.setattr(gen_mod, "port_reachable", lambda url: False)

        res = app_client.get("/api/gen3d/providers")
        data = res.json()
        for provider in data:
            if provider["provider_id"] in ("comfyui", "trellis2", "hunyuan3d"):
                assert provider["proof_source"] == "GEN3D_VERIFY_2026-05-06.json"

    def test_gracefully_handles_missing_proof_file(self, app_client, tmp_path, monkeypatch):
        """If Lane 04 proof file is missing, endpoint still returns without error."""
        import hermes3d.api.routes.generation as gen_mod

        monkeypatch.setattr(gen_mod, "_LANE04_PROOF_PATH", tmp_path / "nonexistent.json")
        monkeypatch.setattr(gen_mod, "port_reachable", lambda url: False)

        res = app_client.get("/api/gen3d/providers")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        # Without proof, all providers return with proof_source=None
        for provider in data:
            assert provider["proof_source"] is None


# ---------------------------------------------------------------------------
# /api/gen3d/templates tests
# ---------------------------------------------------------------------------


class TestGen3DTemplates:
    def test_returns_list(self, app_client, monkeypatch):
        """Endpoint returns a list of template objects."""
        res = app_client.get("/api/gen3d/templates")
        assert res.status_code == 200, res.text
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_calibration_cube_always_present(self, app_client):
        """calibration_cube local template is always in the list."""
        res = app_client.get("/api/gen3d/templates")
        data = res.json()
        ids = [t["id"] for t in data]
        assert "calibration_cube" in ids

    def test_calibration_cube_is_local_executor(self, app_client):
        """calibration_cube template source is local_executor (no provider required)."""
        res = app_client.get("/api/gen3d/templates")
        data = res.json()
        cube = next(t for t in data if t["id"] == "calibration_cube")
        assert cube["source"] == "local_executor"
        assert cube["requires_provider"] is None

    def test_calibration_cube_has_real_outputs(self, app_client):
        """calibration_cube template outputs match what the executor actually produces."""
        res = app_client.get("/api/gen3d/templates")
        data = res.json()
        cube = next(t for t in data if t["id"] == "calibration_cube")
        assert "stl" in cube["outputs"]
        assert "proof_envelope" in cube["outputs"]

    def test_image_to_3d_templates_expose_3mf_outputs(self, app_client):
        """Image-backed generation templates expose 3MF print-package artifacts."""
        res = app_client.get("/api/gen3d/templates")
        data = res.json()
        by_id = {template["id"]: template for template in data}
        assert "3mf" in by_id["precision_image_relief"]["outputs"]
        assert "3mf" in by_id["hunyuan3d_image_to_3d"]["outputs"]

    def test_required_fields_present(self, app_client):
        """Each template has required fields."""
        res = app_client.get("/api/gen3d/templates")
        data = res.json()
        for template in data:
            for field in ("id", "name", "source", "description", "outputs", "requires_provider"):
                assert field in template, (
                    f"Missing field {field!r} in template {template.get('id')}"
                )

    def test_provider_backed_templates_reference_known_providers(self, app_client):
        """Provider-backed templates reference known provider IDs."""
        known = {"comfyui", "trellis2", "hunyuan3d", "triposr", "bambustudio_bridge"}
        res = app_client.get("/api/gen3d/templates")
        data = res.json()
        for template in data:
            if template["requires_provider"] is not None:
                assert template["requires_provider"] in known, (
                    f"Unknown provider {template['requires_provider']!r} in template {template['id']!r}"
                )

    def test_schema_presence_reflects_real_files(self, app_client, monkeypatch):
        """schema_present accurately reflects whether adapter schema file exists."""
        import hermes3d.api.routes.generation as gen_mod

        # Point to a directory that has no schema files
        with tempfile.TemporaryDirectory() as empty_dir:
            monkeypatch.setattr(gen_mod, "_SCHEMAS_DIR", Path(empty_dir))
            res = app_client.get("/api/gen3d/templates")
            data = res.json()
            for template in data:
                if template.get("schema_present") is not None:
                    assert template["schema_present"] is False
                    assert template["schema_file"] is None


# ---------------------------------------------------------------------------
# /api/generation/run reference-image relief tests
# ---------------------------------------------------------------------------


class TestReferenceImageReliefGeneration:
    def test_reference_relief_blocks_without_reference_artifact(self, app_client):
        res = app_client.post(
            "/api/generation/run",
            json={"prompt": "logo relief", "template_id": "reference_image_relief"},
        )
        assert res.status_code == 409
        body = res.json()["detail"]
        assert body["status"] == "blocked"
        assert "reference_artifact_id" in body["reason"]

    def test_reference_relief_persists_processed_image_mesh_proof_and_lineage(
        self, app_client, tmp_path, monkeypatch
    ):
        Image = pytest.importorskip("PIL.Image")
        import hermes3d.api.routes.generation as gen_mod
        from hermes3d.api.routes._common import execute, row, rows

        runtime_root = tmp_path / "runtime"
        monkeypatch.setattr(gen_mod, "implementation_path", lambda *parts: runtime_root.joinpath(*parts))

        source_path = tmp_path / "logo-source.png"
        source = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
        for y in range(8, 24):
            for x in range(8, 24):
                source.putpixel((x, y), (15, 15, 15, 255))
        source.save(source_path)

        reference_id = uuid.uuid4().hex
        execute(
            """
            INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
            VALUES (?, NULL, 'reference_image', 'test', 'INTAKE', NULL, 'logo-source.png', ?, ?, '{}')
            """,
            (reference_id, str(source_path), source_path.stat().st_size),
        )

        def write_processed(reference_path: Path, output_path: Path) -> dict:
            processed = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
            for y in range(8, 24):
                for x in range(8, 24):
                    processed.putpixel((x, y), (15, 15, 15, 255))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            processed.save(output_path)
            return {
                "engine": "rembg",
                "output_path": str(output_path),
                "alpha": {
                    "width": 32,
                    "height": 32,
                    "transparent_pixels": 768,
                    "foreground_pixels": 256,
                    "foreground_bbox": [8, 8, 24, 24],
                },
            }

        monkeypatch.setattr(gen_mod, "_remove_background_to_png", write_processed)

        res = app_client.post(
            "/api/generation/run",
            json={
                "prompt": "logo relief",
                "template_id": "reference_image_relief",
                "reference_artifact_id": reference_id,
                "constraints": {"size_mm": 60, "thickness_mm": 3},
            },
        )
        assert res.status_code == 202, res.text
        body = res.json()
        assert body["accepted"] is True
        assert body["template"] == "reference_image_relief"
        assert body["reference"]["id"] == reference_id
        assert body["processed_reference"]["id"]
        assert Path(body["artifact"]["file_path"]).is_file()
        assert Path(body["processed_reference"]["file_path"]).is_file()
        assert Path(body["proof"]["file_path"]).is_file()

        mesh_row = row("SELECT * FROM artifacts WHERE id = ?", (body["artifact"]["id"],))
        assert mesh_row is not None
        mesh_notes = json.loads(mesh_row["notes"])
        assert mesh_notes["reference_artifact_id"] == reference_id
        assert mesh_notes["processed_reference_artifact_id"] == body["processed_reference"]["id"]
        assert mesh_notes["background_removal"]["engine"] == "rembg"

        processed_row = row(
            "SELECT * FROM artifacts WHERE id = ?",
            (body["processed_reference"]["id"],),
        )
        assert processed_row is not None
        assert processed_row["evidence_type"] == "processed_image"
        assert json.loads(processed_row["notes"])["reference_artifact_id"] == reference_id

        events = rows(
            "SELECT * FROM proof_events WHERE event_type = 'generation.reference_relief.completed'"
        )
        assert len(events) == 1
        payload = json.loads(events[0]["payload"])
        assert payload["reference_artifact_id"] == reference_id
        assert payload["processed_reference_artifact_id"] == body["processed_reference"]["id"]


class TestPrecisionImageReliefGeneration:
    def test_precision_relief_persists_exact_image_mesh_proof_and_lineage(
        self, app_client, tmp_path, monkeypatch
    ):
        Image = pytest.importorskip("PIL.Image")
        import hermes3d.api.routes.generation as gen_mod
        from hermes3d.api.routes._common import execute, row, rows

        runtime_root = tmp_path / "runtime"
        monkeypatch.setattr(gen_mod, "implementation_path", lambda *parts: runtime_root.joinpath(*parts))

        source_path = tmp_path / "logo-source.png"
        source = Image.new("RGBA", (32, 32), (255, 255, 255, 255))
        for y in range(8, 24):
            for x in range(8, 24):
                source.putpixel((x, y), (80 + x, 80 + y, 80 + x, 255))
        source.save(source_path)

        reference_id = uuid.uuid4().hex
        execute(
            """
            INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
            VALUES (?, NULL, 'reference_image', 'test', 'INTAKE', NULL, 'logo-source.png', ?, ?, '{}')
            """,
            (reference_id, str(source_path), source_path.stat().st_size),
        )

        def write_processed(reference_path: Path, output_path: Path) -> dict:
            processed = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
            for y in range(8, 24):
                for x in range(8, 24):
                    shade = 80 + x + y
                    processed.putpixel((x, y), (shade, shade, shade, 255))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            processed.save(output_path)
            return {
                "engine": "rembg",
                "output_path": str(output_path),
                "alpha": {
                    "width": 32,
                    "height": 32,
                    "transparent_pixels": 768,
                    "foreground_pixels": 256,
                    "foreground_bbox": [8, 8, 24, 24],
                },
            }

        monkeypatch.setattr(gen_mod, "_remove_background_to_png", write_processed)

        res = app_client.post(
            "/api/generation/run",
            json={
                "prompt": "perfect 1:1 logo relief",
                "template_id": "precision_image_relief",
                "reference_artifact_id": reference_id,
                "constraints": {
                    "size_mm": 80,
                    "base_thickness_mm": 3,
                    "relief_height_mm": 3,
                    "max_resolution": 96,
                },
            },
        )
        assert res.status_code == 202, res.text
        body = res.json()
        assert body["accepted"] is True
        assert body["template"] == "precision_image_relief"
        assert Path(body["artifact"]["file_path"]).is_file()
        assert Path(body["package_3mf"]["file_path"]).is_file()
        assert Path(body["processed_reference"]["file_path"]).is_file()
        assert Path(body["proof"]["file_path"]).is_file()
        assert body["package_3mf"]["label"].endswith(".3mf")
        assert "3D/3dmodel.model" in body["package_3mf"]["package"]["entries"]
        assert body["mesh_build"]["foreground_cells"] > 0

        mesh_row = row("SELECT * FROM artifacts WHERE id = ?", (body["artifact"]["id"],))
        assert mesh_row is not None
        mesh_notes = json.loads(mesh_row["notes"])
        assert mesh_notes["reference_artifact_id"] == reference_id
        assert mesh_notes["processed_reference_artifact_id"] == body["processed_reference"]["id"]
        assert mesh_notes["package_3mf_artifact_id"] == body["package_3mf"]["id"]
        assert mesh_notes["mesh_build"]["mesh_width"] == 16
        assert mesh_notes["mesh"]["is_watertight"] is True

        package_row = row("SELECT * FROM artifacts WHERE id = ?", (body["package_3mf"]["id"],))
        assert package_row is not None
        assert package_row["evidence_type"] == "3mf"
        package_notes = json.loads(package_row["notes"])
        assert package_notes["mesh_artifact_id"] == body["artifact"]["id"]
        assert package_notes["processed_reference_artifact_id"] == body["processed_reference"]["id"]
        assert package_notes["package"]["format"] == "3mf"

        events = rows(
            "SELECT * FROM proof_events WHERE event_type = 'generation.precision_image_relief.completed'"
        )
        assert len(events) == 1
        payload = json.loads(events[0]["payload"])
        assert payload["reference_artifact_id"] == reference_id
        assert payload["processed_reference_artifact_id"] == body["processed_reference"]["id"]
        assert payload["package_3mf_artifact_id"] == body["package_3mf"]["id"]
