#!/usr/bin/env python3
"""
05_truth_proof/conformance_runner.py

Walk every proof envelope under a root directory and assert four kinds
of conformance:

  1. Schema    — required fields present and well-typed
  2. Canonical — JSON round-trips through the canonical encoder
  3. Signature — HMAC-SHA256 verifies under HERMES3D_PROOF_KEY
                 (or the documented default)
  4. Cross-ref — envelopes sharing the same mesh.sha256 must agree
                 on mesh metadata

Exits 0 iff every gate passes for every envelope.

Usage:
    python 05_truth_proof/conformance_runner.py
    python 05_truth_proof/conformance_runner.py --root var/acceptance-results
    python 05_truth_proof/conformance_runner.py --json
    python 05_truth_proof/conformance_runner.py --require-prod-key
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA_VERSION_SUPPORTED = "1.0.0"
DEFAULT_KEY = b"hermes3d-default-proof-key-not-secret"

REQUIRED_FIELDS = (
    "schema_version",
    "timestamp_unix",
    "generator",
    "mesh",
    "truth_gate_report",
    "signature",
)
REQUIRED_GENERATOR_FIELDS = ("name", "version")
REQUIRED_MESH_FIELDS = ("sha256",)
REQUIRED_REPORT_FIELDS = ("checks",)
REQUIRED_SIG_FIELDS = ("algorithm", "value")


def canonical(doc: dict) -> bytes:
    """Canonical-JSON encoding per PROOF_PROTOCOL §5."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def find_envelopes(root: Path) -> list[Path]:
    """Locate every proof envelope under root.

    Patterns matched:
      * ``*.proof.json``
      * ``proof.json``
      * ``proof-*.json`` (the acceptance runner's per-printer files)
    """
    if not root.exists():
        return []
    out: list[Path] = []
    for p in root.rglob("*.json"):
        name = p.name
        if (
            name.endswith(".proof.json")
            or name == "proof.json"
            or name.startswith("proof-")
        ):
            out.append(p)
    return sorted(out)


def check_schema(doc: dict) -> tuple[bool, str]:
    for f in REQUIRED_FIELDS:
        if f not in doc:
            return False, f"missing required field: {f}"
    if doc["schema_version"] != SCHEMA_VERSION_SUPPORTED:
        return False, f"unsupported schema_version: {doc['schema_version']}"
    if not isinstance(doc.get("timestamp_unix"), (int, float)):
        return False, "timestamp_unix must be a number"
    gen = doc.get("generator", {})
    if not isinstance(gen, dict):
        return False, "generator must be an object"
    for f in REQUIRED_GENERATOR_FIELDS:
        if f not in gen:
            return False, f"generator.{f} missing"
    mesh = doc.get("mesh", {})
    if not isinstance(mesh, dict):
        return False, "mesh must be an object"
    for f in REQUIRED_MESH_FIELDS:
        if f not in mesh:
            return False, f"mesh.{f} missing"
    rep = doc.get("truth_gate_report", {})
    if not isinstance(rep, dict):
        return False, "truth_gate_report must be an object"
    for f in REQUIRED_REPORT_FIELDS:
        if f not in rep:
            return False, f"truth_gate_report.{f} missing"
    if not isinstance(rep.get("checks"), list):
        return False, "truth_gate_report.checks must be a list"
    sig = doc.get("signature", {})
    if not isinstance(sig, dict):
        return False, "signature must be an object"
    for f in REQUIRED_SIG_FIELDS:
        if f not in sig:
            return False, f"signature.{f} missing"
    return True, "ok"


def check_canonical(doc: dict) -> tuple[bool, str]:
    """The signed payload must round-trip through canonical encoding."""
    body = {k: v for k, v in doc.items() if k != "signature"}
    try:
        c1 = canonical(body)
        c2 = canonical(json.loads(c1.decode("utf-8")))
        if c1 != c2:
            return False, "canonical encoding not stable"
    except Exception as exc:  # noqa: BLE001
        return False, f"canonical encode/decode error: {exc}"
    return True, "ok"


def check_signature(doc: dict, key: bytes) -> tuple[bool, str]:
    sig = doc.get("signature", {})
    if sig.get("algorithm") != "HMAC-SHA256":
        return False, f"unsupported algorithm: {sig.get('algorithm')}"
    body = {k: v for k, v in doc.items() if k != "signature"}
    expected = hmac.new(key, canonical(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig.get("value", "")):
        return False, "signature mismatch"
    return True, "ok"


def collect_cross_refs(envelopes: list[tuple[Path, dict]]) -> list[dict[str, Any]]:
    """Group envelopes by shared mesh sha256 and assert metadata agreement."""
    issues: list[dict[str, Any]] = []
    by_mesh: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
    for path, doc in envelopes:
        mesh = doc.get("mesh", {}) or {}
        sha = mesh.get("sha256")
        if sha:
            by_mesh[sha].append((path, doc))

    fields_to_check = ("vertex_count", "face_count", "volume_mm3", "extents_mm", "is_watertight")
    for sha, items in by_mesh.items():
        if len(items) < 2:
            continue
        first_path, first_doc = items[0]
        first_mesh = first_doc.get("mesh", {})
        for other_path, other_doc in items[1:]:
            other_mesh = other_doc.get("mesh", {})
            for f in fields_to_check:
                if f in first_mesh and f in other_mesh and first_mesh[f] != other_mesh[f]:
                    issues.append({
                        "kind": "cross_ref_mesh_disagreement",
                        "field": f,
                        "mesh_sha256": sha,
                        "left": str(first_path),
                        "right": str(other_path),
                        "left_value": first_mesh[f],
                        "right_value": other_mesh[f],
                    })
                    break  # one issue per pair is enough
    return issues


BUNDLE_SCHEMA_VERSION = "bundle-1.0.0"


def _bundle_canonical(doc: dict) -> bytes:
    body = {k: v for k, v in doc.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _bundle_file_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bundle(zip_path: Path, key: bytes) -> tuple[int, dict]:
    """Verify a proof bundle zip produced by scripts/build-bundle.

    Checks:
      1. zip integrity (CRCs)
      2. manifest.json is parseable + has required schema fields
      3. manifest.sig HMAC-SHA256 over canonical(manifest) matches under `key`
      4. every file listed in manifest.files exists in the zip with matching sha256
      5. evidence_ledger.md is present and references files that exist in the bundle
    """
    import zipfile as _zf

    errors: list[str] = []
    out: dict = {"path": str(zip_path), "errors": errors, "ok": False}

    if not zip_path.is_file():
        errors.append(f"bundle not found: {zip_path}")
        return 2, out

    try:
        zf = _zf.ZipFile(zip_path, "r")
    except _zf.BadZipFile as exc:
        errors.append(f"bad zip: {exc}")
        return 2, out

    with zf:
        bad = zf.testzip()
        if bad is not None:
            errors.append(f"corrupt entry in zip: {bad}")
            return 2, out

        names = set(zf.namelist())
        if "manifest.json" not in names:
            errors.append("manifest.json missing from bundle")
            return 2, out
        if "manifest.sig" not in names:
            errors.append("manifest.sig missing from bundle")
            return 2, out

        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        except Exception as exc:
            errors.append(f"manifest.json not valid JSON: {exc}")
            return 2, out

        try:
            sig = json.loads(zf.read("manifest.sig").decode("utf-8"))
        except Exception as exc:
            errors.append(f"manifest.sig not valid JSON: {exc}")
            return 2, out

        for f in ("schema_version", "git", "build", "env", "signer", "files"):
            if f not in manifest:
                errors.append(f"manifest missing field: {f}")
        if manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
            errors.append(
                f"unsupported bundle schema_version: {manifest.get('schema_version')!r} "
                f"(expected {BUNDLE_SCHEMA_VERSION!r})"
            )
        if errors:
            return 1, out

        # 3. signature
        if sig.get("algorithm") != "HMAC-SHA256":
            errors.append(f"unsupported signature algorithm: {sig.get('algorithm')}")
            return 1, out
        expected = hmac.new(key, _bundle_canonical(manifest), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig.get("value", "")):
            errors.append("signature mismatch (manifest tampered or wrong key)")
            return 1, out

        # 4. file presence + hash
        for entry in manifest.get("files", []):
            rel = entry.get("path", "")
            want = entry.get("sha256", "")
            if rel == "manifest.json" or rel == "manifest.sig":
                # signing covers manifest itself; sig is by construction not signed.
                continue
            if rel not in names:
                errors.append(f"missing-file: {rel}")
                continue
            got = _bundle_file_sha256_bytes(zf.read(rel))
            if got != want:
                errors.append(f"hash-mismatch: {rel} (recorded {want[:16]}, got {got[:16]})")

        # 5. evidence ledger cross-refs
        if "evidence_ledger.md" in names:
            ledger_text = zf.read("evidence_ledger.md").decode("utf-8", "replace")
            # rows reference files relative to bundle root in the third column.
            for line in ledger_text.splitlines():
                if not line.startswith("| proof_envelope "):
                    continue
                cols = [c.strip() for c in line.strip("|").split("|")]
                if len(cols) >= 3 and cols[2]:
                    ref = cols[2].replace("\\", "/")
                    if ref and ref not in names and not ref.startswith(("kit_manifest", "honesty_ledger")):
                        errors.append(f"evidence_ledger references missing file: {ref}")
        else:
            errors.append("evidence_ledger.md missing from bundle")

    out["manifest"] = {
        "git": manifest.get("git"),
        "build": manifest.get("build"),
        "files_count": len(manifest.get("files", [])),
    }
    out["ok"] = not errors
    return (0 if not errors else 1), out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", default="var",
        help="dir to walk for envelopes (default: var/)",
    )
    parser.add_argument("--key", default=None, help="proof key (defaults to HERMES3D_PROOF_KEY)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--require-prod-key", action="store_true",
        help="reject envelopes verifiable under the dev default key",
    )
    parser.add_argument(
        "--bundle", default=None,
        help="verify a single proof-bundle zip produced by scripts/build-bundle",
    )
    args = parser.parse_args()

    # Bundle mode is mutually exclusive with the directory walk.
    if args.bundle is not None:
        if args.key is not None:
            key = args.key.encode("utf-8")
        else:
            env_key = os.environ.get("HERMES3D_PROOF_KEY")
            key = env_key.encode("utf-8") if env_key else DEFAULT_KEY
        rc, result = verify_bundle(Path(args.bundle), key)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"[bundle] {result['path']}")
            if result["ok"]:
                print("[bundle] OK — signature + file hashes + cross-refs verified")
                m = result.get("manifest", {})
                print(f"[bundle] git={m.get('git')}  files={m.get('files_count')}")
            else:
                print(f"[bundle] FAIL — {len(result['errors'])} error(s):")
                for e in result["errors"][:30]:
                    print(f"  - {e}")
        return rc

    root = Path(args.root)

    # Resolve the verification key
    if args.key is not None:
        key = args.key.encode("utf-8")
        using_default = False
    else:
        env_key = os.environ.get("HERMES3D_PROOF_KEY")
        if env_key:
            key = env_key.encode("utf-8")
            using_default = False
        else:
            key = DEFAULT_KEY
            using_default = True

    if args.require_prod_key and using_default:
        print(
            "[FAIL] dev default key in use under --require-prod-key; "
            "set HERMES3D_PROOF_KEY",
            file=sys.stderr,
        )
        return 2

    envelope_paths = find_envelopes(root)
    if not envelope_paths:
        msg = f"[conformance] no envelopes found under {root}"
        if args.json:
            print(json.dumps({"summary": {"walked": 0}, "envelopes": []}))
        else:
            print(msg)
        return 0

    schema_ok = canon_ok = sig_ok = 0
    failures: list[dict[str, Any]] = []
    docs: list[tuple[Path, dict]] = []

    for path in envelope_paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            failures.append({"path": str(path), "stage": "load", "detail": str(exc)})
            continue

        s_ok, s_msg = check_schema(doc)
        if s_ok:
            schema_ok += 1
        else:
            failures.append({"path": str(path), "stage": "schema", "detail": s_msg})
            continue

        c_ok, c_msg = check_canonical(doc)
        if c_ok:
            canon_ok += 1
        else:
            failures.append({"path": str(path), "stage": "canonical", "detail": c_msg})

        sig_check_ok, sig_msg = check_signature(doc, key)
        if sig_check_ok:
            sig_ok += 1
        else:
            failures.append({"path": str(path), "stage": "signature", "detail": sig_msg})

        docs.append((path, doc))

    cross_issues = collect_cross_refs(docs)

    walked = len(envelope_paths)
    summary = {
        "walked": walked,
        "schema": f"{schema_ok}/{walked}",
        "canonical": f"{canon_ok}/{walked}",
        "signature": f"{sig_ok}/{walked}",
        "cross_refs": f"{max(0, len(docs) - len(cross_issues))}/{len(docs)}",
        "failures": len(failures) + len(cross_issues),
        "key_source": "HERMES3D_PROOF_KEY" if not using_default else "default (dev)",
    }

    if args.json:
        print(json.dumps({
            "summary": summary,
            "failures": failures,
            "cross_ref_issues": cross_issues,
        }, indent=2))
    else:
        print(f"[conformance] walked {walked} envelopes (key: {summary['key_source']})")
        print(f"[conformance] schema       {summary['schema']} ok")
        print(f"[conformance] canonical    {summary['canonical']} ok")
        print(f"[conformance] signature    {summary['signature']} ok")
        print(f"[conformance] cross-refs   {summary['cross_refs']} ok")
        if failures:
            print(f"[conformance] FAIL — {len(failures)} envelope-level failure(s):")
            for f in failures[:30]:
                print(f"  {f['path']} [{f['stage']}]: {f['detail']}")
            if len(failures) > 30:
                print(f"  ...and {len(failures) - 30} more")
        if cross_issues:
            print(f"[conformance] FAIL — {len(cross_issues)} cross-ref issue(s):")
            for ci in cross_issues[:10]:
                print(f"  {ci['kind']}: field={ci['field']} sha256={ci['mesh_sha256'][:16]}")
        if not failures and not cross_issues:
            print("[conformance] all gates passed")

    return 1 if (failures or cross_issues) else 0


if __name__ == "__main__":
    sys.exit(main())
