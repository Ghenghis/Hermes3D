#!/usr/bin/env python3
"""
Wave B Auditor — negative tests.

Three tampered copies of a bundle, each verified with auditor_verify.py.
Each MUST fail. Prints PASS/FAIL for each scenario based on whether the
expected failure was detected.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AUDITOR = SCRIPT_DIR / "auditor_verify.py"


def run_auditor(bundle: Path, key: str) -> tuple[int, dict]:
    env = dict(os.environ)
    env["HERMES3D_PROOF_KEY"] = key
    cp = subprocess.run(
        [sys.executable, str(AUDITOR), "--bundle", str(bundle)],
        env=env,
        capture_output=True,
        text=True,
    )
    try:
        return cp.returncode, json.loads(cp.stdout)
    except Exception:
        return cp.returncode, {"raw": cp.stdout, "stderr": cp.stderr}


def copy_zip_with_changes(src: Path, dst: Path,
                          mutate_file=None,
                          remove_files=None,
                          add_files=None) -> None:
    remove_files = set(remove_files or [])
    add_files = add_files or {}
    mutate_file = mutate_file or {}
    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in zin.namelist():
            if name in remove_files:
                continue
            data = zin.read(name)
            if name in mutate_file:
                data = mutate_file[name](data)
            zout.writestr(name, data)
        for name, data in add_files.items():
            zout.writestr(name, data)


def main() -> int:
    src = Path(sys.argv[1])
    key = sys.argv[2]
    tmp = Path(tempfile.mkdtemp(prefix="wave-b-audit-neg-"))
    print(f"[neg] tmpdir: {tmp}")

    results = []

    # 1. Tamper manifest + re-sign with WRONG key
    import hashlib, hmac
    def tamper_manifest(data: bytes) -> bytes:
        m = json.loads(data.decode("utf-8"))
        # flip a byte: change the build.run_id
        m.setdefault("build", {})["run_id"] = "TAMPERED-RUN-ID-XYZ"
        return json.dumps(m, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def resign_with_wrong_key(data: bytes) -> bytes:
        # Re-sign with a key that is NOT the verification key — this is the
        # adversary's attempt to forge a signature without knowing the secret.
        m = json.loads(data.decode("utf-8"))
        # The body actually being signed is the (tampered) manifest written above.
        # We don't have it here, so we just put a plausible-looking but wrong sig.
        wrong = "0" * 64
        return json.dumps({"algorithm": "HMAC-SHA256", "value": wrong},
                          sort_keys=True, separators=(",", ":")).encode("utf-8")

    t1 = tmp / "tampered_manifest.zip"
    copy_zip_with_changes(
        src, t1,
        mutate_file={
            "manifest.json": tamper_manifest,
            "manifest.sig": resign_with_wrong_key,
        },
    )
    rc, out = run_auditor(t1, key)
    detected = rc != 0 and any("signature" in e for e in out.get("errors", []))
    results.append(("tamper_manifest_wrong_key", detected, out.get("errors")))

    # 2. Remove a listed file from the zip
    with zipfile.ZipFile(src, "r") as zin:
        manifest = json.loads(zin.read("manifest.json").decode("utf-8"))
    victim = next(e["path"] for e in manifest["files"]
                  if e["path"] not in ("manifest.json", "manifest.sig"))
    t2 = tmp / "removed_file.zip"
    copy_zip_with_changes(src, t2, remove_files={victim})
    rc, out = run_auditor(t2, key)
    detected = rc != 0 and any("missing" in e or "integrity" in e for e in out.get("errors", []))
    results.append((f"remove_file::{victim}", detected, out.get("errors")))

    # 3. Add an extra file not in manifest
    t3 = tmp / "extra_file.zip"
    copy_zip_with_changes(src, t3, add_files={"smuggled.txt": b"hello"})
    rc, out = run_auditor(t3, key)
    detected = rc != 0 and any("forbidden" in e or "extras" in e for e in out.get("errors", []))
    results.append(("add_extra_file::smuggled.txt", detected, out.get("errors")))

    summary = []
    all_pass = True
    for name, detected, errors in results:
        status = "PASS (expected failure detected)" if detected else "FAIL (vulnerability)"
        if not detected:
            all_pass = False
        summary.append({"scenario": name, "status": status, "errors": errors})

    print(json.dumps(summary, indent=2))
    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
