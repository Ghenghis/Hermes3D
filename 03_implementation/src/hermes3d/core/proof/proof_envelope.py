"""HMAC-signed proof envelopes binding a Truth Gate report to evidence files.

Schema version: 1.0.0

A proof envelope contains:
    - schema_version: str
    - timestamp_unix: float
    - generator: {name, version, signature}
    - mesh: {path, sha256, vertex_count, face_count, bbox_mm, volume_mm3}
    - truth_gate_report: {entire TruthGateReport.to_dict()}
    - slicer_report: optional dict
    - visual_evidence: list[{path, sha256, view_name}]
    - signature: {algorithm: "HMAC-SHA256", value: hex_digest}

The signature is computed over `canonical_payload(envelope)` which is the
JSON-serialised envelope WITHOUT the signature field, with sorted keys and
no whitespace. This is deterministic so verification is exact.

The HMAC key is read from the environment variable HERMES3D_PROOF_KEY. If
it is unset, a default key is used which is logged (proof remains valid for
self-check but is NOT cryptographically sealed against tampering by anyone
who has the source). Production deployments MUST set HERMES3D_PROOF_KEY.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import trimesh

from hermes3d.core.validation.truth_gate import (
    TruthGateConfig,
    TruthGateReport,
    run_truth_gate,
)

LOG = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0.0"
DEFAULT_KEY_NOTE = (
    "USING DEFAULT PROOF KEY — set HERMES3D_PROOF_KEY in the environment "
    "for tamper-evident signatures. See docs/SECURITY.md."
)
_DEFAULT_KEY = b"hermes3d-default-proof-key-not-secret"


class ProofVerificationError(Exception):
    """Raised by verify_proof when the envelope fails any check."""


@dataclass
class VisualEvidence:
    """Path + hash + view name for a single rendered evidence image."""

    path: str
    sha256: str
    view_name: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256, "view_name": self.view_name}

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> "VisualEvidence":
        return cls(path=d["path"], sha256=d["sha256"], view_name=d["view_name"])


@dataclass
class ProofEnvelope:
    schema_version: str
    timestamp_unix: float
    generator: dict[str, str]
    mesh: dict[str, Any]
    truth_gate_report: dict[str, Any]
    slicer_report: dict[str, Any] | None = None
    visual_evidence: list[VisualEvidence] = field(default_factory=list)
    signature: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "schema_version": self.schema_version,
            "timestamp_unix": self.timestamp_unix,
            "generator": self.generator,
            "mesh": self.mesh,
            "truth_gate_report": self.truth_gate_report,
            "visual_evidence": [v.to_dict() for v in self.visual_evidence],
        }
        if self.slicer_report is not None:
            d["slicer_report"] = self.slicer_report
        if self.signature is not None:
            d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ProofEnvelope":
        return cls(
            schema_version=d["schema_version"],
            timestamp_unix=float(d["timestamp_unix"]),
            generator=d["generator"],
            mesh=d["mesh"],
            truth_gate_report=d["truth_gate_report"],
            slicer_report=d.get("slicer_report"),
            visual_evidence=[VisualEvidence.from_dict(v) for v in d.get("visual_evidence", [])],
            signature=d.get("signature"),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _proof_key() -> bytes:
    env = os.environ.get("HERMES3D_PROOF_KEY")
    if env:
        return env.encode("utf-8")
    LOG.warning(DEFAULT_KEY_NOTE)
    return _DEFAULT_KEY


def canonical_payload(envelope: ProofEnvelope) -> bytes:
    """Return the deterministic byte-string that the signature is computed over."""
    d = envelope.to_dict()
    d.pop("signature", None)
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign(envelope: ProofEnvelope) -> dict[str, str]:
    key = _proof_key()
    payload = canonical_payload(envelope)
    digest = hmac.new(key, payload, hashlib.sha256).hexdigest()
    return {"algorithm": "HMAC-SHA256", "value": digest}


def _mesh_metadata(mesh_path: Path) -> dict[str, Any]:
    mesh = trimesh.load(str(mesh_path), force="mesh")
    return {
        "path": str(mesh_path.resolve()),
        "sha256": _file_sha256(mesh_path),
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "bbox_mm": [list(map(float, mesh.bounds[0])), list(map(float, mesh.bounds[1]))],
        "extents_mm": list(map(float, mesh.extents)),
        "volume_mm3": float(mesh.volume),
        "is_watertight": bool(mesh.is_watertight),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_proof(
    *,
    mesh_path: str | Path,
    output_path: str | Path | None = None,
    path: str | Path | None = None,
    generator_name: str,
    generator_version: str,
    generator_signature: str,
    truth_gate_config: TruthGateConfig | None = None,
    truth_gate_report: TruthGateReport | dict[str, Any] | None = None,
    slicer_report: dict[str, Any] | None = None,
    visual_evidence_paths: (list[tuple[str, str | Path]] | list[Path] | list[str] | None) = None,
    timestamp_unix: float | None = None,
) -> Path:
    """Build, sign, and write a proof envelope JSON file.

    Args:
        mesh_path: Path to the mesh file the proof is about.
        output_path / path: Where to write the proof JSON. Either name is
            accepted (``path=`` is the modern alias used by the integration
            harness; ``output_path=`` is preserved for backward compatibility).
        generator_name: e.g. "desk_organizer".
        generator_version: e.g. "1.0.0".
        generator_signature: Stable identifier of the inputs that produced the
            mesh (e.g. ``OrganizerSpec.signature()``).
        truth_gate_config: If ``truth_gate_report`` is None, the gate is run
            with this config (defaults to a default-constructed
            TruthGateConfig).
        truth_gate_report: Pre-computed report. Either a TruthGateReport
            object OR its ``.to_dict()`` form. If None, the gate is run.
        slicer_report: Optional slicer summary dict.
        visual_evidence_paths: Either a list of ``(view_name, image_path)``
            tuples, or a flat list of paths (in which case the view names
            are derived from filename stems).
        timestamp_unix: Override the wall-clock timestamp baked into the
            envelope. Use this for reproducible / deterministic builds and
            for tests that compare two envelopes for byte-equality.

    Returns: ``Path`` to the written proof file.
    """
    target = output_path if output_path is not None else path
    if target is None:
        raise TypeError("write_proof requires either output_path= or path=")
    mesh_p = Path(mesh_path)
    if not mesh_p.is_file():
        raise FileNotFoundError(f"mesh not found: {mesh_p}")

    # Accept either a TruthGateReport instance or its dict form.
    if truth_gate_report is None:
        cfg = truth_gate_config or TruthGateConfig()
        truth_gate_report = run_truth_gate(mesh_p, cfg)
    if isinstance(truth_gate_report, TruthGateReport):
        truth_gate_dict = truth_gate_report.to_dict()
    elif isinstance(truth_gate_report, dict):
        truth_gate_dict = truth_gate_report
    else:
        raise TypeError(
            "truth_gate_report must be TruthGateReport, dict, or None; "
            f"got {type(truth_gate_report).__name__}"
        )

    # Normalise visual_evidence_paths to (name, path) tuples.
    raw_visuals = visual_evidence_paths or []
    normalised: list[tuple[str, Path]] = []
    for entry in raw_visuals:
        if isinstance(entry, tuple) and len(entry) == 2:
            view_name, p = entry
            normalised.append((str(view_name), Path(p)))
        else:
            ep = Path(entry)  # type: ignore[arg-type]
            normalised.append((ep.stem, ep))

    visual_evidence: list[VisualEvidence] = []
    for view_name, ep in normalised:
        if not ep.is_file():
            raise FileNotFoundError(f"visual evidence not found: {ep}")
        visual_evidence.append(
            VisualEvidence(
                path=str(ep.resolve()),
                sha256=_file_sha256(ep),
                view_name=view_name,
            )
        )

    ts = float(timestamp_unix) if timestamp_unix is not None else time.time()
    envelope = ProofEnvelope(
        schema_version=SCHEMA_VERSION,
        timestamp_unix=ts,
        generator={
            "name": generator_name,
            "version": generator_version,
            "signature": generator_signature,
        },
        mesh=_mesh_metadata(mesh_p),
        truth_gate_report=truth_gate_dict,
        slicer_report=slicer_report,
        visual_evidence=visual_evidence,
    )
    envelope.signature = _sign(envelope)

    out = Path(target)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fp:
        json.dump(envelope.to_dict(), fp, indent=2, sort_keys=True)
    return out.resolve()


def verify_proof(proof_path: str | Path, *, check_files: bool = True) -> ProofEnvelope:
    """Verify the HMAC signature and (optionally) the referenced files.

    Args:
        proof_path: Path to a proof JSON file.
        check_files: If True, re-hash the referenced mesh and visual
            evidence files and compare to the recorded hashes.

    Returns: the parsed ProofEnvelope on success.

    Raises ProofVerificationError on any mismatch.
    """
    p = Path(proof_path)
    with open(p, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    envelope = ProofEnvelope.from_dict(data)

    if envelope.schema_version != SCHEMA_VERSION:
        raise ProofVerificationError(
            f"schema_version mismatch: got {envelope.schema_version!r}, "
            f"this verifier supports {SCHEMA_VERSION!r}"
        )

    if not envelope.signature or "value" not in envelope.signature:
        raise ProofVerificationError("envelope is missing a signature")

    expected = envelope.signature["value"]
    payload = canonical_payload(envelope)
    actual = hmac.new(_proof_key(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise ProofVerificationError(
            "signature mismatch — envelope was tampered with or the key changed"
        )

    if check_files:
        mesh_p = Path(envelope.mesh["path"])
        if not mesh_p.is_file():
            raise ProofVerificationError(f"referenced mesh not found: {mesh_p}")
        if _file_sha256(mesh_p) != envelope.mesh["sha256"]:
            raise ProofVerificationError(
                f"mesh hash mismatch: file at {mesh_p} differs from recorded hash"
            )
        for ve in envelope.visual_evidence:
            ep = Path(ve.path)
            if not ep.is_file():
                raise ProofVerificationError(f"visual evidence not found: {ep}")
            if _file_sha256(ep) != ve.sha256:
                raise ProofVerificationError(f"visual evidence hash mismatch: {ep}")

    return envelope


__all__ = [
    "SCHEMA_VERSION",
    "ProofEnvelope",
    "ProofVerificationError",
    "VisualEvidence",
    "canonical_payload",
    "verify_proof",
    "write_proof",
]
