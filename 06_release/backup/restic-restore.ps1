[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $EnvFile = (Join-Path $HOME ".hermes3d\restic-env.ps1"),
    [string] $SnapshotId,
    [string] $RestoreRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $EnvFile)) {
    Write-Error "Missing Restic environment file: $EnvFile. Restore credentials must stay outside Git and Syncthing."
    exit 1
}

. $EnvFile

$requiredVars = @("RESTIC_REPOSITORY", "RESTIC_PASSWORD", "B2_ACCOUNT_ID", "B2_ACCOUNT_KEY")
foreach ($name in $requiredVars) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
        Write-Error "Restic environment file did not define required variable: $name"
        exit 1
    }
}

& restic snapshots --tag local-secrets

if ([string]::IsNullOrWhiteSpace($SnapshotId)) {
    $SnapshotId = Read-Host "Snapshot ID to restore"
}
if ([string]::IsNullOrWhiteSpace($RestoreRoot)) {
    $RestoreRoot = Read-Host "Restore target directory (must be a staging path, not live config)"
}

$forbiddenTargets = @(
    (Join-Path $HOME ".hermes3d"),
    (Join-Path $env:APPDATA "Hermes3D"),
    (Join-Path $HOME ".env")
)

foreach ($target in $forbiddenTargets) {
    if ($RestoreRoot.TrimEnd("\") -ieq $target.TrimEnd("\")) {
        Write-Error "Refusing to restore directly into live Hermes3D state: $RestoreRoot"
        exit 1
    }
}

New-Item -ItemType Directory -Force -Path $RestoreRoot | Out-Null

if ($PSCmdlet.ShouldProcess($RestoreRoot, "restore Restic snapshot $SnapshotId")) {
    & restic restore $SnapshotId --target $RestoreRoot
}
