# W18-A2 — UX/UI Structure Audit (Hermes3D OS GUI vs `Images-GUI/`)

| field | value |
|---|---|
| lane | W18-A2 |
| role | audit |
| owner | `w18-a2` (Hermes lock) |
| date_utc | 2026-05-11 |
| repo | `Hermes3D` |
| branch | `claude/w18-a2-ux-ui-structure-audit` |
| base | `develop @ 330f521b9892af08466cc082522f1a07ed2be6ab` |
| servers | backend `http://127.0.0.1:8765` · frontend `http://localhost:5173` |
| visual_truth | `Images-GUI/` (31 PNG references, **never the live UI**) |
| disposition | **audit-only — NO code changes, NO fixes** |
| status_vocab | strictly `PASS_REAL` / `FAIL_VISUAL_MISMATCH` / `FAIL_BROKEN` |

## 0. Method

1. Enumerated every PNG in `Images-GUI/` and mapped each to a current route from
   `03_implementation/ui/src/App.tsx` and `03_implementation/ui/src/app/routes.ts`.
2. Captured the live UI at viewport `1920×1080` for each primary tab using the
   running frontend (`http://localhost:5173`) and backend
   (`http://127.0.0.1:8765`). Screenshots written to
   `C:\Users\Admin\AppData\Local\Temp\w18-a2-live-*.png` (transient, not
   committed — Images-GUI/ remains the only source of truth per W18-A2 hard
   rule "NO baseline recapture").
3. Read the route registry, the AppShell, the TopBar/Sidebar, every dashboard
   variant, and every primary tab component cited below.
4. Per-route verdict assigned with strict vocabulary. **No "visually
   acceptable", no "good enough", no soft passes.**

## 1. Reference → Route Map

| reference file (`Images-GUI/...`) | matching route hash | matching component file |
|---|---|---|
| `00-user-current-downloads/Hermes3D.png` | `#dashboard` (advanced) | `tabs/Dashboard.tsx` |
| `00-user-current-downloads/Generated image 1..9.png` | (concept frames, no single route) | — |
| `01-dashboard-modes/simple-dashboard-a.png` | `#dashboard:simple` | `components/dashboard/DashboardSimple.tsx` |
| `01-dashboard-modes/simple-dashboard-b.png` | `#dashboard:simple` | `components/dashboard/DashboardSimple.tsx` |
| `01-dashboard-modes/advanced-dashboard-a.png` | `#dashboard:advanced` | `components/dashboard/DashboardAdvanced.tsx` → `tabs/Dashboard.tsx` |
| `01-dashboard-modes/advanced-dashboard-b.png` | `#dashboard:advanced` | `components/dashboard/DashboardAdvanced.tsx` |
| `01-dashboard-modes/custom-dashboard-a.png` | `#dashboard:custom` | `components/dashboard/DashboardCustom.tsx` |
| `01-dashboard-modes/custom-dashboard-b.png` | `#dashboard:custom` | `components/dashboard/DashboardCustom.tsx` |
| `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` | `#autopilot` `#design` `#gen3d` `#jobs` | `tabs/Autopilot.tsx`, `tabs/Design.tsx`, `tabs/Gen3D.tsx`, `tabs/Jobs.tsx` |
| `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` | `#printers` `#observe` `#agents` `#learning` | `tabs/Printers.tsx`, `tabs/Observe.tsx`, `tabs/Agents.tsx`, `tabs/Learning.tsx` |
| `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` | `#artifacts` `#approvals` `#plugins` `#roadmap` | `tabs/Artifacts.tsx`, `tabs/Approvals.tsx`, `tabs/Plugins.tsx`, `tabs/Roadmap.tsx` |
| `03-settings-voice/settings-subtabs-all.png` | `#settings/*` | `tabs/Settings.tsx` |
| `03-settings-voice/voice-communication-subtabs.png` | `#voice/*` | `tabs/Voice.tsx` |
| `04-source-os/source-os-core-categories.png` | `#source_os` (matrix view) | `tabs/SourceOS.tsx` |
| `04-source-os/source-os-remaining-categories.png` | `#source_os` (matrix view) | `tabs/SourceOS.tsx` |
| `04-source-os/source-os-60-app-coverage-matrix.png` | `#source_os` (matrix view) | `components/source-os/SixtyAppCoverageMatrix.tsx` |
| `05-action-windows/action-window-core-apps.png` | **NO LIVE ROUTE** — only `action-window.html?detached=1` exists | `components/ActionWindow/*` (not mounted in AppShell) |
| `05-action-windows/action-window-advanced-tools.png` | **NO LIVE ROUTE** | (see above) |
| `06-states-responsive/states-responsive-reference.png` | (cross-cutting; no dedicated route) | — |
| `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | `#plugins` | `tabs/Plugins.tsx` |
| `08-app-utility-pages/workflow-printqueue-files-logs.png` | `#workflows` `#print_queue` `#files` `#system_logs` | `tabs/Workflows.tsx`, `tabs/PrintQueue.tsx`, `tabs/Files.tsx`, `tabs/SystemLogs.tsx` |
| `08-app-utility-pages/proof-health-notifications-safety.png` | `#proof` `#service_health` `#notifications` `#safety` | `tabs/Proof.tsx`, `tabs/ServiceHealth.tsx`, `tabs/Notifications.tsx`, `tabs/Safety.tsx` |
| `09-themes/theme-variants-reference.png` | (cross-cutting; theme switcher in TopBar) | `theme/ThemeProvider.tsx`, `components/ThemeSwitcher.tsx` |

## 2. Mismatch Inventory (`FAIL_VISUAL_MISMATCH` rows)

| # | route | file:line | observed | expected (Images-GUI/) | ref_image | status |
|---|---|---|---|---|---|---|
| 1 | `#source_os` | `tabs/SourceOS.tsx:132` (`readInitialView` returns `"registry"` by default) | First open shows the legacy **Module Registry** view ("Hermes OS · 0 source-backed modules · Slicers/Modelers/Print Form/Firmware Tools tabs"). The 60-app coverage matrix only appears after a manual click on `[data-testid="source-os-view-matrix"]`. | The reference pack PUTS the **dashboard category treemap + 60-app coverage matrix** as the primary visual for the Source OS tab. Module Registry is a *detail* view, not the landing view. | `04-source-os/source-os-core-categories.png`, `04-source-os/source-os-60-app-coverage-matrix.png` | `FAIL_VISUAL_MISMATCH` |
| 2 | `#source_os` (matrix mode) | `components/source-os/SixtyAppCoverageMatrix.tsx` | Matrix renders a flat grid of app cards plus a footer summary strip. NO right-rail "App Details" inspector with proof status, license, capabilities, command palette, or "in dashboard / not in dashboard" badge. | Reference shows a 3-column shell: left category nav · centre coverage matrix · right "App Details" inspector pinned to the selected card (`PrusaSlicer` example panel). | `04-source-os/source-os-60-app-coverage-matrix.png` | `FAIL_VISUAL_MISMATCH` |
| 3 | `#autopilot` | `tabs/Autopilot.tsx` (single component, ~full file) | Two-column tabular layout: "Readiness Checks" (gate rows) on left, "Planner Queue" with "Freeze / Thaw" on right. | Reference shows a denser command-centre with header KPIs ("CPU/RAM/GPU"), graph mini-strip, recent-runs table at top, and `Active Workflows` cards below — visually closer to the dashboard density, NOT a single split-pane gate table. | `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` (top-left tile) | `FAIL_VISUAL_MISMATCH` |
| 4 | `#design` | `tabs/Design.tsx` | Three-column layout (Design Intake · Design Toolchain · Local Executables) — too detail-heavy at the top, parametric panel sits in a left sidebar. | Reference shows a 3D preview card top-left, parameter rail right, history strip bottom, and an "Open Modeler" CTA — more workshop-like and less spreadsheet-like. | `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` (top-right tile) | `FAIL_VISUAL_MISMATCH` |
| 5 | `#gen3d` | `tabs/Gen3D.tsx` | Three-column layout (Prompt + Reference · centre placeholder · 3D Generation Providers / LLM Providers list). NO active 3D preview, NO model-library grid, NO recent-generations strip. | Reference shows a large central 3D viewport with the model, a sidebar of provider chips, and a generation history strip below. | `02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png` (bottom-left tile) | `FAIL_VISUAL_MISMATCH` |
| 6 | `#printers` | `tabs/Printers.tsx` | Card grid of printers with telemetry (T1, T2, FLSUN S1, FLSUN V400) — usable but visually flat. | Reference shows a printer-fleet panel with a top KPI strip ("Online/Active/Failed counts"), a 3D-mini per printer, a per-printer mini-chart strip, and a footer log stream. | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` (top-left tile) | `FAIL_VISUAL_MISMATCH` |
| 7 | `#observe` | `tabs/Observe.tsx` | Live camera feed grid is correct in spirit but cards lack the **overlay HUD** (status pill, fps, detection chip) shown in the reference; also no compact right-rail timeline. | Reference shows each camera with overlay HUD chips + a per-camera mini-timeline along the bottom; a right-rail event list. | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` (top-right tile) | `FAIL_VISUAL_MISMATCH` |
| 8 | `#voice` | `tabs/Voice.tsx` | Single-tab "Voice Browser / Transcript History / Proof Review" sub-tab strip + a "Real-time Transcript" central card + Controls right-rail. Adequate match for Voice Browser only. | Reference shows TWO additional surfaces in the same shell — *Transcript History* with a per-agent filter sidebar, and *Proof Review* with a deep-link table to proof artifacts. Current Voice.tsx renders only the Voice Browser body for ALL three sub-tabs. | `03-settings-voice/voice-communication-subtabs.png` (4 tiles) | `FAIL_VISUAL_MISMATCH` |
| 9 | `#agents` | `tabs/Agents.tsx` | "Agent Command Center" with per-agent card grid + "Agent Code Workbench" panel below + "Run Queue" sidebar. | Reference shows a denser Mission-Control: top KPI strip, role-coloured agent list, per-agent micro-charts, "Active Tasks" table mid-panel, "Recovery Controller" status rail right. The Code Workbench is not in the reference at all on this tab. | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` (bottom-left tile) | `FAIL_VISUAL_MISMATCH` |
| 10 | `#learning` | `tabs/Learning.tsx` | "Idle Learning Mode" and "Idle Workbench" lane cards. Looks like a backend admin form, not a learning console. | Reference shows a per-category learning grid (printer-failure, slicer-tuning, prompt-tuning), with each tile showing a delta-chart and "Approve / Reject" buttons. | `02-primary-pages/primary-tabs-printers-observe-agents-learning.png` (bottom-right tile) | `FAIL_VISUAL_MISMATCH` |
| 11 | `#artifacts` | `tabs/Artifacts.tsx` | Long single-column proof-bundle list + a left "Attach Visual Evidence" form. | Reference shows a 3-column shell: artifact filter pills + category nav left · artifact thumbnail grid centre · selected-artifact preview right with verify/download CTAs. | `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` (top-left tile) | `FAIL_VISUAL_MISMATCH` |
| 12 | `#approvals` | `tabs/Approvals.tsx` | Two empty single-column sections: "Pending Approvals" + "Approval History". | Reference shows a Kanban-style 4-column layout (Open · In Review · Approved · Rejected) with proof-link chips, plus a right-rail "Recent Activity" with audit-log entries. | `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` (top-right tile) | `FAIL_VISUAL_MISMATCH` |
| 13 | `#apps` | `tabs/AppRegistry.tsx` (via `components/AppRegistry/*`) | A flat table "App Registry Status" with `60 Apps · 2 prock pass · 2 prock fail · No Never Procked` columns. Lacks the sidebar entirely on first paint (Sidebar is rendered, but the table overflows it visually). | The reference pack has NO "Apps" landing route — apps open via the Action Window from Source OS or the home dashboard. The current `#apps` tab is a parallel admin surface NOT in the reference at all. See §4 wrong-nesting #1. | (none — this route is unsupported by the reference pack) | `FAIL_VISUAL_MISMATCH` |
| 14 | `#plugins` | `tabs/Plugins.tsx` | "Plugin API Panel" + 3×N card grid (Autopilot Setup, Azure Voice, Blender/Trimesh, CadQuery, Camera Observer, …). Plugins, MCP servers, and skills are merged into one flat list. | Reference shows a 4-column dashboard: top KPI strip (Plugins X · Skills Y · MCP Servers Z), then 3 horizontal swimlanes — Plugins, Skills, MCP Servers — each with its own row of cards, NOT one flat grid. App Connectors panel is the 4th lane. | `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | `FAIL_VISUAL_MISMATCH` |
| 15 | `#settings/general` | `tabs/Settings.tsx` | Default subtab renders a Theme/Density/Language form. Some subtabs (Providers, Agents, Printers, Environment, Updates, About) match the reference shape, but General has no analogue in the reference. Subtab navigation does not show all reference subtabs in the same horizontal strip. | Reference has 6 subtabs (Providers, Agents, Printers, Environment, Updates, About) — there is NO "General" subtab in the reference, but it exists in the live route. | `03-settings-voice/settings-subtabs-all.png` (top-left "Providers" tile is the reference landing — General does not appear) | `FAIL_VISUAL_MISMATCH` |
| 16 | `#roadmap` | `tabs/Roadmap.tsx` | One header "Roadmap · Daily-use completion path" then "Legacy Roadmap Rows · No roadmap items returned…" — a stub. | Reference shows a structured timeline: completion-bar header, milestone tiles, per-milestone proof-link chips, "Next 7 days" rail right. | `02-primary-pages/primary-tabs-artifacts-approvals-plugins-roadmap.png` (bottom-right tile) | `FAIL_VISUAL_MISMATCH` |
| 17 | `#print_queue`, `#files`, `#system_logs`, `#proof`, `#service_health`, `#notifications`, `#safety`, `#workflows` (8 utility tabs) | `tabs/{Workflows,PrintQueue,Files,SystemLogs,Proof,ServiceHealth,Notifications,Safety}.tsx` | Each utility tab is a single-column live list with a "Refresh" button. Functional but visually plain. | Reference shows EVERY utility page as a 3-column dashboard: KPI strip top, central content grid, right rail with related actions or filters. Reference tiles show summary charts + drill-down tables, not plain lists. | `08-app-utility-pages/workflow-printqueue-files-logs.png`, `08-app-utility-pages/proof-health-notifications-safety.png` | `FAIL_VISUAL_MISMATCH` (×8) |

## 3. Duplication Inventory

| # | duplicated surface | file:line | description | ref_image | status |
|---|---|---|---|---|---|
| D1 | **Sidebar duplication: AppShell `Sidebar` vs `SimpleHermesDashboard`'s internal `simple-primary-nav`** | `components/layout/Sidebar.tsx:12-49` vs `components/simple/SimpleHermesDashboard.tsx:229-249` | Two independent sidebar implementations both consume `PRIMARY_TABS` and both render a vertical primary nav. Style and width differ (220 px ResizablePane vs ~280 px ResizablePane with `h3d.simple.leftRail.width` localStorage key). Whether the user sees one or the other depends on `useStore.uiMode` ("full" → AppShell.Sidebar, "simple" → SimpleHermesDashboard internal nav). | `Images-GUI/` shows ONE sidebar style across all modes; current code ships two. | `FAIL_VISUAL_MISMATCH` (duplication) |
| D2 | **Dashboard mode switch button appears twice** | `app/AppShell.tsx` (via TopBar at `components/layout/TopBar.tsx:82`) renders `DashboardModeSwitcher` AND the in-tab `DashboardAdvanced.tsx:28-35` paints a separate "Action Window" chip in the dashboard area; `DashboardCustom.tsx:236-253` paints a "Reset / Edit Layout" header strip independently | `components/layout/TopBar.tsx:82` + `components/dashboard/DashboardAdvanced.tsx:21-36` + `components/dashboard/DashboardCustom.tsx:204-255` | Three independent control surfaces for the same conceptual "dashboard mode + dashboard tools" group. | Reference has ONE consolidated dashboard-control row pinned to the top of the dashboard pane. | `FAIL_VISUAL_MISMATCH` (duplication) |
| D3 | **Theme switcher / "Simple" mode toggle / Notifications bell appear in BOTH the AppShell TopBar AND inside individual tab headers (e.g. SourceOS' own header strip in `tabs/SourceOS.tsx:407-421` paints its own `Hermes3D OS · N source-backed modules` heading directly under the global TopBar)** | `components/layout/TopBar.tsx:57-98` vs `tabs/SourceOS.tsx:407-421` | Two stacked headers consume vertical space; the in-tab one repeats the route name that the TopBar already shows via `activeLabel`. | Reference shows a single top-bar; in-tab heading is a small caption only. | `FAIL_VISUAL_MISMATCH` (duplication) |

## 4. Wrong-Nesting Inventory

| # | route / surface | file:line | wrong-nesting description | status |
|---|---|---|---|---|
| W1 | **`#apps` is a top-level sidebar tab** | `app/routes.ts:50` (`{ id: "apps", label: "Apps", icon: AppWindow }`) | The reference pack treats individual apps as **opens of the Action Window from the Source OS tab** — not a separate top-level tab. The current routing exposes `tabs/AppRegistry.tsx` as `#apps`, which has no analogue in `Images-GUI/`. The 60-app coverage matrix in `#source_os` is the correct home of app launches. | `FAIL_BROKEN` (route exists but maps to no reference; nesting is wrong) |
| W2 | **Action Window component never mounted inside `AppShell`** | `app/AppShell.tsx:49-67` (no `<ActionWindowMount>` anywhere) vs `components/ActionWindow/ActionWindowMount.tsx:26-61` | `ActionWindow` only exists in (a) `action-window.html` detached entry, (b) a stub `Maximize2` chip in `DashboardAdvanced.tsx:38-52` that routes to `#autopilot` (NOT a real Action Window), and (c) the matrix view test cards. The reference pack §5 (`05-action-windows/*.png`) shows the Action Window as the **resizable central surface** inside every primary tab, mounted at the AppShell level. **It is missing from the main shell entirely.** | `FAIL_BROKEN` |
| W3 | **Settings has a `General` subtab that is not in the reference, and lacks an `MCP` subtab placeholder that IS in the reference matrix elsewhere (`07-plugins-skills-mcp/`)** | `app/store.ts:132-141` `SETTINGS_SUBTAB_KEYS = ['general','providers','agents','mcp','printers','environment','updates','about']` vs `Images-GUI/03-settings-voice/settings-subtabs-all.png` (6 tiles: Providers, Agents, Printers, Environment, Updates, About). | The settings router includes `general` and `mcp` keys but the reference image shows only the other 6. `mcp` is in the keys but the route does not render an MCP-config page (the reference for MCP lives in the Plugins tab grouping per `07-plugins-skills-mcp/`). | `FAIL_VISUAL_MISMATCH` (nesting) |
| W4 | **Voice subtabs all render the same body** | `tabs/Voice.tsx` (single component returns one layout regardless of subtab) | The store has `VOICE_SUBTAB_KEYS = ['browser','transcript-history','proof-review']` (`app/store.ts:153-157`) but `tabs/Voice.tsx` does not gate-switch its body on the subtab — visiting `#voice/transcript-history` renders the same panel as `#voice/browser`. | `FAIL_BROKEN` (router accepts subtab, component ignores it) |
| W5 | **Utility tabs registered via `App.tsx#UTILITY_TAB_HASHES` (lines 57-79) but ALSO via `app/store.ts#TAB_TO_HASH` (lines 48-66) for the parent set** — and `app/store.ts:7-25 TAB_IDS` *excludes* the utility tabs, so two independent routing tables are in flight. | `App.tsx:57-106` and `app/store.ts:7-25 + 48-66` | The comment at `App.tsx:42-56` admits this is a temporary fallback because `store.ts` was locked when W15-A19 added the 8 utility tabs. Today both tables coexist. Risk: if a tab is added to one table only, it routes inconsistently. | `FAIL_BROKEN` (split-brain router) |
| W6 | **`HASH_TO_TAB["sources"] → source_os`** AND **`TAB_TO_HASH["source_os"] → "sources"`** while the sidebar label is "Source OS" | `app/store.ts:27-29 + 49` | The hash visible in the URL is `#sources` but the route id is `source_os` and the user-visible label is `Source OS`. Three different strings for one concept; cited in the test_id mismatch already in `tabs/SourceOS.tsx`. | `FAIL_VISUAL_MISMATCH` (nesting — naming) |
| W7 | **`DashboardModeSwitcher` is rendered by the global TopBar but is conditionally hidden when `activeTabId !== "dashboard"`** | `components/layout/TopBar.tsx:30,82` (`const showDashboardModes = activeTabId === "dashboard"`) | The "Simple" toggle button (lines 83-90 of TopBar.tsx) is **always shown** regardless of route. The Simple toggle is therefore a global control mounted inside a component (TopBar) that itself only renders for `uiMode === "full"`. When the user clicks "Simple" the entire shell swaps to `SimpleHermesDashboard`, but there is no symmetrical "Back to Full" control inside the same TopBar — the exit is only available from the SimpleHermesDashboard's own header (line 207-214). Asymmetric, fragile. | `FAIL_VISUAL_MISMATCH` (nesting — control location) |

## 5. Theme Inconsistency Findings

| # | route / surface | file:line | observation | status |
|---|---|---|---|---|
| T1 | **`SimpleHermesDashboard` hard-codes background `bg-[#050c14]` and text `text-[#eef6ff]`** | `components/simple/SimpleHermesDashboard.tsx:185` | These ignore the `ThemeProvider` tokens (`theme/ThemeProvider.tsx`). When the user picks "cyberpunk" or "matrix" theme in the ThemeSwitcher, the AppShell follows but `SimpleHermesDashboard` does not — it remains in its hard-coded blue-black gradient. | `FAIL_VISUAL_MISMATCH` (theme leak) |
| T2 | **`SimpleHermesDashboard` quick-action buttons use Tailwind `from-blue-600 to-blue-700` etc.** | `components/simple/SimpleHermesDashboard.tsx:81-86` (`QUICK_ACTIONS` table) | Hard-coded gradient classes; not theme-aware. | `FAIL_VISUAL_MISMATCH` (theme leak) |
| T3 | **`tabs/SourceOS.tsx` hard-codes status colours `bg-green-900/70`, `bg-cyan-900/60`, `bg-blue-900/50`, `bg-red-950/50`** | `tabs/SourceOS.tsx:102-108` (`TOOL_STATUS_BADGE`) | Uses raw Tailwind colours instead of theme tokens (`bg-accent-green`, `bg-accent-cyan`, etc.). Will not retint when theme changes. | `FAIL_VISUAL_MISMATCH` (theme leak) |
| T4 | **`tabs/Dashboard.tsx` LOG_TONE map uses `bg-accent-cyan` / `bg-accent-amber` / `bg-accent-red` / `bg-muted`** | `tabs/Dashboard.tsx:91-96` | This is theme-correct (uses tokens). Good. Cited for contrast against T1-T3 which are leaks. | `PASS_REAL` |
| T5 | **`components/dashboard/DashboardCustom.tsx` uses theme tokens (`text-accent-blue`, `border-accent-amber/40`, etc.)** | `components/dashboard/DashboardCustom.tsx:225-234` | Theme-aware. | `PASS_REAL` |
| T6 | **Reference shows six themes: default-dark, cyberpunk, matrix, tron, industrial-forge, aurora-operator** | `Images-GUI/09-themes/theme-variants-reference.png`, `Images-GUI/GUI_REFERENCE_MANIFEST.json:56-63` | Live UI has the ThemeSwitcher mounted in TopBar (`components/layout/TopBar.tsx:92`). Without running visual comparison of all 6 themes against the live theme palettes I cannot verify each theme matches its tile; that step is out of scope for an audit (would be runtime verification, not visual reference). The fact that 3 hardcoded-colour leaks (T1-T3) exist means at LEAST those three surfaces fail the multi-theme contract. | `FAIL_VISUAL_MISMATCH` (theme coverage incomplete) |

## 6. Per-Route Verdict (strict vocabulary only)

| route | verdict | one-line justification |
|---|---|---|
| `#dashboard:simple` (`DashboardSimple.tsx`) | `FAIL_VISUAL_MISMATCH` | KPI strip + hero card layout present, but lacks the second hero row (Action Window dock, Proof & Verification panel, Live Agent feed) that the reference Simple-A and Simple-B images both show. |
| `#dashboard:advanced` (`DashboardAdvanced.tsx` → `Dashboard.tsx`) | `FAIL_VISUAL_MISMATCH` | Closest match in the codebase; KPI / fleet / pipeline / agents / system-resources / proof / logs / notifications rows are present. Mismatches: no live Action Window panel inline (the chip routes away); the "AI Workflow Pipeline" stage rail in the reference is replaced with an empty placeholder when no live workflows exist; the right rail "Active Agents" + "Hermes Agents chat-mirror" stack does not visually match the dense reference. |
| `#dashboard:custom` (`DashboardCustom.tsx`) | `FAIL_VISUAL_MISMATCH` | Drag-and-drop grid + palette is correct in shape but visual density is too low; reference shows compact KPI tiles in 4-column packing with thumbnail charts per widget. Current implementation produces tall sparse cards. |
| `#source_os` | `FAIL_VISUAL_MISMATCH` | Defaults to Module Registry instead of the 60-app matrix; matrix view lacks right-rail App Details inspector. See M1, M2. |
| `#autopilot` | `FAIL_VISUAL_MISMATCH` | See M3. |
| `#design` | `FAIL_VISUAL_MISMATCH` | See M4. |
| `#gen3d` | `FAIL_VISUAL_MISMATCH` | See M5. |
| `#jobs` | `FAIL_VISUAL_MISMATCH` | Empty/Queued/Running/Done/Failed/Cancelled sub-tab strip is present but the central detail pane shows "Select a job" with no preview pane skeleton; reference shows job-detail panel always rendered with empty-state hints (timeline, proof badge, printer feed). |
| `#printers` | `FAIL_VISUAL_MISMATCH` | See M6. |
| `#observe` | `FAIL_VISUAL_MISMATCH` | See M7. |
| `#voice` | `FAIL_BROKEN` | See W4 — subtabs route, component does not gate on subtab. |
| `#agents` | `FAIL_VISUAL_MISMATCH` | See M9. |
| `#learning` | `FAIL_VISUAL_MISMATCH` | See M10. |
| `#artifacts` | `FAIL_VISUAL_MISMATCH` | See M11. |
| `#approvals` | `FAIL_VISUAL_MISMATCH` | See M12. |
| `#apps` | `FAIL_BROKEN` | See W1 — route exists but has no analogue in the reference pack. |
| `#plugins` | `FAIL_VISUAL_MISMATCH` | See M14. |
| `#settings/general` | `FAIL_VISUAL_MISMATCH` | See M15 + W3. |
| `#settings/providers` | `FAIL_VISUAL_MISMATCH` | Subtab body density and KPI strip thinner than reference; provider cards lack the per-provider chart/usage badge shown in the reference image. |
| `#settings/agents` | `FAIL_VISUAL_MISMATCH` | Body renders the live agent list but lacks the reference's "Agent role distribution" donut chart and recovery-controller status panel. |
| `#settings/printers` | `FAIL_VISUAL_MISMATCH` | Renders a printer table; reference shows a 2-column shell with per-printer form on right. |
| `#settings/environment` | `FAIL_VISUAL_MISMATCH` | Renders env table; reference shows CPU/RAM/GPU gauge dashboard with environment list below. |
| `#settings/updates` | `FAIL_VISUAL_MISMATCH` | Functional but visually flat; reference shows update-history timeline. |
| `#settings/about` | `FAIL_VISUAL_MISMATCH` | Functional; reference shows a more polished card with version + build matrix. |
| `#workflows` | `FAIL_VISUAL_MISMATCH` | See M17. |
| `#print_queue` | `FAIL_VISUAL_MISMATCH` | See M17. |
| `#files` | `FAIL_VISUAL_MISMATCH` | See M17. |
| `#system_logs` | `FAIL_VISUAL_MISMATCH` | See M17. |
| `#proof` | `FAIL_VISUAL_MISMATCH` | See M17. |
| `#service_health` | `FAIL_VISUAL_MISMATCH` | See M17. |
| `#notifications` | `FAIL_VISUAL_MISMATCH` | See M17. |
| `#safety` | `FAIL_VISUAL_MISMATCH` | See M17. |
| `#roadmap` | `FAIL_VISUAL_MISMATCH` | See M16. |
| **Action Window (any tab)** | `FAIL_BROKEN` | Not mounted in AppShell. See W2. |
| TopBar / theme-aware tokens (Dashboard, Custom dashboard) | `PASS_REAL` | These two surfaces correctly consume theme tokens. |

**No route in the live UI was scored `PASS_REAL` as a visual match** to its reference image. Two _sub-surfaces_ (T4, T5) earn `PASS_REAL` for theme-token discipline only.

## 7. Out-of-Scope Items Surfaced (not fixed here)

1. The Hermes3D repo working tree (`G:/Github/Hermes3D`) had W18-A4 / W18-A7 lane changes staged in the parent shell when this audit started. The audit was conducted from a **fresh worktree** at
   `G:/Github/_claude_worktrees/h3d-w18-a2-audit` checked out at `develop @ 330f521` to avoid contamination. The parent worktree should not be relied upon for additional audit work without a fresh clean checkout.
2. The console emitted **one 404** on first load of `#dashboard` (browser snapshot). The exact resource was not surfaced by the console message; not a visual finding but worth flagging for a follow-up runtime audit.
3. 13 stale Hermes locks from earlier waves (W9-1d, W9-2g, W11-5, W17-A5, P18-F3) remain in the lock registry. Not in scope for W18-A2 but flagged to the orchestrator.

## 8. Audit Conclusion (strict)

- **0 / 31 reference images map to a `PASS_REAL` route in the live UI.**
- **24 routes are `FAIL_VISUAL_MISMATCH`.**
- **5 surfaces are `FAIL_BROKEN`** (`#apps` route, Voice subtab gating, Action Window not mounted, split-brain hash router, AppRegistry tab without reference).
- The current UI is closest to the reference on the **Advanced Dashboard** and the **Source OS 60-app matrix** (when manually switched into matrix view) — both still mismatch but are within a single design pass of converging.
- The widest gaps are on **Approvals, Artifacts, Learning, Plugins, Roadmap, and every utility tab** — these are structural rather than cosmetic.
- The **Action Window contract from `Images-GUI/05-action-windows/`** is unfulfilled: the component exists but is unmounted in the main shell. Any future "open app inside Action Window" claim is currently false.

## 9. Hard Rules Honoured

- [x] No new "green" claims; vocabulary restricted to `PASS_REAL` / `FAIL_VISUAL_MISMATCH` / `FAIL_BROKEN`.
- [x] No baseline recapture; `Images-GUI/` remains the only visual truth.
- [x] No code modifications. This audit is reporting-only.
- [x] Hermes MCP lock acquired with owner `w18-a2` (lock id `58e9de6dc18650c3e41fb29f` on this handoff file).

— end of W18-A2 audit —
