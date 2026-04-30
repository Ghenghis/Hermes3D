# UI-Final Tab Specifications

## Visual contract
Use the supplied dark Hermes3D dashboard screenshot as the master visual contract. All screens reuse the same shell, card style, typography, status badges, neon blue/green/orange accents, dense data layout, and no white-heavy surfaces.

## Universal shell
- Left vertical sidebar with icons and labels.
- Top header with system state, active branch/release, proof status, and user/system controls.
- Main content uses responsive grid cards.
- Right inspector rail appears where helpful.
- Every tab supports docked and undocked panel states.
- Every panel has: title, status badge, actions menu, collapse, undock, fullscreen.

## Tabs

### 1. Dashboard
Purpose: high-level 12-printer and agentic factory overview.
Panels:
- System health cards.
- Printer fleet mini table.
- Active workflow timeline.
- Agents running.
- Proof bundle status.
- Resource panel.
Acceptance:
- Visually matches screenshot at 1920x1080.
- Screenshot gate captured.

### 2. Agents
Panels:
- Agent roster: Planner, Implementer, BlenderModeler, MeshQA, SlicerQA, PrinterControl, Repair, Reviewer, Releaser, Auditor.
- Selected agent details.
- Live task log.
- Model/provider selector.
Actions:
- Pause, resume, retry, handoff, request proof.
Safety:
- Agents cannot send printer movement/print commands without policy gate.

### 3. Workflows
Panels:
- Visual pipeline: Prompt -> 3D Gen -> Blender MCP -> Mesh QA -> 3MF -> Slicer -> Printer -> Proof.
- Active workflows.
- Failed steps with repair actions.
- Workflow templates.
Acceptance:
- Each node has status, logs, artifacts, retry budget.

### 4. 3D Generation
Panels:
- Prompt + reference image uploader.
- Provider selector: MiniMax Vision, TRELLIS, Hunyuan3D, TripoSR, custom.
- Generated model cards.
- Send to Blender MCP.
Acceptance:
- Mock output first; real providers later behind config.

### 5. Blender MCP
Panels:
- Provider manager: ahujasid default, VxAI experimental, official/custom slots.
- Blender process status.
- MCP tool capability checklist.
- Viewport screenshot panel.
- Command/safe execution history.
- 3MF export proof.
Actions:
- Connect, validate tools, run smoke test, export 3MF, rollback provider.
Safety:
- No shell/network/file-system escape in Blender Python.

### 6. Slicing
Panels:
- File queue: STL, OBJ, 3MF.
- Slicer selector: FLSUN Slicer, PrusaSlicer, OrcaSlicer, Cura.
- Profile selector per printer.
- Slice output cards.
- G-code/3MF validation results.
Actions:
- Launch external slicer docked/undocked/fullscreen.
- Dry-run slice.
- Import/export profiles.
Acceptance:
- Slice dry-run before any print start.

### 7. Printer Fleet
Panels:
- Full 12-printer table.
- Adapter status per printer: Moonraker, OctoPrint, Printrun, Manual.
- IP/port/USB details.
- Camera/web UI launch buttons.
- Maintenance flags.
Acceptance:
- No printer command buttons visible until adapter detected and safety policy loaded.

### 8. Print Queue
Panels:
- Queue by priority.
- Printer assignment suggestions.
- Job detail inspector.
- Pause/cancel/retry with confirmation.
Acceptance:
- Queue operations are simulated until printer adapter is write-enabled.

### 9. Printer Control
Panels:
- Printer selector.
- Jog controls.
- Temp controls.
- G-code console.
- Emergency stop.
Integrations:
- Printrun for USB serial/direct control.
- Moonraker for Klipper API.
- OctoPrint for legacy/API control.
Safety:
- Dangerous actions require confirmation modal + reason + proof log.
- Manual G-code requires preview and allowlist/denylist scan.

### 10. Docked Apps
Purpose: host existing external GUIs without losing Hermes3D context.
Panels:
- Fluidd dock panel.
- Mainsail dock panel.
- OctoPrint dock panel.
- Slicer GUI launcher panel.
- Blender launcher panel.
Modes:
- Docked iframe/webview if allowed.
- Undocked resizable BrowserWindow/WebView.
- Fullscreen native/external app.
Acceptance:
- If iframe denied by headers/CSP, fall back to external browser/fullscreen.

### 11. Proof & Reports
Panels:
- Proof bundles.
- Gate matrix.
- Screenshots.
- Commit/branch metadata.
- Artifact download.
Acceptance:
- Each release has signed proof bundle and evidence ledger.

### 12. System Logs
Panels:
- Unified logs.
- Filters by agent/tool/printer/severity.
- Search.
- Export.
Acceptance:
- Every external tool launch and printer command is logged.

### 13. Settings
Sections:
- AI providers.
- Blender MCP providers + versions.
- External repo registry.
- Slicers.
- Printer adapters.
- Dock/undock behavior.
- OTA/update policy.
- Safety policy.
- Theme.
Acceptance:
- Settings changes produce config diff + validation before save.
