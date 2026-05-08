# PrusaSlicer-master

## Purpose

PrusaSlicer is the canonical upstream slicer (maintained by Prusa Research, derived from Slic3r) that converts STL/OBJ/AMF meshes into G-code for FFF printers or PNG layers for mSLA printers. It is widely the reference implementation against which the Slic3r-derived ecosystem (including OrcaSlicer) compares behavior.

In Hermes3D OS it is the secondary / reference slicing module, paired with OrcaSlicer. The Source OS module registry can use it as an alternative slicer for users on Prusa hardware, and as a CLI-only `libslic3r` engine for headless slicing in automated pipelines.

## Tech stack

- Languages: C++ (all user-facing), C
- Core library: `libslic3r` (standalone, embeddable)
- Build system: CMake (`CMakeLists.txt`, `CMakePresets.json`, `build_win.bat`)
- License: see `LICENSE`

## Status

Vendored snapshot, not a git repo.
- Last write time of folder: 2026-04-22 07:07:52
- Version per `version.inc`: `SLIC3R_VERSION = 2.9.5-beta2`, build ID `PrusaSlicer-2.9.5-beta2+UNKNOWN`
- Tracks upstream `master` branch.

## Top-level layout

- `src/` — C++ source (libslic3r + GUI)
- `deps/`, `bundled_deps/` — third-party builds
- `build-utils/`, `cmake/` — build helpers
- `resources/` — profiles, icons
- `doc/`, `tests/`, `sandboxes/`
- `.github/`
- `CMakeLists.txt`, `CMakePresets.json`, `version.inc`
- `build_win.bat`
- `README.md`, `LICENSE`
- `.clang-format`, `.gitignore`

## Hermes3D integration (INFERRED)

INFERRED: registered alongside Orca as a slicer alternative:
- `kind: cli`
- `binary: prusa-slicer` (from build output) and/or libslic3r linked statically
- `verifier: prusa-slicer --help` exit 0 + version regex matching `2.9.5-beta2`
- `capabilities: ["slice.fff", "slice.msla", "gcode.export", "png.export", "libslic3r.link"]`
- Headless mode (`--cli`) makes it ideal for batch/server workflows in Hermes Agent task runners.

## Disk size

201.04 MB

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#fafafa" stroke="#ddd"/>
  <rect x="10" y="80" width="80" height="50" fill="#ffd6a5" stroke="#222"/>
  <text x="50" y="100" text-anchor="middle" font-family="sans-serif" font-size="11">STL/OBJ</text>
  <text x="50" y="118" text-anchor="middle" font-family="sans-serif" font-size="10">AMF</text>
  <rect x="120" y="50" width="130" height="100" fill="#ea580c" stroke="#222"/>
  <text x="185" y="80" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#fff">PrusaSlicer</text>
  <text x="185" y="98" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">2.9.5-beta2</text>
  <text x="185" y="115" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">libslic3r core</text>
  <text x="185" y="132" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">CLI + GUI</text>
  <rect x="280" y="40" width="105" height="40" fill="#a3e635" stroke="#222"/>
  <text x="333" y="65" text-anchor="middle" font-family="sans-serif" font-size="12">FFF G-code</text>
  <rect x="280" y="100" width="105" height="40" fill="#7dd3fc" stroke="#222"/>
  <text x="333" y="120" text-anchor="middle" font-family="sans-serif" font-size="11">mSLA PNG</text>
  <text x="333" y="134" text-anchor="middle" font-family="sans-serif" font-size="10">layer images</text>
  <line x1="90" y1="105" x2="120" y2="100" stroke="#222" stroke-width="2" marker-end="url(#a7)"/>
  <line x1="250" y1="80" x2="280" y2="60" stroke="#222" stroke-width="2" marker-end="url(#a7)"/>
  <line x1="250" y1="120" x2="280" y2="120" stroke="#222" stroke-width="2" marker-end="url(#a7)"/>
  <defs>
    <marker id="a7" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#222"/>
    </marker>
  </defs>
  <text x="200" y="25" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="bold">PrusaSlicer FFF + mSLA</text>
  <text x="200" y="180" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#666">Reference slicer; libslic3r usable as headless library</text>
</svg>
