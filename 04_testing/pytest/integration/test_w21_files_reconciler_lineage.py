from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def isolated_reconciler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point the files reconciler and DB at a temp workspace."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("HERMES3D_QUEUE_POLLER_DISABLED", "1")
    monkeypatch.setenv("HERMES3D_PERSONA_EXECUTOR_DISABLED", "1")
    for mod_name in list(sys.modules):
        if mod_name.startswith("hermes3d.api.routes"):
            sys.modules.pop(mod_name, None)

    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", tmp_path / "hermes3d.db")
    db_init.reset_initialization_state()
    db_init.init_db(force=True)

    from hermes3d.api.routes import artifacts, files

    monkeypatch.setattr(files, "_VAR_DIR", tmp_path / "var")
    return files, artifacts, db_init


def _write(path: Path, data: bytes = b"proof-backed test bytes") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _artifact_by_label(db_init, label: str) -> dict:
    conn = db_init.connect()
    try:
        row = conn.execute("SELECT * FROM artifacts WHERE label = ?", (label,)).fetchone()
        assert row is not None, f"missing artifact row for {label}"
        return dict(row)
    finally:
        conn.close()


def _notes(row: dict) -> dict:
    return json.loads(row["notes"])


def test_files_scanner_marks_zero_byte_packages_unusable(isolated_reconciler) -> None:
    files, _artifacts, _db_init = isolated_reconciler
    run = files._VAR_DIR / "generation" / "run-zero"
    _write(run / "good.stl", b"solid good\nendsolid good\n")
    _write(run / "bad.manual-test.3mf", b"")

    body = files.list_files()
    indexed = {item.name: item for item in body.items}

    assert indexed["good.stl"].usable is True
    assert indexed["good.stl"].invalid_reason is None
    assert indexed["bad.manual-test.3mf"].usable is False
    assert indexed["bad.manual-test.3mf"].invalid_reason == "zero_byte_artifact"


def test_reconcile_backlinks_sibling_outputs_for_lineage(isolated_reconciler) -> None:
    files, artifacts, db_init = isolated_reconciler
    run = files._VAR_DIR / "generation" / "run-linked"
    _write(run / "logo_relief.stl", b"solid logo\nendsolid logo\n")
    _write(run / "logo_relief.proof.json", b'{"truth_gate":"pass"}')
    _write(run / "logo_relief.rembg.png", b"\x89PNG\r\n\x1a\nforeground")
    _write(run / "logo_relief.preview.svg", b"<svg />")
    _write(run / "logo_relief.3mf", b"PK\x03\x04real package")

    inserted = files.reconcile_var_artifacts()
    assert inserted["generation"] == 5

    mesh = _artifact_by_label(db_init, "logo_relief.stl")
    proof = _artifact_by_label(db_init, "logo_relief.proof.json")
    processed = _artifact_by_label(db_init, "logo_relief.rembg.png")
    preview = _artifact_by_label(db_init, "logo_relief.preview.svg")
    package = _artifact_by_label(db_init, "logo_relief.3mf")

    mesh_notes = _notes(mesh)
    assert mesh_notes["proof_artifact_id"] == proof["id"]
    assert mesh_notes["processed_reference_artifact_id"] == processed["id"]
    assert mesh_notes["thumbnail_artifact_id"] == preview["id"]
    assert mesh_notes["package_3mf_artifact_id"] == package["id"]

    assert _notes(proof)["mesh_artifact_id"] == mesh["id"]
    assert _notes(processed)["mesh_artifact_id"] == mesh["id"]
    assert _notes(preview)["mesh_artifact_id"] == mesh["id"]
    assert _notes(package)["mesh_artifact_id"] == mesh["id"]

    lineage = artifacts.artifact_lineage(mesh["id"])
    child_ids = {child["id"] for child in lineage["children"]}
    parent_ids = {parent["id"] for parent in lineage["parents"]}

    assert proof["id"] in child_ids
    assert processed["id"] in child_ids
    assert preview["id"] in child_ids
    assert package["id"] in child_ids
    assert proof["id"] in parent_ids
    assert processed["id"] in parent_ids
    assert preview["id"] in parent_ids
    assert package["id"] in parent_ids


def test_reconcile_does_not_link_zero_byte_package_as_usable_child(isolated_reconciler) -> None:
    files, artifacts, db_init = isolated_reconciler
    run = files._VAR_DIR / "generation" / "run-invalid-package"
    _write(run / "part.stl", b"solid part\nendsolid part\n")
    _write(run / "part.proof.json", b'{"truth_gate":"pass"}')
    _write(run / "part.manual-test.3mf", b"")

    files.reconcile_var_artifacts()

    mesh = _artifact_by_label(db_init, "part.stl")
    package = _artifact_by_label(db_init, "part.manual-test.3mf")
    mesh_notes = _notes(mesh)
    package_notes = _notes(package)

    assert "package_3mf_artifact_id" not in mesh_notes
    assert package_notes["valid"] is False
    assert package_notes["invalid_reason"] == "zero_byte_artifact"

    lineage = artifacts.artifact_lineage(mesh["id"])
    child_ids = {child["id"] for child in lineage["children"]}
    assert package["id"] in child_ids
    assert all(
        child["via"] == "mesh_artifact_id"
        for child in lineage["children"]
        if child["id"] == package["id"]
    )
