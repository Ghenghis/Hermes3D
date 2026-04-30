<#
.SYNOPSIS
  Hermes3D-OS Lite — Setup Wizard (Windows / PowerShell).
.DESCRIPTION
  Guided zero-to-running flow for non-coders.
  Validates env -> installs deps -> installs hooks -> runs acceptance -> launches Gradio UI.
#>
param([switch]$Yes)
$ErrorActionPreference = 'Stop'
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

function Banner($t){ Write-Host ""; Write-Host ("=" * 60) -ForegroundColor Cyan; Write-Host "  $t" -ForegroundColor Cyan; Write-Host ("=" * 60) -ForegroundColor Cyan; Write-Host "" }
function Ask($prompt, $default='y'){ if ($Yes) { return $true }; $a = Read-Host "$prompt [$default]"; if ([string]::IsNullOrWhiteSpace($a)) { $a = $default }; return ($a -match '^[Yy]') }

Clear-Host
Banner 'Hermes3D-OS Lite — Setup Wizard'
Write-Host "This wizard will:"
Write-Host "  1. Validate your environment (Python, git, node)"
Write-Host "  2. Install Hermes3D + dependencies"
Write-Host "  3. Install pre-push git hooks (branch discipline)"
Write-Host "  4. Run the acceptance test suite"
Write-Host "  5. Launch the Gradio UI in your browser"
Write-Host ""
if (-not (Ask 'Proceed?' 'y')) { Write-Host 'Cancelled.'; exit 0 }

Banner 'Step 1/5  Preflight'
& "$Root\scripts\preflight.ps1"
if ($LASTEXITCODE -ne 0) { Write-Host "Preflight failed. Fix the missing tools, then re-run." -ForegroundColor Red; exit 1 }

Banner 'Step 2/5  Installing Hermes3D'
$Pyproj = if (Test-Path "$Root\02-SCAFFOLDING\pyproject.toml") { "$Root\02-SCAFFOLDING" } else { $Root }
Push-Location $Pyproj
try {
  python -m pip install -e ".[all]" 2>&1 | Select-Object -Last 8
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[all] extras unavailable; falling back to base install" -ForegroundColor Yellow
    python -m pip install -e . 2>&1 | Select-Object -Last 8
  }
} finally { Pop-Location }

Banner 'Step 3/5  Installing branch-discipline git hooks'
if (Test-Path "$Root\scripts\install-hooks.ps1") {
  & "$Root\scripts\install-hooks.ps1"
} else {
  Write-Host "scripts\install-hooks.ps1 not found yet (added by sibling task A.5). Skipping." -ForegroundColor Yellow
}

Banner 'Step 4/5  Acceptance suite (48 cells)'
$Acc = "$Root\04-TEST-CASE-DESK-ORGANIZER\run_acceptance.py"
if (Test-Path $Acc) {
  python $Acc 2>&1 | Select-Object -Last 10
  if ($LASTEXITCODE -ne 0) {
    Write-Host 'Acceptance run reported failures.' -ForegroundColor Red
    if (-not (Ask 'Continue to UI launch anyway?' 'y')) { exit 1 }
  }
} else { Write-Host "Acceptance runner not found. Skipping." -ForegroundColor Yellow }

Banner 'Step 5/5  Launching Gradio UI'
Write-Host 'Opening http://localhost:7860 ...' -ForegroundColor Green
Start-Process 'http://localhost:7860' -ErrorAction SilentlyContinue
python -m hermes3d.app.launcher
