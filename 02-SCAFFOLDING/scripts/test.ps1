<#
.SYNOPSIS
    Run the Hermes3D-OS Lite test suite.

.PARAMETER Integration
    Include Layer-C integration tests (requires PrusaSlicer/OrcaSlicer + optional services).

.PARAMETER E2E
    Include Layer-D end-to-end UI tests (also enables -Integration).

.PARAMETER AcceptanceOnly
    Run only the acceptance runner.

.EXAMPLE
    pwsh scripts/test.ps1                  # Layer A + B
    pwsh scripts/test.ps1 -Integration     # + C
    pwsh scripts/test.ps1 -E2E             # + C + D
    pwsh scripts/test.ps1 -AcceptanceOnly
#>
[CmdletBinding()]
param(
    [switch]$Integration,
    [switch]$E2E,
    [switch]$AcceptanceOnly,
    [Parameter(ValueFromRemainingArguments)][string[]]$ExtraArgs
)

$ErrorActionPreference = 'Stop'

if ($E2E) { $Integration = $true }

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $repoRoot
try {
    $env:PYTHONPATH = (Join-Path $repoRoot 'src') + [System.IO.Path]::PathSeparator + $env:PYTHONPATH
    if (-not $env:HERMES3D_PROOF_KEY) {
        $env:HERMES3D_PROOF_KEY = 'hermes3d-default-proof-key-not-secret'
    }

    $py = $null
    foreach ($cmd in @('python', 'py', 'python3')) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            $py = $cmd
            break
        }
    }
    if (-not $py) {
        Write-Host '[FAIL] Python not on PATH. Run scripts/doctor.ps1 first.' -ForegroundColor Red
        exit 1
    }

    if ($AcceptanceOnly) {
        Write-Host '[1/1] Acceptance runner ...'
        & $py '..\04-TEST-CASE-DESK-ORGANIZER\run_acceptance.py'
        exit $LASTEXITCODE
    }

    # Layer A — ruff (best-effort)
    Write-Host '[1/4] Layer A: static gates ...'
    if (Get-Command ruff -ErrorAction SilentlyContinue) {
        & ruff format --check src tests
        if ($LASTEXITCODE -ne 0) { Write-Host '[FAIL] ruff format' -ForegroundColor Red; exit 1 }
        & ruff check src tests
        if ($LASTEXITCODE -ne 0) { Write-Host '[FAIL] ruff check' -ForegroundColor Red; exit 1 }
        Write-Host '  [PASS] ruff format + check' -ForegroundColor Green
    } else {
        Write-Host '  [WARN] ruff not installed; skipping format + lint' -ForegroundColor Yellow
    }

    # Forbidden-pattern scan
    Write-Host '  [SCAN] forbidden patterns ...'
    $patterns = 'TODO|FIXME|STUB|PLACEHOLDER|NOT_IMPLEMENTED'
    $hits = Get-ChildItem -Recurse -Path 'src/hermes3d' -Filter *.py |
            Select-String -Pattern $patterns
    if ($hits) {
        Write-Host '[FAIL] Forbidden patterns found in runtime code:' -ForegroundColor Red
        $hits | ForEach-Object { Write-Host ('  {0}:{1}: {2}' -f $_.Path, $_.LineNumber, $_.Line) }
        exit 1
    }
    Write-Host '  [PASS] no forbidden patterns in src/hermes3d' -ForegroundColor Green

    # Layer B
    Write-Host '[2/4] Layer B: unit + smoke tests ...'
    $pytestArgs = if ($Integration) { @('tests/') } else { @('tests/unit', 'tests/conformance') }
    if ($ExtraArgs) { $pytestArgs += $ExtraArgs }
    & $py '-m' 'pytest' @pytestArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host '[3/4] Layer B: acceptance runner ...'
    & $py '..\04-TEST-CASE-DESK-ORGANIZER\run_acceptance.py'
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if ($E2E) {
        Write-Host '[4/4] Layer D: E2E launcher smoke ...'
        & $py '-c' 'import hermes3d.app.launcher'
        if ($LASTEXITCODE -ne 0) {
            Write-Host '  [FAIL] launcher import failed' -ForegroundColor Red
            exit 1
        }
        Write-Host '  [PASS] launcher importable' -ForegroundColor Green
    } else {
        Write-Host '[4/4] Layer D: skipped (use -E2E to enable)'
    }

    Write-Host ''
    Write-Host '[OK] All applicable layers green.' -ForegroundColor Green
} finally {
    Pop-Location
}
