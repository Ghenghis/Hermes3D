# Dock / Undock Playwright Spec

Test flow: open Hermes3D, navigate to Integrations, open each tool in docked mode, screenshot, click undock, confirm state, screenshot, click fullscreen/external, confirm launch or graceful unsupported message, verify no console errors.

Hard fail: blank panel, console error, broken layout, crash after close, unsupported without explanation.
