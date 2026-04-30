<#
.SYNOPSIS
  Hermes3D wizard recording wrapper (Windows / PowerShell).
.DESCRIPTION
  Captures the entire wizard.ps1 session via Start-Transcript, plus a
  structured summary.json and env.txt. The recording becomes part of the
  truth-gate proof bundle.
#>
param(
  [switch]$AutoYes,
  [switch]$Quick
)
$ErrorActionPreference = 'Continue'
$Root = Resolve-Path "$PSScriptRoot\.."
Set-Location $Root

$Utc = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$RunDir = Join-Path $Root "var\wizard-runs\$Utc"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
$Transcript = Join-Path $RunDir 'transcript.txt'
$EnvFile    = Join-Path $RunDir 'env.txt'
$ExitFile   = Join-Path $RunDir 'exit_code.txt'
$Summary    = Join-Path $RunDir 'summary.json'

# Env fingerprint
$envLines = @(
  "timestamp_utc=$Utc"
  "host=$($env:COMPUTERNAME)"
  "user=$($env:USERNAME)"
  "cwd=$Root"
  "python=$(python --version 2>&1)"
  "git=$(git --version)"
  "node=$(node --version 2>&1)"
  "git_branch=$(git symbolic-ref --short HEAD 2>$null)"
  "git_commit=$(git rev-parse HEAD)"
)
Set-Content -Path $EnvFile -Value $envLines -Encoding UTF8

$start = Get-Date
Start-Transcript -Path $Transcript -Force | Out-Null
$exitCode = 0
try {
  if ($Quick) {
    & "$Root\scripts\preflight.ps1"
    if ($LASTEXITCODE -ne 0) { $exitCode = $LASTEXITCODE }
    Write-Host "(quick mode: skipped acceptance + UI)"
  } elseif ($AutoYes) {
    & "$Root\scripts\wizard.ps1" -Yes
    $exitCode = $LASTEXITCODE
  } else {
    & "$Root\scripts\wizard.ps1"
    $exitCode = $LASTEXITCODE
  }
} catch {
  Write-Host "EXCEPTION: $_" -ForegroundColor Red
  $exitCode = 1
} finally {
  Stop-Transcript | Out-Null
}
$end = Get-Date

$exitCode | Set-Content -Path $ExitFile -Encoding UTF8
$verdict = if ($exitCode -eq 0) { 'PASS' } else { 'FAIL' }

@{
  timestamp_utc    = $Utc
  duration_seconds = [int]($end - $start).TotalSeconds
  exit_code        = $exitCode
  verdict          = $verdict
  transcript_path  = $Transcript
  env_path         = $EnvFile
  flags            = @{ auto_yes = [bool]$AutoYes; quick = [bool]$Quick }
} | ConvertTo-Json -Depth 5 | Set-Content -Path $Summary -Encoding UTF8

Write-Host ''
Write-Host ('=' * 60)
Write-Host "Wizard recording: $RunDir"
Write-Host "Verdict: $verdict"
Write-Host "Transcript: $Transcript"
Write-Host "Summary:    $Summary"
Write-Host ('=' * 60)
exit $exitCode
