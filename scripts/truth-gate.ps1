<#
.SYNOPSIS
  Hermes3D Unified Truth Gate (Windows / PowerShell).
.DESCRIPTION
  Single command, single verdict, single signed bundle.
  Combines: ruff format + check, forbidden-pattern, pytest unit/conformance/integration,
  acceptance runner, Playwright E2E (advisory), honesty diff, signed proof bundle + verify.
  Exit 0 = GREEN, 1 = RED. Layer D Playwright is advisory.
#>
param()
$ErrorActionPreference = 'Continue'
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

$Utc = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$RunDir = Join-Path $Root "var\truth-gate\$Utc"
New-Item -ItemType Directory -Force -Path "$RunDir\logs" | Out-Null

$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$Py = if (Get-Command python3 -ErrorAction SilentlyContinue) { 'python3' }
      elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' }
      else { Write-Host '[FAIL] python not found' -ForegroundColor Red; exit 1 }

$verdicts = New-Object System.Collections.Generic.List[string]
$overall = $true

function Banner($t){ Write-Host ("-" * 60); Write-Host "[step] $t" -ForegroundColor Cyan }

function Run-Step {
  param([string]$Name, [bool]$Advisory, [scriptblock]$Cmd)
  Banner $Name
  $log = Join-Path "$RunDir\logs" ("$($Name -replace ' ','_').log")
  & $Cmd 2>&1 | Tee-Object -FilePath $log | Out-Null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "  PASS  ($log)" -ForegroundColor Green
    $script:verdicts.Add("PASS $Name") | Out-Null
  } else {
    if ($Advisory) {
      Write-Host "  ADVISORY-FAIL  ($log)" -ForegroundColor Yellow
      $script:verdicts.Add("ADVISORY $Name") | Out-Null
    } else {
      Write-Host "  FAIL  ($log)" -ForegroundColor Red
      $script:verdicts.Add("FAIL $Name") | Out-Null
      $script:overall = $false
    }
  }
}

Write-Host "===== Hermes3D Truth Gate ($Utc) =====" -ForegroundColor Cyan
Write-Host "Run dir: $RunDir"

# Layer A
if (Get-Command ruff -ErrorAction SilentlyContinue) {
  Run-Step 'ruff format --check' $false { ruff format --check 03_implementation/src 04_testing/pytest }
  Run-Step 'ruff check' $false { ruff check 03_implementation/src 04_testing/pytest }
} else { Write-Host '[skip] ruff not installed' -ForegroundColor Yellow }
Run-Step 'forbidden-pattern scan' $false { & $Py scripts/scaffolding/forbidden_pattern_scan.py }

# Layer B
Run-Step 'pytest unit' $false { & $Py -m pytest 04_testing/pytest/unit --tb=short -q --maxfail=20 }
Run-Step 'pytest conformance' $false { & $Py -m pytest 04_testing/pytest/conformance --tb=short -q }
Run-Step 'acceptance runner' $false { & $Py 04_testing/acceptance/run_acceptance.py }

# Layer C
Run-Step 'pytest integration' $false { & $Py -m pytest 04_testing/pytest/integration --tb=short -q --maxfail=10 }

# Layer D (advisory)
if (Test-Path "$Root\scripts\run-e2e.ps1") {
  Run-Step 'run-e2e (Playwright)' $true { & "$Root\scripts\run-e2e.ps1" }
}

# Layer F
Run-Step 'regenerate manifest' $false { & $Py 00_overview/contract/_generate_manifest.py }
Run-Step 'honesty diff' $false { & $Py scripts/scaffolding/honesty_diff.py }

# Bundle
Banner 'build proof bundle'
$env:HERMES3D_PROOF_KEY = if ($env:HERMES3D_PROOF_KEY) { $env:HERMES3D_PROOF_KEY } else { 'hermes3d-default-proof-key-not-secret' }
& "$Root\scripts\build-bundle.ps1" -Output $RunDir 2>&1 | Tee-Object -FilePath "$RunDir\logs\build-bundle.log" | Out-Null
$Bundle = Get-ChildItem -Path $RunDir -Filter '*.zip' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($Bundle) {
  Write-Host "  PASS  bundle: $($Bundle.FullName)" -ForegroundColor Green
  $verdicts.Add('PASS build-bundle') | Out-Null
  Banner 'verify proof bundle'
  & $Py 05_truth_proof/conformance_runner.py --bundle $Bundle.FullName 2>&1 | Tee-Object -FilePath "$RunDir\logs\bundle-verify.log" | Out-Null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "  PASS  signature + cross-refs verified" -ForegroundColor Green
    $verdicts.Add('PASS bundle-verify') | Out-Null
  } else { Write-Host "  FAIL  see logs" -ForegroundColor Red; $verdicts.Add('FAIL bundle-verify')|Out-Null; $overall = $false }
} else { Write-Host "  FAIL  no bundle produced" -ForegroundColor Red; $verdicts.Add('FAIL build-bundle')|Out-Null; $overall = $false }

# Summary
Write-Host ('-' * 60)
Write-Host '===== Truth Gate Summary =====' -ForegroundColor Cyan
foreach ($v in $verdicts) {
  if ($v.StartsWith('PASS')) { Write-Host "  $($v.Substring(5))" -ForegroundColor Green }
  elseif ($v.StartsWith('ADVISORY')) { Write-Host "  $($v.Substring(9)) (advisory)" -ForegroundColor Yellow }
  else { Write-Host "  $($v.Substring(5))" -ForegroundColor Red }
}
$summary = @{ timestamp_utc = $Utc; verdict = $(if ($overall) { 'GREEN' } else { 'RED' }); steps = $verdicts; bundle = $Bundle.FullName } | ConvertTo-Json -Depth 5
Set-Content -Path "$RunDir\summary.json" -Value $summary -Encoding UTF8

Write-Host ('-' * 60)
if ($overall) {
  Write-Host 'TRUTH GATE: GREEN' -ForegroundColor Green
  if ($Bundle) { Write-Host "Bundle: $($Bundle.FullName)" -ForegroundColor Green }
  exit 0
} else {
  Write-Host 'TRUTH GATE: RED' -ForegroundColor Red
  Write-Host "See logs in $RunDir\logs\" -ForegroundColor Red
  exit 1
}
