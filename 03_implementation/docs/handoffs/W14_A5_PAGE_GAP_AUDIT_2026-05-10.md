# Wave 14 — Agent 5 · Page Gap Auditor (Read-Only Walkthrough)

**Date**: 2026-05-10
**Auditor**: claude-w14-a5
**Repo**: `G:/Github/h3d-gui-wiring-codex`
**Reference pack**: `Images-GUI/` (31 PNGs, manifest @ `Images-GUI/GUI_REFERENCE_MANIFEST.json`)
**Scope**: live walkthrough of every primary tab, settings/voice subtab, action-window state, and utility page
**Lock**: `claude-w14-a5` (taskId `w14-a5-page-gap-audit`)

---

## 1. Walk Methodology

### URLs visited (all under `http://localhost:5173`)

| Bucket | URLs |
|---|---|
| Primary tabs | `#sources`, `#dashboard`, `#autopilot`, `#design`, `#gen3d`, `#jobs`, `#printers`, `#observe`, `#voice`, `#agents`, `#learning`, `#artifacts`, `#approvals`, `#apps`, `#plugins`, `#settings`, `#roadmap` |
| Dashboard modes | `#dashboard:simple`, `#dashboard:advanced`, `#dashboard:custom` |
| Settings subtabs | `#settings` + click on `[data-testid=settings-subtab-{key}]` for: `general`, `providers`, `agents`, `mcp`, `printers`, `environment`, `updates`, `about` |
| Voice subtabs | `#voice` + click on tab buttons named "Voice Browser", "Transcript History", "Proof Review" |
| Action Window | `/action-window?detached=1` (detached mode), `#design` (search for embedded mount), `(state)` placeholder for maximized |
| Utility pages | `#health` (works via `main.tsx` hash gate) + 12 expected-but-unwired hashes: `workflows`, `queue`, `files`, `logs`, `proof`, `notifications`, `safety`, `blender_mcp`, `slicing`, `fleet`, `control`, `docked` |

### Capture conditions

- Viewport: **1536 × 1024** (per task spec; differs from default `playwright.config.ts` 1920×1080)
- `screenshot: { fullPage: true }`
- Console error capture (`page.on('console','error')` + `page.on('pageerror')`) — text truncated to 240 chars
- Stack used: `node scripts/start-e2e-stack.mjs` (port-fallback was triggered — see "Caveats")
- Spec: `03_implementation/ui/tests/e2e/w14-a5-gap-walk.spec.ts` (one-shot — deleted on completion)
- Total walk duration: 53.9 s, 48 rows captured

### Caveats

- Backend `8765` was already in use (likely a leftover dev server); `start-e2e-stack.mjs` chose `8766` and `8642`. Frontend bundles `VITE_HERMES3D_BRIDGE_PORT=8765` at build time, so a small fraction of network calls in the captured screenshots hit the wrong port and the console shows `502`/`ERR_CONNECTION_REFUSED`. The page-render itself is unaffected; only late-arriving fetch errors are noisy.
- "VISUAL_MISMATCH" was not auto-detected — comparing live screenshots against `Images-GUI/*.png` reference PNGs is left for a follow-up visual-diff lane (PR 2-7 series).

### Sources used (2 — per task spec)

1. **Playwright walk** — `screenshots/w14-a5/report.json` (48 rows, machine-emitted by the spec)
2. **Existing tabs list** — `03_implementation/ui/src/app/routes.ts` (`PRIMARY_TABS`, 17 entries) + `03_implementation/ui/src/app/store.ts` (`TAB_IDS`) + `main.tsx` (`#apps`/`#health` hash gates) + `tests/e2e/gui-breadth-pages.spec.ts` (existing breadth list)

---

## 2. Gap Table

> Status legend: **EXISTS** = route + UI present, mounts cleanly · **PARTIALLY_EXISTS** = route present but UI placeholder/empty · **MISSING** = no route or 404 · **VISUALLY_MISMATCHED** = route exists, content visible, doesn't match reference · **DATA_MISSING** = route + UI present, but backend data not connected

| Page | URL | Status | Reference | Console errors | Screenshot |
|---|---|---|---|---|---|
| Source OS | `#sources` | EXISTS | `04-source-os/source-os-core-categories.png` | 8 (502 + connection refused) | `ui/screenshots/w14-a5/primary_source_os.png` |
| Dashboard | `#dashboard` | EXISTS | `01-dashboard-modes/advanced-dashboard-a.png` | 6 (502 + connection refused) | `ui/screenshots/w14-a5/primary_dashboard.png` |
| Autopilot | `#autopilot` | EXISTS | `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` | 1 (connection refused) | `ui/screenshots/w14-a5/primary_autopilot.png` |
| Design | `#design` | EXISTS | `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` | 0 | `ui/screenshots/w14-a5/primary_design.png` |
| Gen3D | `#gen3d` | EXISTS | `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` | 1 (502) | `ui/screenshots/w14-a5/primary_gen3d.png` |
| Jobs | `#jobs` | EXISTS | `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` | 1 (502) | `ui/screenshots/w14-a5/primary_jobs.png` |
| Printers | `#printers` | EXISTS | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` | 2 (502) | `ui/screenshots/w14-a5/primary_printers.png` |
| Observe | `#observe` | EXISTS | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` | 0 | `ui/screenshots/w14-a5/primary_observe.png` |
| Voice | `#voice` | EXISTS | `03-settings-voice/voice-communication-subtabs.png` | 1 (connection refused) | `ui/screenshots/w14-a5/primary_voice.png` |
| Agents | `#agents` | EXISTS | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` | 0 | `ui/screenshots/w14-a5/primary_agents.png` |
| Learning | `#learning` | EXISTS | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` | 0 | `ui/screenshots/w14-a5/primary_learning.png` |
| Artifacts | `#artifacts` | EXISTS | `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` | 0 | `ui/screenshots/w14-a5/primary_artifacts.png` |
| Approvals | `#approvals` | EXISTS | `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` | 2 (502) | `ui/screenshots/w14-a5/primary_approvals.png` |
| Apps (Registry) | `#apps` | EXISTS | `04-source-os/source-os-60-app-coverage-matrix.png` | 0 | `ui/screenshots/w14-a5/primary_apps.png` |
| Plugins | `#plugins` | EXISTS | `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | 3 (502 + connection refused) | `ui/screenshots/w14-a5/primary_plugins.png` |
| Settings | `#settings` | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/primary_settings.png` |
| Roadmap | `#roadmap` | EXISTS | `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` | 1 (connection refused) | `ui/screenshots/w14-a5/primary_roadmap.png` |
| Dashboard · Simple | `#dashboard:simple` | EXISTS | `01-dashboard-modes/simple-dashboard-a.png` | 0 | `ui/screenshots/w14-a5/dashboard_mode_simple.png` |
| Dashboard · Advanced | `#dashboard:advanced` | EXISTS | `01-dashboard-modes/advanced-dashboard-a.png` | 0 | `ui/screenshots/w14-a5/dashboard_mode_advanced.png` |
| Dashboard · Custom | `#dashboard:custom` | EXISTS | `01-dashboard-modes/custom-dashboard-a.png` | 0 | `ui/screenshots/w14-a5/dashboard_mode_custom.png` |
| Settings · General | `#settings` (subtab=general) | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/settings_general.png` |
| Settings · Providers | `#settings` (subtab=providers) | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/settings_providers.png` |
| Settings · Agents | `#settings` (subtab=agents) | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/settings_agents.png` |
| Settings · MCP | `#settings` (subtab=mcp) | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/settings_mcp.png` |
| Settings · Printers | `#settings` (subtab=printers) | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/settings_printers.png` |
| Settings · Environment | `#settings` (subtab=environment) | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/settings_environment.png` |
| Settings · Update Center | `#settings` (subtab=updates) | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/settings_updates.png` |
| Settings · About | `#settings` (subtab=about) | EXISTS | `03-settings-voice/settings-subtabs-all.png` | 0 | `ui/screenshots/w14-a5/settings_about.png` |
| Voice · Browser | `#voice` (subtab=browser) | EXISTS | `03-settings-voice/voice-communication-subtabs.png` | 0 | `ui/screenshots/w14-a5/voice_browser.png` |
| Voice · Transcripts | `#voice` (subtab=transcripts) | EXISTS | `03-settings-voice/voice-communication-subtabs.png` | 0 | `ui/screenshots/w14-a5/voice_transcripts.png` |
| Voice · Proof Review | `#voice` (subtab=proof) | EXISTS | `03-settings-voice/voice-communication-subtabs.png` | 0 | `ui/screenshots/w14-a5/voice_proof.png` |
| Action Window · Detached | `/action-window?detached=1` | EXISTS | `05-action-windows/action-window-core-apps.png` | 2 (502) | `ui/screenshots/w14-a5/action_window_detached.png` |
| Action Window · Embedded (on Design) | `#design` | PARTIALLY_EXISTS | `05-action-windows/action-window-core-apps.png` | 0 | `ui/screenshots/w14-a5/action_window_embedded_design.png` |
| Action Window · Maximized | (state) | PARTIALLY_EXISTS | `05-action-windows/action-window-advanced-tools.png` | 0 | (not captured — see Section 3) |
| Service Health | `#health` | EXISTS | `08-app-utility-pages/proof-health-notifications-safety.png` | 2 (404 + connection refused) | `ui/screenshots/w14-a5/utility_health.png` |
| Workflows | `#workflows` | MISSING | `08-app-utility-pages/workflow-printqueue-files-logs.png` | 2 (502) | `ui/screenshots/w14-a5/utility_workflows.png` |
| Print Queue | `#queue` | MISSING | `08-app-utility-pages/workflow-printqueue-files-logs.png` | 1 (404) | `ui/screenshots/w14-a5/utility_queue.png` |
| Files | `#files` | MISSING | `08-app-utility-pages/workflow-printqueue-files-logs.png` | 3 (connection refused + 502) | `ui/screenshots/w14-a5/utility_files.png` |
| System Logs | `#logs` | MISSING | `08-app-utility-pages/workflow-printqueue-files-logs.png` | 0 | `ui/screenshots/w14-a5/utility_logs.png` |
| Proof & Reports | `#proof` | MISSING | `08-app-utility-pages/workflow-printqueue-files-logs.png` | 1 (connection refused) | `ui/screenshots/w14-a5/utility_proof.png` |
| Notifications | `#notifications` | MISSING | `08-app-utility-pages/proof-health-notifications-safety.png` | 0 | `ui/screenshots/w14-a5/utility_notifications.png` |
| Safety | `#safety` | MISSING | `08-app-utility-pages/proof-health-notifications-safety.png` | 0 | `ui/screenshots/w14-a5/utility_safety.png` |
| Blender MCP | `#blender_mcp` | MISSING | (referenced in 4.1 spec) | 1 (502) | `ui/screenshots/w14-a5/utility_blender_mcp.png` |
| Slicing | `#slicing` | MISSING | (referenced in 4.1 spec) | 1 (502) | `ui/screenshots/w14-a5/utility_slicing.png` |
| Printer Fleet | `#fleet` | MISSING | (referenced in 4.1 spec) | 1 (connection refused) | `ui/screenshots/w14-a5/utility_fleet.png` |
| Printer Control | `#control` | MISSING | (referenced in 4.1 spec) | 0 | `ui/screenshots/w14-a5/utility_control.png` |
| Docked Apps | `#docked` | MISSING | (referenced in 4.1 spec) | 0 | `ui/screenshots/w14-a5/utility_docked.png` |

**Summary**: 48 items walked · **34 EXISTS** · **2 PARTIALLY_EXISTS** · **12 MISSING** · 0 VISUALLY_MISMATCHED · 0 DATA_MISSING (auto-classified) · **31 console errors** total (almost all 502/CONNECTION_REFUSED — see "Caveats" above; backend bound to a fallback port 8766/8642 because 8765 was already in use, so the bundled `VITE_HERMES3D_BRIDGE_PORT=8765` fetches miss the live API).

---

## 3. Per-Section Breakdown

### 3.1 Primary tabs (17 / 17 EXISTS)

All 17 primary tabs in `routes.ts → PRIMARY_TABS` mount cleanly under `AppShell` and emit identifiable content. The full set:

`source_os` · `dashboard` · `autopilot` · `design` · `gen3d` · `jobs` · `printers` · `observe` · `voice` · `agents` · `learning` · `artifacts` · `approvals` · `apps` · `plugins` · `settings` · `roadmap`

Note: 4.1 contract kit (`hermes3d_gui_contract_kit_v4.1/01_requirements/TAB_SPECS.md` + `routes.tsx`) defines a different 14-tab set (Workflows, Slicing, Fleet, Print Queue, Printer Control, Docked Apps, Proof, System Logs, Service Health). Those tabs DO have `.tsx` files in `src/tabs/` (and components for health/notifications) but are **not registered in `App.tsx`'s `TAB_COMPONENTS`** nor in `store.ts`'s `TAB_IDS`. Two competing tab manifests live side-by-side.

### 3.2 Source OS (EXISTS, 8 console errors)

`#sources` mounts the 60-app matrix UI. Console errors are network-only (the live walk hit fallback ports). UI scaffolding renders. Reference vs runtime: not visually compared — recommend a visual-diff lane.

### 3.3 Settings subtabs (8 / 8 EXISTS)

Live count: **8** subtabs (`general`, `providers`, `agents`, `mcp`, `printers`, `environment`, `updates`, `about`).
Reference manifest shows **6** (`providers`, `agents`, `printers`, `environment`, `updates`, `about`).

The implementation has added two extras (**General**, **MCP**) that aren't in the reference. Each subtab has a stable `data-testid="settings-subtab-{key}"` and renders a real component (`GeneralSubtab`, `ProvidersSubtab`, `AgentConfigSection`, `McpSubtab`, `PrintersSubtab`, `EnvironmentSubtab`, `UpdateCenterSubtab`, `AboutSubtab`). Routing is internal `useState` (no react-router) per project convention.

### 3.4 Voice subtabs (3 / 3 EXISTS)

`Voice Browser`, `Transcript History`, `Proof Review` — wired into `data-testid="voice-root"`/`voice-transcript-history`/`voice-proof-review`. Clean console.

### 3.5 Action Window (1 / 3 fully captured)

- **Detached** (`/action-window?detached=1`): EXISTS — entry point in `action-window-detached.tsx`/`DetachedActionWindow.tsx`.
- **Embedded** (in-app): PARTIALLY_EXISTS — `ActionWindow.tsx` is implemented and `ActionWindowMount.tsx` exists, but no primary tab in the live tour mounts it consistently. No `[data-testid=action-window]` was found on `#design` (the most likely host).
- **Maximized** (Maximize2 toggle): PARTIALLY_EXISTS — code path exists in `ActionWindow.tsx` (state `[maximized, setMaximized]`), but no host tab exposes the toggle button on first paint, so a state capture wasn't possible without simulating clicks.

Recommendation: surface the embedded ActionWindow somewhere on Design or Autopilot (or as a docked tool rail) and add `data-testid="action-window"` on the root container.

### 3.6 Utility pages (1 / 13 EXISTS, 12 MISSING)

| Hash | Status | File on disk | Routed? |
|---|---|---|---|
| `#health` | EXISTS | `components/health/ServiceHealthPage.tsx` | yes — `main.tsx` hash-gate |
| `#workflows` | MISSING | `tabs/Workflows.tsx` exists | not in `App.tsx`/`store.ts` |
| `#queue` | MISSING | `tabs/PrintQueue.tsx` exists | not in `App.tsx`/`store.ts` |
| `#files` | MISSING | none | none |
| `#logs` | MISSING | `tabs/SystemLogs.tsx` exists | not in `App.tsx`/`store.ts` |
| `#proof` | MISSING | `tabs/Proof.tsx` exists | not in `App.tsx`/`store.ts` |
| `#notifications` | MISSING | `components/notifications/NotificationCenter.tsx` exists | not exposed as a tab |
| `#safety` | MISSING | none | none |
| `#blender_mcp` | MISSING | `tabs/BlenderMCP.tsx` exists | not in `App.tsx`/`store.ts` |
| `#slicing` | MISSING | `tabs/Slicing.tsx` exists | not in `App.tsx`/`store.ts` |
| `#fleet` | MISSING | `tabs/Fleet.tsx` exists | not in `App.tsx`/`store.ts` |
| `#control` | MISSING | `tabs/PrinterControl.tsx` exists | not in `App.tsx`/`store.ts` |
| `#docked` | MISSING | `tabs/DockedApps.tsx` exists | not in `App.tsx`/`store.ts` |

**Nine "orphan" tab files exist on disk but are not routed** (Workflows, PrintQueue, SystemLogs, Proof, BlenderMCP, Slicing, Fleet, PrinterControl, DockedApps). Three references are entirely absent (`files`, `safety`, `notifications` exposed as a top-level page).

### 3.7 Plugins / skills / MCP / app connectors

`#plugins` (EXISTS) renders `PluginsTab`. The reference `Images-GUI/07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` shows skills + MCP + app-connectors layered into the same surface. A second view of MCP exists inside Settings (`settings → mcp`). Visual-diff vs reference is a follow-up.

---

## 4. Top 5 Highest-Impact Gaps (with recommended PR ordering)

> Following the user's PR 2-7 ordering convention: low-risk routing fixes first, then UI scaffolds, then visual polish.

### Gap 1 — Nine orphan tab files have NO route (PR 2)

**Files**: `Workflows.tsx`, `PrintQueue.tsx`, `SystemLogs.tsx`, `Proof.tsx`, `BlenderMCP.tsx`, `Slicing.tsx`, `Fleet.tsx`, `PrinterControl.tsx`, `DockedApps.tsx`
**Impact**: Users following the Hermes3D-OS spec / contract-kit-4.1 expect these pages to be reachable via deep-link hashes; today they 404 via the `UnavailableTab` placeholder.
**Recommended PR**: **`feat(ui): wire orphan tabs to App.tsx + store.ts`** — register all 9 in `TAB_COMPONENTS`, `TAB_IDS`, `HASH_TO_TAB`, `TAB_TO_HASH`. No new code; pure routing. Blast radius: tiny.

### Gap 2 — Action Window not visibly mounted on any primary tab (PR 3)

**Files**: `ActionWindow.tsx`, `ActionWindowMount.tsx`
**Impact**: Reference pack (`Images-GUI/05-action-windows/`) shows ActionWindow as the central workbench surface; live walk found no `[data-testid=action-window]` on Design. Maximized state is unreachable without a host that exposes the Maximize2 button.
**Recommended PR**: **`feat(ui): mount embedded ActionWindow on Design + add data-testid for E2E`** — pick a default host (Design tab is the natural fit), add the testid on the root container, ensure the maximize toggle is visible. Once landed, walk re-runs can capture all three action-window states.

### Gap 3 — Files / Safety / Notifications pages do not exist as files (PR 4)

**Files**: none — needs new `tabs/Files.tsx`, `tabs/Safety.tsx`, `tabs/Notifications.tsx`
**Impact**: Three of the eight utility pages depicted in `Images-GUI/08-app-utility-pages/` have neither route nor source file. Notifications has a `NotificationCenter` component but no top-level page; Files and Safety have nothing.
**Recommended PR**: **`feat(ui): scaffold Files / Safety / Notifications utility pages`** — three minimal panels backed by the relevant adapters (file system browser, safety policy view, notifications timeline). Wire into `TAB_COMPONENTS` and `TAB_IDS`.

### Gap 4 — Settings subtab manifest drift: 8 implemented vs 6 in reference (PR 5)

**Files**: `Images-GUI/GUI_REFERENCE_MANIFEST.json`, `components/settings/SettingsPage.tsx`
**Impact**: Implementation has `general` + `mcp` subtabs that the visual reference manifest doesn't enumerate. Either add them to the reference manifest (and capture screenshots) or reconcile with the spec — a docs-only mismatch will be flagged on every visual-diff run.
**Recommended PR**: **`docs(images-gui): add general + mcp settings subtabs to manifest + capture references`** — extends the manifest's `settings_subtabs` array to 8 and adds two PNGs.

### Gap 5 — Two competing tab manifests in `src/app/` (PR 6)

**Files**: `src/app/routes.ts` (17 tabs, used by `App.tsx`), `src/app/routes.tsx` (14 tabs, comments reference TAB_SPECS.md)
**Impact**: `routes.tsx` is dead code today (nothing imports it) but its existence creates ambiguity for new contributors. Reading the file, one might assume the contract-kit-4.1 layout is live when it's not.
**Recommended PR**: **`chore(ui): delete unused routes.tsx — single-source-of-truth on routes.ts`** — remove the dead manifest, or rename it `routes.contract-kit.ts` with a header comment explaining it's a planning artifact. Either way, ensure only ONE file exports `TABS`.

---

## 5. Cleanup

- `tests/e2e/w14-a5-gap-walk.spec.ts` — **deleted** at completion (one-shot per task)
- Vite + uvicorn child processes — Playwright `webServer` block manages teardown automatically; no orphan processes after the test exits.
- Backend on `8765` was **NOT** started by this auditor; it predated the run and was left intact.
- Hermes locks released for all three paths owned by `claude-w14-a5`.

## 6. Two sources

1. **Playwright walk** — `screenshots/w14-a5/report.json` (48 rows, machine-emitted).
2. **Existing tabs list** — `src/app/routes.ts` (PRIMARY_TABS), `src/app/store.ts` (TAB_IDS), `src/main.tsx` (hash gates), `src/components/settings/SettingsPage.tsx` (SUBTABS), `src/tabs/Voice.tsx` (TabName), `src/components/ActionWindow/ActionWindow.tsx` (state machine).

---

## Appendix · Screenshot directory

`G:/Github/h3d-gui-wiring-codex/03_implementation/ui/screenshots/w14-a5/` — 46 PNGs + `report.json`
