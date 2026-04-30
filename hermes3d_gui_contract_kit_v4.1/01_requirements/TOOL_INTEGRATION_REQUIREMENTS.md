# Tool Integration Requirements

Hermes3D integrates external tools through adapters. External repos/apps are not merged into core app logic.

## Integration levels

0. Detected.
1. Read-only.
2. Preview.
3. Staged write.
4. User-approved write.
5. Automated write only after safety gates, audit logs, rollback, and allowlists exist.

## Tool-specific requirements

- Blender / Blender MCP: detect install/provider; validate scene info, viewport screenshot, safe execute, 3MF export; screenshot proof; mesh QA before slicer.
- PrusaSlicer / OrcaSlicer / FLSUN Slicer / Cura: detect binary; version command; slice known-good fixture to staging; never send to printer during smoke test.
- Printrun: detect pronsole/pronterface; list serial ports; read-only first; movement/heating disabled until safety gate GREEN.
- Moonraker: query `/server/info` and `/printer/info`; writes require allowlist.
- Fluidd / Mainsail: external web UIs; dock/undock iframe/browser-window only if headers allow; otherwise external fullscreen.
- OctoPrint: API key required; read-only first; write-control only after explicit enable.
