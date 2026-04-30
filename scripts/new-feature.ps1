# Create a new feat/<area>/<short-desc> branch from origin/develop (PowerShell).
[CmdletBinding()]
param(
    [Parameter(Position=0)] [string] $Area,
    [Parameter(Position=1)] [string] $ShortDesc
)

$ErrorActionPreference = 'Stop'

if (-not $Area)      { $Area      = Read-Host 'area' }
if (-not $ShortDesc) { $ShortDesc = Read-Host 'short-desc' }

function Test-Slug {
    param([string]$Label, [string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { throw "$Label cannot be empty." }
    if ($Value.Length -gt 40)                 { throw "$Label exceeds 40 chars." }
    if ($Value -notmatch '^[a-z0-9-]+$') {
        throw "$Label must match [a-z0-9-]+ (no spaces, no uppercase, no underscores)."
    }
}

Test-Slug 'area'       $Area
Test-Slug 'short-desc' $ShortDesc

$branch = "feat/$Area/$ShortDesc"

Write-Host 'Fetching origin/develop...'
& git fetch origin develop
if ($LASTEXITCODE -ne 0) { throw 'git fetch failed.' }

$existing = & git show-ref --verify --quiet "refs/heads/$branch"
if ($LASTEXITCODE -eq 0) { throw "Branch '$branch' already exists locally." }

& git checkout -b $branch origin/develop
if ($LASTEXITCODE -ne 0) { throw 'git checkout failed.' }

Write-Host ''
Write-Host "OK: created $branch from origin/develop." -ForegroundColor Green
Write-Host ''
Write-Host 'Next steps:'
Write-Host "  1. Run 'pwsh -File scripts/install-hooks.ps1' once to enable the pre-push hook"
Write-Host '     (refuses pushes to main/master, runs fast tests).'
Write-Host "  2. Commit your work, then 'git push -u origin $branch'."
Write-Host "  3. Open a PR targeting 'develop' (NOT main)."
Write-Host ''
Write-Host 'Rules: see 06_release/BRANCH_STRATEGY.md.'
