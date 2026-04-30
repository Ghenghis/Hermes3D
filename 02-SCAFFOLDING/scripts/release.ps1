<#
.SYNOPSIS
    Produce a versioned release zip with checksums + signed proof envelope.

.PARAMETER DryRun
    Build the artifact and checksum but skip the proof envelope.

.PARAMETER Version
    Version string (defaults to project.version in pyproject.toml).
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$Version
)
$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $repoRoot
try {
    $py = if (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'py' }

    if (-not $Version) {
        $Version = & $py -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
    }

    $outDir = "dist/release/$Version"
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    $artifactName = "hermes3d_os_lite_v${Version}.zip"
    $artifact = "$outDir/$artifactName"

    Write-Host "[release] packaging $artifact ..." -ForegroundColor Cyan

    # Stage the files
    $stage = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ("h3d-stage-" + [guid]::NewGuid())) -Force
    try {
        foreach ($d in @('src', 'tests', 'config', 'scripts', 'env')) {
            if (Test-Path $d) { Copy-Item -Recurse -Path $d -Destination (Join-Path $stage $d) }
        }
        foreach ($f in @('pyproject.toml', 'requirements.txt', 'requirements-dev.txt', '.gitignore', '.editorconfig')) {
            if (Test-Path $f) { Copy-Item $f $stage }
        }
        Compress-Archive -Path "$stage/*" -DestinationPath $artifact -Force
    } finally {
        Remove-Item -Recurse -Force $stage
    }

    $artSha = (Get-FileHash $artifact -Algorithm SHA256).Hash.ToLower()
    "$artSha  $artifactName" | Set-Content -Path "$artifact.sha256"
    Write-Host "  sha256: $artSha"
    $size = (Get-Item $artifact).Length
    Write-Host "  size:   $size bytes"

    if ($DryRun) {
        Write-Host '[release] dry-run; skipping proof envelope.' -ForegroundColor Yellow
        exit 0
    }

    $proof = "$outDir/hermes3d_os_lite_v${Version}.proof.json"
    $gitCommit = try { (& git rev-parse HEAD 2>$null).Trim() } catch { 'unknown' }
    if (-not $gitCommit) { $gitCommit = 'unknown' }
    $pythonVer = & $py -c 'import sys; print(".".join(str(x) for x in sys.version_info[:3]))'
    $now = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $hostFp = $env:COMPUTERNAME

    $proofKey = if ($env:HERMES3D_PROOF_KEY) { $env:HERMES3D_PROOF_KEY } else { 'hermes3d-default-proof-key-not-secret' }
    $env:PYTHONPATH = (Join-Path $repoRoot 'src') + [System.IO.Path]::PathSeparator + $env:PYTHONPATH

    $script = @"
import hashlib, hmac, json
doc = {
    "envelope_version": "1.0.0",
    "produced_at": "$now",
    "produced_by": {
        "tool": "scripts/release.ps1",
        "git_commit": "$gitCommit",
        "python": "$pythonVer",
        "host_fingerprint": "$hostFp",
    },
    "subject": {"kind": "release", "version": "$Version", "artifact": "$artifactName"},
    "inputs": {"artifact_sha256": "$artSha"},
    "decision": {
        "pass": True,
        "checks": [
            {"name": "artifact_built", "pass": True, "detail": "zip created"},
            {"name": "sha256_recorded", "pass": True, "detail": "$artSha"},
        ],
    },
}
canonical = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
mac = hmac.new(b"$proofKey", canonical, hashlib.sha256).hexdigest()
doc["signature"] = {"algorithm": "HMAC-SHA256", "value": mac}
with open(r"$proof", "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
print(f"  proof:  {mac[:16]}...")
"@
    & $py -c $script
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host '[release] done.' -ForegroundColor Green
    Write-Host "  artifact: $artifact"
    Write-Host "  proof:    $proof"
} finally {
    Pop-Location
}
