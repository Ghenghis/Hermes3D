# External Repo Policy

## Do not merge giant repos into core
Claude may clone/download repos into `source-lab/`, but must not copy entire upstream apps into Hermes3D source.

## Why
- Blender, PrusaSlicer, OrcaSlicer, Cura are large upstream apps with their own build systems.
- Maintaining forks would create update pain.
- Hermes3D only needs stable control boundaries.

## Correct pattern
```text
source-lab/<tool-repo>       # reference/source clone only
installed-tools/<tool>       # user installed binary or extracted zip
hermes3d/adapters/<tool>.py  # small adapter owned by Hermes3D
```

## What Claude can do
- Add repo links to registry.
- Clone to `source-lab/` for inspection.
- Detect installed binaries.
- Launch external apps.
- Call documented CLI/API/MCP interfaces.
- Create adapters.
- Write tests.

## What Claude must not do without explicit approval
- Replace upstream slicer code.
- Patch printer firmware.
- Bypass vendor restrictions/cloud controls.
- Send live print commands before dry-run proof gates.
