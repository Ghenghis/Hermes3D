[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $EnvFile = (Join-Path $HOME ".hermes3d\restic-env.ps1"),
    [string] $WorkspaceRoot = $env:HERMES3D_WORKSPACE,
    [string] $UserStateRoot = (Join-Path $HOME ".hermes3d"),
    [string] $RoamingStateRoot = (Join-Path $env:APPDATA "Hermes3D")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $EnvFile)) {
    Write-Error "Missing Restic environment file: $EnvFile. Create it outside Git and outside Syncthing before running backups."
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

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
}

$candidatePaths = @(
    (Join-Path $HOME ".env"),
    (Join-Path $WorkspaceRoot "03_implementation\config\printers.user.toml"),
    $UserStateRoot,
    $RoamingStateRoot
)

$backupPaths = @()
foreach ($path in $candidatePaths) {
    if (Test-Path -LiteralPath $path) {
        $backupPaths += (Resolve-Path -LiteralPath $path).Path
    } else {
        Write-Warning "Skipping missing backup path: $path"
    }
}

if ($backupPaths.Count -eq 0) {
    Write-Error "No Hermes3D local backup paths exist yet; refusing to create an empty Restic snapshot."
    exit 1
}

if ($PSCmdlet.ShouldProcess("Restic repository", "backup Hermes3D local private state")) {
    & restic backup @backupPaths --tag local-secrets --exclude-caches
    & restic forget --tag local-secrets --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
}
