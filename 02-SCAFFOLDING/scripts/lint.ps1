<#
.SYNOPSIS
    Layer A static gates: ruff check + format-check + forbidden-pattern scan.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Continue'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $repoRoot
$failures = 0
try {
    if (Get-Command ruff -ErrorAction SilentlyContinue) {
        Write-Host '[lint] ruff check ...'
        & ruff check src tests
        if ($LASTEXITCODE -ne 0) { $failures += 1 }
        Write-Host '[lint] ruff format --check ...'
        & ruff format --check src tests
        if ($LASTEXITCODE -ne 0) { $failures += 1 }
    } else {
        Write-Host '[WARN] ruff not installed — pip install ruff' -ForegroundColor Yellow
    }

    if (Get-Command mypy -ErrorAction SilentlyContinue) {
        Write-Host '[lint] mypy --strict src/hermes3d ...'
        & mypy --strict --no-incremental src/hermes3d
        if ($LASTEXITCODE -ne 0) {
            Write-Host '[WARN] mypy reported issues (allowed during v5 hardening; see HONESTY_LEDGER)' -ForegroundColor Yellow
        }
    } else {
        Write-Host '[WARN] mypy not installed — pip install mypy' -ForegroundColor Yellow
    }

    Write-Host '[lint] forbidden-pattern scan ...'
    $hits = Get-ChildItem -Recurse -Path 'src/hermes3d' -Filter *.py |
            Select-String -Pattern 'TODO|FIXME|STUB|PLACEHOLDER|NOT_IMPLEMENTED'
    if ($hits) {
        Write-Host '[FAIL] Forbidden patterns:' -ForegroundColor Red
        $hits | ForEach-Object { Write-Host ('  {0}:{1}: {2}' -f $_.Path, $_.LineNumber, $_.Line) }
        $failures += 1
    }

    if ($failures -gt 0) {
        Write-Host ("[FAIL] $failures lint failure(s).") -ForegroundColor Red
        exit 1
    }
    Write-Host '[OK] lint passed.' -ForegroundColor Green
} finally {
    Pop-Location
}
