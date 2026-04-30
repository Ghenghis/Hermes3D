<#
.SYNOPSIS
    Apply ruff format to src/ and tests/.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $repoRoot
try {
    if (-not (Get-Command ruff -ErrorAction SilentlyContinue)) {
        Write-Host '[FAIL] ruff not installed. pip install ruff' -ForegroundColor Red
        exit 1
    }
    Write-Host '[format] running ruff format ...'
    & ruff format src tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host '[format] done.'
} finally {
    Pop-Location
}
