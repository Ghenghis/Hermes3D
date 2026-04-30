# ADR-001 — UI-Final Dashboard

**Status:** Accepted (2026-04-30)
**Decision drivers:** the user (project owner)
**Supersedes:** none
**Related:** [`01_requirements/ui_final_dashboard_scope.md`](../../01_requirements/ui_final_dashboard_scope.md), [`06_release/UI_FINAL_VISUAL_CONTRACT.png`](../../06_release/UI_FINAL_VISUAL_CONTRACT.png)

## Context

The kit's stabilization-phase UI is the existing Gradio launcher (`hermes3d.app.launcher`). It has a deliberately minimal four-tab layout (Truth Gate Validator, Generate Desk Organizer, Pipeline Dry-Run, Disabled Full Autonomous Pipeline) used purely to verify reachability and core action wiring during stabilization. It is not the long-term operator surface.

The long-term operator surface is a real fleet-management dashboard:

- 12-printer live fleet view (status, IPs, current job, progress)
- Multi-stage AI workflow pipeline visualization
- Live agent activity stream
- Proof-bundle viewer
- System resource panel
- Recent jobs + notifications
- Dark-first interface

The visual contract for this dashboard is locked at `06_release/UI_FINAL_VISUAL_CONTRACT.png`. That image is authoritative — the implementation must match it 1:1.

## Decision

**Build UI-Final on a parallel track, not on `develop`, until v5.3.0-rc1 has been cut from a fully-stabilized develop.**

Concretely:

1. **Stabilization continues unchanged on `develop`.** The current Gradio launcher remains the only UI on `develop` until rc1.
2. **UI-Final is implemented on `feat/ui-final-dashboard`** — a long-lived feature branch that does not merge until rc1 is tagged AND its own UI-Final E2E gate is GREEN.
3. **Stack:** React + Tailwind, dark-first only. Reusable components: Sidebar, Header, StatCard, PrinterFleetTable, WorkflowPipeline, AgentStatusPanel, ActivityLog, ProofPanel, ResourcePanel, RecentJobsPanel, NotificationsPanel.
4. **Implementation order:**
   1. Static frontend with hardcoded sample data matching the 12-printer fleet.
   2. Playwright screenshot test against the visual contract.
   3. Iterate UI until the Playwright capture is visually close to the contract.
   4. Only then wire real Hermes3D backend data.
5. **No Gradio replacement on develop until UI-Final has its own Playwright gate (Layer D-2 or equivalent) GREEN.** The Gradio launcher continues to satisfy the existing minimum UI gate (Layer D) on `develop` indefinitely until that swap.
6. **The screenshot is the visual contract.** Any deviation requires a contract update (commit a new `UI_FINAL_VISUAL_CONTRACT.png` with rationale) before implementation drifts.

## Consequences

**Positive:**
- rc1 stabilization is not disrupted by a major UI rebuild.
- The visual spec is captured and version-controlled now, so it cannot drift while we focus on backend stability.
- UI-Final can iterate freely without affecting release-quality gates.
- When UI-Final lands, it lands as a complete, gated swap — not a half-finished migration.

**Negative:**
- Two UI codebases coexist for the duration of UI-Final development (Gradio on develop, React on feat/ui-final-dashboard). Drift risk on the API contract that both consume.
- Long-lived feature branch will accumulate merge debt against develop. Mitigation: rebase onto develop weekly.

**Neutral:**
- This ADR formalizes the user's "stabilize first, beautify last" rule, codified in project memory on 2026-04-30.

## Alternatives considered

- **Pivot now**: pause stabilization, build UI-Final on develop. Rejected — pushes rc1 indefinitely and risks polishing on a moving backend.
- **Incremental swap**: replace one Gradio tab at a time with React. Rejected — produces a worst-of-both-worlds intermediate state and inflates Layer D test scope.
- **Defer the visual contract**: capture the screenshot later. Rejected — the screenshot is concrete now and capturing it locks the spec before scope creep happens.

## Validation

UI-Final is "done" when:
- Playwright screenshot test produces an image visually equivalent to `UI_FINAL_VISUAL_CONTRACT.png` (manual + automated comparison).
- All 11 reusable components render with no broken layout at 1920×1080.
- No console errors on boot.
- All 12 printers from the fleet render with correct IPs, statuses, and progress.
- Dark theme only — no light-mode artifacts anywhere.
- Screenshot artifact is bundled into the proof envelope.
- Backend wiring connects to the real Hermes3D FastAPI surface (post-static phase).
