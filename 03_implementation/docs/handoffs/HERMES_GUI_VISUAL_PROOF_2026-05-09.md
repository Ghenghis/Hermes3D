# Hermes3D OS GUI - Playwright Visual Proof Harness (W6-6)

**Owner:** claude-w6-6-visual-proof
**Date:** 2026-05-09
**Branch:** `claude/w6-6-playwright-visual-proof` (off `feat/hermes3d-7-complete-gui-repo-wiring`)
**Worktree:** `G:/Github/_claude_worktrees/h3d-claude-w6-6-visual`
**Lane:** Wave 6 lane 5 (visual-proof against `Images-GUI/`), prep for lane 3.

## Problem

W5-3 ran a Playwright smoke and produced 6 green screenshots, but it never
compared those screenshots against the `Images-GUI/` reference pack (31 PNGs
covering all 16 primary tabs, settings/voice subtabs, source-os categories,
action-window templates, responsive states, plugins/skills/MCP, app utility
pages, and 6 themes). Per the user, "Add Playwright visual proof against
the reference images." This handoff documents the harness that fills that
gap and the methodology for running, reading, and updating it.

## Methodology

| Knob | Value | Why |
|---|---|---|
| Viewport | 1920 x 1080 | Matches existing playwright.e2e.config.ts and the 1920-wide reference PNGs from `Images-GUI/`. |
| Screenshot mode | `fullPage: true` | Reference PNGs cover full pages, not just viewport. |
| Animations | `disabled` | Playwright's animation freeze removes a major source of flake. |
| Wait sequence | `domcontentloaded` -> `networkidle` -> 500 ms quiet period -> `wait_test_id` (when set) | Prevents async data loads from racing the screenshot. |
| Pixel diff engine | Playwright bundled `pixelmatch` via `toHaveScreenshot` | Free, MIT-licensed, no new dependency added. |
| Per-pixel threshold | `0.2` (config-wide), per-target `tolerance` overrides via `maxDiffPixelRatio` | 10% pixel diff is the base default per `visual-targets.json`; theme/state references use 15-25%. |
| `updateSnapshots` | `none` | Hard contract: this run NEVER auto-updates reference PNGs. Refresh requires `--update-snapshots` and a PR review. |
| `snapshotPathTemplate` | `{arg}{ext}` | When the spec calls `toHaveScreenshot([...segments])`, Playwright `path.join`s the segments and resolves them against the `playwright.visual.config.ts` directory (`03_implementation/ui/`). The spec passes a relative chain back to `Images-GUI/` so the reference PNGs are the single source of truth (no `__snapshots__/` duplicates). |

## Files added by this lane

```
03_implementation/ui/playwright.visual.config.ts
03_implementation/ui/tests/visual/visual-targets.json
03_implementation/ui/tests/visual/visual-proof.spec.ts
03_implementation/ui/tests/visual/visual-proof-reporter.ts
03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json   (generated)
03_implementation/docs/handoffs/HERMES_GUI_VISUAL_PROOF_2026-05-09.md
```

W6-3 / W6-4 components were NOT modified. Visual proof is read-only against
the live UI.

## Targets catalog

`visual-targets.json` is the manifest. 31 entries, one per PNG in
`Images-GUI/`. Each entry carries:

```json
{
  "target": "01_dashboard_advanced_a",
  "reference": "Images-GUI/01-dashboard-modes/advanced-dashboard-a.png",
  "route": "/#dashboard",
  "status": "live | future",
  "tolerance": 0.10,
  "wait_test_id": "dashboard-root",
  "notes": "Owned by Wave 6 lane 3 (W6-3 dashboard mode switcher) for parity work."
}
```

### Status taxonomy

- `live` - target's route renders in the current main app and a comparison can run today.
- `future` - target requires UI work that is owned by another lane (W6-3 dashboard modes / theme switcher; W6-4 Action Window). The harness emits a `skipped-future` row so reviewers see the gap without the run failing.

The harness also emits two runtime statuses that are not present in the
manifest:

- `skipped-missing-reference` - the manifest path resolved to no PNG on disk.
- `missing-baseline` - the screenshot assertion ran but Playwright reported the snapshot was absent (defensive; this should be unreachable now that `updateSnapshots: "none"` is set, but the reporter still classifies it).

### Coverage breakdown

| Folder | PNGs | Live | Future | Notes |
|---|---:|---:|---:|---|
| `00-user-current-downloads` | 10 | 1 | 9 | `Hermes3D.png` is the user-approved baseline; Generated 1-9 are visual-direction PNGs, not 1:1 page snapshots. |
| `01-dashboard-modes` | 6 | 1 | 5 | `advanced-dashboard-a` is the closest live match. Simple/Custom/Advanced-B are W6-3 work. |
| `02-primary-pages` | 3 | 3 | 0 | Composite refs anchored to Autopilot / Printers / Artifacts. Per-tab specs already exist; this lane adds the cross-tab visual layer. |
| `03-settings-voice` | 2 | 2 | 0 | Settings (`/#settings`) and Voice (`/#voice`) routes. |
| `04-source-os` | 3 | 3 | 0 | Source OS landing (`/#sources`) - core / remaining / 60-app matrix. |
| `05-action-windows` | 2 | 0 | 2 | Action Window is W6-4. |
| `06-states-responsive` | 1 | 0 | 1 | Loading/empty/blocked/recovering states. Future, lane TBD. |
| `07-plugins-skills-mcp` | 1 | 1 | 0 | Plugins (`/#plugins`) landing. |
| `08-app-utility-pages` | 2 | 0 | 2 | Composite of workflow + print queue / proof + health. Anchored to Jobs/Observe but no single live route covers them yet. |
| `09-themes` | 1 | 0 | 1 | Theme switcher not implemented. |
| **Total** | **31** | **11** | **20** | 11 live targets exercise pixel diff today; 20 future targets are tracked but skipped. |

## How to run

```powershell
# 1. Install playwright browsers if missing (one-time):
cd G:\Github\h3d-gui-wiring-codex\03_implementation\ui
npx playwright install chromium

# 2. Run the visual harness (starts dev server via webServer):
npx playwright test --config=playwright.visual.config.ts

# 3. Read the JSON summary:
type ..\docs\evidence\visual_proof_2026-05-09\summary.json
```

The webServer block in `playwright.visual.config.ts` reuses
`scripts/start-e2e-stack.mjs` (same path used by the E2E config), so no
separate dev-server orchestration is needed. The first run will boot the
stack on `127.0.0.1:5173`.

### First-run results (2026-05-10 03:38 UTC)

Run on `claude/w6-6-playwright-visual-proof` branch off
`feat/hermes3d-7-complete-gui-repo-wiring`, in a clean worktree at
`G:/Github/_claude_worktrees/h3d-claude-w6-6-visual` with `node_modules/`
junctioned to the parent codex repo.

| Status | Count | Notes |
|---|---:|---|
| match | 0 | Live targets could not produce a pixel diff because the SPA never mounted. |
| diff | 0 | |
| missing-baseline | 0 | All 31 reference PNGs are present on disk. |
| skipped-future | 20 | Future targets skipped as expected. |
| skipped-missing-reference | 0 | |
| error | 11 | All 11 live targets timed out waiting for their `wait_test_id` to mount. Root cause is a pre-existing Vite HMR error in `src/app/routes.tsx`: `ReferenceError: $RefreshReg$ is not defined`, blocking React from rendering. This pre-dates this lane and reproduces with the existing E2E config too. |
| **total** | **31** | All 31 reference PNGs catalogued. |

The lane is unblocked once the Vite HMR / Fast Refresh issue on
`feat/hermes3d-7-complete-gui-repo-wiring` is fixed (likely a missing
`@vitejs/plugin-react` preamble or a stale Vite 8 / React-plugin
incompatibility). At that point a re-run will yield real `match` / `diff`
rows. The harness itself does NOT need a fix; the current failure mode is
doing what it should: reporting concrete error data per target and
emitting the JSON summary.

The 20 `skipped-future` rows are the expected design: those references
are owned by W6-3 (dashboard modes / theme switcher / custom dashboards),
W6-4 (Action Window), or future state-screen lanes.

## How to update reference PNGs (intentional UI changes)

This is an explicit, audited operation. Never auto-merge an update.

1. Verify the UI change is intentional and approved (PR review, design ack).
2. Run the harness with `--update-snapshots` to overwrite reference PNGs in
   `Images-GUI/`:
   ```powershell
   cd G:\Github\h3d-gui-wiring-codex\03_implementation\ui
   npx playwright test --config=playwright.visual.config.ts --update-snapshots
   ```
3. Run `git diff Images-GUI/` and inspect every changed PNG visually before
   staging.
4. Add the new reference PNGs in a separate commit titled
   `chore(visual-proof): update Images-GUI baseline for <reason>` so the
   diff is reviewable in isolation from product changes.
5. Re-run the harness without `--update-snapshots` to confirm the next run
   passes against the new baseline.

## Persistence rule for failed targets

For each `diff` (failed comparison), the JSON summary records:

- `target` - manifest key
- `diff_pixels` (when extractable from Playwright failure message)
- `total_pixels` (when extractable; otherwise omitted)
- `ratio` (diff pixels / total pixels)
- `diff_path` - relative path to the Playwright-emitted diff PNG
  (typically `test-results/visual/__diff__/<target>.png` or
  `test-results/<test-id>/<target>-diff.png`)
- `evidence_path` - relative path to the live screenshot
- `error` - first 600 chars of the failure message
- `route`, `reference`, `tolerance` - copied from the manifest

Suggested follow-up workflow:

```
target_name              -> populated
diff_pixels_count        -> from summary.diff_pixels
diff_image_path          -> from summary.diff_path
next_fix_attempt         -> assigned by the orchestrator (W6-3 for dashboard, W6-4 for Action Window, etc.)
evidence_id              -> hash(target + run_started_at) once a Hermes proof event is emitted
```

The lane that owns the failing target should consume the diff PNG, fix the
component, and re-run the harness. This harness MUST NOT be modified to
"chase" the live UI; that is a baseline update (above) which is an
explicit operator action.

## Constraints honored

- No new npm dependency added: pixel-diff is delegated to Playwright's
  bundled `pixelmatch` via `toHaveScreenshot`.
- No paid services: dev server is local; no cloud screenshot diffing.
- No secrets in tests or fixtures.
- Existing playwright.config.ts and playwright.e2e.config.ts are untouched.
- W6-3 and W6-4 components are not modified by this lane.

## Sources

1. Playwright snapshot / visual comparison guide -
   <https://playwright.dev/docs/test-snapshots>
2. Playwright `toHaveScreenshot` API reference -
   <https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot>
