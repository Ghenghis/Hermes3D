# W14 A3 — Visual Oracle Architect Design (2026-05-10)

**Owner:** claude-w14-a3-visual-oracle
**Task:** W14-A3-VISUAL-ORACLE-2026-05-10
**Wave:** 14 / Agent 3 (Visual Oracle Architect)
**Scope:** DESIGN ONLY — no harness implementation in this lane.
**Predecessors:** W6-6 (visual harness), W8-12 (Vite refresh), W8-14 (path/networkidle), W8-15 (viewport align). Verdict at the end of W8-15: **9 match / 1 diff / 1 error / 20 skipped-future** out of 31 references.

---

## 1. Existing Harness Inventory (W6-6 / W8-14 / W8-15)

| File | Purpose | What it covers today |
|---|---|---|
| `03_implementation/ui/playwright.visual.config.ts` | Playwright config for the visual suite | Single global viewport `1536x1024`; one project `visual-chromium-1536x1024`; `updateSnapshots: "none"`; `snapshotPathTemplate: "{arg}{ext}"`; mirrors via `globalSetup`; reporter wired; `webServer` boots `scripts/start-e2e-stack.mjs`. |
| `03_implementation/ui/tests/visual/visual-proof.spec.ts` | Per-target spec generator | Iterates `visual-targets.json`; navigates `target.route`, waits `wait_test_id` 15s + `domcontentloaded` + 500ms quiet; calls `expect(page).toHaveScreenshot(segments, { fullPage:true, animations:"disabled", maxDiffPixelRatio: target.tolerance })`; emits annotations for the reporter. |
| `03_implementation/ui/tests/visual/visual-proof-reporter.ts` | Custom reporter | Walks `test.annotations` + `result.attachments` to write `03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json` with rows `{target,status,route,reference,tolerance,diff_pixels,ratio,evidence_path,diff_path,error}`. Status set: `match` / `diff` / `missing-baseline` / `skipped-future` / `skipped-missing-reference` / `error`. |
| `03_implementation/ui/tests/visual/visual-targets.json` | Target manifest | 31 entries with `{target, reference, route, status, tolerance, wait_test_id, notes}`; top-level `viewport: {1536,1024}` and `tolerance_default: 0.1`. |
| `03_implementation/ui/tests/visual/global-setup.ts` | One-way mirror | Walks `Images-GUI/**/*.png`, copies to `tests/visual/__refs__/` with mtime+size skip; prunes orphans; never writes back. |
| `03_implementation/ui/tests/e2e/_helpers.ts` (REUSED) | Shared E2E helpers | Has `attachErrorCapture`/`assertNoErrors`/`assertNoFakeVisibleText` with a 5-token offline allow-list (`502`, `ERR_CONNECTION_REFUSED`, `ERR_FAILED`) and 9-term `FORBIDDEN_VISIBLE_TERMS` set. **Not** wired into the visual suite. |

**Coverage gap (one sentence).** The current harness compares ONE full-page screenshot per target against a single global 1536x1024 viewport with no console-error / 404 / fake-marker / clock-determinism gates and no support for collage references that pack 3-4 tabs into one PNG, so the 11 live targets only prove pixel parity for the dominant size and are blind to runtime regressions.

---

## 2. Required Extensions (5)

### 2.1 Exact viewport per reference
**Why.** W8-15 confirmed `toHaveScreenshot` is not resolution-tolerant. The 2 outliers (`1672x941`, `1586x992`) cannot match under a single global viewport without re-capturing references — which is forbidden by W8-15 contract.
**How.** Each `visual-targets.json` entry gains `viewport: {width, height}` derived at manifest-author time from the reference PNG IHDR (verified by `global-setup.ts`). At config-load time the harness reads the manifest, deduplicates `(width,height)` pairs, and emits one Playwright `project` per unique viewport (e.g. `visual-chromium-1536x1024`, `visual-chromium-1672x941`, `visual-chromium-1586x992`). Each test sets `test.use({ viewport })` from the manifest entry so the project assignment + per-test override are both correct on a strict run.
**Source.** `https://playwright.dev/docs/api/class-testoptions#test-options-viewport` (TestOptions.viewport semantics, per-project + per-test override precedence).

### 2.2 Crop region map (for collage references)
**Why.** Five references in `Images-GUI/02-primary-pages/` and `08-app-utility-pages/` are 4-tab collages, not single-route captures. Comparing them as `fullPage:true` against one route only proves the first quadrant.
**How.** A target may include `regions: [{name, route, wait_test_id, x, y, width, height}]`. When `regions` is present the spec loops over each region: it navigates `region.route`, waits for `region.wait_test_id`, and calls `expect(page).toHaveScreenshot([..., `${target}__${region.name}`], { clip: {x,y,width,height} })`. The reference PNG is split-by-clip on first run (cached under `__refs__/<target>/<region.name>.png` via a build-time helper). Reporter records one row per region with `parent_target` lineage.
**Source.** `https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot` (`clip` option for region capture).

### 2.3 Console error fail (mandatory, no allow-list bypass)
**Why.** `_helpers.ts` already has `attachErrorCapture` but it pre-filters 3 fragments (`502`, `ERR_CONNECTION_REFUSED`, `ERR_FAILED`) so a backend-down state silently passes. The visual oracle must fail on ANY browser-side console error.
**How.** Visual suite imports `attachErrorCapture` but with `allowList: []` (no offline carve-outs). At `test.afterEach` the spec calls `assertNoErrors(page)` against the strict empty list. Errors are captured both from `page.on("pageerror")` and `page.on("console", m => m.type()==="error")`. If the backend is offline that's a harness misconfig, not an acceptable visual-test outcome.

### 2.4 Network-404 fail
**Why.** A 404 on a tab-specific endpoint (e.g. `/api/source/modules`) renders an empty/skeleton component that often visually matches the reference (both blank), masking a real wiring regression. Must explicitly fail.
**How.** New helper `tests/visual/network-404-tracker.ts`. Hooks `page.on("response", r => r.status()===404 && capture(r.url(), r.request().method()))`. At `afterEach` it asserts the captured list is empty. Same-origin only by default; cross-origin (CDN, fonts, analytics) opt-in via `allowedHosts: []` in the manifest entry — empty by default.

### 2.5 No-fake DOM scan
**Why.** A component might render placeholder text the user has not yet replaced; a 0% pixel diff against a placeholder reference would lock that placeholder in. Visual parity must coexist with content truth.
**How.** New helper `tests/visual/no-fake-scanner.ts`. After waitForStable but before screenshot, evaluates `document.body.innerText` and matches a denylist sourced from the existing `FORBIDDEN_VISIBLE_TERMS` (9 tokens) plus visual-specific markers (`mockData`, `__test_`, `lorem ipsum`, `placeholder`, `Coming Soon`). Also scans `document.querySelectorAll("[data-mock], [data-fixture], [data-placeholder]")` and fails on any hit. Single hit -> test fails with a structured error including the marker, the closest `data-testid` ancestor, and the offending innerText snippet.

---

## 3. PR 1 File List + LoC Estimates

| # | File | New / Edit | LoC est. | Purpose |
|---|---|---|---|---|
| 1 | `03_implementation/ui/playwright.visual.config.ts` | EDIT (rewrite) | ~140 | Read manifest at config load; emit one project per unique `(width,height)`; carry per-target metadata into `metadata.viewport` so the spec can route. |
| 2 | `03_implementation/ui/tests/visual/visual-targets.json` | EDIT | ~+90 | Add `viewport` per entry; add `regions[]` for the 5 collage targets; promote 3 currently-future targets to `live` once their `wait_test_id` is wired. |
| 3 | `03_implementation/ui/tests/visual/visual-proof.spec.ts` | EDIT (rewrite) | ~210 | Per-target viewport `test.use`; region-loop branch; clock.install; theme=light force; wire 404 tracker + console-strict + no-fake scan; preserve annotation contract. |
| 4 | `03_implementation/ui/tests/visual/visual-proof-reporter.ts` | EDIT | ~+80 | Region-level rows (`parent_target`, `region`); console_errors[] + network_404s[] + fake_hits[] arrays; new statuses `console-error`, `network-404`, `fake-hit`, `region-diff`. |
| 5 | `03_implementation/ui/tests/visual/no-fake-scanner.ts` | NEW | ~70 | DOM-scan helper exporting `assertNoFakeMarkers(page, opts)`. |
| 6 | `03_implementation/ui/tests/visual/network-404-tracker.ts` | NEW | ~60 | Returns `{install, drain, assertEmpty}` triple bound to a `Page`. |
| 7 | `03_implementation/ui/tests/visual/_visual-helpers.ts` | NEW | ~90 | Strict-mode `attachConsoleErrorCapture` (no allow-list), `installDeterministicClock`, `forceLightTheme`, `stubDeterministicData`. |
| 8 | `03_implementation/ui/tests/visual/visual-targets.schema.json` | EDIT | ~+40 | Schema entries for `viewport`, `regions[]`, `allowedHosts[]`, `data_stubs[]`. |

**Total: 8 files (3 NEW + 5 EDIT) — ~780 LoC** (≈430 net-new across the 3 new files + ~350 in rewrites/diffs).

---

## 4. Per-Target Schema (JSON example)

```json
{
  "target": "02_primary_autopilot_design_gen3d_jobs",
  "reference": "Images-GUI/02-primary-pages/primary-tabs-autopilot-design-gen3d-jobs.png",
  "viewport": { "width": 1536, "height": 1024 },
  "tolerance": 0.0,
  "max_tolerance": 0.05,
  "tolerance_rationale": "",
  "status": "live",
  "regions": [
    {
      "name": "autopilot",
      "route": "/#autopilot",
      "wait_test_id": "autopilot-root",
      "clip": { "x": 0,    "y": 0,   "width": 768, "height": 512 }
    },
    {
      "name": "design",
      "route": "/#design",
      "wait_test_id": "design-root",
      "clip": { "x": 768,  "y": 0,   "width": 768, "height": 512 }
    },
    {
      "name": "gen3d",
      "route": "/#gen3d",
      "wait_test_id": "gen3d-root",
      "clip": { "x": 0,    "y": 512, "width": 768, "height": 512 }
    },
    {
      "name": "jobs",
      "route": "/#jobs",
      "wait_test_id": "jobs-root",
      "clip": { "x": 768,  "y": 512, "width": 768, "height": 512 }
    }
  ],
  "deterministic": {
    "clock_iso": "2026-05-10T12:00:00Z",
    "theme": "light",
    "data_stubs": [
      { "url_glob": "**/api/source/modules", "fixture": "tests/visual/__fixtures__/source-modules.canon.json" }
    ]
  },
  "allowed_hosts": [],
  "notes": "Composite of 4 primary tabs. Per-region clip rectangles match Images-GUI capture grid."
}
```

A non-collage entry omits `regions[]` and uses a single full-page screenshot — same shape as today, plus the new `viewport` and `deterministic` blocks.

---

## 5. Failure-Mode Table

| # | Trigger | Status emitted | Reporter row keys populated | Test outcome |
|---|---|---|---|---|
| 1 | Pixel diff > `target.tolerance` | `diff` | `diff_pixels`, `ratio`, `diff_path`, `evidence_path` | FAIL |
| 2 | Region pixel diff > `region.tolerance ?? target.tolerance` | `region-diff` | `region`, `parent_target`, `diff_pixels`, `ratio`, `diff_path` | FAIL (sibling regions still run) |
| 3 | Console error captured (any, no allow-list) | `console-error` | `console_errors[]` (text+url+location) | FAIL |
| 4 | 404 response same-origin | `network-404` | `network_404s[]` (url+method+initiator) | FAIL |
| 5 | Forbidden DOM marker hit | `fake-hit` | `fake_hits[]` (marker+selector+snippet) | FAIL |
| 6 | Reference PNG dim != `target.viewport` (boot-time check) | `error` (config) | `error: "viewport mismatch <ref> vs <target>"` | FAIL FAST (suite aborts before any browser launch) |
| 7 | `wait_test_id` 15s timeout | `error` | `error: "wait_test_id timeout"` | FAIL |
| 8 | Missing baseline (PNG not on disk) | `missing-baseline` | `error` | FAIL (was `skipped-missing-reference` in W6-6) |
| 9 | `status==="future"` and no live route | `skipped-future` | `error: notes` | SKIP (allowed) |
| 10 | Reference dim outlier without manifest acknowledgement | `error` (config) | `error: "outlier viewport — opt-in required"` | FAIL FAST |

**Tolerance policy.** Default `tolerance: 0.0` (0% diff). Per-target opt-in tolerance up to `max_tolerance: 0.05` requires `tolerance_rationale` non-empty in the manifest; the spec asserts this at boot. Anything > 5% must be filed as a separate `IMAGES_GUI_RECAPTURE_<target>` task — not absorbed by the harness.

---

## 6. Deterministic Environment Recipe

Applied at the start of every test (in `_visual-helpers.ts::primeDeterministic(page, target)`):

1. **Clock.** `await page.clock.install({ time: target.deterministic?.clock_iso ?? "2026-05-10T12:00:00Z" })`. Then `await page.clock.pauseAt(...)` so any `setInterval`-driven status badges, "5s ago" relative timestamps, and `Math.random` seeds run from a fixed base. Every spec uses the same default unless the target overrides.
2. **Theme.** `await page.addInitScript(() => { localStorage.setItem("hermes3d.theme", "light"); document.documentElement.dataset.theme = "light"; })`. Light is canonical for `Images-GUI/`. Theme-variant references (target `09_theme_variants_reference`) are out of scope until W6-3 ships the switcher.
3. **Animations.** Already disabled via `expect.toHaveScreenshot.animations: "disabled"` + `prefers-reduced-motion: reduce` emulation on the project `use` block.
4. **Fonts.** `await page.evaluate(() => document.fonts.ready)` after `wait_test_id` mounts so font swap is complete before screenshot.
5. **Data stubs.** Per-target `deterministic.data_stubs[]` registers `page.route(url_glob, fulfill from fixture file)` BEFORE `page.goto`. Fixtures live under `tests/visual/__fixtures__/<target>.canon.json` and are committed (not generated). Empty array means the target is fine against the live dev server.
6. **Network-404 tracker.** Installed before the first navigation; survives in-test SPA route changes.
7. **Console capture.** Installed before navigation; strict empty allow-list.
8. **No-fake scan.** Runs once at `afterEach` after the screenshot assertion has either passed or attached its diff PNG.

The recipe is idempotent: running the same target twice in the same CI minute produces byte-identical actual.png on a known-good build.

**Source.** `https://playwright.dev/docs/clock` (`page.clock.install`, `pauseAt`, `setFixedTime` semantics + supported timer types).

---

## 7. Rollback Plan (target stuck > 0% after 2 loops)

Define one "loop" = one PR cycle landing on `main` with re-run evidence (>= 1 commit, CI green, summary.json regenerated).

1. **Loop 1.** Land harness + canonical references; re-run; if a target reports `diff > 0`, file the diff PNG path + ratio in `summary.json`.
2. **Loop 2.** Land the targeted component fix (owned by W6-3 / W6-4 / their successors); re-run.
3. **If still > 0% after Loop 2:**
   - 3a. **Outlier-viewport rollback.** If `reference_dim != target.viewport` (e.g. 1672x941, 1586x992): set `status: "future"` with `notes: "blocked-on-recapture: <reason>"` and open `IMAGES_GUI_RECAPTURE_<target>` task against the `Images-GUI/` pack. Do NOT bump tolerance to mask. Revert any harness-side workaround introduced in Loop 1.
   - 3b. **Live-content rollback.** If diff is bounded (`<= 0.05`) and visual review approves the new look: bump `tolerance` to the measured ratio rounded up to the next 0.01 with mandatory `tolerance_rationale` ("user-approved <date>: <one-sentence reason>"). Reporter requires this annotation; missing rationale fails boot.
   - 3c. **Component rollback.** If diff is unbounded (`> 0.05`) and the component was changed in Loop 2: `git revert` the component change, mark the target `status: "future"` with `notes: "regressed-on-loop-2: reverted <SHA>"`, and re-open the implementation lane.
4. **Hard stop.** A target may not stay in `diff` for more than 2 loops without either a recapture task, a tolerance bump with rationale, or a component revert. The reporter exits non-zero on any `diff` row whose `loops_open >= 3` (tracked in a sibling `loops.json` updated by CI).
5. **Lock cleanup.** All per-loop attempts release Hermes3D locks on exit; stale locks are recovered after 90 minutes via the orchestrator's standard sweep.

---

## Sources

1. **Playwright `toHaveScreenshot` reference** (clip option, `maxDiffPixelRatio`, animations control): https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot
2. **Playwright `page.clock.install` reference** (deterministic clock + `pauseAt` / `setFixedTime` for date-dependent UI): https://playwright.dev/docs/clock

---

## Constraints honored

- DESIGN ONLY — no harness file under `03_implementation/ui/tests/visual/` was modified by this lane; all changes land in PR 1 of the implementation phase.
- Hermes3D lock acquired on this doc path (`claude-w14-a3-visual-oracle`, lock_id recorded in MCP state).
- No paid services — Sigstore / GitHub Attestations / GitHub Packages contract preserved; harness runs against local dev server.
- No secrets read or written; `G:\private\` untouched.
- Reference pack remains the single source of truth (PR #128); harness conforms.
- W6-6 / W8-14 / W8-15 design invariants preserved: `updateSnapshots: "none"`, one-way `Images-GUI/ -> __refs__/` mirror, `domcontentloaded + 500ms` (NOT `networkidle`).
