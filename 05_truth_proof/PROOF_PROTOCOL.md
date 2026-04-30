# PROOF PROTOCOL — Hermes3D-OS Lite

> The wire format for every signed proof envelope, and the protocol
> for verifying them.

This document is the canonical reference. The implementation lives in
`03_implementation/src/hermes3d/core/proof/proof_envelope.py`. Any
disagreement between this doc and the code is a bug; the code wins
in the short term but the doc must be brought into sync before the
next release.

---

## 1. Why this exists

A print farm that automates real-world hardware needs an audit trail.
Not "logs" — logs can be edited. **Signed envelopes** that an
independent verifier can walk through after the fact and report:

- "yes, the truth gates ran consistently with the recorded mesh +
  inputs," or
- "no, the envelope and the JSON disagree."

When the agentic surface is involved (LLMs proposing actions), the
proof envelope is the only thing that says what *actually* happened —
distinct from what an LLM said happened.

---

## 2. Envelope shape (v5, schema_version `1.0.0`)

Every envelope is a single JSON document with this canonical structure:

```json
{
  "schema_version": "1.0.0",
  "timestamp_unix": 1745000000.123,
  "generator": {
    "name": "desk_organizer",
    "version": "1.0.0",
    "signature": "4ee082d000"
  },
  "mesh": {
    "path": "/abs/path/to/mesh.stl",
    "sha256": "ab77d326...",
    "vertex_count": 314,
    "face_count": 624,
    "volume_mm3": 541411.42,
    "extents_mm": [180.0, 100.0, 90.0],
    "bbox_mm": [[-90.0, -50.0, 0.0], [90.0, 50.0, 90.0]],
    "is_watertight": true
  },
  "truth_gate_report": {
    "checks": [
      {
        "name": "watertight",
        "status": "pass",
        "threshold": {"required": true},
        "measured": {"watertight": true, "open_edges": 0},
        "message": "Mesh is watertight."
      }
    ],
    "overall_status": "pass"
  },
  "slicer_report": null,
  "visual_evidence": [],
  "signature": {
    "algorithm": "HMAC-SHA256",
    "value": "0f2cc45123a3..."
  }
}
```

Required fields:

- `schema_version` — semver string. Currently `"1.0.0"`.
- `timestamp_unix` — float, seconds since the Unix epoch (UTC).
- `generator` — provenance: `{name, version, signature}`. The
  `signature` here is a short hash of the generator's source, useful
  for detecting accidental code changes; it's separate from the
  envelope `signature`.
- `mesh` — content-addressed mesh metadata. The `sha256` is over the
  STL/3MF/OBJ file bytes, not over a parsed mesh.
- `truth_gate_report` — outcome of every gate that ran. See §4.
- `slicer_report` — `null` if no slicer ran; otherwise the typed
  slicer outcome dict.
- `visual_evidence` — list of `{path, sha256, view_name}` records for
  rendered evidence images.
- `signature` — HMAC-SHA256 over the canonical-JSON encoding of the
  document with the `signature` field removed. See §5.

Optional fields are listed even when empty (`visual_evidence: []`,
`slicer_report: null`) so the canonical encoding is stable across
producers.

---

## 3. The signing key

The HMAC key comes from the environment variable `HERMES3D_PROOF_KEY`.

If unset, the implementation falls back to the literal string
`hermes3d-default-proof-key-not-secret` and emits a `WARNING` log
line. This default exists so the kit's tests can run on a fresh clone
without configuration; **do not use it in production**.

Verifiers can be run in `--require-prod-key` mode, in which case any
envelope that verifies under the default key is rejected with a clear
diagnostic.

---

## 4. The truth-gate report

`truth_gate_report` records the outcome of every gate that ran for
this artefact. Each check is:

```json
{
  "name": "<gate_name>",
  "status": "pass | fail | skip",
  "threshold": { ... },
  "measured": { ... },
  "message": "<human-readable summary>"
}
```

The overall status is included as a top-level field
(`overall_status`) and equals `"pass"` iff every check is `pass` or
`skip`. Eight gate names are reserved (see
`00_overview/contract/TRUTH_AND_PROOF_SYSTEM.md`):

`schema`, `watertight`, `geometry`, `bed_fit`, `material_capable`,
`skill_safe`, `spool_sufficient`, `printer_health`.

A producer is allowed to emit fewer than eight checks (some gates
don't apply to every subject — e.g. the slicer subject doesn't run
`bed_fit`). The verifier doesn't require all eight; it just requires
that every check that *is* present has a valid status.

---

## 5. Canonical-JSON encoding

The signature is taken over the **canonical-JSON** encoding of the
document with the `signature` field removed.

Canonical JSON in this kit means:

1. UTF-8 encoded bytes.
2. JSON object keys sorted lexicographically at every depth.
3. No whitespace between tokens (Python: `separators=(",", ":")`).
4. No trailing newline.
5. Numbers: integers emitted without trailing `.0`; floats with
   Python's default shortest-round-trip representation.
6. Booleans: `true` / `false`. Null: `null`.

Reference Python implementation:

```python
import json
def canonical(doc: dict) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

The kit's `core.proof.proof_envelope.canonical_payload()` is the
authoritative implementation. JS / Rust / Go implementations in
adjacent tooling must match it byte-for-byte. We test this in
`tests/conformance/test_acceptance.py`.

---

## 6. Signing

```python
import hashlib, hmac

def sign(doc_without_sig: dict, key: bytes) -> str:
    return hmac.new(key, canonical(doc_without_sig), hashlib.sha256).hexdigest()

doc["signature"] = {
    "algorithm": "HMAC-SHA256",
    "value": sign(doc_without_sig, key),
}
```

---

## 7. Verifying

```python
def verify(doc: dict, key: bytes) -> bool:
    sig = doc.get("signature") or {}
    if sig.get("algorithm") != "HMAC-SHA256":
        return False
    body = {k: v for k, v in doc.items() if k != "signature"}
    expected = hmac.new(key, canonical(body), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig.get("value", ""), expected)
```

Notes:

- Use `hmac.compare_digest` to avoid timing attacks.
- A failing verify is **never** "fixed" by re-signing the doc; that
  would defeat the point.
- Callers that need to use the doc after verification should copy the
  dict first.

---

## 8. The conformance runner

`05_truth_proof/conformance_runner.py` walks every proof envelope
under a root and asserts:

- **Schema** — every required field is present and well-typed.
- **Canonical** — the JSON round-trips through `canonical()` to the
  same bytes.
- **Signature** — HMAC-SHA256 verifies under the configured key.
- **Cross-references** — envelopes that share a `mesh.sha256` make
  consistent claims about the mesh's metadata.

Run it directly:

```bash
python 05_truth_proof/conformance_runner.py --root var/acceptance-results
python 05_truth_proof/conformance_runner.py --root var/acceptance-results --json
python 05_truth_proof/conformance_runner.py --root var/acceptance-results --require-prod-key
```

CI runs the conformance runner against the acceptance run as part of
the `layer_b_smoke_and_acceptance` job.

---

## 9. Forward compatibility

`schema_version` is semver:

- **Patch bumps** (1.0.0 → 1.0.1) — typo fixes, doc clarifications,
  no schema change.
- **Minor bumps** (1.0.x → 1.1.0) — additive fields. Verifiers must
  ignore unknown fields.
- **Major bumps** (1.x.x → 2.0.0) — breaking changes. The verifier
  must dispatch on `schema_version` and may refuse to verify older
  envelopes (or upgrade them through a documented migration).

We do not ship an envelope migration tool in v5. When v6 changes the
format, that tool is in scope.

---

## 10. Failure modes and what they mean

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `signature mismatch` | Envelope edited after signing, OR `HERMES3D_PROOF_KEY` differs between signer and verifier | Compare keys; do not edit envelopes |
| `canonical encoding not stable` | Producer emitted non-canonical JSON (trailing whitespace, wrong number formatting) | Use the reference `canonical_payload()` |
| `unsupported algorithm` | An old prototype envelope (pre-v5) | Re-run the producing job |
| `missing signature` | Producer crashed mid-write, OR file truncated | Re-run; check disk space |
| `dev default key in use under --require-prod-key` | `HERMES3D_PROOF_KEY` not set | Set a strong random value before running production |
| `cross_ref: mesh sha256 disagreement` | Two envelopes claim the same mesh sha256 but record different metadata | Investigate — likely a kit bug |

---

## 11. The promise

When `proof-collect.{sh,ps1}` reports `verified=N, failed=0` — and
the conformance runner reports `all gates passed` — you know:

- Every recorded decision was made under a key you control.
- No envelope has been edited since signing.
- The check chain (truth gates → dispatch → slicer → upload) was
  consistent across the whole farm.

That's the audit trail. It's the kit's most boring feature and its
most important one.
