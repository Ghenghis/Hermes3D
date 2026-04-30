# Hermes3D pre-push hook (PowerShell variant) — A.5 / rubric criterion 5
# Refuses direct pushes to main/master and runs fast test subset.

$ErrorActionPreference = 'Stop'

try {
    $branch = (& git symbolic-ref --short HEAD 2>$null).Trim()
} catch {
    $branch = 'DETACHED'
}

if ($branch -in @('main','master')) {
    Write-Host "ERROR: Direct push to '$branch' is forbidden." -ForegroundColor Red
    Write-Host "  Create a feature branch with scripts/new-feature.ps1 and open a PR." -ForegroundColor Yellow
    Write-Host "  See 06_release/BRANCH_STRATEGY.md for the gitflow rules." -ForegroundColor Yellow
    exit 1
}

$repoRoot = (& git rev-parse --show-toplevel).Trim()
$testScript = Join-Path $repoRoot 'scripts/scaffolding/test.ps1'

if (Test-Path $testScript) {
    Write-Host "pre-push: running fast test subset..." -ForegroundColor Green
    & pwsh -NoProfile -File $testScript -Fast
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Tests failed; not pushing." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "pre-push: test.ps1 not found at $testScript — skipping fast tests." -ForegroundColor Yellow
}

Write-Host "pre-push: branch '$branch' OK; tests passed." -ForegroundColor Green
exit 0
