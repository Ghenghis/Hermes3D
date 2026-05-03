param(
    [string]$Version = "",
    [string]$PackId = "Hermes3D-OS"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
Push-Location $RepoRoot
try {
    $tag = if ($Version) {
        $Version
    } elseif ($env:GITHUB_REF_NAME) {
        $env:GITHUB_REF_NAME -replace "^v", ""
    } else {
        "0.0.0-dev"
    }

    Write-Host "[windows-pack] building PyInstaller onedir bundle for version $tag"
    python -m PyInstaller --onedir `
        --name=Hermes3D `
        --paths=03_implementation/src `
        --collect-all=hermes3d `
        --collect-all=gradio `
        --collect-all=trimesh `
        --hidden-import=manifold3d `
        --hidden-import=rtree `
        --noconfirm `
        --distpath=dist/win `
        03_implementation/src/hermes3d/app/launcher.py

    Write-Host "[windows-pack] packing Velopack release"
    vpk pack `
        --packId=$PackId `
        --packVersion=$tag `
        --packDir=dist/win/Hermes3D `
        --mainExe=Hermes3D.exe `
        --outputDir=dist/release-win

    Write-Host "[windows-pack] artifacts written to dist/release-win"
} finally {
    Pop-Location
}
