# blender

## Purpose

Vendored snapshot of the Blender source tree (the free and open source 3D creation suite — modeling, rigging, animation, simulation, rendering, compositing, motion tracking, video editing). Inside Hermes3D OS, Blender is the upstream modeling stage of the additive-manufacturing pipeline: STL/OBJ assets are authored or repaired in Blender and then handed downstream to a slicer (OrcaSlicer or PrusaSlicer) before reaching a printer host (Printrun).

The Source OS module registry treats `apps\blender` as a buildable / launchable external tool. Hermes3D does not embed the Blender renderer — it shells out to a built `blender` binary or to a build target produced from this tree.

## Tech stack

- Languages: C/C++ (core), Python 3 (scripts/add-ons, build orchestration)
- Build system: CMake (`CMakeLists.txt`, `make.bat`, `GNUmakefile`)
- License: GPLv3 (`COPYING`)
- Python tooling: `pyproject.toml` (autopep8 config)

## Status

Vendored snapshot, not a git repo (no `.git` directory present).
- Last write time of folder: 2026-04-30 12:35:38
- Mirror of upstream `blender/blender` main; no embedded version tag inside this snapshot's top-level files.

## Top-level layout

- `assets/`, `build_files/`, `doc/`, `extern/`, `intern/`, `lib/`, `locale/`, `release/`, `scripts/`, `source/`, `tests/`, `tools/`
- `.gitea/`, `.github/`, `.well-known/`
- `CMakeLists.txt`, `GNUmakefile`, `make.bat` — build entry points
- `pyproject.toml` — Python tooling config
- `README.md`, `AUTHORS`, `COPYING`
- `.clang-format`, `.clang-tidy`, `.editorconfig`, `.gitattributes`, `.gitignore`, `.gitmodules`, `.git-blame-ignore-revs`

## Hermes3D integration (INFERRED)

INFERRED: registered in the Source OS module registry as a CLI verifier. Probable contract:
- `kind: cli`
- `binary: blender` (resolved from `lib/` builds or system PATH)
- `verifier: blender --version` exit code 0 + version regex
- `capabilities: ["model.import", "model.export.stl", "model.export.obj"]`

Because this is the source tree (not a built binary), Hermes3D OS most likely has a parallel "built artifact" path under `lib\` or expects a system-installed Blender; the vendored tree is the pinned source for reproducible builds.

## Disk size

282.18 MB

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#fafafa" stroke="#ddd"/>
  <rect x="20" y="70" width="90" height="60" fill="#ff7e1c" stroke="#222"/>
  <text x="65" y="95" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#fff">Blender</text>
  <text x="65" y="115" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">model author</text>
  <rect x="155" y="70" width="90" height="60" fill="#dcdcdc" stroke="#222"/>
  <text x="200" y="95" text-anchor="middle" font-family="sans-serif" font-size="13">STL / OBJ</text>
  <text x="200" y="115" text-anchor="middle" font-family="sans-serif" font-size="10">mesh asset</text>
  <rect x="290" y="70" width="90" height="60" fill="#5a8dee" stroke="#222"/>
  <text x="335" y="95" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#fff">Slicer</text>
  <text x="335" y="115" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">Orca / Prusa</text>
  <line x1="110" y1="100" x2="155" y2="100" stroke="#222" stroke-width="2" marker-end="url(#a1)"/>
  <line x1="245" y1="100" x2="290" y2="100" stroke="#222" stroke-width="2" marker-end="url(#a1)"/>
  <defs>
    <marker id="a1" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#222"/>
    </marker>
  </defs>
  <text x="200" y="30" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="bold">Blender role in Hermes3D pipeline</text>
  <text x="200" y="170" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#666">Source-OS CLI verifier: blender --version</text>
</svg>
