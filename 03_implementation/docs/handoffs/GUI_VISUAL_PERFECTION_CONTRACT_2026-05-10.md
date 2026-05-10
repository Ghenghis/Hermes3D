# GUI Visual-Perfection Contract (2026-05-10)

**Owner:** `claude-w14-a6-integrator`
**Wave:** 14 / Agent 6 (Contract Integrator)
**Mode:** READ-ONLY synthesis (doc-only). No source/test edits in this lane.
**Predecessors (inputs synthesized):** W14-A1 Reference Inventory, W14-A2 Route/Feature Matrix, W14-A3 Visual Oracle Design, W14-A4 Design Token Audit, W14-A5 Page Gap Audit. PR #128 (Images-GUI pack) is the immutable visual baseline.
**Lock:** Hermes3D MCP — owner `claude-w14-a6-integrator`, ttlMinutes 60, taskId `w14-a6-contract-integrator`.
**Two sources cited (per task spec):** see Section 10.

This document is the canonical, mergeable contract that the next 8 PRs (PR 1 through PR 8) implement against. Implementation lanes MUST treat this as the single source of truth; any deviation requires a written addendum in `03_implementation/docs/handoffs/`.

---

## 1. Reference Inventory (per W14-A1)

PR #128 delivered 31 PNG references organised into 10 sub-folders. The Images-GUI pack is **non-overwriteable**: re-capture is forbidden in this contract; viewport is normalised on the harness side instead (see Section 3 and W8-15 contract).

### 1.1 Sub-folder count (verbatim from W14-A1)

| Folder | Count | Purpose |
|---|---:|---|
| `00-user-current-downloads/` | 10 | User-provided/current approved references |
| `01-dashboard-modes/` | 6 | Simple, Advanced, Custom dashboard mode references |
| `02-primary-pages/` | 3 | Primary tab references (composite, 4 tabs per PNG) |
| `03-settings-voice/` | 2 | Settings + voice/communication subtabs (composites) |
| `04-source-os/` | 3 | Source OS categories + 60-app coverage matrix |
| `05-action-windows/` | 2 | Resizable Action Window templates |
| `06-states-responsive/` | 1 | Responsive layouts and state screens |
| `07-plugins-skills-mcp/` | 1 | Plugins, skills, MCP servers, app connectors |
| `08-app-utility-pages/` | 2 | Workflows, queue, files, logs, proof, health, notifications, safety |
| `09-themes/` | 1 | Theme variants (default/cyberpunk/matrix/tron/forge/aurora) |
| **TOTAL** | **31** | matches `total_png_references` in `Images-GUI/GUI_REFERENCE_MANIFEST.json` |

### 1.2 Collage classification (15 PNGs require crop maps)

Single-image PNGs cannot be diffed against a single route when they pack multiple states or tabs into one canvas. Per A1, **15 of 31 PNGs are collages** spanning ~115 distinct UI states. The crop map for each is mandatory before that target can move from `status: "future"` to `status: "live"` in `visual-targets.json`. The 15 collage targets are: `02-primary-pages/*` (3 PNGs, 4 tabs each), `03-settings-voice/*` (2, 6 + 3 subtabs), `04-source-os/*` (3, ~71 cells in aggregate), `05-action-windows/*` (2, 4-6 templates each), `06-states-responsive/states-responsive-reference.png` (1), `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` (1), `08-app-utility-pages/*` (2, 4 surfaces each), `09-themes/theme-variants-reference.png` (1).

The remaining 16 PNGs are single-state or direction references: 6 dashboard state-variants in `01-dashboard-modes/`, the user-baseline `Hermes3D.png`, and 9 `Generated image *.png` direction PNGs.

### 1.3 Dimension outliers (6 PNGs, 2 distinct shapes)

Reference baseline (per W8-15 / `playwright.visual.config.ts`) is **1536x1024**. 26 of 31 PNGs match. The 6 outliers and the rule for handling them:

| # | PNG | Dims | Disposition under this contract |
|---:|---|---|---|
| 1 | `04-source-os/source-os-60-app-coverage-matrix.png` | 1672x941 | Per-image viewport override (live target) |
| 2 | `04-source-os/source-os-remaining-categories.png` | 1586x992 | Per-image viewport override (live target) |
| 3 | `01-dashboard-modes/simple-dashboard-a.png` | 1672x941 | Per-image viewport override (future) |
| 4 | `01-dashboard-modes/simple-dashboard-b.png` | 1672x941 | Per-image viewport override (future) |
| 5 | `00-user-current-downloads/Generated image 1.png` | 1672x941 | Per-image viewport override (future, direction-only) |
| 6 | `00-user-current-downloads/Generated image 2.png` | 1672x941 | Per-image viewport override (future, direction-only) |

**Rule (locked):** outliers are normalised by per-image `viewport: {width,height}` in `visual-targets.json`. **Re-capture of any Images-GUI PNG is prohibited** unless the user signs an explicit recapture authorisation; W8-15 Option B remains vetoed. PR 1 implements per-image viewports as a typed manifest field.

### 1.4 Manifest reconciliation

A1 confirmed zero drift between `Images-GUI/GUI_REFERENCE_MANIFEST.json`, the filesystem, and `visual-targets.json`: 31 PNGs declared, 31 on disk, 31 targets in the manifest with status `live` (11) or `future` (20). No orphan PNGs, no missing targets.

---

## 2. Route Mapping (per W14-A2)

### 2.1 Route-to-reference matrix summary

A2 walked the 31 PNGs against `routes.ts` (the live 17-tab router) and the FastAPI surface (213 handler paths). Verdict: **25 EXISTS / 6 PARTIAL / 0 MISSING**. Live hash routes total 17 tabs + 1 shim (`#health`). A stale `app/routes.tsx` (14-entry pre-W6 list) is unconsumed and will be deleted under this contract.

The 6 PARTIAL entries (each requires a wiring fix, listed in 2.2):

| Reference image | Why PARTIAL |
|---|---|
| `03-settings-voice/settings-subtabs-all.png` | Subtabs lack URL hash; 8 implemented vs 6 in spec (superset) |
| `03-settings-voice/voice-communication-subtabs.png` | Subtabs lack URL hash |
| `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | No `/api/skills`, no top-level `#mcp`, no skills component |
| `08-app-utility-pages/workflow-printqueue-files-logs.png` | Workflows/PrintQueue/SystemLogs orphans (files exist, no route) |
| `08-app-utility-pages/proof-health-notifications-safety.png` | `#health` shim only; `#proof`/`#notifications`/`#safety` unrouted |
| `09-themes/theme-variants-reference.png` | Only dark/light in `tokens.ts`; 4 themes missing |

### 2.2 Missing-route / orphan-component list (verbatim from A2 §4)

| Gap | Required hash route | Required component | Backend exists? |
|---|---|---|---|
| Settings subtab not URL-addressable | `#settings/<subtab>` | extend `SettingsPage.tsx`, `tabIdFromHash` | yes (8 endpoints) |
| Voice subtab not URL-addressable | `#voice/<browser\|transcripts\|proof>` | extend `tabs/Voice.tsx` | yes (9 endpoints) |
| Workflows orphan | `#workflows` | register `tabs/Workflows.tsx` | yes (`/api/workflows`) |
| Print queue orphan | `#queue` | register `tabs/PrintQueue.tsx` (or fold into `#jobs`) | yes (`/api/jobs`) |
| System logs orphan | `#logs` | register `tabs/SystemLogs.tsx` | yes (`/api/logs`) |
| Service Health is shim | `#service_health` | promote `ServiceHealthPage.tsx` to tab | yes |
| Proof orphan | `#proof` | register `tabs/Proof.tsx` | yes (`/api/proof/*`) |
| Notifications inline only | `#notifications` | promote `NotificationCenter.tsx` | yes (7 endpoints) |
| Safety has no UI | `#safety` | new component bound to `/api/safety/*` | yes |
| Skills registry has no UI | `#skills` (or under `#plugins`) | new component | partial — needs `/api/skills` |
| Themes beyond dark/light | n/a (within `#settings/general`) | extend `theme/tokens.ts` with 4 palettes | n/a |
| Pre-W6 router stale | n/a | delete `app/routes.tsx` (14-tab) | n/a |

### 2.3 Backend gap list (verbatim from A2 §5)

The reference pack implies four endpoints that are not currently in the FastAPI handler list:

1. `/api/skills` — skills registry list + per-skill metadata (for `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png`)
2. `/api/connectors` — connector → app coverage matrix (for the same reference)
3. `/api/settings/themes` — list of available palette ids (today only `/api/settings/theme` accepts a single string field)
4. `/api/dashboard/layouts` — optional server-side persistence of custom dashboard layout (today only `localStorage[h3d.dashboard.custom.layout]`)

Plus a clarification, not strictly missing: `/api/notifications` accepts category-filter query params at runtime, but the route-table reflection does not surface that. A2 also flagged `/api/notifications/stream` exists but a category-filtered variant should be exposed for the Notifications utility page surface.

---

## 3. Visual Oracle Specification (per W14-A3)

A3 specifies the harness extensions that turn pixel parity into a runtime-truth gate. PR 1 lands all 8 files in a single change.

### 3.1 Five required extensions (verbatim from A3 §2)

1. **Exact viewport per reference.** Manifest entries gain `viewport: {width,height}` derived from the reference PNG IHDR. Config emits one Playwright project per unique `(width,height)` pair (3 expected: 1536x1024, 1672x941, 1586x992). Per-test `test.use({ viewport })` pulls from the manifest entry.
2. **Crop region map for collages.** A target may include `regions: [{name, route, wait_test_id, clip:{x,y,width,height}}]`. The spec loops over each region, navigates `region.route`, asserts `expect(page).toHaveScreenshot([..., \`${target}__${region.name}\`], { clip })`. The reference is split-by-clip on first run.
3. **Console error fail.** Visual suite imports `attachErrorCapture` with `allowList: []` (no offline carve-outs). `assertNoErrors(page)` runs in `afterEach`. Backend-down state is a harness misconfig, not an acceptable visual outcome.
4. **Network-404 fail.** New helper `network-404-tracker.ts` hooks `page.on("response", r => r.status()===404 && capture(...))`. Same-origin only by default; cross-origin opt-in via empty `allowedHosts: []` in the manifest entry.
5. **No-fake DOM scan.** New helper `no-fake-scanner.ts` evaluates `document.body.innerText` against the existing 9-token `FORBIDDEN_VISIBLE_TERMS` plus visual markers (`mockData`, `__test_`, `lorem ipsum`, `placeholder`, `Coming Soon`) and `[data-mock]/[data-fixture]/[data-placeholder]` selectors. Any hit fails with the marker, the closest `data-testid` ancestor, and the offending innerText snippet.

### 3.2 Deterministic environment recipe (verbatim from A3 §6)

Applied at the start of every test in `_visual-helpers.ts::primeDeterministic(page, target)`:

1. **Clock.** `page.clock.install({ time: target.deterministic?.clock_iso ?? "2026-05-10T12:00:00Z" })` then `page.clock.pauseAt(...)`.
2. **Theme.** `page.addInitScript(() => { localStorage.setItem("hermes3d.theme", "light"); document.documentElement.dataset.theme = "light"; })`.
3. **Animations.** `expect.toHaveScreenshot.animations: "disabled"` + `prefers-reduced-motion: reduce` emulation.
4. **Fonts.** `await page.evaluate(() => document.fonts.ready)` after `wait_test_id` mounts.
5. **Data stubs.** Per-target `deterministic.data_stubs[]` registers `page.route(url_glob, fulfill from fixture)` BEFORE `page.goto`. Fixtures committed under `tests/visual/__fixtures__/<target>.canon.json`.
6. **Network-404 tracker** installed before first navigation, surviving SPA route changes.
7. **Console capture** installed before navigation, strict empty allow-list.
8. **No-fake scan** runs once at `afterEach` after the screenshot assertion.

The recipe is idempotent — the same target run twice in the same CI minute produces a byte-identical `actual.png` on a known-good build.

### 3.3 PR 1 file list (verbatim from A3 §3 — 8 files / ~780 LoC)

| # | File | New / Edit | LoC est. |
|---|---|---|---|
| 1 | `03_implementation/ui/playwright.visual.config.ts` | EDIT (rewrite) | ~140 |
| 2 | `03_implementation/ui/tests/visual/visual-targets.json` | EDIT (+90) | ~+90 |
| 3 | `03_implementation/ui/tests/visual/visual-proof.spec.ts` | EDIT (rewrite) | ~210 |
| 4 | `03_implementation/ui/tests/visual/visual-proof-reporter.ts` | EDIT (+80) | ~+80 |
| 5 | `03_implementation/ui/tests/visual/no-fake-scanner.ts` | NEW | ~70 |
| 6 | `03_implementation/ui/tests/visual/network-404-tracker.ts` | NEW | ~60 |
| 7 | `03_implementation/ui/tests/visual/_visual-helpers.ts` | NEW | ~90 |
| 8 | `03_implementation/ui/tests/visual/visual-targets.schema.json` | EDIT (+40) | ~+40 |

Total: 3 NEW + 5 EDIT, ~780 LoC (≈430 net-new + ~350 in rewrites/diffs).

---

## 4. Missing Components and Endpoints (synthesis of A2 + A5)

Synthesising A2's route gaps and A5's runtime walk yields a single canonical list of work for the wiring lanes (PR 5 and PR 7).

### 4.1 Nine orphan tab files to register

A5's runtime walk found 9 `.tsx` files on disk in `03_implementation/ui/src/tabs/` that are not in `App.tsx`'s `TAB_COMPONENTS`, `store.ts`'s `TAB_IDS`, or the `HASH_TO_TAB` / `TAB_TO_HASH` maps. They 404 via `UnavailableTab` placeholder today.

| Hash | Source file | Lands in PR |
|---|---|---|
| `#workflows` | `tabs/Workflows.tsx` | PR 5 |
| `#queue` | `tabs/PrintQueue.tsx` | PR 5 |
| `#logs` | `tabs/SystemLogs.tsx` | PR 5 |
| `#proof` | `tabs/Proof.tsx` | PR 5 |
| `#blender_mcp` | `tabs/BlenderMCP.tsx` | PR 5 |
| `#slicing` | `tabs/Slicing.tsx` | PR 5 |
| `#fleet` | `tabs/Fleet.tsx` | PR 5 |
| `#control` | `tabs/PrinterControl.tsx` | PR 5 |
| `#docked` | `tabs/DockedApps.tsx` | PR 5 |

### 4.2 Three missing source files to scaffold

A5 confirmed no source file exists for these utility surfaces. PR 7 creates minimal panels backed by the relevant adapters.

| Hash | New file | Backend |
|---|---|---|
| `#files` | `tabs/Files.tsx` | `/api/artifacts`, `/api/artifacts/list` (artifact browser) |
| `#safety` | `tabs/Safety.tsx` | `/api/safety/*`, `/api/printers/{id}/safety-state`, `/api/printers/{id}/safety-events/*` |
| `#notifications` | `tabs/Notifications.tsx` | `/api/notifications`, `/api/notifications/stream` (promotes `NotificationCenter.tsx` to a top-level page) |

### 4.3 Four missing backend endpoints

The four endpoints implied by the reference pack but absent from the 213-route handler table:

| Endpoint | Reference | Implements in PR | Defer condition |
|---|---|---|---|
| `/api/skills` | `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` | PR 5 (lands with `#skills` UI) | Defer if skills source-of-truth is still under design — annotate in `visual-targets.json` `notes` |
| `/api/connectors` | same | PR 5 | Defer if connector matrix is fully derivable from `/api/apps`+`/api/plugins` (then collapse the spec) |
| `/api/settings/themes` | `09-themes/theme-variants-reference.png` | PR 2 (token system delivers the catalog) | Cannot defer — needed for theme-picker round-trip |
| `/api/dashboard/layouts` | `01-dashboard-modes/custom-dashboard-*.png` | PR 3 | Defer permitted: localStorage-only keep is acceptable for v0.x; deferral must be annotated with rationale in `visual-targets.json` |

### 4.4 Action Window — three states

A5 walk classified Action Window as 1 EXISTS (detached) / 2 PARTIALLY_EXISTS (embedded, maximized).

| State | Today | PR 7 deliverable |
|---|---|---|
| Detached | `/action-window?detached=1` mounts `DetachedActionWindow.tsx`, EXISTS | Capture maintained |
| Embedded | `ActionWindow.tsx` exists but no host tab mounts it on first paint | Mount embedded ActionWindow on `#design` (default host) with `data-testid="action-window"` on root |
| Maximized | `[maximized, setMaximized]` state code path exists; no host exposes the toggle | Maximize2 toggle visible from embedded host; capture state via `data-testid="action-window-maximized"` |

---

## 5. PR Order (8 PRs, locked)

The 8-PR sequence below is the only authorised path from `main` to `GUI_VISUAL_E2E_GREEN`. Each PR ships one Hermes evidence chain (`hermes_run_gate` PASS) plus a green truth-gate proof. Any reorder requires a written addendum.

### PR 1 — Visual Oracle Harness (A3's design)

Scope: implement the 8 files in §3.3. Adds the 5 extensions (per-image viewport, crop regions, console-error fail, network-404 fail, no-fake scan) and the deterministic environment recipe (clock, theme, animations, fonts, data stubs). All 31 targets become introspectable; 11 `live` targets gate the suite, 20 `future` targets remain `skipped-future`. Boot-time check fails fast on viewport/reference dim mismatch.
Gate: `npx playwright test --config tests/visual` passes; new statuses `console-error`, `network-404`, `fake-hit`, `region-diff` round-trip into `summary.json`.

### PR 2 — Shell + Token System (A4's deltas)

Scope: apply the A4 token deltas. Decision-record the **primary hue question** (cyan `#22d3ee` vs blue `#3b80f4`) — recommended path: keep cyan for v0.x, file `IMAGES_GUI_RECAPTURE_PRIMARY_HUE` task for the v1 brand revisit. Implement the low-risk shifts: `--h3d-color-background` `#0a0e1a` → `#000c14`, `--h3d-color-surface` `#0f1626` → `#01101a`, `--h3d-color-surface-2` `#141d33` → `#001420`, `--h3d-color-border` `#1f2a44` → `#19232e`. Sidebar default width `260` → `200`. `borderRadius.card` `8px` → `6px`. WCAG ≥ 4.5:1 re-checked for every fg/bg pair (lower bg + same fg → contrast improves). Theme catalog (4 missing palettes — `cyberpunk`, `matrix`, `tron`, `industrial_forge`, `aurora_operator`) lands here so `/api/settings/themes` has data; component-side `ThemeSwitcher` reads them.
Gate: visual oracle 11 live targets remain green or improve; console errors = 0; no-fake scan = 0.

### PR 3 — Dashboard Modes (existing W6-3 Simple/Advanced/Custom)

Scope: verify visual targets for `#dashboard:simple`, `#dashboard:advanced`, `#dashboard:custom`. A5 confirmed all three EXIST. Promote the 4 dashboard mode futures (`01_dashboard_simple_a/b`, `01_dashboard_custom_a/b`) to `live` once `wait_test_id` is wired; advanced is already live. Custom dashboard layout persistence: implement `/api/dashboard/layouts` OR formally defer (annotate `visual-targets.json`).
Gate: 6 dashboard targets all `match` at 0% diff (or approved tolerance with rationale).

### PR 4 — Source OS + 60 Apps

Scope: preserve 60/60 app coverage in `#sources` and `#apps[/<id>]`. Wire crop regions for the three Source OS collages (`source-os-core-categories.png`, `source-os-remaining-categories.png`, `source-os-60-app-coverage-matrix.png`). App detail panel and action launch path are exercised via the visual suite. The two known viewport outliers (1672x941, 1586x992) use the per-image override from PR 1.
Gate: 3 source-os targets `match` at 0% diff at their per-image viewport; 60-app crop map covers all 60 cells.

### PR 5 — Primary Tabs (wire 9 orphans)

Scope: register the 9 orphan hashes from §4.1 in `App.tsx::TAB_COMPONENTS`, `store.ts::TAB_IDS`, `HASH_TO_TAB`, `TAB_TO_HASH`. Promote `ServiceHealthPage` from `main.tsx` shim to a registered tab (`#service_health`). Implement `/api/skills` and `/api/connectors` (or document their deferral). Visual match for the three primary collages (`02-primary-pages/*`) at the per-tab crop level; for `07-plugins-skills-mcp/plugins-skills-mcp-app-connectors.png` at the 4-region crop level. Delete stale `app/routes.tsx`.
Gate: 17 + 9 = 26 hashes mount cleanly; 4 collage targets pass crop-region diffs.

### PR 6 — Settings + Voice (reconcile 8 vs 6)

Scope: reconcile the manifest drift A5 found — 8 settings subtabs implemented (`general`, `providers`, `agents`, `mcp`, `printers`, `environment`, `updates`, `about`) vs 6 in the reference (`providers`, `agents`, `printers`, `environment`, `updates`, `about`). Decision: extend the manifest (+ 2 reference PNGs for `general` and `mcp`) under user authorisation, OR fold `mcp` into `general`. Make subtabs URL-addressable (`#settings/<subtab>`, `#voice/<browser|transcripts|proof>`) by extending `tabIdFromHash` and the subtab read paths in `SettingsPage.tsx` and `tabs/Voice.tsx`. Voice 3-region crop map lands.
Gate: settings + voice collage targets pass per-subtab crop diffs; deep-links to subtabs round-trip.

### PR 7 — Action Window + Utility Pages (mount + scaffold 3 missing)

Scope: mount embedded `ActionWindow` on `#design` (default host) with `data-testid="action-window"`; expose Maximize2 toggle on first paint with `data-testid="action-window-maximized"`. Capture all three Action Window states (detached, embedded, maximized) for the two collage targets. Scaffold the 3 missing utility pages from §4.2 (`Files.tsx`, `Safety.tsx`, `Notifications.tsx`), wired to their existing backends. The two `08-app-utility-pages/*` collages get crop maps over their 4 surfaces each.
Gate: Action Window 3-state crop pass; 3 new tabs mount cleanly with no console errors and no fake markers.

### PR 8 — Final Visual E2E (full suite + handoff)

Scope: run the full visual suite end-to-end. All 31 references must be covered by single or crop-region targets. All 11 originally-live targets and any promoted targets must pass at 0% pixel diff (or approved per-target tolerance with `tolerance_rationale`). Generate the W11-1-style proof bundle as `GUI_VISUAL_E2E_COMPLETION_2026-05-10.md` with `summary.json` excerpt, console-error roll-up (must be 0), network-404 roll-up (must be 0 same-origin), no-fake roll-up (must be 0), secret-scan roll-up (must be 0), and a `loops.json` excerpt demonstrating no target stayed in `diff` more than 2 loops.
Gate: `GUI_VISUAL_E2E_GREEN` (see §8 for the formal definition of done).

---

## 6. Acceptance Rules

These rules apply uniformly to PR 1 through PR 8. Any merge that violates any rule is reverted, not patched.

1. **Pixel diff default = 0%.** `tolerance: 0.0` is the default in `visual-targets.json`. Any per-target opt-in up to `max_tolerance: 0.05` (5%) requires an explicit `tolerance_rationale` string (one sentence, dated, signed by reviewer) and the manifest schema enforces non-empty rationale at boot. Anything > 5% must be filed as `IMAGES_GUI_RECAPTURE_<target>` task — not absorbed by the harness.
2. **Console error → fail.** Any `page.on("pageerror")` or `page.on("console","error")` event during the test fails the test. No allow-list. Backend-down is a harness misconfig.
3. **Network 404 (same-origin) → fail.** Cross-origin opt-in via `allowedHosts: []` in the manifest entry only; default empty.
4. **No-fake DOM scan → fail.** Any innerText match against the denylist (`mockData`, `fakeData`, `lorem ipsum`, `placeholder`, `__test_`) or any element matching `[data-mock]/[data-fixture]/[data-placeholder]` fails the test. Hit is reported with marker, closest `data-testid` ancestor, and snippet.
5. **Dim outliers.** Per-image viewport override via the manifest is allowed (no recapture). PNG IHDR vs `target.viewport` is verified at boot; mismatch fails fast before any browser launch.
6. **Collage targets.** A `regions[]` map is REQUIRED before merge of any PR that promotes a collage target from `future` to `live`. Region rectangles must tile the reference (gaps and overlaps are both lint failures).
7. **Reference pack is non-overwriteable.** No PR may modify `Images-GUI/**/*.png` or the manifest without an explicit user authorisation captured as a separate addendum doc.
8. **Hermes lock discipline.** Every PR's contract-touched paths must be lock-acquired before edit and released on merge.

---

## 7. No-Fake / No-Secret Proof Rules

Both scanners run in CI for every PR before merge. Either scanner returning > 0 hits is a hard merge-block.

### 7.1 No-fake DOM scan

Markers (sourced from existing `_helpers.ts::FORBIDDEN_VISIBLE_TERMS` plus visual-specific additions):

- innerText regex (case-insensitive): `mockData`, `fakeData`, `lorem ipsum`, `placeholder`, `__test_`, `Coming Soon`
- attribute selectors: `[data-mock]`, `[data-fixture]`, `[data-placeholder]`

Implementation lives in `tests/visual/no-fake-scanner.ts` (PR 1) and is invoked from every visual test's `afterEach`.

### 7.2 Secret scan (W5-10 regex)

Patterns (case-sensitive; pre-existing W5-10 regex set, repeated here verbatim for the contract):

- `sk-` (OpenAI / Anthropic style)
- `Bearer ` followed by ≥ 30 chars of base-tokenish content
- JWT (`eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+`)
- `AKIA[A-Z0-9]{16}` (AWS access keys)
- `gh[pousr]_[A-Za-z0-9_]{30,}` (GitHub PAT family)

Scanner sweep targets the staged diff plus the rendered DOM at `afterEach`. Any hit blocks the merge and triggers `G:\private\` review.

Both scanners must report 0 hits before any of the 8 PRs is allowed to merge.

---

## 8. Definition of Done — `GUI_VISUAL_E2E_GREEN`

The final gate that PR 8 must satisfy. All 11 items below are conjunctive (every one must hold).

1. **All 31 references covered** as either single-target screenshots or crop regions. No reference PNG is unreachable from the manifest.
2. **All 11 live targets match at 0% diff** (or have user-approved reference correction filed as `IMAGES_GUI_RECAPTURE_<target>` with sign-off).
3. **All 20 future targets either become live or are explicitly deferred** with a written reason in `visual-targets.json::notes` and a referenced task id.
4. **Console errors total = 0** across the full walk in the `summary.json` aggregation (strict, no allow-list).
5. **Network 404 same-origin = 0** across the full walk in `summary.json`.
6. **No-fake scan = 0 hits** across all targets at `afterEach`.
7. **Secret scan = 0 hits** in the staged diff and rendered DOM.
8. **All 9 orphan tabs registered, mount cleanly, and visually match** their reference (single-tab or crop region) — `#workflows`, `#queue`, `#logs`, `#proof`, `#blender_mcp`, `#slicing`, `#fleet`, `#control`, `#docked`.
9. **All 3 scaffold files created and wired** — `tabs/Files.tsx`, `tabs/Safety.tsx`, `tabs/Notifications.tsx` mounted on `#files`, `#safety`, `#notifications` respectively.
10. **All 4 missing backend endpoints implemented** (`/api/skills`, `/api/connectors`, `/api/settings/themes`, `/api/dashboard/layouts`) OR explicitly deferred with rationale in `visual-targets.json::notes`.
11. **W11-1-style final proof bundle generated** at `03_implementation/docs/handoffs/GUI_VISUAL_E2E_COMPLETION_2026-05-10.md` with `summary.json` excerpt, scanner roll-ups, `loops.json` excerpt, and Hermes evidence chain PASS marker.

Item count: **11 conjunctive criteria**.

---

## 9. Stop Conditions (per user's rule)

Maximum **2 loops per target** before the implementation lane must classify the blocker and act. A "loop" is one PR cycle landing on `main` with re-run evidence (≥ 1 commit, CI green, `summary.json` regenerated).

After Loop 2 fails, the lane MUST classify the blocker into exactly one of:

1. **`code`** — a component change is required. Open a follow-up implementation lane (W6-3 / W6-4 / successors) and either bump tolerance with `tolerance_rationale` if diff is bounded ≤ 0.05, or `git revert` the regressing change and mark the target `status: "future"` with `notes: "regressed-on-loop-2: reverted <SHA>"`.
2. **`reference`** — the Images-GUI PNG itself is wrong (resolution, content drift). Set `status: "future"` with `notes: "blocked-on-recapture: <reason>"` and open `IMAGES_GUI_RECAPTURE_<target>` against the user. **Do NOT bump tolerance to mask** a stale reference.
3. **`viewport`** — reference dim ≠ harness viewport. Apply per-image viewport override in the manifest. If override doesn't resolve the diff, escalate to `reference`.
4. **`data`** — backend / data-stub mismatch. Update `deterministic.data_stubs[]` fixture; commit fixture under `tests/visual/__fixtures__/<target>.canon.json`.
5. **`browser`** — Playwright / Chromium upgrade or font-rendering drift. Pin the browser version in `package-lock.json` and document in the PR.

The reporter exits non-zero on any `diff` row whose `loops_open >= 3` (tracked in a sibling `loops.json` updated by CI). All per-loop attempts release Hermes locks on exit; stale locks are recovered after 90 minutes via the orchestrator's standard sweep.

A target may not stay in `diff` for more than 2 loops without one of: a recapture task, a tolerance bump with rationale, or a component revert. Anything else is classified as a process failure and escalated.

---

## 10. Sources

1. **ITIL 4 — Service Transition (release management, change control, plan-and-prepare)** — provides the structural pattern for staged rollout with explicit gates per PR. https://www.axelos.com/certifications/itil-service-management/itil-4-foundation
2. **W14 A1-A5 handoff documents** (the inputs synthesized by this contract):
   - `03_implementation/docs/handoffs/W14_A1_GUI_REFERENCE_INVENTORY_2026-05-10.md`
   - `03_implementation/docs/handoffs/W14_A2_ROUTE_REFERENCE_MATRIX_2026-05-10.md`
   - `03_implementation/docs/handoffs/W14_A3_VISUAL_ORACLE_DESIGN_2026-05-10.md`
   - `03_implementation/docs/handoffs/W14_A4_DESIGN_TOKEN_AUDIT_2026-05-10.md`
   - `03_implementation/docs/handoffs/W14_A5_PAGE_GAP_AUDIT_2026-05-10.md`

---

## 11. Constraints honoured

- READ-ONLY: no source/test files modified by this contract lane; all 8 PRs land separately.
- Hermes3D lock acquired on this doc path (`claude-w14-a6-integrator`, lock_id recorded in MCP state); will be released after this doc is finalized.
- Free / open-source tooling only — Sigstore + GitHub Attestations + GitHub Packages, never Azure Artifact Signing.
- No secrets read or written; `G:\private\` untouched.
- PR #128 reference pack remains the single source of truth; harness conforms.
- W6-6 / W8-14 / W8-15 design invariants preserved (`updateSnapshots: "none"`, one-way `Images-GUI/ → __refs__/` mirror, `domcontentloaded + 500ms` not `networkidle`).
- 4.1 contract-kit references retained in `01_requirements/` as planning artifacts; live router remains `app/routes.ts`.
- Honest gap: §4.3 includes `/api/dashboard/layouts` and `/api/connectors` as DEFERRABLE — implementation lanes must annotate the deferral rather than implementing silently.

---

**End of contract.** Implementation may begin with PR 1.
