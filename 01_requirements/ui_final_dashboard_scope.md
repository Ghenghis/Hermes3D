# UI-Final Dashboard — Scope of Work

**Status:** Active (parallel track)
**Branch:** `feat/ui-final-dashboard`
**Visual contract:** [`06_release/UI_FINAL_VISUAL_CONTRACT.png`](../06_release/UI_FINAL_VISUAL_CONTRACT.png)
**ADR:** [`02_architecture/adr/ADR-ui-final-dashboard.md`](../02_architecture/adr/ADR-ui-final-dashboard.md)

## Goal

Replace the stabilization-phase Gradio launcher with a real fleet-management dashboard that matches `UI_FINAL_VISUAL_CONTRACT.png` 1:1.

## Stack

- **Frontend:** React + Tailwind CSS
- **Theme:** Dark-first only. No white UI surfaces anywhere.
- **Build:** Vite (assumed; final tooling decision part of phase 1).
- **Testing:** Playwright with screenshot capture against the visual contract.
- **Target viewport:** 1920×1080 primary; layout must not break down to 1366×768.

## Components (reusable, in `feat/ui-final-dashboard`)

1. **Sidebar** — Hermes3D logo + version chip; nav: Dashboard / Agents / Workflows / 3D Generation / Blender MCP / Slicing / Printer Fleet / Print Queue / Files & Projects / Proof & Reports / System Logs / Settings. Quick Actions block at bottom (New Project, Generate 3D, Upload File, Slice & Prepare, Print Now).
2. **Header** — title "AI-DRIVEN 3D PRINTING OS"; subtitle "Design. Verify. Slice. Print. Monitor. Repeat."; right-side: System Status pill, clock, notifications bell, settings cog, avatar.
3. **StatCard** — Total Printers, Active Prints, Queued Prints, Success Rate, System Health. Each has primary number, sublabel, and a small sparkline area.
4. **PrinterFleetTable** — # / Printer / IP / Status / Current Job / Progress. 12 rows, color-coded status badges (Printing / Idle / Offline). Progress bars with percentage.
5. **WorkflowPipeline** — Six-stage horizontal pipeline (Prompt → 3D Generation → Blender MCP → Validation → Slicing → Print) with per-stage state (complete / in progress / pending) and connecting arrows.
6. **CurrentProjectPanel** — Project title, timestamped activity log, in-progress badge, 3D preview thumbnail, "View Details" button.
7. **AgentStatusPanel** — Agent name, role icon, Running/Standby badge. Agents: Planner, Blender, QA, Slicer, Printer, Recovery, Auditor, Reviewer.
8. **ActivityLog** — Live agent activity stream (timestamp + agent + line of output).
9. **ResourcePanel** — CPU / RAM / Disk gauges (donut/half-circle); Network up/down with sparkline.
10. **RecentJobsPanel** — Last 8 jobs: name, printer, progress %, "Done" badges where applicable.
11. **ProofPanel** — Last verification timestamp + VERIFIED badge + bundle path + "View Report" button.
12. **NotificationsPanel** — Last 4 notifications (info / warning / success), age in minutes, Clear All.

## Mock data (phase 1, hardcoded)

Printer fleet (12 entries — IPs from the user's known live fleet where applicable):

| # | Printer            | IP            | Status   |
|---|--------------------|---------------|----------|
| 1 | FLSUN QQ-S Pro     | 192.168.0.10  | Printing |
| 2 | FLSUN T1           | 192.168.0.11  | Printing |
| 3 | FLSUN T1           | 192.168.0.12  | Printing |
| 4 | FLSUN Super Racer  | 192.168.0.13  | Idle     |
| 5 | Creality CR-10S    | 192.168.0.14  | Idle     |
| 6 | FLSUN S1           | 192.168.0.15  | Printing |
| 7 | FLSUN V400         | 192.168.0.16  | Idle     |
| 8 | Tronxy D01 Pro     | 192.168.0.17  | Offline  |
| 9 | Tronxy X5SA Pro    | 192.168.0.18  | Idle     |
| 10| Creality CR-6 Max  | 192.168.0.19  | Printing |
| 11| Prusa MK3S         | 192.168.0.20  | Idle     |
| 12| Sovol SV-01        | 192.168.0.21  | Idle     |

Note: 192.168.0.10/.11/.12/.34 are the *real* live fleet IPs per project memory. The other entries are mock placeholders for the static phase; backend wiring (later phase) reconciles with `03_implementation/config/printers.user.toml`.

## Acceptance gates (UI-Final layer, NOT rc1 layer)

A separate Playwright gate (Layer D-UI-Final) is added on `feat/ui-final-dashboard` only. It must pass before any merge to develop:

- App launches at 1920×1080 with no console errors.
- All 12 printers render with correct fleet data.
- All 11 reusable components are present and visible.
- Layout does not break at 1366×768.
- Playwright captures `test-results/visual/ui-final-dashboard.png`.
- Manual + automated comparison against `UI_FINAL_VISUAL_CONTRACT.png` is "visually close" (subjective sign-off by the project owner).
- The captured screenshot is bundled into the proof envelope.

## Implementation phases (on the branch only)

1. **Phase 1 — Static frontend.** Scaffold React + Tailwind + Vite under `03_implementation/ui-final/` (or similar; final path TBD). Hardcode the 12-row fleet, sample agent activity, sample workflow stages, sample notifications.
2. **Phase 2 — Visual iteration.** Run Playwright screenshot test, compare against the visual contract, iterate until close.
3. **Phase 3 — Backend wiring.** Connect the real Hermes3D FastAPI surface (already running on :8765 via `hermes3d.api.server:app`). Replace mocks with live data. Add the new gate to CI.
4. **Phase 4 — Cutover.** Once Layer D-UI-Final is GREEN AND v5.3.0-rc1 is tagged on `main`, merge `feat/ui-final-dashboard` → develop and remove the Gradio launcher.

## Constraints (from project rules)

- **Dark-first only.** No white UI surfaces.
- **Stable selectors.** All interactive components must expose `data-testid` (or stable React component IDs) for Playwright. No coupling to Tailwind class names or framework-internal DOM in test selectors.
- **No partial merges.** UI-Final does not land in pieces; the swap is atomic, gated on the screenshot test + manual sign-off.
- **No backend changes for UI-Final until phase 3.** Phase 1 + 2 are pure frontend.
- **Memory-locked rule:** "stabilize first, beautify in parallel, merge later." No exceptions until rc1 is out the door.
