# Hermes3D Full GUI Integration Contract Kit v4.1 — Execution Hardening

Status: **handoff-ready for Claude/Windsurf implementation**, with execution-hardening rules added on top of v4 dual-edition architecture.

This kit defines one Hermes3D system with two deployment modes:

1. **Windows Desktop GPU Worker Edition** — runs heavy compute on the user workstation, including detected NVIDIA GPUs such as EVGA FTW3 Ultra RTX 3090 Ti.
2. **Ubuntu VPS Control Server Edition** — remote cockpit that mirrors the same UI and routes GPU/modeling/slicing jobs back to the Windows worker through a secure tunnel.

## v4.1 hardening additions

- Real external repo registry fields required before implementation.
- Executable registry validator instead of pseudocode only.
- Claude task files per phase.
- Windows + Ubuntu verification matrix.
- Security policy for remote GPU worker and printer control.
- Dock/undock/fullscreen acceptance gates.
- Tool install verification commands.
- Definition-of-done checklist for every tab and integration.
- Final no-merge/no-release rules.

## Non-negotiable rule

Do **not** merge UI-Final, remote-control, GPU-worker routing, slicer write operations, or printer write-control until the relevant proof gates are GREEN.
