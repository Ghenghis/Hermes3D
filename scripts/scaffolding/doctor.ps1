<#
.SYNOPSIS
    Hermes3D-OS Lite environment prerequisite check (Windows / PowerShell 7+).

.DESCRIPTION
    Verifies that the host machine has every dependency required to run
    Hermes3D-OS Lite. Exits 1 if any required prerequisite is missing.

.EXAMPLE
    pwsh scripts/doctor.ps1
    pwsh scripts/doctor.ps1 -Json
#>
[CmdletBinding()]
param(
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

$results = New-Object System.Collections.Generic.List[hashtable]

function Add-Result {
    param(
        [Parameter(Mandatory)][ValidateSet('PASS', 'WARN', 'FAIL')][string]$Status,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Detail,
        [string]$Fix = ''
    )
    $results.Add(@{
        Status = $Status
        Name = $Name
        Detail = $Detail
        Fix = $Fix
    })
}

function Test-Python {
    $py = $null
    foreach ($cmd in @('python', 'py', 'python3')) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($null -ne $found) {
            $py = $cmd
            break
        }
    }
    if (-not $py) {
        Add-Result FAIL 'python' 'not found on PATH' 'Install Python 3.11+ from python.org or via winget install Python.Python.3.11'
        return $null
    }
    $version = & $py -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}")' 2>$null
    if (-not $version) {
        Add-Result FAIL 'python' "could not query version via $py" 'Reinstall Python from python.org'
        return $null
    }
    $parts = $version.Split('.')
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Add-Result FAIL 'python' "$version (need >=3.11)" 'Install Python 3.11+ from python.org'
    } else {
        Add-Result PASS 'python' $version
    }
    return $py
}

function Test-PythonPackages {
    param([string]$Py)
    if (-not $Py) { return }
    $required = @('trimesh', 'numpy', 'fastapi', 'uvicorn', 'pydantic', 'httpx')
    $missing = @()
    foreach ($pkg in $required) {
        & $Py -c "import $pkg" 2>$null
        if ($LASTEXITCODE -ne 0) { $missing += $pkg }
    }
    if ($missing.Count -gt 0) {
        Add-Result FAIL 'python deps' ("missing: " + ($missing -join ', ')) 'pip install -r requirements.txt'
    } else {
        Add-Result PASS 'python deps' 'all 6 core packages present'
    }
}

function Test-DevPackages {
    param([string]$Py)
    if (-not $Py) { return }
    & $Py -c 'import pytest' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Add-Result WARN 'dev deps' 'pytest missing (only required for tests)' 'pip install -r requirements-dev.txt'
    } else {
        Add-Result PASS 'dev deps' 'pytest present'
    }
}

function Test-Slicer {
    $found = $null
    foreach ($cmd in @('prusa-slicer', 'PrusaSlicer', 'prusaslicer-console', 'orcaslicer', 'OrcaSlicer')) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            $found = $cmd
            break
        }
    }
    if ($found) {
        Add-Result PASS 'slicer' "$found on PATH"
    } else {
        Add-Result WARN 'slicer' 'neither PrusaSlicer nor OrcaSlicer on PATH' 'winget install Prusa3D.PrusaSlicer or download from prusa3d.com'
    }
}

function Test-DiskSpace {
    $drive = (Get-Location).Drive
    if (-not $drive) {
        Add-Result WARN 'disk space' 'cannot determine free space (UNC path?)'
        return
    }
    $freeGB = [math]::Floor($drive.Free / 1GB)
    if ($freeGB -lt 5) {
        Add-Result FAIL 'disk space' "${freeGB}GB free (need >=5GB)" 'Free up disk space'
    } elseif ($freeGB -lt 20) {
        Add-Result WARN 'disk space' "${freeGB}GB free (recommend >=20GB)" '20GB recommended for slicer cache + builds'
    } else {
        Add-Result PASS 'disk space' "${freeGB}GB free"
    }
}

function Test-VarDir {
    if (-not (Test-Path '.\var')) {
        try {
            New-Item -ItemType Directory -Path '.\var' -Force | Out-Null
            Add-Result PASS 'var dir' 'created .\var'
        } catch {
            Add-Result FAIL 'var dir' 'could not create .\var' 'Check directory permissions'
        }
    } else {
        Add-Result PASS 'var dir' 'exists'
    }
}

function Test-ProofKey {
    if ($env:HERMES3D_PROOF_KEY) {
        Add-Result PASS 'proof key' 'HERMES3D_PROOF_KEY set'
    } else {
        Add-Result WARN 'proof key' 'HERMES3D_PROOF_KEY not set (using dev default)' 'Set HERMES3D_PROOF_KEY in .env for production'
    }
}

function Test-Gpu {
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if ($smi) {
        try {
            $name = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null | Select-Object -First 1
            if ($name) {
                Add-Result PASS 'gpu' $name.Trim()
            } else {
                Add-Result WARN 'gpu' 'nvidia-smi present but no GPU detected'
            }
        } catch {
            Add-Result WARN 'gpu' 'nvidia-smi failed to run'
        }
    } else {
        Add-Result WARN 'gpu' 'nvidia-smi not on PATH (optional for LLM acceleration)'
    }
}

function Test-Ollama {
    $url = if ($env:HERMES3D_LLM_BASE_URL) { $env:HERMES3D_LLM_BASE_URL } else { 'http://127.0.0.1:11434' }
    try {
        $null = Invoke-WebRequest -Uri "$url/api/tags" -TimeoutSec 1 -UseBasicParsing 2>$null
        Add-Result PASS 'ollama' "reachable at $url"
    } catch {
        Add-Result WARN 'ollama' "not reachable at $url (optional)" 'Start ollama if you want LLM features'
    }
}

function Test-Wsl {
    if (Get-Command wsl -ErrorAction SilentlyContinue) {
        try {
            $distros = & wsl --list --quiet 2>$null
            if ($distros) {
                Add-Result PASS 'wsl' ('distros: ' + ($distros -join ', '))
            } else {
                Add-Result WARN 'wsl' 'wsl present but no distros installed'
            }
        } catch {
            Add-Result WARN 'wsl' 'wsl present but query failed'
        }
    } else {
        Add-Result WARN 'wsl' 'wsl not installed (optional for Linux-side tooling)'
    }
}

function Test-Docker {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            $null = & docker info 2>$null
            if ($LASTEXITCODE -eq 0) {
                Add-Result PASS 'docker' 'daemon reachable'
            } else {
                Add-Result WARN 'docker' 'docker installed but daemon not running' 'Start Docker Desktop'
            }
        } catch {
            Add-Result WARN 'docker' 'docker installed but query failed'
        }
    } else {
        Add-Result WARN 'docker' 'docker not on PATH (optional for integration tests)'
    }
}

# --- Run checks ---
$py = Test-Python
Test-PythonPackages -Py $py
Test-DevPackages -Py $py
Test-Slicer
Test-DiskSpace
Test-VarDir
Test-ProofKey
Test-Gpu
Test-Ollama
Test-Wsl
Test-Docker

$pass = ($results | Where-Object { $_.Status -eq 'PASS' }).Count
$warn = ($results | Where-Object { $_.Status -eq 'WARN' }).Count
$fail = ($results | Where-Object { $_.Status -eq 'FAIL' }).Count

if ($Json) {
    $out = [pscustomobject]@{
        results = $results
        summary = @{ pass = $pass; warn = $warn; fail = $fail }
    }
    $out | ConvertTo-Json -Depth 4
} else {
    Write-Host 'Hermes3D-OS Lite -- environment doctor'
    Write-Host '======================================'
    foreach ($r in $results) {
        switch ($r.Status) {
            'PASS' {
                Write-Host ('  [PASS] {0,-20} {1}' -f $r.Name, $r.Detail) -ForegroundColor Green
            }
            'WARN' {
                Write-Host ('  [WARN] {0,-20} {1}' -f $r.Name, $r.Detail) -ForegroundColor Yellow
                if ($r.Fix) { Write-Host ('         {0}' -f $r.Fix) -ForegroundColor DarkGray }
            }
            'FAIL' {
                Write-Host ('  [FAIL] {0,-20} {1}' -f $r.Name, $r.Detail) -ForegroundColor Red
                if ($r.Fix) { Write-Host ('         {0}' -f $r.Fix) -ForegroundColor DarkGray }
            }
        }
    }
    Write-Host ''
    Write-Host ("Summary: {0} pass, {1} warn, {2} fail" -f $pass, $warn, $fail)
}

if ($fail -gt 0) { exit 1 }
exit 0
