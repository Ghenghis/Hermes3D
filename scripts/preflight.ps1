<#
.SYNOPSIS
  Hermes3D Preflight — validates dev environment against contract requirements.
.DESCRIPTION
  Checks for required (Python>=3.11, git, node) and optional tools.
  Writes a JSON capability report to var/preflight/<utc>.json.
  Exits 0 if ready, 1 if blockers found.
#>
param()
$ErrorActionPreference = 'Stop'
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

$Utc = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$OutDir = Join-Path $Root 'var\preflight'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutFile = Join-Path $OutDir "$Utc.json"

$RequiredOk = $true
$Cap = @{}

function Check-Tool {
  param([string]$Name, [string]$Cmd, [bool]$Required)
  $found = Get-Command $Cmd -ErrorAction SilentlyContinue
  if ($found) {
    $ver = ''
    try { $ver = (& $Cmd --version 2>&1 | Select-Object -First 1) -as [string] } catch { $ver = '?' }
    $Cap[$Name] = @{ state = 'present'; detail = $ver }
    Write-Host "  [OK] $Name -> $ver" -ForegroundColor Green
  } else {
    $Cap[$Name] = @{ state = 'missing'; detail = '' }
    if ($Required) {
      Write-Host "  [MISS] $Name (REQUIRED)" -ForegroundColor Red
      $script:RequiredOk = $false
    } else {
      Write-Host "  [opt] $Name (optional, skipped)" -ForegroundColor Yellow
    }
  }
}

Write-Host ""
Write-Host "===== Hermes3D Preflight ($Utc) ====="
Write-Host ""
Write-Host "Required tools:"
Check-Tool 'python' 'python' $true
Check-Tool 'git'    'git'    $true
Check-Tool 'node'   'node'   $true

Write-Host ""
Write-Host "Optional tools:"
foreach ($t in 'pip','pytest','ruff','mypy','npx','blender','ollama','prusa-slicer','orca-slicer','gh') {
  Check-Tool $t $t $false
}

# Python >= 3.11 check
$PyV = ''
try {
  $PyV = & python -c 'import sys;print(".".join(map(str,sys.version_info[:3])))' 2>$null
  $maj,$min,$pat = $PyV.Split('.')
  if (([int]$maj -gt 3) -or ([int]$maj -eq 3 -and [int]$min -ge 11)) {
    Write-Host "  [OK] Python $PyV >= 3.11" -ForegroundColor Green
  } else {
    Write-Host "  [BAD] Python $PyV < 3.11" -ForegroundColor Red
    $RequiredOk = $false
  }
} catch { Write-Host "  [BAD] python missing" -ForegroundColor Red; $RequiredOk = $false }

# Hooks path check
$HooksPath = (git config --get core.hooksPath 2>$null)
if ($HooksPath -eq '.githooks') {
  Write-Host "  [OK] core.hooksPath = .githooks" -ForegroundColor Green
} else {
  Write-Host "  [WARN] core.hooksPath not set; run scripts\install-hooks.ps1" -ForegroundColor Yellow
}

$report = [ordered]@{
  timestamp_utc  = $Utc
  required_ok    = $RequiredOk
  python_version = $PyV
  hooks_path     = if ($HooksPath) { $HooksPath } else { 'unset' }
  capabilities   = $Cap
}
$report | ConvertTo-Json -Depth 5 | Set-Content -Path $OutFile -Encoding UTF8
Write-Host ""
Write-Host "Report written: $OutFile"
Write-Host ""
if ($RequiredOk) {
  Write-Host "Preflight OK" -ForegroundColor Green
  exit 0
} else {
  Write-Host "Preflight FAILED — install missing required tools, then re-run." -ForegroundColor Red
  exit 1
}
