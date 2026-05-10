# W15 A5 — Visual Oracle Auditor Gap Report (2026-05-10)

**Owner:** claude-w15-a5-visual-oracle-auditor
**Task:** W15-A5-VISUAL-ORACLE-GAPS-2026-05-10
**Wave:** 15 / Agent 5 (Visual Oracle Auditor)
**Scope:** READ-ONLY audit. Compare current `origin/develop` visual harness vs W14-A3 oracle design + user spec gaps.
**Predecessors:** W6-6 (PR #189 closed; superseded), W8-14 (PR #194 merged), W8-15 (PR #196 merged), W14-A3 (design doc 2026-05-10).

---

## 1. Current Oracle Inventory on `origin/develop`

| File | Status | LoC | Last-touched lane |
|---|---|---|---|
| `03_implementation/ui/playwright.visual.config.ts` | EXISTS | 98 | W8-15 (PR #196) |
| `03_implementation/ui/tests/visual/visual-targets.json` | EXISTS | 290 | W6-6 (PR #189-era content) |
| `03_implementation/ui/tests/visual/visual-proof.spec.ts` | EXISTS | 214 | W8-14 (PR #194) |
| `03_implementation/ui/tests/visual/visual-proof-reporter.ts` | EXISTS | 299 | W6-6 |
| `03_implementation/ui/tests/visual/global-setup.ts` | EXISTS | 147 | W8-14 (PR #194) |
| `03_implementation/ui/tests/visual/__refs__/.gitkeep` | EXISTS | n/a | W8-14 mirror dest |
| `03_implementation/ui/tests/visual/no-fake-scanner.ts` | **MISSING** | 0 | W14-A3 design only |
| `03_implementation/ui/tests/visual/network-404-tracker.ts` | **MISSING** | 0 | W14-A3 design only |
| `03_implementation/ui/tests/visual/_visual-helpers.ts` | **MISSING** | 0 | W14-A3 design only |
| `03_implementation/ui/tests/visual/visual-targets.schema.json` | **MISSING** | 0 | W14-A3 design only |

**Total existing oracle LoC on develop:** 1,048 (config 98 + manifest 290 + spec 214 + reporter 299 + global-setup 147).

**Capabilities currently implemented (verbatim from develop source):**
- One-way `Images-GUI/ -> __refs__/` mirror via `globalSetup` (W8-14).
- `updateSnapshots: "none"` (no auto-baseline write).
- `snapshotPathTemplate: "{arg}{ext}"` resolved forward-only inside test root.
- One Playwright project at fixed `viewport: { width: 1536, height: 1024 }`.
- 31-target manifest (`visual-targets.json`) with `{target, reference, route, status, tolerance, wait_test_id, notes}`.
- `wait_test_id` 15s timeout + `domcontentloaded` + 500ms quiet (W8-14 swap from `networkidle`).
- `expect(page).toHaveScreenshot(segments, { fullPage: true, animations: "disabled", maxDiffPixelRatio: target.tolerance })`.
- Custom reporter writing `summary.json` with status set `{match, diff, missing-baseline, skipped-future, skipped-missing-reference, error}`.
- `webServer` boots `scripts/start-e2e-stack.mjs` (local-only, no paid services).

---

## 2. Capability Matrix: Develop vs W14-A3 Spec

| Capability | On develop? | Needed? | Gap |
|---|---|---|---|
| Crop manifest support (`regions[]` per target with `clip` rect) | NO | YES (5 collage refs in `02-primary-pages/`, `08-app-utility-pages/`) | **GAP** — spec only does `fullPage: true`; first quadrant proven, rest blind. |
| Viewport overrides per target | NO (single global `1536x1024`) | YES (2 outliers: `1672x941`, `1586x992`) | **GAP** — outliers cannot match without manifest-driven projects. |
| Console-error mandatory fail (no allow-list) | NO | YES | **GAP** — `_helpers.ts` carries 3-fragment offline allow-list and is not wired into visual suite. |
| Network-404 fail | NO | YES | **GAP** — no `page.on("response")` hook; 404 silently passes. |
| No-fake DOM scan | NO | YES | **GAP** — `_helpers.ts::assertNoFakeVisibleText` exists but is not wired into visual suite. |
| Pixel comparison (`toHaveScreenshot` + `maxDiffPixelRatio`) | YES | YES | none |
| Deterministic clock (`page.clock.install` + `pauseAt`) | NO | YES | **GAP** — no clock primer; relative timestamps + `setInterval` badges leak time-of-day. |
| Theme determinism (force light via `addInitScript`) | NO | YES | **GAP** — theme not pinned; W14 ThemeSwitcher (PR #204) can flip mid-run. |
| `document.fonts.ready` await | NO | YES | **GAP** — font swap flake risk. |
| Region screenshots (`clip` per region) | NO | YES | **GAP** — see crop manifest row; same root cause. |

**Tally:** 1 capability fully present / 10 capabilities needed / **9 gaps**.

---

## 3. W14-PR1 Status

`gh pr list --search "w14-pr1"` returns `[]`. No branch named `claude/w14-pr1-visual-oracle-harness` is on `origin` (`git branch -r` filtered for `w14-pr1` empty). The W14-A3 lane shipped DESIGN ONLY (per its own header: "DESIGN ONLY — no harness implementation in this lane"). The handoff explicitly says PR 1 is the next lane's responsibility.

**Verdict on W14-PR1:** **NOT FOUND** (not in flight, not merged, not closed — never opened).

Closest active PRs in the visual lineage on `origin/develop`:
- PR #194 `claude/w8-14-visual-proof-harness-fix` — MERGED (outputPath escape + networkidle timeout fix).
- PR #196 `claude/w8-15-visual-viewport-align` — MERGED (viewport align to 1536x1024).
- PR #189 `claude/w6-6-playwright-visual-proof` — CLOSED (initial harness; superseded by W8-14/W8-15 forward-fixes).

No subsequent visual-oracle harness PR exists.

---

## 4. Exact Harness Gaps — What Agent 9 Must Implement

Agent 9 (or whoever owns implementation PR 1) must land the 3-NEW + 5-EDIT file set from W14-A3 §3, with the following discrete deliverables:

1. **`playwright.visual.config.ts`** EDIT (~140 LoC rewrite). Read manifest at config load, dedupe `(width,height)` pairs, emit one project per unique viewport. Carry per-target metadata into `metadata.viewport`.
2. **`visual-targets.json`** EDIT (+90 LoC). Add `viewport: {width,height}` per entry derived from PNG IHDR. Add `regions[]` for the 5 collage targets in `02-primary-pages/` and `08-app-utility-pages/`. Promote 3 currently-future targets to `live` once `wait_test_id` is wired.
3. **`visual-proof.spec.ts`** EDIT (~210 LoC rewrite). Per-target `test.use({ viewport })`. Region-loop branch using `expect(...).toHaveScreenshot([..., regionName], { clip: {x,y,width,height} })`. Wire `clock.install` + `pauseAt`, `addInitScript` theme=light, `document.fonts.ready`. Wire 404-tracker, console-strict capture (empty allow-list), no-fake DOM scan in `afterEach`.
4. **`visual-proof-reporter.ts`** EDIT (+80 LoC). Emit region-level rows (`parent_target`, `region`); add `console_errors[]`, `network_404s[]`, `fake_hits[]`; add status set `{console-error, network-404, fake-hit, region-diff}`.
5. **`no-fake-scanner.ts`** NEW (~70 LoC). `assertNoFakeMarkers(page, opts)` — innerText denylist + `[data-mock]/[data-fixture]/[data-placeholder]` selectors. Source the 9-token denylist from existing `FORBIDDEN_VISIBLE_TERMS` in `_helpers.ts` plus visual-specific markers.
6. **`network-404-tracker.ts`** NEW (~60 LoC). `{install, drain, assertEmpty}` triple bound to a `Page`. Same-origin only by default; opt-in cross-origin via `allowedHosts: []`.
7. **`_visual-helpers.ts`** NEW (~90 LoC). Strict-mode `attachConsoleErrorCapture(page, { allowList: [] })`, `installDeterministicClock(page, isoString)`, `forceLightTheme(page)`, `stubDeterministicData(page, stubs)`.
8. **`visual-targets.schema.json`** EDIT (+40 LoC). Schema entries for `viewport`, `regions[]`, `allowed_hosts[]`, `data_stubs[]`, `deterministic.clock_iso`, `deterministic.theme`, `tolerance_rationale`, `max_tolerance`.

**Boot-time guards (must be added to spec or config):**
- Reference PNG dim != `target.viewport` -> FAIL FAST (config error).
- `tolerance > max_tolerance` without `tolerance_rationale` -> FAIL FAST.
- Outlier viewport without manifest acknowledgement -> FAIL FAST.

**Total LoC: ~780** (430 net-new + 350 in rewrites/diffs).

**Out of scope for Agent 9 (per W14-A3 rollback plan):** component-side fixes for any target whose diff exceeds tolerance after harness lands. Those belong to W6-3 (dashboard mode switcher) / W6-4 (Action Window) successor lanes.

---

## 5. Verdict

**ORACLE_PARTIAL.**

The visual harness exists and is structurally sound (manifest + spec + reporter + globalSetup mirror). It correctly enforces `updateSnapshots: "none"`, single-source-of-truth from `Images-GUI/`, and the W8-14 `networkidle` fix. However, only **1 of 10** required capabilities is present. The 9 gaps are all in code paths the W14-A3 design has already specified line-by-line; they have simply not yet been implemented because no W14-PR1 / W15 implementation lane has been opened on `origin/develop`. Until the 8-file change set lands, the harness only proves pixel parity for the dominant 1536x1024 viewport on full-page captures — which is blind to console errors, network 404s, placeholder content, theme drift, time drift, and regions outside the first quadrant of collage references.

---

## Sources

1. **Playwright `toHaveScreenshot` reference** (canonical `clip`, `maxDiffPixelRatio`, `animations: "disabled"` semantics that the gap analysis maps to): https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot
2. **Chromatic visual-tests harness pattern** (cross-project benchmark for the missing capabilities — fonts.ready, deterministic clock, console-error gating, region/component crops): https://www.chromatic.com/docs/visual-tests/

---

## Constraints honored

- READ-ONLY — no harness file under `03_implementation/ui/tests/visual/` was touched.
- Hermes3D MCP server reachable throughout audit.
- 2 sources cited (1 official Playwright, 1 cross-project Chromatic).
- No paid services referenced.
- No secrets read; `G:\private\` untouched.
- Reference pack (PR #128 / #134) remains the single source of truth.
- Cross-checked against W14-A3 design doc verbatim for the 5 required extensions and 8-file PR-1 list.
