# Dock / Undock Requirements

## Goal
Hermes3D must act like a cockpit. External tools can be docked into panels when safe, undocked into resizable windows, or launched fullscreen as native apps.

## Supported modes
1. Docked panel
   - Web apps: iframe/webview when allowed.
   - Native apps: status/preview dock only, launch button for full app.
2. Undocked resizable window
   - Separate Electron/Tauri/browser window, stays linked to Hermes3D state.
3. Fullscreen external app
   - Native Blender/slicer/Pronterface launches normally.

## Tool behavior
- Fluidd/Mainsail/OctoPrint: try docked web panel; fallback to external browser if blocked.
- Blender: native app fullscreen/external; Hermes3D shows status, screenshots, command log.
- FLSUN/Prusa/Orca/Cura slicers: native app; Hermes3D shows profile/job/file state.
- Printrun/Pronterface: native app or embedded console adapter; write commands require confirmation.

## Acceptance gates
- Every panel can undock and re-dock without losing state.
- Closing undocked window does not kill backend adapter unless user confirms.
- If app cannot dock, UI shows clear reason and fallback.
