<#
.SYNOPSIS
    Start the Hermes3D-OS Lite dev stack (Gradio UI + REST API + supervisor).

.PARAMETER UiOnly
    Only start the Gradio UI.

.PARAMETER ApiOnly
    Only start the REST API.

.PARAMETER NoSupervisor
    Skip the supervisor daemon.

.PARAMETER NoUi
    Don't start the Gradio UI (useful for headless dev).

.PARAMETER NoApi
    Don't start the REST API.

.PARAMETER Remote
    Also start the Telegram/Discord remote-control bridge.

.EXAMPLE
    pwsh scripts/run-dev.ps1               # start everything except remote
    pwsh scripts/run-dev.ps1 -UiOnly
#>
[CmdletBinding()]
param(
    [switch]$UiOnly,
    [switch]$ApiOnly,
    [switch]$NoSupervisor,
    [switch]$NoUi,
    [switch]$NoApi,
    [switch]$Remote
)

$ErrorActionPreference = 'Stop'

$ui = $true
$api = $true
$supervisor = $true

if ($UiOnly) { $api = $false; $supervisor = $false }
if ($ApiOnly) { $ui = $false; $supervisor = $false }
if ($NoSupervisor) { $supervisor = $false }
if ($NoUi) { $ui = $false }
if ($NoApi) { $api = $false }

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '....')
Push-Location $repoRoot

$env:PYTHONPATH = (Join-Path $repoRoot '03_implementation/src') + [System.IO.Path]::PathSeparator + $env:PYTHONPATH
if (-not $env:HERMES3D_PROOF_KEY) {
    $env:HERMES3D_PROOF_KEY = 'hermes3d-default-proof-key-not-secret'
}

New-Item -ItemType Directory -Path 'var' -Force | Out-Null
New-Item -ItemType Directory -Path 'logs' -Force | Out-Null

$processes = New-Object System.Collections.Generic.List[System.Diagnostics.Process]

function Stop-AllProcesses {
    Write-Host ''
    Write-Host '[run-dev] shutting down ...' -ForegroundColor Yellow
    foreach ($p in $processes) {
        if (-not $p.HasExited) {
            try {
                $p.CloseMainWindow() | Out-Null
                if (-not $p.WaitForExit(2000)) {
                    $p.Kill()
                }
            } catch {
                # process already exited
            }
        }
    }
}

try {
    $py = $null
    foreach ($cmd in @('python', 'py', 'python3')) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            $py = $cmd
            break
        }
    }
    if (-not $py) { throw 'Python not on PATH. Run scripts/doctor.ps1 first.' }

    if ($api) {
        Write-Host '[run-dev] starting REST API on :8765 ...' -ForegroundColor Cyan
        $apiProc = Start-Process -FilePath $py `
            -ArgumentList '-m', 'uvicorn', 'hermes3d.api.server:app',
                          '--host', '127.0.0.1', '--port', '8765',
                          '--log-level', 'info' `
            -RedirectStandardOutput 'logs/api.log' `
            -RedirectStandardError  'logs/api.err.log' `
            -PassThru -NoNewWindow
        $processes.Add($apiProc)
        Start-Sleep -Seconds 1
    }

    if ($supervisor) {
        Write-Host '[run-dev] starting supervisor daemon ...' -ForegroundColor Cyan
        $supProc = Start-Process -FilePath $py `
            -ArgumentList '-m', 'hermes3d.core.supervisor.daemon' `
            -RedirectStandardOutput 'logs/supervisor.log' `
            -RedirectStandardError  'logs/supervisor.err.log' `
            -PassThru -NoNewWindow
        $processes.Add($supProc)
    }

    if ($Remote) {
        if (-not $env:HERMES3D_TELEGRAM_BOT_TOKEN -and -not $env:HERMES3D_DISCORD_CONTROL_WEBHOOK) {
            Write-Host '[WARN] -Remote requested but no Telegram/Discord credentials set; skipping.' -ForegroundColor Yellow
        } else {
            Write-Host '[run-dev] starting remote-control bridge ...' -ForegroundColor Cyan
            $remoteProc = Start-Process -FilePath $py `
                -ArgumentList '-m', 'hermes3d.core.integrations.remote_control' `
                -RedirectStandardOutput 'logs/remote_control.log' `
                -RedirectStandardError  'logs/remote_control.err.log' `
                -PassThru -NoNewWindow
            $processes.Add($remoteProc)
        }
    }

    if ($ui) {
        Write-Host '[run-dev] starting Gradio UI on :7860 ...' -ForegroundColor Cyan
        Write-Host '[run-dev]   logs in logs/, press Ctrl+C to stop' -ForegroundColor DarkGray
        # The Gradio launcher runs in the foreground. When it exits, the trap above
        # tears down the rest.
        & $py '-m' 'hermes3d.app.launcher'
    } else {
        Write-Host '[run-dev] no UI requested; press Ctrl+C to stop background services.' -ForegroundColor DarkGray
        while ($processes.Count -gt 0) {
            Start-Sleep -Seconds 1
            $processes = [System.Collections.Generic.List[System.Diagnostics.Process]] (
                $processes | Where-Object { -not $_.HasExited }
            )
        }
    }
} finally {
    Stop-AllProcesses
    Pop-Location
}
