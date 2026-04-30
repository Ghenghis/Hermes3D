# Install Hermes3D project-local git hooks (A.5) — PowerShell variant.
$ErrorActionPreference = 'Stop'

$repoRoot = (& git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$hooksDir = '.githooks'
if (-not (Test-Path $hooksDir)) {
    Write-Error "$hooksDir not found at $repoRoot"
}

& git config core.hooksPath $hooksDir

if (-not (Test-Path "$hooksDir/pre-push")) {
    Write-Error "$hooksDir/pre-push missing."
}

Write-Host "OK: core.hooksPath = $hooksDir (project-local)" -ForegroundColor Green
Write-Host "Installed hooks:"
Get-ChildItem $hooksDir | ForEach-Object { Write-Host "  $($_.Name)" }
Write-Host ""
Write-Host "pre-push will:"
Write-Host "  1. Refuse pushes to main/master"
Write-Host "  2. Run scripts/scaffolding/test.sh --fast (or test.ps1 -Fast) before push"
Write-Host ""
Write-Host "Note: On Windows, git uses the bash hook via sh.exe (Git-Bash). The .ps1 hook" -ForegroundColor Yellow
Write-Host "is provided as a reference for users who prefer PowerShell-only workflows."  -ForegroundColor Yellow
