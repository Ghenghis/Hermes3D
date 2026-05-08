# blender-main

## Purpose

Second vendored snapshot of the Blender source tree, mirroring the upstream `main` branch. Functionally identical to `apps\blender` at the time of capture; the duplicate is most likely retained for diff/audit purposes (e.g. comparing a tagged release vs. main) by Hermes3D OS build pipelines. Same role as the sibling `blender/` folder: 3D modeling stage that produces STL/OBJ for downstream slicing.

## Tech stack

- Languages: C/C++ (core), Python 3 (scripts/add-ons)
- Build system: CMake (`CMakeLists.txt`, `make.bat`, `GNUmakefile`)
- License: GPLv3
- Python tooling: `pyproject.toml`

## Status

Vendored snapshot, not a git repo (no `.git` directory; files are unarchived without git mode bits — `Mode -----`).
- Last write time of folder: 2026-04-30 12:35:38
- No embedded version tag at top level; corresponds to upstream blender `main` branch HEAD at extract time.
- Companion artifacts adjacent to this folder: `blender-main.bundle`, `blender-main.tar.gz`, `blender-main.zip` (the source archives this folder was unpacked from).

## Top-level layout

- `assets/`, `build_files/`, `doc/`, `extern/`, `intern/`, `lib/`, `locale/`, `release/`, `scripts/`, `source/`, `tests/`, `tools/`
- `.gitea/`, `.github/`, `.well-known/`
- `CMakeLists.txt`, `GNUmakefile`, `make.bat`
- `pyproject.toml`, `README.md`, `AUTHORS`, `COPYING`
- `.clang-format`, `.clang-tidy`, `.editorconfig`, `.gitattributes`, `.gitignore`, `.gitmodules`, `.git-blame-ignore-revs`

## Hermes3D integration (INFERRED)

INFERRED: same module registry entry shape as `apps\blender`, distinguished by a `branch: main` tag. Probable use:
- Build pipeline produces `blender-main` → smoke test → diff vs. tagged `blender` snapshot.
- Source OS exposes a single logical `blender` capability; the registry probably picks one of the two trees by env/preset.
- Verifier: `blender --version` (after build) — same as sibling.

## Disk size

282.18 MB

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#fafafa" stroke="#ddd"/>
  <rect x="20" y="80" width="100" height="50" fill="#ff7e1c" stroke="#222"/>
  <text x="70" y="100" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#fff">blender (tag)</text>
  <text x="70" y="118" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">stable</text>
  <rect x="20" y="20" width="100" height="50" fill="#ff9e4a" stroke="#222"/>
  <text x="70" y="40" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#fff">blender-main</text>
  <text x="70" y="58" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">tracking HEAD</text>
  <rect x="160" y="50" width="100" height="60" fill="#cccccc" stroke="#222"/>
  <text x="210" y="75" text-anchor="middle" font-family="sans-serif" font-size="12">build + diff</text>
  <text x="210" y="92" text-anchor="middle" font-family="sans-serif" font-size="10">Source-OS</text>
  <rect x="290" y="50" width="90" height="60" fill="#5a8dee" stroke="#222"/>
  <text x="335" y="75" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#fff">pipeline</text>
  <text x="335" y="92" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">slice/print</text>
  <line x1="120" y1="45" x2="160" y2="70" stroke="#222" stroke-width="2" marker-end="url(#a2)"/>
  <line x1="120" y1="105" x2="160" y2="90" stroke="#222" stroke-width="2" marker-end="url(#a2)"/>
  <line x1="260" y1="80" x2="290" y2="80" stroke="#222" stroke-width="2" marker-end="url(#a2)"/>
  <defs>
    <marker id="a2" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#222"/>
    </marker>
  </defs>
  <text x="200" y="155" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#666">Twin source trees enable A/B verification</text>
  <text x="200" y="175" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#888">main vs. release tag for regression detection</text>
</svg>
