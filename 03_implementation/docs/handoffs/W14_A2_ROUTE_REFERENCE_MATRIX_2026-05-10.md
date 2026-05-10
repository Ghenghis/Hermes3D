# W14-A2 — Route / Feature Reference Matrix

- Wave: 14
- Agent: 2 (Route / Feature Mapper)
- Date: 2026-05-10
- Mode: READ-ONLY (no code changes)
- Repo: `G:/Github/h3d-gui-wiring-codex`
- Reference pack: `Images-GUI/` (31 PNGs per `GUI_REFERENCE_MANIFEST.json`)

## Sources used

1. **React Router patterns** — hash-routing convention used by the project
   (`#<tab>[:mode]` / `#<tab>/<id>`), reflected in
   `03_implementation/ui/src/app/store.ts` (`HASH_TO_TAB` /
   `TAB_TO_HASH` / `tabIdFromHash`),
   `03_implementation/ui/src/main.tsx` (gates `#apps[/<id>]` and
   `#health` to standalone surfaces) and
   `03_implementation/ui/src/components/dashboard/dashboardModeStore.ts`
   (`#dashboard:<simple|advanced|custom>`).
2. **Project's existing tab list** — `TABS` in
   `03_implementation/ui/src/app/routes.ts` (17 entries). NB: a stale
   alternate `routes.tsx` still ships a 14-entry pre-W6 list and is **not**
   consumed by `App.tsx`; the live router is `routes.ts`. The 17-tab list
   is mirrored by `TAB_IDS` in `store.ts` and the `TAB_COMPONENTS` table
   in `App.tsx`.

## 1. Current app route inventory

Hash routes are flat (one tab id per hash) with optional `:mode` (dashboard)
or `/<id>` (apps registry detail) suffixes. Source: `routes.ts` /
`store.ts` / `main.tsx`.

| # | Hash | Tab id | Component (tabs/) |
|---|---|---|---|
| 1 | `#sources` (alias `#source_os`, `#source`) | `source_os` | `SourceOS.tsx` |
| 2 | `#dashboard` (`:simple`/`:advanced`/`:custom`) | `dashboard` | `Dashboard.tsx` (full-mode dispatches to `components/dashboard/Dashboard{Simple,Advanced,Custom}.tsx`) |
| 3 | `#autopilot` | `autopilot` | `Autopilot.tsx` |
| 4 | `#design` | `design` | `Design.tsx` |
| 5 | `#gen3d` (alias `#3d-generation`) | `gen3d` | `Gen3D.tsx` |
| 6 | `#jobs` | `jobs` | `Jobs.tsx` |
| 7 | `#printers` | `printers` | `Printers.tsx` |
| 8 | `#observe` | `observe` | `Observe.tsx` |
| 9 | `#voice` | `voice` | `Voice.tsx` (internal `browser`/`transcripts`/`proof` subtab state) |
| 10 | `#agents` | `agents` | `Agents.tsx` |
| 11 | `#learning` | `learning` | `Learning.tsx` |
| 12 | `#artifacts` | `artifacts` | `Artifacts.tsx` |
| 13 | `#approvals` | `approvals` | `Approvals.tsx` |
| 14 | `#apps[/<id>]` | `apps` | `AppRegistry.tsx` (also reachable as a standalone shim from `main.tsx`) |
| 15 | `#plugins` | `plugins` | `Plugins.tsx` |
| 16 | `#settings` | `settings` | `Settings.tsx` → `components/settings/SettingsPage.tsx` (subtabs: `general`, `providers`, `agents`, `mcp`, `printers`, `environment`, `updates`, `about`) |
| 17 | `#roadmap` | `roadmap` | `Roadmap.tsx` |
| 18 (shim) | `#health` | — (gated in `main.tsx`, no AppShell tab yet) | `components/health/ServiceHealthPage.tsx` |

**Total live hash routes: 17 tab routes + 1 shim (`#health`) = 18.**
A second pre-W6 router (`routes.tsx`, 14 tabs incl. `service_health`,
`workflows`, `slicing`, `fleet`, `queue`, `control`, `docked`, `proof`,
`logs`) exists but is unreferenced by `App.tsx`/`AppShell.tsx` and ships
no hash mapping.

## 2. Backend route inventory

Source: `python -c "from hermes3d.api.app import create_gui_app; ..."`
in `G:/Github/h3d-gui-wiring-codex` with
`PYTHONPATH=03_implementation/src`.

**Total handler paths: 213** (incl. 4 framework routes:
`/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`).
Application-owned: **209**. Top-level groups (path counts):

| Group | Path count |
|---|---:|
| `/api/agents/*` | 13 |
| `/api/approvals/*` | 3 |
| `/api/apps/*` | 4 |
| `/api/artifacts/*` | 5 |
| `/api/autonomous/*` | 7 |
| `/api/autopilot/*` | 4 |
| `/api/code-operator/*` | 47 |
| `/api/design/*` | 5 |
| `/api/desktop/*` | 4 |
| `/api/dimensional-reports` | 1 |
| `/api/env/status` | 1 |
| `/api/events/stream` | 1 |
| `/api/gen3d/*` | 2 |
| `/api/generation/*` | 3 |
| `/api/jobs/*` | 9 |
| `/api/learning/*` | 8 |
| `/api/logs` | 1 |
| `/api/modules/*` | 28 |
| `/api/notifications/*` | 7 |
| `/api/observe/*` | 13 |
| `/api/plugins/*` | 7 |
| `/api/ports` | 2 |
| `/api/printers/*` | 17 |
| `/api/proof/*` | 2 |
| `/api/providers/health` | 1 |
| `/api/roadmap/*` | 3 |
| `/api/safety/*` | 2 |
| `/api/settings/*` | 5 |
| `/api/source-os/*` | 2 |
| `/api/sources/readiness` | 1 |
| `/api/system/*` | 3 |
| `/api/truth-gate/*` | 3 |
| `/api/voice/*` | 9 |
| `/api/workflows` | 1 |
| `/v1/chat/completions` | 1 |
| `/health` | 1 |
| Framework (docs/openapi/redoc) | 4 |

## 3. Route-to-reference matrix

Reference images enumerated from `Images-GUI/` (31 PNGs). One row per
reference PNG. "Status" reflects whether a hash route + matching tab
component exists today; visual fidelity is **not** assessed (out of scope
for read-only mapping — Playwright proof remains the runtime gate per
`GUI_REFERENCE_MANIFEST.json`).

### 00 — User current downloads (`Images-GUI/00-user-current-downloads/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `Generated image 1.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Generated image 2.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Generated image 3.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Generated image 4.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Generated image 5.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Generated image 6.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Generated image 7.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Generated image 8.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Generated image 9.png` | n/a (visual exemplar) | n/a | n/a | EXISTS (reference only) |
| `Hermes3D.png` | n/a (brand mark) | n/a | n/a | EXISTS (reference only) |

### 01 — Dashboard modes (`Images-GUI/01-dashboard-modes/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `simple-dashboard-a.png` | `#dashboard:simple` | `components/dashboard/DashboardSimple.tsx` (+ legacy `simple/SimpleHermesDashboard.tsx` for `uiMode='simple'`) | `/api/system/snapshot`, `/api/providers/health`, `/api/notifications` | EXISTS |
| `simple-dashboard-b.png` | `#dashboard:simple` | `components/dashboard/DashboardSimple.tsx` | same as above | EXISTS |
| `advanced-dashboard-a.png` | `#dashboard:advanced` | `components/dashboard/DashboardAdvanced.tsx` | `/api/system/snapshot`, `/api/agents`, `/api/observe/status`, `/api/jobs`, `/api/notifications`, `/api/providers/health` | EXISTS |
| `advanced-dashboard-b.png` | `#dashboard:advanced` | `components/dashboard/DashboardAdvanced.tsx` | same as above | EXISTS |
| `custom-dashboard-a.png` | `#dashboard:custom` | `components/dashboard/DashboardCustom.tsx` (palette persisted to `localStorage[h3d.dashboard.custom.layout]`) | same data sources as advanced; no dedicated layout endpoint | EXISTS |
| `custom-dashboard-b.png` | `#dashboard:custom` | `components/dashboard/DashboardCustom.tsx` | same as above | EXISTS |

### 02 — Primary pages (`Images-GUI/02-primary-pages/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `primary-tabs-autopilot-design-gen3d-jobs.png` | `#autopilot`, `#design`, `#gen3d`, `#jobs` | `tabs/Autopilot.tsx`, `tabs/Design.tsx`, `tabs/Gen3D.tsx`, `tabs/Jobs.tsx` | `/api/autopilot/*`, `/api/design/*`, `/api/gen3d/*`, `/api/generation/*`, `/api/jobs/*` | EXISTS |
| `primary-tabs-printers-observe-agents-learning.png` | `#printers`, `#observe`, `#agents`, `#learning` | `tabs/Printers.tsx`, `tabs/Observe.tsx`, `tabs/Agents.tsx`, `tabs/Learning.tsx` | `/api/printers/*`, `/api/observe/*`, `/api/agents/*`, `/api/learning/*` | EXISTS |
| `primary-tabs-artifacts-approvals-plugins-roadmap.png` | `#artifacts`, `#approvals`, `#plugins`, `#roadmap` | `tabs/Artifacts.tsx`, `tabs/Approvals.tsx`, `tabs/Plugins.tsx`, `tabs/Roadmap.tsx` | `/api/artifacts/*`, `/api/approvals/*`, `/api/plugins/*`, `/api/roadmap/*` | EXISTS |

### 03 — Settings & voice (`Images-GUI/03-settings-voice/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `settings-subtabs-all.png` | `#settings` (internal subtab state — no nested hash) | `tabs/Settings.tsx` → `components/settings/SettingsPage.tsx` (8 subtabs: general/providers/agents/mcp/printers/environment/updates/about) | `/api/settings`, `/api/settings/theme`, `/api/settings/update-center`, `/api/providers/health`, `/api/printers`, `/api/env/status`, `/api/agents/config`, `/api/code-operator/mcp-locks/state` | PARTIAL (subtabs lack URL hash; spec image enumerates 6 subtabs `providers/agents/printers/environment/updates/about`, app ships 8 incl. `general` and `mcp` extras — superset of spec) |
| `voice-communication-subtabs.png` | `#voice` (internal subtab state — `browser` / `transcripts` / `proof`) | `tabs/Voice.tsx` | `/api/voice/agents`, `/api/voice/voices`, `/api/voice/providers`, `/api/voice/preview`, `/api/voice/stt`, `/api/voice/transcripts`, `/api/voice/proof-events`, `/api/voice/recordings/{id}` | PARTIAL (subtabs lack URL hash; otherwise matches spec) |

### 04 — Source OS (`Images-GUI/04-source-os/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `source-os-core-categories.png` | `#sources` | `tabs/SourceOS.tsx` + `components/source-os/{ModuleList,SecondaryNav,AppDetailPanel}.tsx` | `/api/source-os/modules`, `/api/source-os/modules/{module_id}`, `/api/sources/readiness`, `/api/modules`, `/api/modules/{id}/install*`, `/api/modules/{id}/launch`, `/api/modules/runtime/*` | EXISTS |
| `source-os-remaining-categories.png` | `#sources` (scrolled / filter) | same | same | EXISTS |
| `source-os-60-app-coverage-matrix.png` | `#sources` (matrix view) + `#apps[/<id>]` for app drill-in | `tabs/SourceOS.tsx`, `tabs/AppRegistry.tsx`, `components/AppRegistry/{AppStatusPanel,AppDetailPanel}.tsx` | `/api/apps`, `/api/apps/{app_id}`, `/api/apps/{app_id}/run-proof`, `/api/apps/{app_id}/rollback`, `/api/source-os/modules`, `/api/modules/runtime/setup-queue` | EXISTS |

### 05 — Action windows (`Images-GUI/05-action-windows/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `action-window-core-apps.png` | All tabs (Action Window is a global mount) | `components/ActionWindow/{ActionWindow,ActionWindowMount,DetachedActionWindow}.tsx` + `action-window-detached.tsx` (separate window) | `/api/agents/{persona_id}/actions/{action_id}`, `/api/agents/actions/{action_id}`, `/api/agents/{persona_id}/confirm-action/{action_id}`, `/api/agents/{persona_id}/deny-action/{action_id}`, `/api/code-operator/cli-runners/run`, `/api/modules/{id}/launch` | EXISTS |
| `action-window-advanced-tools.png` | All tabs (advanced tool surface in same Action Window) | same components | same; additionally `/api/code-operator/teams/*`, `/api/code-operator/recovery/*`, `/api/code-operator/patch/*` | EXISTS |

### 06 — States & responsive (`Images-GUI/06-states-responsive/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `states-responsive-reference.png` | All tabs (responsive layout exemplar across modes) | `app/AppShell.tsx`, `components/layout/{Sidebar,TopBar,Panel,ResizablePane}.tsx`, `components/StatusBanners/*`, `components/Onboarding/*` | n/a (presentation only); banner inputs come from `/api/system/runtime-readiness`, `/api/providers/health`, `/api/notifications` | EXISTS |

### 07 — Plugins / skills / MCP (`Images-GUI/07-plugins-skills-mcp/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `plugins-skills-mcp-app-connectors.png` | `#plugins`, `#settings` (`mcp` subtab), `#apps` | `tabs/Plugins.tsx`, `components/settings/McpSubtab.tsx`, `tabs/AppRegistry.tsx`, `components/AppRegistry/AppStatusPanel.tsx` | `/api/plugins`, `/api/plugins/{id}/{activate,deactivate,config,logs,status}`, `/api/code-operator/mcp-locks/state`, `/api/apps`, `/api/apps/{id}` | PARTIAL (no dedicated "skills" registry route or component; MCP surface lives only as a Settings subtab — no top-level `#mcp` hash) |

### 08 — App / utility pages (`Images-GUI/08-app-utility-pages/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `workflow-printqueue-files-logs.png` | `#jobs` (queue + logs surface), `#artifacts` (files), partial `#observe` | `tabs/Jobs.tsx`, `tabs/Artifacts.tsx`, `tabs/Observe.tsx`; legacy `tabs/Workflows.tsx`, `tabs/PrintQueue.tsx`, `tabs/SystemLogs.tsx` exist but are NOT in live `TABS` | `/api/workflows`, `/api/jobs`, `/api/jobs/{id}/events`, `/api/artifacts`, `/api/artifacts/list`, `/api/logs`, `/api/proof/events` | PARTIAL (workflows / print-queue / system-logs implementations exist as orphan tabs but have no live hash route; reference image expects standalone navigable pages) |
| `proof-health-notifications-safety.png` | `#health` (shim only — no AppShell tab), `#dashboard:advanced` (notifications drawer) | `components/health/ServiceHealthPage.tsx`, `components/notifications/NotificationCenter.tsx`, `components/StatusBanners/*`; legacy `tabs/Proof.tsx` exists but is not registered | `/api/proof/bundles`, `/api/proof/events`, `/api/providers/health`, `/api/notifications`, `/api/notifications/stream`, `/api/safety/propose`, `/api/safety/veto`, `/api/printers/{id}/safety-state`, `/api/printers/{id}/safety-events/*` | PARTIAL (no `#proof` or `#notifications` top-level hash; `#health` reachable only via `main.tsx` shim, not the Sidebar; safety surface has no UI page despite having endpoints) |

### 09 — Themes (`Images-GUI/09-themes/`)

| Image | Target route | Component | Backend truth source | Status |
|---|---|---|---|---|
| `theme-variants-reference.png` | `#settings` (`general` subtab — theme picker) + global `ThemeSwitcher` mount | `components/ThemeSwitcher/ThemeSwitcher.tsx`, `theme/ThemeProvider.tsx`, `theme/tokens.ts` | `/api/settings/theme`, `/api/settings` | PARTIAL (W8-3 token surface ships dark + light only; reference shows 6 themes — `default_hermes_dark`, `cyberpunk`, `matrix`, `tron`, `industrial_forge`, `aurora_operator` — additional palettes not yet present in `tokens.ts`) |

### Summary counts

- Reference images mapped: **31** (10 brand exemplars + 21 functional refs)
- Functional refs scored EXISTS: **17** (6 dashboard, 3 primary tab grids, 3 source-os, 2 action-window, 1 responsive, 2 sub-totals when combined with above counts; see notes)
- Functional refs scored PARTIAL: **5** (settings, voice, plugins/MCP, workflows/queue/files/logs, proof/health/notifications/safety, themes — minus brand exemplars)
- Functional refs scored MISSING: **0** (no functional reference is wholly without a route)

Recount with the "Status" column literally:
EXISTS = 24 rows (10 brand + 6 dashboard + 3 primary + 3 source-os + 2 action-window + 1 responsive — i.e., 25, see exact rows above);
PARTIAL = 6 rows (settings, voice, plugins/MCP, workflows/queue/files/logs, proof/health/notifications/safety, themes);
MISSING = 0 rows.

**Final tally: 25 EXISTS / 6 PARTIAL / 0 MISSING across 31 reference images.**

## 4. Missing routes / components list

No reference image is wholly without an implementation, so there are no
`MISSING` rows. Gaps captured as `PARTIAL` above are itemised here for
the wiring lane to address:

| Gap | Reference image | Required route | Required component | Backend already exists? |
|---|---|---|---|---|
| Settings subtab not URL-addressable | `03-settings-voice/settings-subtabs-all.png` | `#settings/<subtab>` (e.g. `#settings/providers`) | extend `components/settings/SettingsPage.tsx` to read from hash; update `tabIdFromHash` to keep nested segment | yes (8 settings endpoints) |
| Voice subtab not URL-addressable | `03-settings-voice/voice-communication-subtabs.png` | `#voice/<browser|transcripts|proof>` | extend `tabs/Voice.tsx` to read trailing hash segment | yes (9 voice endpoints) |
| Workflows page orphan | `08-app-utility-pages/workflow-printqueue-files-logs.png` | `#workflows` | register existing `tabs/Workflows.tsx` in `TABS`/`HASH_TO_TAB`/`TAB_COMPONENTS` | yes (`/api/workflows`) |
| Print queue page orphan | same image | `#queue` (or merge into `#jobs`) | register `tabs/PrintQueue.tsx` or fold into `tabs/Jobs.tsx` | yes (`/api/jobs`) |
| System logs page orphan | same image | `#logs` | register `tabs/SystemLogs.tsx` | yes (`/api/logs`) |
| Service Health is a shim | `08-app-utility-pages/proof-health-notifications-safety.png` | `#service_health` (top-level Sidebar entry) | promote `components/health/ServiceHealthPage.tsx` to a registered tab; remove `main.tsx` hash gate | yes (`/api/system/runtime-readiness`, `/api/providers/health`) |
| Proof page orphan | same image | `#proof` | register `tabs/Proof.tsx` | yes (`/api/proof/bundles`, `/api/proof/events`) |
| Notifications surface only inline | same image | `#notifications` (or notification-centre detached route) | promote `components/notifications/NotificationCenter.tsx` to its own surface | yes (7 notification endpoints) |
| Safety has no dedicated UI | same image | `#safety` (or under Observe / Printer Control) | new component bound to safety endpoints | yes (`/api/safety/*`, `/api/printers/{id}/safety-*`) |
| MCP has no top-level page | `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | `#mcp` (or keep as Settings subtab) | optional promotion of `components/settings/McpSubtab.tsx` | yes (`/api/code-operator/mcp-locks/state`) |
| Skills registry has no UI | same image | `#skills` (or extension of `#plugins`) | new component | partial — no `/api/skills/*` endpoint (see §5) |
| Themes beyond `dark`/`light` | `09-themes/theme-variants-reference.png` | n/a (in `#settings/general`) | extend `theme/tokens.ts` with `cyberpunk`, `matrix`, `tron`, `industrial_forge`, `aurora_operator` palettes | n/a (theme is client-side; persisted via `/api/settings/theme`) |
| Pre-W6 router stale | n/a | n/a (cleanup) | delete `app/routes.tsx` (14-tab) — only `routes.ts` is consumed by `App.tsx` | n/a |

## 5. Backend endpoints needed but missing

| Reference need | Existing endpoint(s) | Missing endpoint |
|---|---|---|
| Skills registry (`07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png`) | `/api/plugins`, `/api/code-operator/mcp-locks/state` | `/api/skills` (registry list + per-skill metadata) |
| Custom dashboard layout persistence (`01-dashboard-modes/custom-dashboard-*.png`) | client-side `localStorage[h3d.dashboard.custom.layout]` only | optional `/api/dashboard/layouts` (server-side persistence) |
| Theme catalog beyond default (`09-themes/theme-variants-reference.png`) | `/api/settings/theme` (string field) | `/api/settings/themes` (list of available palette ids) |
| App connector matrix (`07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` — connector-by-app grid) | `/api/apps`, `/api/plugins` | `/api/connectors` (connector → app coverage matrix) |
| Notification stream filtering by category (`08-app-utility-pages/proof-health-notifications-safety.png`) | `/api/notifications/stream` | `/api/notifications?category=safety|proof|health` (query-param filtering not currently reflected in route table) |

All other reference panels are already covered by an existing API.

---
**End of W14-A2 deliverable.** Read-only scan complete; no source files
modified.
