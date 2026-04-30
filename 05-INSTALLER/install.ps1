<#
.SYNOPSIS
    Hermes3D-OS Lite installer (Windows / PowerShell 7+).

.DESCRIPTION
    Reads 05-INSTALLER/manifest.json, installs every required component,
    asks the user about optional components, and runs verify_install.py.

.PARAMETER Components
    Comma-separated list of optional components to enable. Use 'all' for
    every component, 'minimal' for required-only.

.PARAMETER NoVerify
    Skip the verify_install.py step at the end.

.PARAMETER Quiet
    Don't prompt for optional components — accept defaults.

.EXAMPLE
    pwsh 05-INSTALLER/install.ps1
    pwsh 05-INSTALLER/install.ps1 -Components 'gradio_ui,rest_api,ollama_provider'
    pwsh 05-INSTALLER/install.ps1 -Components 'all'
#>
[CmdletBinding()]
param(
    [string]$Components = '',
    [switch]$NoVerify,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

$installerDir = $PSScriptRoot
$repoRoot = Resolve-Path (Join-Path $installerDir '..')
$scaffolding = Join-Path $repoRoot '02-SCAFFOLDING'

Write-Host '================================================================'
Write-Host '  Hermes3D-OS Lite Installer (v5)' -ForegroundColor Cyan
Write-Host '================================================================'

# Load manifest
$manifestPath = Join-Path $installerDir 'manifest.json'
if (-not (Test-Path $manifestPath)) {
    Write-Host "[FAIL] manifest not found at $manifestPath" -ForegroundColor Red
    exit 1
}
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

# Locate Python
$py = $null
foreach ($cmd in @('python', 'py', 'python3')) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $py = $cmd
        break
    }
}
if (-not $py) {
    Write-Host '[FAIL] Python 3.11+ required. Install from https://python.org' -ForegroundColor Red
    exit 1
}
$pyVer = & $py -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")'
Write-Host "[1/5] Python: $pyVer ($py)" -ForegroundColor Green

# Determine which components to install
$chosen = @{}
$properties = $manifest.components | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name
foreach ($key in $properties) {
    $component = $manifest.components.$key
    if ($component.required) {
        $chosen[$key] = $true
        continue
    }
    if ($Components -eq 'all') {
        $chosen[$key] = $true
        continue
    }
    if ($Components -eq 'minimal') {
        $chosen[$key] = $false
        continue
    }
    if ($Components) {
        $chosen[$key] = ($Components.Split(',') -contains $key)
        continue
    }
    if ($Quiet) {
        $chosen[$key] = ([bool]$component.default)
        continue
    }
    # Interactive prompt
    $defaultLabel = if ($component.default) { 'Y/n' } else { 'y/N' }
    $prompt = "  Install '$key' ($($component.description))? [$defaultLabel]"
    $resp = Read-Host $prompt
    if (-not $resp) { $chosen[$key] = ([bool]$component.default) }
    else { $chosen[$key] = ($resp -match '^[Yy]') }
}

Write-Host ''
Write-Host '[2/5] Installing core package + dependencies ...' -ForegroundColor Cyan
Push-Location $scaffolding
try {
    & $py -m pip install --upgrade pip
    & $py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'core requirements failed' }
    & $py -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw 'editable install failed' }
} finally {
    Pop-Location
}

Write-Host ''
Write-Host '[3/5] Installing optional components ...' -ForegroundColor Cyan
foreach ($key in $properties) {
    if (-not $chosen[$key]) { continue }
    $component = $manifest.components.$key
    if ($component.required) { continue }
    Write-Host "  + $key — $($component.install)"
    Invoke-Expression "& $py -m $($component.install)"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    [WARN] $key install failed; continuing." -ForegroundColor Yellow
    }
    if ($component.external_setup) {
        Write-Host "    note: external setup at $($component.external_setup)" -ForegroundColor DarkGray
    }
    if ($component.credentials_required) {
        Write-Host "    note: set these env vars: $($component.credentials_required -join ', ')" -ForegroundColor DarkGray
    }
}

Write-Host ''
Write-Host '[4/5] Creating runtime directories ...' -ForegroundColor Cyan
foreach ($dir in $manifest.directories_created) {
    $full = Join-Path $scaffolding ($dir -replace '^\.\/', '')
    if (-not (Test-Path $full)) {
        New-Item -ItemType Directory -Path $full -Force | Out-Null
        Write-Host "  + $dir"
    }
}

if ($NoVerify) {
    Write-Host ''
    Write-Host '[5/5] verification skipped (-NoVerify)' -ForegroundColor Yellow
} else {
    Write-Host ''
    Write-Host '[5/5] running verify_install.py ...' -ForegroundColor Cyan
    & $py (Join-Path $installerDir 'verify_install.py')
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[FAIL] verification failed.' -ForegroundColor Red
        exit 1
    }
}

Write-Host ''
Write-Host '================================================================'
Write-Host '  Install complete.' -ForegroundColor Green
Write-Host '  Next steps:' -ForegroundColor Cyan
foreach ($step in $manifest.post_install_steps) {
    Write-Host "    - $step"
}
Write-Host '================================================================'
