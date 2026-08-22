# scripts/run-e2e.ps1 — Windows companion to run-e2e.sh.
#
# Boots FastAPI on :8765 + Gradio on :7860, polls health, runs Playwright,
# tears down, exits with Playwright's exit code. Logs/artifacts captured to
# var/e2e-runs/<utc>/.

$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $RepoRoot

$Stamp  = (Get-Date -AsUTC).ToString('yyyyMMddTHHmmssZ')
$RunDir = Join-Path $RepoRoot "var/e2e-runs/$Stamp"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$ApiPort = if ($env:HERMES3D_API_PORT) { $env:HERMES3D_API_PORT } else { '8765' }
$UiPort  = if ($env:HERMES3D_UI_PORT)  { $env:HERMES3D_UI_PORT }  else { '7860' }

$env:PYTHONPATH       = "$RepoRoot\03_implementation\src;$($env:PYTHONPATH)"
$env:HERMES3D_PROOF_KEY = if ($env:HERMES3D_PROOF_KEY) { $env:HERMES3D_PROOF_KEY } else { 'hermes3d-default-proof-key-not-secret' }
$env:HERMES3D_API_URL = "http://127.0.0.1:$ApiPort"
$env:HERMES3D_UI_URL  = "http://127.0.0.1:$UiPort"

$ApiLog = Join-Path $RunDir 'api.log'
$UiLog  = Join-Path $RunDir 'ui.log'
$PwLog  = Join-Path $RunDir 'playwright.log'

Write-Host "[run-e2e] artifacts -> $RunDir"

$apiProc = Start-Process -FilePath 'python' `
    -ArgumentList @('-m','uvicorn','hermes3d.api.app:app','--host','127.0.0.1','--port',$ApiPort,'--log-level','info') `
    -RedirectStandardOutput $ApiLog -RedirectStandardError "$ApiLog.err" -PassThru -NoNewWindow

$env:HERMES3D_HOST = '127.0.0.1'
$env:HERMES3D_PORT = $UiPort
$uiProc = Start-Process -FilePath 'python' `
    -ArgumentList @('-m','hermes3d.app.launcher') `
    -RedirectStandardOutput $UiLog -RedirectStandardError "$UiLog.err" -PassThru -NoNewWindow

function Stop-All {
    foreach ($p in @($apiProc, $uiProc)) {
        if ($p -and -not $p.HasExited) {
            try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
}
Register-EngineEvent PowerShell.Exiting -Action { Stop-All } | Out-Null

function Wait-Endpoint($url, $label, $log) {
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
                Write-Host "[run-e2e]   $label ready: $url"
                return $true
            }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    Write-Host "[FAIL] $label did not come up at $url within 30s"
    if (Test-Path $log) { Get-Content $log -Tail 80 | Write-Host }
    return $false
}

$exit = 0
try {
    if (-not (Wait-Endpoint "http://127.0.0.1:$ApiPort/health" 'FastAPI' $ApiLog)) { $exit = 1; throw 'api timeout' }
    if (-not (Wait-Endpoint "http://127.0.0.1:$UiPort/" 'Gradio' $UiLog))         { $exit = 1; throw 'ui timeout' }

    Push-Location (Join-Path $RepoRoot '04_testing/playwright')
    try {
        & npm test 2>&1 | Tee-Object -FilePath $PwLog
        $exit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
} catch {
    if ($exit -eq 0) { $exit = 1 }
    Write-Host "[run-e2e] aborted: $_"
} finally {
    Stop-All
    foreach ($d in @('playwright-report','test-results')) {
        $src = Join-Path $RepoRoot "04_testing/playwright/$d"
        if (Test-Path $src) {
            Copy-Item -Recurse -Force $src $RunDir -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "[run-e2e] exit=$exit   artifacts in $RunDir"
exit $exit
