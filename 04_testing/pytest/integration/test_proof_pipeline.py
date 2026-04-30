"""Integration test — the full proof-bundle pipeline end-to-end.

Walks every step the production system performs:

    1. Build a parametric desk organizer mesh.
    2. Export STL.
    3. Run Truth Gate (with a real printer profile).
    4. Render 6 deterministic views (PNG).
    5. Sign a proof envelope (HMAC-SHA256).
    6. Verify the envelope on a fresh client.
    7. Tamper with the mesh, re-verify, expect failure.

If this passes, the proof system is end-to-end functional. This is the
strongest single check in the suite — it touches every runnable subsystem.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hermes3d.core.design.desk_organizer import OrganizerSpec, build_organizer
from hermes3d.core.proof.proof_envelope import (
    ProofVerificationError,
    verify_proof,
    write_proof,
)
from hermes3d.core.validation.truth_gate import TruthGateConfig, run_truth_gate
from hermes3d.core.visual.render import render_all_views


@pytest.fixture(autouse=True)
def proof_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES3D_PROOF_KEY", "test-key-do-not-use-in-prod")


def test_full_proof_pipeline(tmp_path: Path) -> None:
    # Step 1+2: build + export
    mesh = build_organizer(OrganizerSpec())
    stl = tmp_path / "organizer.stl"
    mesh.export(stl)
    assert stl.stat().st_size > 0

    # Step 3: Truth Gate against an actual printer profile
    cfg = TruthGateConfig(printer_profile_id="prusa_mk3s")
    tg_report = run_truth_gate(stl, cfg)
    assert tg_report.passed, f"Truth Gate failed: {tg_report.to_dict()}"

    # Step 4: render 6 canonical views
    render_dir = tmp_path / "views"
    rendered = render_all_views(mesh, render_dir, name_prefix="organizer")
    assert len(rendered) == 6, f"Expected 6 views, got {len(rendered)}"
    for _name, png in rendered:
        assert Path(png).stat().st_size > 1000, f"Render too small: {png}"

    # Step 5: sign the proof envelope
    proof_path = tmp_path / "proof.json"
    visual_paths = [Path(p) for _name, p in rendered]
    write_proof(
        path=proof_path,
        mesh_path=stl,
        truth_gate_report=tg_report.to_dict(),
        visual_evidence_paths=visual_paths,
        slicer_report=None,
        generator_name="hermes3d.core.design.desk_organizer",
        generator_version="1.0.0",
        generator_signature=OrganizerSpec().signature(),
    )
    assert proof_path.exists()

    # Step 6: verify on a fresh load
    envelope = verify_proof(proof_path, check_files=True)
    assert envelope.signature["algorithm"] == "HMAC-SHA256"
    assert envelope.mesh["sha256"] == tg_report.mesh_sha256
    assert len(envelope.visual_evidence) == 6

    # Step 7: tamper with the mesh -> verification must fail
    with stl.open("ab") as fh:
        fh.write(b"X")  # one extra byte
    with pytest.raises(ProofVerificationError):
        verify_proof(proof_path, check_files=True)


def test_proof_rejects_tampered_envelope(tmp_path: Path) -> None:
    """Editing the JSON itself (not the mesh) must also be detected by the
    HMAC signature — the signature covers the canonical payload."""
    mesh = build_organizer(
        OrganizerSpec(
            width_mm=120,
            depth_mm=80,
            height_mm=45,
            tray_count=2,
            pen_count=2,
            phone_slot=False,
            cable_passthrough=False,
        )
    )
    stl = tmp_path / "compact.stl"
    mesh.export(stl)
    cfg = TruthGateConfig(printer_profile_id="flsun_qqs_pro")
    tg = run_truth_gate(stl, cfg)
    proof_path = tmp_path / "proof.json"
    write_proof(
        path=proof_path,
        mesh_path=stl,
        truth_gate_report=tg.to_dict(),
        visual_evidence_paths=[],
        generator_name="test",
        generator_version="1.0.0",
        generator_signature="abc123",
    )
    # Tamper with the truth_gate_report block but keep signature
    raw = proof_path.read_text(encoding="utf-8")
    tampered = raw.replace('"overall_status": "pass"', '"overall_status": "FORGED"')
    proof_path.write_text(tampered, encoding="utf-8")
    with pytest.raises(ProofVerificationError):
        verify_proof(proof_path, check_files=False)


def test_proof_envelope_is_deterministic(tmp_path: Path) -> None:
    """Given identical inputs (incl. timestamp), proof signature must be
    deterministic — required for caching + reproducible builds."""
    mesh = build_organizer(OrganizerSpec())
    stl = tmp_path / "det.stl"
    mesh.export(stl)
    cfg = TruthGateConfig(printer_profile_id="creality_cr10s")
    tg = run_truth_gate(stl, cfg)

    p1 = tmp_path / "p1.json"
    p2 = tmp_path / "p2.json"
    # Use a fixed timestamp so signatures match.
    write_proof(
        path=p1,
        mesh_path=stl,
        truth_gate_report=tg.to_dict(),
        visual_evidence_paths=[],
        generator_name="g",
        generator_version="1.0.0",
        generator_signature="x",
        timestamp_unix=1700000000.0,
    )
    write_proof(
        path=p2,
        mesh_path=stl,
        truth_gate_report=tg.to_dict(),
        visual_evidence_paths=[],
        generator_name="g",
        generator_version="1.0.0",
        generator_signature="x",
        timestamp_unix=1700000000.0,
    )
    import json

    e1 = json.loads(p1.read_text())
    e2 = json.loads(p2.read_text())
    assert e1["signature"]["value"] == e2["signature"]["value"]
