#!/usr/bin/env python3
"""
Independent Wave B Auditor verifier.

Implements its OWN verification logic for proof bundles — does NOT call
05_truth_proof/conformance_runner.py. Used to cross-check the bundle
infrastructure for the Wave B audit.

Checks (a–e):
  a. signature  : HMAC-SHA256 over canonical(manifest) under HERMES3D_PROOF_KEY
                  matches manifest.sig.value
  b. file hash  : every file in manifest.files exists in the zip with sha256 match
  c. cross-refs : evidence_ledger.md references files that exist in the zip;
                  every "| proof_envelope " row has a non-empty proof path
  d. forbidden  : every file in the zip is referenced from manifest.files or is
                  one of the structural files (manifest.json / manifest.sig)
  e. commit     : manifest.git.sha is a real commit (`git cat-file -e <sha>`)

Usage:
  python auditor_verify.py --bundle <zip> [--key K]
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def canonical(doc: dict) -> bytes:
    body = {k: v for k, v in doc.items() if k != "signature"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def audit(zip_path: Path, key: bytes) -> dict:
    result = {
        "bundle": str(zip_path),
        "checks": {},
        "errors": [],
    }
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        sig = json.loads(zf.read("manifest.sig").decode("utf-8"))

        # (a) signature
        expected = hmac.new(key, canonical(manifest), hashlib.sha256).hexdigest()
        actual = sig.get("value", "")
        sig_ok = hmac.compare_digest(expected, actual)
        result["checks"]["a_signature"] = {
            "ok": sig_ok,
            "algorithm": sig.get("algorithm"),
            "expected_prefix": expected[:16],
            "actual_prefix": actual[:16],
        }
        if not sig_ok:
            result["errors"].append("signature mismatch")

        # (b) file hashes
        files = manifest.get("files", [])
        bad_hashes = []
        missing = []
        for entry in files:
            rel = entry["path"]
            want = entry["sha256"]
            if rel in ("manifest.json", "manifest.sig"):
                continue
            if rel not in names:
                missing.append(rel)
                continue
            got = sha256_bytes(zf.read(rel))
            if got != want:
                bad_hashes.append(
                    {"path": rel, "want": want[:16], "got": got[:16]}
                )
        result["checks"]["b_file_hashes"] = {
            "ok": not bad_hashes and not missing,
            "files_total": len(files),
            "missing": missing,
            "bad_hashes": bad_hashes,
        }
        if missing or bad_hashes:
            result["errors"].append(
                f"file integrity: {len(missing)} missing, {len(bad_hashes)} bad hashes"
            )

        # (c) cross-refs in evidence_ledger.md
        ledger_refs_missing = []
        ledger_rows = 0
        empty_proof_rows = []
        if "evidence_ledger.md" in names:
            text = zf.read("evidence_ledger.md").decode("utf-8", "replace")
            for line in text.splitlines():
                if not line.startswith("| proof_envelope "):
                    continue
                ledger_rows += 1
                cols = [c.strip() for c in line.strip("|").split("|")]
                if len(cols) >= 3:
                    ref = cols[2].replace("\\", "/")
                    if not ref:
                        empty_proof_rows.append(line[:80])
                    elif ref not in names and not ref.startswith(
                        ("kit_manifest", "honesty_ledger")
                    ):
                        ledger_refs_missing.append(ref)
        else:
            result["errors"].append("evidence_ledger.md missing")
        cross_ok = (
            "evidence_ledger.md" in names
            and not ledger_refs_missing
            and not empty_proof_rows
        )
        result["checks"]["c_cross_refs"] = {
            "ok": cross_ok,
            "rows_seen": ledger_rows,
            "missing_refs": ledger_refs_missing,
            "empty_proof_rows": empty_proof_rows,
        }
        if ledger_refs_missing or empty_proof_rows:
            result["errors"].append("evidence_ledger cross-refs invalid")

        # (d) forbidden extras: every zip file should be referenced
        manifest_paths = {e["path"] for e in files}
        manifest_paths.update({"manifest.json", "manifest.sig"})
        extras = sorted(names - manifest_paths)
        result["checks"]["d_forbidden_extras"] = {
            "ok": not extras,
            "extras": extras,
        }
        if extras:
            result["errors"].append(f"forbidden extras: {extras}")

        # (e) commit binding
        sha = (manifest.get("git") or {}).get("sha", "")
        commit_ok = False
        if sha:
            cp = subprocess.run(
                ["git", "cat-file", "-e", sha],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
            )
            commit_ok = cp.returncode == 0
        result["checks"]["e_commit_binding"] = {
            "ok": commit_ok,
            "sha": sha,
        }
        if not commit_ok:
            result["errors"].append(f"commit binding failed: sha={sha!r}")

    result["ok"] = not result["errors"]
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True)
    p.add_argument("--key", default=None)
    args = p.parse_args()
    key = (args.key or os.environ.get("HERMES3D_PROOF_KEY") or "").encode("utf-8")
    if not key:
        print("error: HERMES3D_PROOF_KEY (or --key) required", file=sys.stderr)
        return 2
    out = audit(Path(args.bundle), key)
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
