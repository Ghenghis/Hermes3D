<#
.SYNOPSIS
    Gather every proof envelope under var/ and verify HMAC signatures,
    producing a consolidated report at var/proof-report.json.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $repoRoot
try {
    $py = if (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'py' }
    $env:PYTHONPATH = (Join-Path $repoRoot 'src') + [System.IO.Path]::PathSeparator + $env:PYTHONPATH
    if (-not (Test-Path 'var')) { New-Item -ItemType Directory -Path 'var' -Force | Out-Null }
    & $py (Join-Path $PSScriptRoot 'proof-collect.sh') 2>&1 | Out-Null
    # Fallback: run a Python one-liner directly (Bash script may not work on plain Windows)
    $script = @'
import json, os, sys, hashlib, hmac
from pathlib import Path
roots = [Path("var"), Path("dist/release")]
files = []
for root in roots:
    if not root.exists(): continue
    for p in root.rglob("*.json"):
        if p.name.endswith(".proof.json") or p.name == "proof.json":
            files.append(p)
key = os.environ.get("HERMES3D_PROOF_KEY", "hermes3d-default-proof-key-not-secret").encode()
report = {"count": len(files), "envelopes": []}
ok = bad = 0
for f in files:
    entry = {"path": str(f).replace("\\", "/"), "ok": None}
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
        entry["produced_at"] = doc.get("produced_at")
        entry["subject"] = doc.get("subject")
        sig = doc.pop("signature", None)
        canonical = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
        expected = hmac.new(key, canonical, hashlib.sha256).hexdigest()
        entry["ok"] = bool(sig and sig.get("value") == expected)
        if entry["ok"]: ok += 1
        else: bad += 1
    except Exception as exc:
        entry["ok"] = False; entry["error"] = str(exc); bad += 1
    report["envelopes"].append(entry)
report["summary"] = {"verified": ok, "failed": bad}
Path("var/proof-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"[proof-collect] {len(files)} envelopes; verified={ok}, failed={bad}")
print(f"[proof-collect] report at var/proof-report.json")
sys.exit(0 if bad == 0 else 1)
'@
    & $py -c $script
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
