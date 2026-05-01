# Hermes3D — print env-detect report as JSON.
#
# Read-only: runs nvidia-smi --query-gpu, node --version, wmic (Windows only).
# No installs. No mutations. No network calls.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    python -c "import json; from hermes3d.env.detect import detect_env; print(json.dumps(detect_env().to_dict(), indent=2))"
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
