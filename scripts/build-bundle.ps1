<#
    Hermes3D A.6 — emit a single signed proof bundle for the current build.

    Usage:
        scripts\build-bundle.ps1
        scripts\build-bundle.ps1 -Output 05_truth_proof\bundles\
        scripts\build-bundle.ps1 -KeyEnvVar HERMES3D_PROOF_KEY
#>
[CmdletBinding()]
param(
    [string]$Output = "",
    [string]$KeyEnvVar = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

$argList = @((Join-Path $repoRoot "scripts/_build_bundle.py"))
if ($Output)    { $argList += @("--output", $Output) }
if ($KeyEnvVar) { $argList += @("--key-env-var", $KeyEnvVar) }
if ($Rest)      { $argList += $Rest }

& $python @argList
exit $LASTEXITCODE
