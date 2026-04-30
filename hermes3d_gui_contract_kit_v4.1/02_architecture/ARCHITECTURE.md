# Hermes3D Integration Architecture

## Core boundary
Hermes3D owns:
- UI shell and dashboard.
- Backend API.
- Adapter contracts.
- Proof system.
- Safety policy.
- Workflow orchestration.

Hermes3D does not own:
- Blender internals.
- Slicer internals.
- Fluidd/Mainsail/OctoPrint source.
- Printer firmware.

## Layers
```text
React/Tailwind UI
  -> Hermes3D API
    -> Adapter Registry
      -> Provider Adapter
        -> External Tool/API/App
```

## Adapter types
- `MCPAdapter`: Blender MCP providers.
- `SlicerAdapter`: FLSUN, Prusa, Orca, Cura.
- `PrinterApiAdapter`: Moonraker, OctoPrint.
- `UsbPrinterAdapter`: Printrun/Printcore.
- `WebPanelAdapter`: Fluidd, Mainsail, OctoPrint web.
- `ExternalAppAdapter`: Blender/slicer native apps.

## Provider manager
Every provider has:
- detect()
- install_or_stage()
- validate()
- promote()
- rollback()
- launch()
- status()
- capabilities()

## Update safety
Never auto-promote external updates. Updates go through staging and validation.

## Printer command safety
Commands move through:
```text
UI action -> policy check -> dry-run if possible -> confirmation -> adapter call -> log -> proof bundle
```
