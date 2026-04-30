#!/usr/bin/env bash
# scripts/proof-collect.sh — gather every proof envelope under var/ and
# verify HMAC signatures, producing a consolidated report.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

OUT="var/proof-report.json"
mkdir -p var

PYTHONPATH="$REPO_ROOT/03_implementation/src" python3 - <<'PY'
import json, os, sys
from pathlib import Path

# Walk var/ for *.proof.json and var/acceptance-results/**/proof.json
roots = [Path("var"), Path("dist/release")]
files = []
for root in roots:
    if not root.exists():
        continue
    for p in root.rglob("*.json"):
        if p.name.endswith(".proof.json") or p.name == "proof.json":
            files.append(p)

try:
    from hermes3d.core.proof.proof_envelope import verify_envelope  # type: ignore[attr-defined]
    have_verifier = True
except Exception as exc:  # noqa: BLE001
    have_verifier = False
    print(f"[WARN] verify_envelope not importable: {exc}; reporting metadata only.")

key = os.environ.get("HERMES3D_PROOF_KEY", "hermes3d-default-proof-key-not-secret").encode()

report = {"count": len(files), "envelopes": []}
ok = 0
bad = 0
for f in files:
    entry = {"path": str(f), "ok": None}
    try:
        with f.open("r", encoding="utf-8") as fh:
            doc = json.load(fh)
        entry["produced_at"] = doc.get("produced_at")
        entry["subject"] = doc.get("subject")
        if have_verifier:
            entry["ok"] = bool(verify_envelope(doc, key))
        else:
            # Hand-verify: recompute HMAC over the doc minus signature
            import hashlib, hmac
            sig = doc.pop("signature", None)
            canonical = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
            expected = hmac.new(key, canonical, hashlib.sha256).hexdigest()
            entry["ok"] = bool(sig and sig.get("value") == expected)
        if entry["ok"]:
            ok += 1
        else:
            bad += 1
    except Exception as exc:  # noqa: BLE001
        entry["ok"] = False
        entry["error"] = str(exc)
        bad += 1
    report["envelopes"].append(entry)

report["summary"] = {"verified": ok, "failed": bad}
Path("var/proof-report.json").write_text(json.dumps(report, indent=2))
print(f"[proof-collect] {len(files)} envelopes; verified={ok}, failed={bad}")
print(f"[proof-collect] report at var/proof-report.json")
sys.exit(0 if bad == 0 else 1)
PY
