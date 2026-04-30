# ADR-002: Docked, Undocked, and Fullscreen Tool Modes

## Decision
Every tool panel must support at least one of these modes: docked panel, undocked resizable window, fullscreen external launch.

## Rationale
Some tools are web apps that can dock; others are native apps better launched fullscreen. Hermes3D must not force one interaction model.

## Fallbacks
- If web iframe/webview is blocked, open external browser.
- If native app is not installed, show install/detect instructions.
- If source repo exists but no binary exists, do not pretend the tool is ready.
