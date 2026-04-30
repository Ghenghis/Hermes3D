<#
.SYNOPSIS
    Produce a production wheel under dist/.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $repoRoot
try {
    $py = if (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'py' }

    & $py -c 'import build' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[build] installing build module ...'
        & $py -m pip install --user build
    }

    if (Test-Path 'dist') { Remove-Item -Recurse -Force 'dist' }
    if (Test-Path 'build') { Remove-Item -Recurse -Force 'build' }

    Write-Host '[build] python -m build --wheel ...'
    & $py -m build --wheel
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host '[build] artifacts:'
    Get-ChildItem dist | Format-Table Name, Length

    foreach ($whl in Get-ChildItem 'dist/*.whl') {
        $hash = (Get-FileHash $whl.FullName -Algorithm SHA256).Hash.ToLower()
        "$hash  $($whl.Name)" | Set-Content -Path "$($whl.FullName).sha256"
        Write-Host "  sha256: $hash"
    }
    Write-Host '[build] done.' -ForegroundColor Green
} finally {
    Pop-Location
}
