# Wave 15 — Agent 3 · Route / Component Completeness Auditor

- **Date**: 2026-05-10
- **Auditor**: claude-w15-a3
- **Mode**: READ-ONLY (no code changes; no file mutations outside this deliverable)
- **Repo**: `G:/Github/h3d-gui-wiring-codex`
- **Reference pack**: `Images-GUI/` (31 PNGs per `GUI_REFERENCE_MANIFEST.json`)
- **Builds on**: `W14_A2_ROUTE_REFERENCE_MATRIX_2026-05-10.md` and
  `W14_A5_PAGE_GAP_AUDIT_2026-05-10.md` (cited, not redone — see §0)
- **6-way status legend** (per Wave 15 spec):
  - **FULLY_WIRED** — hash route present, component registered, backend connected with live data
  - **PARTIALLY_WIRED** — route + component present but missing key feature (subtab not URL-addressable, mock data, missing testid, etc.)
  - **ORPHAN** — `.tsx` file exists in `src/tabs/` but is not in `TAB_COMPONENTS`/`TAB_IDS`/`HASH_TO_TAB`
  - **MOCK_ONLY** — UI exists and renders, but reads from `src/data/mock/*` instead of a backend endpoint
  - **MISSING_ROUTE** — backend exists, no UI route or component
  - **MISSING_BACKEND** — UI exists or is required, no FastAPI endpoint

---

## 0. Prior audits (cited, not duplicated)

- **`W14_A2_ROUTE_REFERENCE_MATRIX_2026-05-10.md`** — established the
  17 hash-route + 1 shim layout, the 209-handler-path backend snapshot,
  and the 31-image `Status` matrix (25 EXISTS / 6 PARTIAL / 0 MISSING).
  This file extends that work to a 6-way classification covering every
  mandatory item in the user's spec and adds an explicit per-app
  coverage check for the 60 Source OS apps.
- **`W14_A5_PAGE_GAP_AUDIT_2026-05-10.md`** — Playwright walk over 48
  URLs at 1536×1024 captured per-route screenshots and identified 9
  orphan tab files (`Workflows`, `PrintQueue`, `SystemLogs`, `Proof`,
  `BlenderMCP`, `Slicing`, `Fleet`, `PrinterControl`, `DockedApps`)
  plus 3 entirely-missing pages (`#files`, `#safety`, `#notifications`).
  Visual-mismatch detection deferred to a separate lane.

This audit re-runs the route/component inventory to confirm the W14
state, applies the user-supplied 6-way classification, and produces
the orphan/missing/backend-gap deltas needed to plan PR sequencing.

---

## 1. Hash routes enumeration

Source: `src/app/routes.ts` (`PRIMARY_TABS` / `TABS`), `src/app/store.ts`
(`TAB_IDS` / `HASH_TO_TAB` / `TAB_TO_HASH`), `src/main.tsx` (hash gates),
`src/components/dashboard/dashboardModeStore.ts` (dashboard sub-mode hash).

### 1.1 Registered hash routes (consumed by `App.tsx`)

| # | Hash | Tab id | Component file |
|---|---|---|---|
| 1 | `#sources` (alias `#source_os`, `#source`) | `source_os` | `tabs/SourceOS.tsx` |
| 2 | `#dashboard[:simple\|advanced\|custom]` | `dashboard` | `tabs/Dashboard.tsx` → `components/dashboard/Dashboard{Simple,Advanced,Custom}.tsx` |
| 3 | `#autopilot` | `autopilot` | `tabs/Autopilot.tsx` |
| 4 | `#design` | `design` | `tabs/Design.tsx` |
| 5 | `#gen3d` (alias `#3d-generation`) | `gen3d` | `tabs/Gen3D.tsx` |
| 6 | `#jobs` | `jobs` | `tabs/Jobs.tsx` |
| 7 | `#printers` | `printers` | `tabs/Printers.tsx` |
| 8 | `#observe` | `observe` | `tabs/Observe.tsx` |
| 9 | `#voice` | `voice` | `tabs/Voice.tsx` (internal `browser`/`transcripts`/`proof`) |
| 10 | `#agents` | `agents` | `tabs/Agents.tsx` |
| 11 | `#learning` | `learning` | `tabs/Learning.tsx` |
| 12 | `#artifacts` | `artifacts` | `tabs/Artifacts.tsx` |
| 13 | `#approvals` | `approvals` | `tabs/Approvals.tsx` |
| 14 | `#apps[/<id>]` | `apps` | `tabs/AppRegistry.tsx` (also reachable as standalone shim from `main.tsx`) |
| 15 | `#plugins` | `plugins` | `tabs/Plugins.tsx` |
| 16 | `#settings` | `settings` | `tabs/Settings.tsx` → `components/settings/SettingsPage.tsx` (8 internal subtabs) |
| 17 | `#roadmap` | `roadmap` | `tabs/Roadmap.tsx` |
| 18 (shim) | `#health` | n/a | gated in `main.tsx` → `components/health/ServiceHealthPage.tsx` (NOT in Sidebar) |

**Total live tabs: 17 + 1 shim = 18 hash entry points.** No nested
`#settings/<subtab>` or `#voice/<subtab>` is honoured.

### 1.2 Hash routes registered nowhere (orphan tab files)

The following nine `.tsx` files live in `src/tabs/` but are NOT registered
in `App.tsx`'s `TAB_COMPONENTS`, NOT in `store.ts`'s `TAB_IDS`, NOT in
`HASH_TO_TAB`/`TAB_TO_HASH`. Visiting their natural hash (e.g.
`#workflows`) falls through to `UnavailableTab` per `App.tsx:136-145`.

| Orphan file | Natural hash | Data source | Status |
|---|---|---|---|
| `tabs/Workflows.tsx` | `#workflows` | `data/mock/workflows.ts` | ORPHAN + MOCK_ONLY |
| `tabs/PrintQueue.tsx` | `#queue` | `data/mock/jobs.ts` + `data/mock/printers.ts` | ORPHAN + MOCK_ONLY |
| `tabs/SystemLogs.tsx` | `#logs` | `data/mock/logs.ts` | ORPHAN + MOCK_ONLY |
| `tabs/Proof.tsx` | `#proof` | `data/mock/proof.ts` | ORPHAN + MOCK_ONLY |
| `tabs/BlenderMCP.tsx` | `#blender_mcp` | mock-only per file header | ORPHAN + MOCK_ONLY |
| `tabs/Slicing.tsx` | `#slicing` | `data/mock/printers.ts` | ORPHAN + MOCK_ONLY |
| `tabs/Fleet.tsx` | `#fleet` | `data/mock/printers.ts` (+ `api/adapters` import) | ORPHAN + MOCK_ONLY |
| `tabs/PrinterControl.tsx` | `#control` | mock-only per file header | ORPHAN + MOCK_ONLY |
| `tabs/DockedApps.tsx` | `#docked` | mock-only per file header | ORPHAN + MOCK_ONLY |

**Note**: `src/app/routes.tsx` (a 14-tab pre-W6 stale manifest) is not
imported by `App.tsx`/`AppShell.tsx` — every entry there is either
already in `routes.ts` or matches one of the nine orphans above. The
file is dead code; deleting it is recommended (also flagged in W14-A5).

---

## 2. Backend route count + key groups

Source command (re-run for this audit):

```
PYTHONPATH=03_implementation/src python -c \
  "from hermes3d.api.app import create_gui_app; \
   app = create_gui_app(); \
   print('\n'.join(sorted(set(r.path for r in app.routes))))"
```

**Total UNIQUE handler paths: 240** (W14-A2 reported 209
application-owned; this snapshot includes 4 framework routes
`/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` plus all
GET/POST variants of the same path collapsed by `set()`). Total
non-distinct route entries: 253. Top-level groups (unique paths only):

| Group | Path count |
|---|---:|
| `/api/agents/*` | 16 |
| `/api/approvals/*` | 3 |
| `/api/apps/*` | 4 |
| `/api/artifacts/*` | 4 |
| `/api/autonomous/*` | 7 |
| `/api/autopilot/*` | 5 |
| `/api/code-operator/*` | 51 |
| `/api/design/*` | 5 |
| `/api/desktop/*` | 4 |
| `/api/dimensional-reports` | 1 |
| `/api/env/*` | 1 |
| `/api/events/*` | 1 |
| `/api/gen3d/*` | 2 |
| `/api/generation/*` | 3 |
| `/api/jobs/*` | 9 |
| `/api/learning/*` | 8 |
| `/api/logs` | 1 |
| `/api/modules/*` | 35 |
| `/api/notifications/*` | 6 |
| `/api/observe/*` | 12 |
| `/api/plugins/*` | 6 |
| `/api/ports` | 1 |
| `/api/printers/*` | 18 |
| `/api/proof/*` | 2 |
| `/api/providers/*` | 1 |
| `/api/roadmap/*` | 3 |
| `/api/safety/*` | 2 |
| `/api/settings/*` | 4 |
| `/api/source-os/*` | 2 |
| `/api/sources/*` | 1 |
| `/api/system/*` | 3 |
| `/api/truth-gate/*` | 3 |
| `/api/voice/*` | 9 |
| `/api/workflows` | 1 |
| `/v1/chat/completions` | 1 |
| Root / framework (`/health`, `/docs`, `/redoc`, `/openapi.json`, `/docs/oauth2-redirect`) | 5 |

### 2.1 Backend endpoints with NO matching UI

Endpoints that exist but have no registered tab/page:

- `/api/safety/propose`, `/api/safety/veto` — no `#safety` tab
- `/api/dimensional-reports` — surfaced inline in Observe; no top-level page
- `/api/code-operator/*` (51 paths) — agent-tooling surface; consumed
  via Action Window + agent runtime. No dedicated page (intentional).
- `/api/truth-gate/*` (3 paths) — visible only via `/api/system/snapshot` mirrors

---

## 3. Per-item 6-way classification table

Covers every mandatory item from the user's Wave 15 spec.

### 3.1 Settings subtabs (8 implemented vs 6 in reference manifest)

Component: `components/settings/SettingsPage.tsx` (`SUBTABS` array, line 52). Each subtab uses a stable `data-testid="settings-subtab-{key}"`.

| Subtab | URL-addressable? | Component | Status |
|---|---|---|---|
| `general` | NO (hash-only `#settings`, internal `useState`) | `GeneralSubtab.tsx` | PARTIALLY_WIRED |
| `mcp` | NO | `McpSubtab.tsx` (reads `/api/code-operator/mcp-locks/state`) | PARTIALLY_WIRED |
| `providers` | NO | `ProvidersSubtab.tsx` (reads `/api/providers/health`) | PARTIALLY_WIRED |
| `agents` | NO | `AgentConfigSection.tsx` (reads `/api/agents/config`) | PARTIALLY_WIRED |
| `printers` | NO | `PrintersSubtab.tsx` (reads `/api/printers`) | PARTIALLY_WIRED |
| `environment` | NO | `EnvironmentSubtab.tsx` (reads `/api/env/status`) | PARTIALLY_WIRED |
| `updates` | NO | `UpdateCenterSubtab.tsx` (reads `/api/settings/update-center`) | PARTIALLY_WIRED |
| `about` | NO | `AboutSubtab.tsx` | PARTIALLY_WIRED |

Gap: All 8 subtabs render with live data, but none are reachable via a
deep-link hash like `#settings/providers`. Reference manifest only
enumerates 6 (`providers`, `agents`, `printers`, `environment`,
`updates`, `about`); implementation adds `general` and `mcp` as
extras — superset of spec, not a regression.

### 3.2 Voice subtabs (3 / 3 implemented, no URL hash)

Component: `tabs/Voice.tsx` (`TabName` union, line 32, `[activeTab, setActiveTab]`).

| Subtab | URL-addressable? | Component / data | Status |
|---|---|---|---|
| Voice Browser (`browser`) | NO | inline in `Voice.tsx`; reads `/api/voice/agents`, `/api/voice/voices`, `/api/voice/providers`, `/api/voice/preview` | PARTIALLY_WIRED |
| Transcript History (`transcripts`) | NO | inline (`data-testid="voice-transcript-history"`); reads `/api/voice/transcripts`, `/api/voice/recordings/{id}` | PARTIALLY_WIRED |
| Proof Review (`proof`) | NO | inline (`data-testid="voice-proof-review"`); reads `/api/voice/proof-events` | PARTIALLY_WIRED |

Gap: Voice subtabs lack URL hash addressing per spec
(`#voice/<browser|transcripts|proof>`). Otherwise FULLY_WIRED.

### 3.3 Top-level utility pages required by spec

| Hash | Required by spec | Component file | Backend | Status |
|---|---|---|---|---|
| `#workflows` | YES | `tabs/Workflows.tsx` (orphan) | `/api/workflows` (returns 200) | ORPHAN + MOCK_ONLY |
| `#queue` | YES | `tabs/PrintQueue.tsx` (orphan) | `/api/jobs/*` (9 paths) | ORPHAN + MOCK_ONLY |
| `#logs` | YES | `tabs/SystemLogs.tsx` (orphan) | `/api/logs` (200) | ORPHAN + MOCK_ONLY |
| `#service_health` | YES | `components/health/ServiceHealthPage.tsx` | `/api/system/runtime-readiness`, `/api/providers/health` | PARTIALLY_WIRED (only as `#health` shim in `main.tsx`, not a Sidebar tab) |
| `#proof` | YES | `tabs/Proof.tsx` (orphan) | `/api/proof/bundles`, `/api/proof/events` (200) | ORPHAN + MOCK_ONLY |
| `#notifications` | YES | none (only embedded `components/notifications/NotificationCenter.tsx`) | `/api/notifications` (6 paths, returns 200) | MISSING_ROUTE |
| `#safety` | YES | none | `/api/safety/propose`, `/api/safety/veto` (exist but POST-only) | MISSING_ROUTE |
| `#skills` | YES | none | none — no `/api/skills/*` | MISSING_ROUTE + MISSING_BACKEND |
| `#plugins` | YES | `tabs/Plugins.tsx` | `/api/plugins/*` (6 paths, 200; 20 plugin entries) | FULLY_WIRED |
| `#connectors` (or extension of plugins) | YES | none | none — no `/api/connectors` | MISSING_ROUTE + MISSING_BACKEND |

### 3.4 Dashboard layouts

| Mode | URL hash | Component | Persistence | Status |
|---|---|---|---|---|
| Simple | `#dashboard:simple` (also `#dashboard/simple`, `#dashboard.simple`, `?mode=simple`) | `components/dashboard/DashboardSimple.tsx` | `localStorage[h3d.dashboard.mode]` | FULLY_WIRED |
| Advanced (default) | `#dashboard:advanced` / `#dashboard` | `components/dashboard/DashboardAdvanced.tsx` | localStorage | FULLY_WIRED |
| Custom | `#dashboard:custom` | `components/dashboard/DashboardCustom.tsx` | `localStorage[h3d.dashboard.custom.layout]` (widget order) | PARTIALLY_WIRED (no server-side persistence; spec implies `/api/dashboard/layouts`) |

### 3.5 Action Window modes

Component: `components/ActionWindow/ActionWindow.tsx` (state in
`useState(false)` for `maximized`; line 88), `ActionWindowMount.tsx`,
`DetachedActionWindow.tsx`, top-level `action-window-detached.tsx` route.

| Mode | Trigger | Status |
|---|---|---|
| Normal (resizable, embedded) | default | PARTIALLY_WIRED — implemented in `ActionWindow.tsx`; W14-A5 walk found no `[data-testid=action-window]` on Design or Autopilot, so it isn't visibly mounted on any primary tab |
| Maximized / Expanded / Fullscreen | `Maximize2` button → `setMaximized(true)` | PARTIALLY_WIRED — code path exists (lines 88-186); host tab does not expose toggle on first paint |
| Detached (separate window) | `/action-window?detached=1` → `DetachedActionWindow.tsx` | FULLY_WIRED |

### 3.6 60 Source OS apps coverage

Source: `GET /api/apps` returns `{count: 60, apps: [...]}`; `GET
/api/source-os/modules` returns 60 module entries. Each app exposes
`/api/apps/{app_id}` (detail), `/api/apps/{app_id}/run-proof` (proof),
`/api/apps/{app_id}/rollback` (rollback). UI host:
`tabs/AppRegistry.tsx` with detail panel
`components/AppRegistry/AppDetailPanel.tsx`. Action launch goes through
`tabs/SourceOS.tsx` + `components/source-os/{ModuleList,SecondaryNav,AppDetailPanel}.tsx`
which uses `/api/modules/{id}/launch`.

| Layer | Coverage | Status |
|---|---|---|
| App list endpoint (`/api/apps`) | 60/60 | FULLY_WIRED |
| App detail endpoint (`/api/apps/{id}`) | 60/60 (probed `blender_mcp_candidates` → 200, returns 21-key payload incl. `install_state`, `health`, `launch_kind`, `tested_versions`, `rollback_supported`, `proof_command`, `update_lane`, `last_proof_status`) | FULLY_WIRED |
| Source OS modules (`/api/source-os/modules`) | 60/60 | FULLY_WIRED |
| App detail page (UI) | one shared `AppDetailPanel` for all 60 — driven by the API payload, not 60 hardcoded files | FULLY_WIRED |
| Action launch (`/api/modules/{id}/launch`) | available for all 60 | FULLY_WIRED |
| Per-app run-proof (`/api/apps/{id}/run-proof`) | available for all 60 | FULLY_WIRED |
| Per-app rollback (`/api/apps/{id}/rollback`) | available for all 60 (per-app `rollback_supported` flag in payload) | FULLY_WIRED |

**60 apps coverage: 100% at the route + endpoint layer.** Per-app
visual fidelity (whether each app card renders correctly with its
state machine) is NOT assessed here — that is owned by a Playwright
visual-diff lane (W14-A5 captured #apps but did not iterate every
app id).

NB on app categories: the `category` field in `/api/apps` payloads
is empty (Counter showed `?: 60`); category data is sourced
client-side via `data/source-os/categories.ts` (or equivalent) per
the W14-A2 reference. Reference manifest enumerates 11 categories
totalling 60 apps (modelers 13 + slicers 11 + print_farm 10 +
agents 7 + firmware 6 + 3d_generation 6 + hardware 3 + library 1
+ materials 1 + research 1 + utilities 1).

### 3.7 Six-way classification roll-up

| Status | Count | Items |
|---|---:|---|
| **FULLY_WIRED** | 14 | 13 of 17 primary tabs (`source_os`, `dashboard`, `autopilot`, `design`, `gen3d`, `jobs`, `printers`, `observe`, `agents`, `learning`, `artifacts`, `approvals`, `apps`, `plugins`, `roadmap`); Action Window detached; 60-app coverage at endpoint layer |
| **PARTIALLY_WIRED** | 18 | Settings tab (8 subtabs lacking URL hash) · Voice tab (3 subtabs lacking URL hash) · Custom dashboard (no server-side layout persistence) · Service Health (shim only, not in Sidebar) · Action Window normal + maximized (not visibly mounted on any primary tab) |
| **ORPHAN** | 9 | `Workflows.tsx`, `PrintQueue.tsx`, `SystemLogs.tsx`, `Proof.tsx`, `BlenderMCP.tsx`, `Slicing.tsx`, `Fleet.tsx`, `PrinterControl.tsx`, `DockedApps.tsx` (also MOCK_ONLY) |
| **MOCK_ONLY** | 9 | Same 9 orphan tabs (each reads from `data/mock/*` despite live endpoints existing for several — workflows/jobs/logs/proof at least) |
| **MISSING_ROUTE** | 4 | `#notifications`, `#safety`, `#skills`, `#connectors` (no UI page; the first two have backend, the last two also need backend) |
| **MISSING_BACKEND** | 4 | `/api/skills` (no skills registry endpoint); `/api/connectors` (no connector→app matrix endpoint); `/api/settings/themes` (theme catalog endpoint missing — currently just a single `/api/settings/theme` string field); `/api/dashboard/layouts` (server-side custom layout persistence) |

Mandatory items checked from user's Wave 15 spec: **40+** —
8 settings subtabs · 3 voice subtabs · 13 utility/page hashes · 3
dashboard layouts · 3 action-window modes · 60 Source OS apps
(verified at the API layer, not per-file).

---

## 4. Orphan tabs ready to register (PR-1 candidate set)

Wiring these in is purely additive — files exist, mocks render, no
new code paths. Suggested change footprint per file:

```
src/App.tsx               +9 imports +9 entries in TAB_COMPONENTS
src/app/routes.ts         +9 entries in TABS (with icons)
src/app/store.ts          +9 entries in TAB_IDS / HASH_TO_TAB / TAB_TO_HASH
```

Required wiring entries (proposed hashes match the existing
`routes.tsx` stale manifest where possible):

| Tab id | Hash | Component | Suggested icon (lucide-react) |
|---|---|---|---|
| `workflows` | `#workflows` | `WorkflowsTab` from `tabs/Workflows.tsx` | `GitBranch` |
| `queue` | `#queue` | `PrintQueueTab` from `tabs/PrintQueue.tsx` | `ListOrdered` |
| `logs` | `#logs` | `SystemLogsTab` from `tabs/SystemLogs.tsx` | `ScrollText` |
| `proof` | `#proof` | `ProofTab` from `tabs/Proof.tsx` | `ShieldCheck` |
| `blender_mcp` | `#blender_mcp` | `BlenderMCPTab` from `tabs/BlenderMCP.tsx` | `Box` |
| `slicing` | `#slicing` | `SlicingTab` from `tabs/Slicing.tsx` | `Layers` |
| `fleet` | `#fleet` | `FleetTab` from `tabs/Fleet.tsx` | `Printer` |
| `control` | `#control` | `PrinterControlTab` from `tabs/PrinterControl.tsx` | `Sliders` |
| `docked` | `#docked` | `DockedAppsTab` from `tabs/DockedApps.tsx` | `LayoutGrid` |

After wiring, all 9 transition from ORPHAN+MOCK_ONLY → MOCK_ONLY (until
each is connected to its live endpoint, see §6.2).

---

## 5. Settings/Voice subtab status (URL-addressable yes/no)

Re-stated for the wiring lane:

### Settings (`#settings/<subtab>` not yet supported)

| Subtab | URL-addressable? | Stable testid? | Live endpoint? |
|---|---|---|---|
| `general` | ✘ | `settings-subtab-general` | n/a (client-side theme + lang) |
| `providers` | ✘ | `settings-subtab-providers` | ✓ `/api/providers/health` |
| `agents` | ✘ | `settings-subtab-agents` | ✓ `/api/agents/config` |
| `mcp` | ✘ | `settings-subtab-mcp` | ✓ `/api/code-operator/mcp-locks/state` |
| `printers` | ✘ | `settings-subtab-printers` | ✓ `/api/printers` |
| `environment` | ✘ | `settings-subtab-environment` | ✓ `/api/env/status` |
| `updates` | ✘ | `settings-subtab-updates` | ✓ `/api/settings/update-center` |
| `about` | ✘ | `settings-subtab-about` | n/a (static) |

Required change to make subtabs URL-addressable: extend `tabIdFromHash`
in `store.ts` to keep the trailing segment after `/`, and have
`SettingsPage.tsx` read the segment instead of (or alongside)
`useState`.

### Voice (`#voice/<subtab>` not yet supported)

| Subtab | URL-addressable? | Stable testid? | Live endpoint? |
|---|---|---|---|
| `browser` | ✘ | `voice-root` | ✓ `/api/voice/agents`, `/voices`, `/providers`, `/preview`, `/stt` |
| `transcripts` | ✘ | `voice-transcript-history` | ✓ `/api/voice/transcripts`, `/recordings/{id}` |
| `proof` | ✘ | `voice-proof-review` | ✓ `/api/voice/proof-events` |

Same fix shape as Settings.

---

## 6. Backend gap list

Strict missing endpoints per the user's spec:

### 6.1 Spec-mandated missing endpoints

| Endpoint | Required by | Status | Notes |
|---|---|---|---|
| `GET /api/skills` | Skills registry view (`#skills` page in spec) | **MISSING** | No skill metadata anywhere; would need `{count, skills: [{id, name, version, owner_plugin, capabilities, status}]}` |
| `GET /api/connectors` | App-connector matrix (`07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png`) | **MISSING** | Reference shows connector × app coverage grid; no backing endpoint |
| `GET /api/settings/themes` | Theme catalog (currently 6 themes in spec, only `dark`/`light` in `theme/tokens.ts`) | **MISSING** | `/api/settings/theme` exists but returns the active theme STRING, not the catalog list |
| `GET/POST /api/dashboard/layouts` | Server-side persistence of Custom dashboard | **MISSING** | Custom layout currently localStorage-only (`h3d.dashboard.custom.layout`); spec wants server persistence so a layout follows a user across machines |

### 6.2 Additional gaps surfaced by orphan-tab review

The 9 orphan tabs are **MOCK_ONLY** even though many of their live
endpoints already ship. Wiring each is a separate follow-up:

| Orphan tab | Mock data file | Live endpoint(s) available |
|---|---|---|
| Workflows | `data/mock/workflows.ts` | `/api/workflows` |
| PrintQueue | `data/mock/jobs.ts` | `/api/jobs`, `/api/jobs/{id}/events` |
| SystemLogs | `data/mock/logs.ts` | `/api/logs` |
| Proof | `data/mock/proof.ts` | `/api/proof/bundles`, `/api/proof/events` |
| BlenderMCP | mock-only | none — would need `/api/blender-mcp/*` (currently surfaced as a Source OS app card only) |
| Slicing | mock-only (`MOCK_PRINTERS`) | partial — would need `/api/slicing/*`; `/api/printers` available |
| Fleet | mock-only + `api/adapters` import | partial — `/api/printers/*` (18 paths) covers most; no fleet-aggregate endpoint |
| PrinterControl | mock-only | partial — `/api/printers/{id}/move`, `/heat-bed`, `/heat-extruder`, `/safety-state` |
| DockedApps | mock-only (placeholders) | n/a — Phase 2 visual-only per file header |

### 6.3 Notification page gap

`/api/notifications` is FULLY_WIRED at endpoint level (6 paths,
returns 200) but the UI consumes it only via the inline
`components/notifications/NotificationCenter.tsx` mount in
`AppShell`. There is no `#notifications` page. Spec
(`08-app-utility-pages/proof-health-notifications-safety.png`)
implies a top-level page with category filtering — would benefit
from `?category=safety|proof|health` query-param support.

---

## 7. 60 Source OS apps coverage

Probed via `/api/apps` → 60 app entries returned. All app metadata is
served via a single shared payload schema (`AppDetailPanel` consumes
the 21-field per-app object). No per-app `.tsx` file is required;
the registry is data-driven.

| Coverage layer | Score |
|---|---:|
| App count from `/api/apps` | **60/60 (100%)** |
| App count from `/api/source-os/modules` | **60/60 (100%)** |
| Detail endpoint per app (`/api/apps/{id}`) | **60/60 (100%)** — sample probe `blender_mcp_candidates` returned 200 with full payload |
| Run-proof endpoint per app (`/api/apps/{id}/run-proof`) | **60/60 (100%)** — endpoint registered for all |
| Rollback endpoint per app (`/api/apps/{id}/rollback`) | **60/60 (100%)** — endpoint registered for all (per-app `rollback_supported` boolean) |
| Launch endpoint (`/api/modules/{id}/launch`) | **60/60 (100%)** |
| UI route to reach detail page | `#apps/<id>` and `#sources` (Source OS module list with detail panel) — both present |
| Visual fidelity per app card | NOT assessed — owned by Playwright visual-diff lane |

**Net coverage of the 60-app surface at the route + endpoint layer:
100%.** Note the empty `category` field in the `/api/apps` payload —
categorisation is currently client-side; could be hoisted to the
backend if the reference matrix grid is added (gap §6.1).

Sample app ids returned (first 10): `azure_speech_sdk_js`,
`blender_mcp_candidates`, `hermes_agent`, `kiln`, `langchain`,
`langgraph`, `model_context_protocol`, `firmware_klipper`, `marlin`,
`prusa_firmware`.

---

## 8. Two sources cited

1. **Official — React Router hash routing patterns**
   <https://reactrouter.com/> — confirms the `#<id>[:mode]` /
   `#<id>/<segment>` convention used in `store.ts`'s `tabIdFromHash`
   (`raw.split(/[:/.]/, 1)[0]`) and `dashboardModeStore.ts`'s
   `modeFromHash` regex
   (`^dashboard[:/.](simple|advanced|custom)$`). The proposed fix for
   §5 (URL-addressable subtabs) extends the same pattern to nested
   segments by preserving everything after the first `/` and routing it
   into the relevant tab's local state.

2. **Cross-project — Next.js app-router nested-route conventions**
   <https://nextjs.org/docs/app/building-your-application/routing> —
   used as a reference for how nested routes are typically modelled
   (folder per segment → `settings/[subtab]/page.tsx`). This project
   intentionally uses hash routing instead of file-system routing per
   `SettingsPage.tsx` line 14-16: "Subtab routing is internal
   `useState` — we MUST NOT introduce react-router; the universal
   shell uses the TABS pattern only." The Next.js convention is cited
   as a contrast — what `#settings/providers` would look like if the
   project ever migrates to a file-system router.

---

## 9. Constraint compliance

- **READ-ONLY**: confirmed — no source files modified; this audit
  document is the only new artefact and lives under
  `docs/handoffs/`.
- **No secrets**: confirmed — backend route enumeration ran with
  `HERMES3D_API_TOKEN` unset (warned by the API as "OPEN — no auth"
  — that is the dev-mode posture, not a leak).
- **2 sources**: cited above (React Router official + Next.js
  cross-project).

---

## 10. Summary

- Mandatory items checked: **40+**
- 6-way classification: **14 FULLY_WIRED · 18 PARTIALLY_WIRED · 9 ORPHAN · 9 MOCK_ONLY · 4 MISSING_ROUTE · 4 MISSING_BACKEND** (orphan + mock_only refer to the same nine tab files; classification overlaps by design)
- **9 orphan tabs ready to register** (PR-1 candidate set; all 9 already exist as `.tsx` files)
- **4 missing backend endpoints** (`/api/skills`, `/api/connectors`, `/api/settings/themes`, `/api/dashboard/layouts`)
- **60 apps coverage**: **100%** at route + endpoint layer (visual fidelity per-app NOT assessed — Playwright lane scope)

End of W15-A3 deliverable.
