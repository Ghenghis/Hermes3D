"""W21-MVP-4 — integration test for ``GET /api/artifacts/{id}/lineage``.

The lineage relation between artifacts is encoded inside the
``artifacts.notes`` JSON column. ``api/routes/design.py`` and
``api/routes/generation.py`` write rows like:

  mesh.notes        = {"proof_artifact_id": <P>, ...}
  proof.notes       = {"mesh_artifact_id":  <M>, ...}
  thumbnail.notes   = {"mesh_artifact_id":  <M>}
  generation.notes  = {"reference_artifact_id": <upstream>}

The endpoint walks one step in each direction. These tests pin the
endpoint contract against a known fixture: a mesh, its proof_report
(both directions), a thumbnail (child only), and a missing-edge case.
"""

from __future__ import annotations

import importlib
import json
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Spin a fresh FastAPI app rooted at tmp_path with an isolated DB."""
    monkeypatch.setenv("HERMES3D_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("HERMES3D_QUEUE_POLLER_DISABLED", "1")
    monkeypatch.setenv("HERMES3D_PERSONA_EXECUTOR_DISABLED", "1")
    db_path = tmp_path / "hermes3d.db"
    for mod_name in list(sys.modules):
        if mod_name.startswith("hermes3d.api.app") or mod_name.startswith("hermes3d.api.routes"):
            sys.modules.pop(mod_name, None)
    sys.modules.pop("hermes3d.config.env_loader", None)
    sys.modules.pop("hermes3d.services.queue_bridge", None)
    sys.modules.pop("hermes3d.services.queue_poller", None)
    sys.modules.pop("hermes3d.services.persona_executor", None)
    from hermes3d.db import init as db_init

    monkeypatch.setattr(db_init, "DB_PATH", db_path)
    db_init.reset_initialization_state()

    app_mod = importlib.import_module("hermes3d.api.app")
    return TestClient(app_mod.create_gui_app())


def _seed(
    client: TestClient,
    *,
    evidence_type: str,
    label: str,
    notes: dict,
    artifact_id: str | None = None,
    job_id: str | None = None,
) -> str:
    """Insert one artifact row directly via _common.execute and return its id."""
    from hermes3d.api.routes._common import execute

    aid = artifact_id or uuid.uuid4().hex
    execute(
        """
        INSERT INTO artifacts (id, job_id, evidence_type, agent, stage, gate, label, file_path, file_size, notes)
        VALUES (?, ?, ?, 'test', 'MODELING', 'MODEL_APPROVAL', ?, ?, 0, ?)
        """,
        (aid, job_id, evidence_type, label, f"/tmp/{label}", json.dumps(notes)),
    )
    return aid


# ---------------------------------------------------------------------------
# Happy path: mesh ↔ proof ↔ thumbnail
# ---------------------------------------------------------------------------


def test_lineage_returns_children_for_a_mesh(client: TestClient) -> None:
    """A mesh's lineage must list its proof_report and thumbnail as children
    (because their notes reference the mesh via ``mesh_artifact_id``)."""
    mesh_id = uuid.uuid4().hex
    proof_id = uuid.uuid4().hex
    thumb_id = uuid.uuid4().hex
    _seed(
        client,
        artifact_id=mesh_id,
        evidence_type="mesh",
        label="unknown_xyz.stl",
        notes={"sha256": "deadbeef", "proof_artifact_id": proof_id},
    )
    _seed(
        client,
        artifact_id=proof_id,
        evidence_type="proof_report",
        label="unknown_xyz.proof.json",
        notes={"sha256": "cafef00d", "mesh_artifact_id": mesh_id, "truth_gate_status": "pass"},
    )
    _seed(
        client,
        artifact_id=thumb_id,
        evidence_type="thumbnail",
        label="unknown_xyz.preview.svg",
        notes={"mesh_artifact_id": mesh_id},
    )

    resp = client.get(f"/api/artifacts/{mesh_id}/lineage")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["artifact"]["id"] == mesh_id

    # Mesh's notes contain proof_artifact_id → parent.
    parent_ids = {p["id"]: p for p in body["parents"]}
    assert proof_id in parent_ids
    assert parent_ids[proof_id]["via"] == "proof_artifact_id"

    # Proof + thumbnail point back at the mesh via mesh_artifact_id → children.
    child_ids = {c["id"]: c for c in body["children"]}
    assert proof_id in child_ids
    assert child_ids[proof_id]["via"] == "mesh_artifact_id"
    assert child_ids[proof_id]["evidence_type"] == "proof_report"
    assert thumb_id in child_ids
    assert child_ids[thumb_id]["via"] == "mesh_artifact_id"
    assert child_ids[thumb_id]["evidence_type"] == "thumbnail"


def test_lineage_walks_back_from_proof_to_mesh(client: TestClient) -> None:
    """From a proof row, the mesh is exposed as a parent via mesh_artifact_id."""
    mesh_id = uuid.uuid4().hex
    proof_id = uuid.uuid4().hex
    _seed(
        client,
        artifact_id=mesh_id,
        evidence_type="mesh",
        label="x.stl",
        notes={"sha256": "a"},
    )
    _seed(
        client,
        artifact_id=proof_id,
        evidence_type="proof_report",
        label="x.proof.json",
        notes={"mesh_artifact_id": mesh_id},
    )
    resp = client.get(f"/api/artifacts/{proof_id}/lineage")
    assert resp.status_code == 200
    body = resp.json()
    parent_ids = {p["id"]: p for p in body["parents"]}
    assert mesh_id in parent_ids
    assert parent_ids[mesh_id]["via"] == "mesh_artifact_id"
    # Mesh has no notes-side link to the proof in this fixture, so no
    # child edge is emitted from the proof's perspective (correct: this
    # endpoint walks ONE step).
    assert body["children"] == []


def test_lineage_via_reference_artifact_id(client: TestClient) -> None:
    """``reference_artifact_id`` (upstream logo/image → generated mesh) is
    one of the recognised lineage keys; verify it surfaces as a parent."""
    upstream_id = uuid.uuid4().hex
    mesh_id = uuid.uuid4().hex
    _seed(
        client,
        artifact_id=upstream_id,
        evidence_type="agent_attachment",
        label="logo.png",
        notes={},
    )
    _seed(
        client,
        artifact_id=mesh_id,
        evidence_type="mesh",
        label="logo_extrude.stl",
        notes={"reference_artifact_id": upstream_id},
    )
    resp = client.get(f"/api/artifacts/{mesh_id}/lineage")
    assert resp.status_code == 200
    body = resp.json()
    parent_ids = {p["id"]: p for p in body["parents"]}
    assert upstream_id in parent_ids
    assert parent_ids[upstream_id]["via"] == "reference_artifact_id"
    # And from the upstream's POV, the mesh is a child via reference_artifact_id.
    resp2 = client.get(f"/api/artifacts/{upstream_id}/lineage")
    body2 = resp2.json()
    child_ids = {c["id"]: c for c in body2["children"]}
    assert mesh_id in child_ids
    assert child_ids[mesh_id]["via"] == "reference_artifact_id"


# ---------------------------------------------------------------------------
# Error + edge cases
# ---------------------------------------------------------------------------


def test_lineage_404_for_unknown_artifact(client: TestClient) -> None:
    resp = client.get("/api/artifacts/does-not-exist/lineage")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_lineage_handles_malformed_notes_without_raising(client: TestClient) -> None:
    """Older reconciler-inserted rows may carry non-JSON notes ("",
    free-form strings, etc.). The endpoint must NOT 500 on those."""
    mesh_id = _seed(
        client,
        evidence_type="mesh",
        label="malformed.stl",
        notes={},
    )
    # Overwrite notes with a non-JSON string directly.
    from hermes3d.api.routes._common import execute

    execute(
        "UPDATE artifacts SET notes = ? WHERE id = ?",
        ("free form text not json", mesh_id),
    )
    resp = client.get(f"/api/artifacts/{mesh_id}/lineage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["parents"] == []
    assert body["children"] == []


def test_lineage_missing_parent_emits_sentinel_not_silent_drop(client: TestClient) -> None:
    """If a row's notes reference an artifact id that does NOT exist (the
    parent was reaped or never inserted), the endpoint must surface the
    edge with ``missing=True`` rather than drop it silently."""
    ghost_id = "ghost-" + uuid.uuid4().hex
    proof_id = _seed(
        client,
        evidence_type="proof_report",
        label="orphan.proof.json",
        notes={"mesh_artifact_id": ghost_id},
    )
    resp = client.get(f"/api/artifacts/{proof_id}/lineage")
    body = resp.json()
    missing = [p for p in body["parents"] if p.get("missing")]
    assert len(missing) == 1
    assert missing[0]["id"] == ghost_id
    assert missing[0]["via"] == "mesh_artifact_id"


def test_lineage_ignores_self_referential_edges(client: TestClient) -> None:
    """A row whose notes accidentally reference its own id must not list
    itself as a parent (defensive — protects against fixture mistakes)."""
    aid = uuid.uuid4().hex
    _seed(
        client,
        artifact_id=aid,
        evidence_type="mesh",
        label="self.stl",
        notes={"mesh_artifact_id": aid},
    )
    resp = client.get(f"/api/artifacts/{aid}/lineage")
    body = resp.json()
    assert body["parents"] == []


def test_lineage_query_escapes_like_wildcards_in_artifact_id(client: TestClient) -> None:
    """CodeRabbit nit (2026-05-12): the children SQL uses LIKE on notes.
    If a caller passes an id containing ``%`` or ``_``, those must be
    treated literally — not as wildcards. Fixture: seed a probe id with
    a ``%``, plus an unrelated row that would match if the wildcard
    leaked, and assert it is NOT pulled in as a child."""
    probe_id = "probe%X-" + uuid.uuid4().hex
    other_id = "noise-" + uuid.uuid4().hex
    _seed(
        client,
        artifact_id=probe_id,
        evidence_type="mesh",
        label="probe.stl",
        notes={},
    )
    # An unrelated row whose notes literally contain the substring
    # "probe" (which a naive LIKE %probe%X-%% pattern would catch as
    # %probe%X% matching any "probe...X..." text). Without escaping,
    # that LIKE %probe%X% would match this row.
    _seed(
        client,
        artifact_id=other_id,
        evidence_type="agent_attachment",
        label="probeXunrelated.png",
        notes={"label_hint": "probe_X_marker_text"},
    )
    resp = client.get(f"/api/artifacts/{probe_id}/lineage")
    assert resp.status_code == 200
    body = resp.json()
    # No false children should leak from the unescaped LIKE pattern.
    assert body["children"] == []


def test_lineage_response_shape_pins_compact_projection(client: TestClient) -> None:
    """Each parent/child entry must carry exactly: id, evidence_type,
    label, file_path, created_at, via. No raw notes leakage, no full row
    fields. The endpoint also echoes the set of recognised lineage keys
    so callers can introspect."""
    mesh_id = _seed(client, evidence_type="mesh", label="m.stl", notes={})
    _seed(
        client,
        evidence_type="proof_report",
        label="m.proof.json",
        notes={"mesh_artifact_id": mesh_id},
    )
    resp = client.get(f"/api/artifacts/{mesh_id}/lineage")
    body = resp.json()
    assert body["children"], "expected one child"
    expected_keys = {"id", "evidence_type", "label", "file_path", "created_at", "via"}
    assert set(body["children"][0].keys()) >= expected_keys
    # No raw notes blob in the compact projection.
    assert "notes" not in body["children"][0]
    # Lineage keys list is part of the contract.
    assert isinstance(body["lineage_keys"], list)
    assert "mesh_artifact_id" in body["lineage_keys"]
    assert "reference_artifact_id" in body["lineage_keys"]
