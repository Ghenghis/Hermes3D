# Slicer Adapters

## Supported slicers
- FLSUN Slicer
- PrusaSlicer
- OrcaSlicer
- Cura

## Adapter stages
1. Detect installed binary or user zip.
2. Launch GUI.
3. Detect CLI support.
4. Import model.
5. Dry-run slice.
6. Export G-code/3MF.
7. Validate output file size and headers.
8. Map printer profile.

## FLSUN Slicer
Priority for FLSUN printers. Treat user-provided zip as local source. Do not assume CLI support until detected.

## PrusaSlicer
Preferred stable CLI path where available. Use config bundles/profiles per printer.

## OrcaSlicer
Use official repo/binary only. Do not use cloud-bypass forks or unofficial unlock projects.

## Cura
Optional; detect binary and profile support.

## Safety
Slicing can run automatically. Printing cannot start automatically without proof gate and confirmation.
