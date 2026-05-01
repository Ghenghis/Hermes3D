# Hermes3D — wrapper for the production registry validator.
#
# Forwards all arguments to `python -m hermes3d.registry.validator`. The default
# (no args) validates the kit's external_repos_registry.yaml.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    python -m hermes3d.registry.validator @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
