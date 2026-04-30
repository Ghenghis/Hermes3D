"""Proof system: signed evidence envelopes for every Truth Gate result.

Public API:
    from hermes3d.core.proof import write_proof, verify_proof, ProofEnvelope

A proof envelope is a JSON file binding together:
  - the mesh hash (SHA-256)
  - the generator signature (parameters)
  - the Truth Gate report
  - optional slicer report
  - optional visual evidence paths + their hashes
  - an HMAC-SHA256 signature over the canonical JSON payload

Verification is pure-Python and has no external dependencies beyond the
standard library + Pydantic.
"""

from hermes3d.core.proof.proof_envelope import (
    ProofEnvelope,
    ProofVerificationError,
    VisualEvidence,
    canonical_payload,
    verify_proof,
    write_proof,
)

__all__ = [
    "ProofEnvelope",
    "ProofVerificationError",
    "VisualEvidence",
    "canonical_payload",
    "verify_proof",
    "write_proof",
]
