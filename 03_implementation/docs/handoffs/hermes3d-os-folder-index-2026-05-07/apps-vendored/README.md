# apps-vendored — category index

This directory indexes the seven vendored applications under `G:\Github\apps\` that Hermes3D OS bundles or builds as part of its 3D modeling/slicing/printing pipeline. Each linked file gives a shallow inspection (top-level layout, build metadata, version, integration shape, an SVG pipeline diagram).

## Pipeline at a glance

`Blender` (model) → `STL/OBJ/3MF` → `OrcaSlicer` / `PrusaSlicer` (slice) → `G-code` → `Printrun` (host) → printer. `Hermes Desktop` is the GUI shell tying it all together; `locale` is shared translation data.

## Modules

| # | Folder | One-liner |
|---|--------|-----------|
| 1 | [blender](./blender.md) | Blender source tree (tag snapshot) — 3D modeling stage producing STL/OBJ for slicing. |
| 2 | [blender-main](./blender-main.md) | Twin Blender source tree tracking upstream `main` — used for A/B regression diff against the tag snapshot. |
| 3 | [hermes-desktop-main](./hermes-desktop-main.md) | Electron + React 19 desktop GUI (v0.2.2) for Hermes Agent — the H3D user-facing shell hosting Claw3d and tool dispatch. |
| 4 | [locale](./locale.md) | Gettext translation overlay for Printrun (ar/de/fr/hy/it/nl + `pronterface.pot`) — decoupled i18n data. |
| 5 | [OrcaSlicer-main](./OrcaSlicer-main.md) | OrcaSlicer 2.4.0-dev (SoftFever fork of Slic3r) — primary FFF slicer with Klipper/PrusaLink/OctoPrint network bridges. |
| 6 | [Printrun-printrun-2.2.0](./Printrun-printrun-2.2.0.md) | Printrun 2.2.0 — Python printer-host suite (printcore, pronsole, pronterface, plater) streaming G-code over serial. |
| 7 | [PrusaSlicer-master](./PrusaSlicer-master.md) | PrusaSlicer 2.9.5-beta2 — reference C++ slicer (FFF + mSLA), with embeddable `libslic3r` for headless pipelines. |

## Disk footprint

| Folder | MB |
|---|---:|
| blender | 282.18 |
| blender-main | 282.18 |
| hermes-desktop-main | 16.79 |
| locale | 0.61 |
| OrcaSlicer-main | 293.29 |
| Printrun-printrun-2.2.0 | 3.66 |
| PrusaSlicer-master | 201.04 |
| **Total** | **~1,079.75** |

## Notes

- None of the seven folders are git repositories; all are vendored snapshots (last-write times range 2024-10-20 to 2026-04-30).
- Adjacent to these folders the parent `G:\Github\apps\` also contains the source archives (`*.zip`, `*.tar.gz`, `blender-main.bundle`) plus prebuilt `Pronsole.exe` / `Pronterface.exe` binaries.
- Source OS module-registry contracts shown in each file are marked `INFERRED` where not directly observable in the snapshot.
