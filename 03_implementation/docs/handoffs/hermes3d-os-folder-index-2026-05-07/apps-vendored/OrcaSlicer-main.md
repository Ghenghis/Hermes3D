# OrcaSlicer-main

## Purpose

OrcaSlicer is an open-source next-gen slicer for FFF 3D printers, derived from the Slic3r/PrusaSlicer/SuperSlicer lineage and maintained by SoftFever. It converts STL/OBJ/3MF meshes into G-code with extensive calibration, seam, support, and network-printer features. In Hermes3D OS it is the primary slicing module — the bridge between Blender-authored mesh assets and the Printrun host that drives the printer.

This vendored snapshot is the source-of-record from which Hermes3D OS builds and verifies the Orca CLI / GUI. Network printer integration (Klipper, PrusaLink, OctoPrint) means Orca can also act as a printer-side endpoint Hermes3D talks to over HTTP.

## Tech stack

- Languages: C++ (core), some C, Python (build/scripts), Shell + Batch
- Build system: CMake (`CMakeLists.txt`, `build_release_vs2022.bat`, `build_linux.sh`, `build_release_macos.sh`, `build_flatpak.sh`)
- Localization: `localization/`
- License: see `LICENSE.txt`

## Status

Vendored snapshot, not a git repo.
- Last write time of folder: 2026-04-30 05:19:13
- Version per `version.inc`: `SoftFever_VERSION = 2.4.0-dev`, `SLIC3R_VERSION = 02.05.01.52`
- App name/key: `OrcaSlicer`

## Top-level layout

- `src/` — C++ source (Slic3r-derived)
- `deps/`, `deps_src/` — third-party dependency builds
- `cmake/`, `tools/`, `scripts/` — build and helper tooling
- `resources/` — printer/filament profiles, icons, shaders
- `localization/`, `SoftFever_doc/`
- `tests/`, `sandboxes/`
- `.devcontainer/`, `.github/`, `.idea/`, `.claude/`
- `CMakeLists.txt`, `version.inc`
- `build_release_vs2022.bat`, `build_release_vs.bat`, `build_release.bat`, `build_linux.sh`, `build_release_macos.sh`, `build_flatpak.sh`
- `AGENTS.md`, `CLAUDE.md`, `README.md`, `SECURITY.md`, `LICENSE.txt`
- `.clang-format`, `.cursorignore`, `.dockerignore`, `.doxygen`, `.gitattributes`, `.gitignore`

## Hermes3D integration (INFERRED)

INFERRED: registered as a `cli` + `network` hybrid module:
- `kind: cli`
- `binary: OrcaSlicer` (from build output)
- `verifier: OrcaSlicer --help-fff` exit code 0 + version regex matching `2.4.0-dev`
- `capabilities: ["slice.fff", "gcode.export", "klipper.connect", "prusalink.connect", "octoprint.connect"]`
- Possible HTTP probe to its built-in network bridge for printer status

The presence of `AGENTS.md` and `CLAUDE.md` at the top level suggests this snapshot is already wired for AI-agent automation, which Hermes Agent can drive directly.

## Disk size

293.29 MB

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#fafafa" stroke="#ddd"/>
  <rect x="10" y="80" width="80" height="50" fill="#ffd6a5" stroke="#222"/>
  <text x="50" y="100" text-anchor="middle" font-family="sans-serif" font-size="11">STL / OBJ</text>
  <text x="50" y="118" text-anchor="middle" font-family="sans-serif" font-size="10">3MF</text>
  <rect x="120" y="60" width="120" height="90" fill="#f97316" stroke="#222"/>
  <text x="180" y="90" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#fff">OrcaSlicer</text>
  <text x="180" y="108" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">2.4.0-dev</text>
  <text x="180" y="125" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">slice + profiles</text>
  <text x="180" y="140" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">network bridge</text>
  <rect x="270" y="40" width="115" height="40" fill="#a3e635" stroke="#222"/>
  <text x="328" y="65" text-anchor="middle" font-family="sans-serif" font-size="12">G-code → Printrun</text>
  <rect x="270" y="100" width="115" height="40" fill="#60a5fa" stroke="#222"/>
  <text x="328" y="118" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#fff">Klipper / OctoPrint</text>
  <text x="328" y="132" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">PrusaLink HTTP</text>
  <line x1="90" y1="105" x2="120" y2="105" stroke="#222" stroke-width="2" marker-end="url(#a5)"/>
  <line x1="240" y1="80" x2="270" y2="60" stroke="#222" stroke-width="2" marker-end="url(#a5)"/>
  <line x1="240" y1="130" x2="270" y2="120" stroke="#222" stroke-width="2" marker-end="url(#a5)"/>
  <defs>
    <marker id="a5" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#222"/>
    </marker>
  </defs>
  <text x="200" y="25" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="bold">OrcaSlicer slicing + network</text>
  <text x="200" y="180" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#666">Mesh in, G-code out, optional direct printer push</text>
</svg>
