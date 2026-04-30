# Printer Adapters

## Moonraker
Use for Klipper printers. Read-only first: status, temps, files, websocket events. Write operations gated.

## Fluidd / Mainsail
These are frontends over Moonraker, not printer APIs. Hermes3D may dock/undock them as web panels, but printer control should use Moonraker adapter.

## OctoPrint
Use REST API and web UI panel. Detect API key and server health. Write operations gated.

## Printrun / Printcore
Use for direct USB/serial printers. Highest caution. Start with port detection and read-only query. Manual G-code requires confirmation and denylist scan.

## Printer mapping
Unknown printers start in Manual/Detect mode. Adapter assignment is explicit per printer.

## Emergency controls
Emergency stop must be visible only after adapter capability is verified. It must never be mocked as working.
