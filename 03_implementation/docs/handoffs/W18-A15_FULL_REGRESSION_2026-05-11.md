# W18-A15 — Full Regression Runner (consolidated proof)

**Task ID:** W18-A15-FULL-REGRESSION-RUNNER-2026-05-11
**Lock owner:** w18-a15
**Generated UTC:** 2026-05-11T11:47:45.477Z
**Workspace:** `G:\Github\Hermes3D` (worktree `.claude/worktrees/w18-a15`)
**Branch:** `claude/w18-a15-regression-runner`

## STRICT operator freeze
No printer hardware writes. Pinned:
- `GUI_PHYSICAL_PRINT_GREEN` = OUT_OF_SCOPE_BY_OPERATOR
- `GUI_PRINTER_DRY_RUN_GREEN` = OUT_OF_SCOPE_BY_OPERATOR

No printer hardware touched. Pinned verdicts unchanged.

## Overall verdict

**FAIL**

### Why FAIL
- `playwright.e2e.config.ts`: 88 passed, 3 failed, 0 skipped. The 3 failures are:
  1. **printer panel reflects operator IPs and keeps S1 test locked** — pre-existing live-stack issue, the `MOONRAKER (OK|FAIL)` badge never reaches visible state because the local stack has no real Moonraker peer (operator-side, not introduced by this regression).
  2. **Source OS wires source app backup, update check, and gated update execution** — 30 s test timeout waiting for the `Setup Queue` button. Same shape as a known Source OS live-route issue.
  3. **W18-A9 slicer real-artifact audit** — 30 s test timeout. The W18-A9 lane spec needs `test.setTimeout(10 * 60_000)` because the real STL → G-code path takes ~32 s; the lane-dedicated config sets a 10-minute timeout but the legacy `playwright.e2e.config.ts` does not. Running the spec via `playwright.w18-a9.config.ts` directly passes in 33 s. Recommend lifting test timeout in either the spec or the e2e config to capture this fairly.
- `playwright.visual.config.ts`: 25 passed, 16 failed, 20 skipped. The 16 failures are `page.waitForLoadState` timeouts against the shared :5173 stack (live tests racing the unmocked stack); the 20 skips are W15-A9 `status: "future"` placeholder targets that still use `test.skip()` directly. The W18-A14 no-skip-harness PR has not yet merged to develop, so the `test.skip()` sites are still in place and the no-skip contract correctly flags them.
- `playwright.breadth.config.ts`: 3 passed, 0 failed, 0 skipped — clean **PASS_REAL**.
- `playwright.w18-a11.config.ts`: 1 passed, 0 failed, 0 skipped — clean **PASS_REAL**.
- `playwright.w18-a9.config.ts`: 1 passed, 0 failed, 0 skipped — clean **PASS_REAL** when run with its own 10-minute timeout config.

### W18 merge state during this sweep
At watchdog trigger time (iter=6, ~0.16 h elapsed under the tight-trigger threshold), the target-lane merge count was 3/10 (`a5`, `a7`, `a11`). Auxiliary non-target W18 lanes already merged at that time: `a2`, `a3`, `a6` — for 6 total W18 PRs merged to develop. After the watchdog fired and during the regression sweep, `a9` (PR #239) also merged, so the regression run was re-baselined on develop and the new lane-specific configs (`playwright.w18-a9.config.ts`, `playwright.w18-a11.config.ts`) were exercised individually. The remaining target lanes (`a1-pickup`, `a4`, `a8`, `a10-pickup`, `a13`, `a14-pickup`) were still open or in-flight when this sweep ran; the orchestrator should re-invoke W18-A15 once they land.

## Watchdog snapshot

```json
{
  "iter": 6,
  "now": "2026-05-11T11:29:02.423Z",
  "elapsedHours": 0.16794805555555556,
  "mergedCount": 3,
  "openCount": 3,
  "mergedLanes": [
    {
      "lane": "a5",
      "pr": 237,
      "url": "https://github.com/Ghenghis/Hermes3D/pull/237"
    },
    {
      "lane": "a7",
      "pr": 233,
      "url": "https://github.com/Ghenghis/Hermes3D/pull/233"
    },
    {
      "lane": "a11",
      "pr": 240,
      "url": "https://github.com/Ghenghis/Hermes3D/pull/240"
    }
  ],
  "openLanes": [
    {
      "lane": "a4",
      "pr": 232,
      "url": "https://github.com/Ghenghis/Hermes3D/pull/232"
    },
    {
      "lane": "a8",
      "pr": 238,
      "url": "https://github.com/Ghenghis/Hermes3D/pull/238"
    },
    {
      "lane": "a9",
      "pr": 239,
      "url": "https://github.com/Ghenghis/Hermes3D/pull/239"
    }
  ]
}
```

## Per-config table

| Config | Label | Verdict | Passed | Failed | Skipped | Duration |
|---|---|---|---:|---:|---:|---:|
| `playwright.e2e.config.ts` | e2e (full stack) | **FAIL** | 88 | 3 | 0 | 218s |
| `playwright.visual.config.ts` | visual proof (Images-GUI oracle) | **FAIL** | 25 | 16 | 20 | 0s |
| `playwright.breadth.config.ts` | breadth (Vite preview, stubbed backend) | **PASS_REAL** | 3 | 0 | 0 | 11s |
| `playwright.w18-a11.config.ts` | lane w18-a11 | **PASS_REAL** | 1 | 0 | 0 | 22s |
| `playwright.w18-a9.config.ts` | lane w18-a9 | **PASS_REAL** | 1 | 0 | 0 | 33s |

Skip-aware verdicts: any skipped test counts as FAIL (per W18-A14 no-skip-harness contract).


### Failed specs for `playwright.e2e.config.ts`

- **printer panel reflects operator IPs and keeps S1 test locked** (`live-gui.spec.ts`)
  - `Error: [2mexpect([22m[31mlocator[39m[2m).[22mtoBeVisible[2m([22m[2m)[22m failed  Locator: getByTestId('printers-root').locator('section').filter({ hasText: 'T1 #1' }).getByText(/MOONRAKER (O`
- **Source OS wires source app backup, update check, and gated update execution** (`live-gui.spec.ts`)
  - `[31mTest timeout of 30000ms exceeded.[39m`
  - `Error: locator.click: Test timeout of 30000ms exceeded. Call log: [2m  - waiting for getByTestId('source-os-root').getByRole('button', { name: 'Setup Queue', exact: true })[22m [2m    - locator res`
- **Audit: GUI surface -> slicer -> real G-code on disk + no printer-control** (`w18-a9-slicer-real-artifact.spec.ts`)
  - `[31mTest timeout of 30000ms exceeded.[39m`


### Failed specs for `playwright.visual.config.ts`

- **tests\visual\dashboard.visual.spec.ts:44:3 › Dashboard @ 1920×1080 › renders all panels and matches visual baseline** (`tests\visual\dashboard.visual.spec.ts:44:3`)
- **tests\visual\dock.spec.ts:61:3 › Panel dock state machine @ 1920×1080 › every tab panel exposes required Phase 2 chrome** (`tests\visual\dock.spec.ts:61:3`)
- **tests\visual\dock.spec.ts:101:3 › Panel dock state machine @ 1920×1080 › fullscreen overlay renders fixed-position CSS (no native window)** (`tests\visual\dock.spec.ts:101:3`)
- **tests\visual\dock.spec.ts:149:3 › Panel dock state machine @ 1920×1080 › no external window or network calls during dock interactions** (`tests\visual\dock.spec.ts:149:3`)
- **tests\visual\dock.spec.ts:203:3 › Panel dock state machine @ 1920×1080 › source has no external window/process launch path** (`tests\visual\dock.spec.ts:203:3`)
- **tests\visual\fleet.live.spec.ts:81:1 › live mode reads local bridge and marks four fixture printers as live** (`tests\visual\fleet.live.spec.ts:81:1`)
- **tests\visual\gen3d.plan_preview.spec.ts:28:1 › live mode previews a planner DAG without execution affordances** (`tests\visual\gen3d.plan_preview.spec.ts:28:1`)
- **tests\visual\gen3d.planner_mode.spec.ts:28:1 › live mode shows via-LLM badge when bridge response sets planner_mode=llm** (`tests\visual\gen3d.planner_mode.spec.ts:28:1`)
- **tests\visual\gen3d.planner_mode.spec.ts:78:1 › live mode shows template badge when bridge response sets planner_mode=template** (`tests\visual\gen3d.planner_mode.spec.ts:78:1`)
- **tests\visual\gen3d.provider_health.spec.ts:3:1 › live mode shows green and amber dots when bridge response provides them** (`tests\visual\gen3d.provider_health.spec.ts:3:1`)
- **tests\visual\gen3d.provider_health.spec.ts:61:1 › live mode shows red dot when probe failed** (`tests\visual\gen3d.provider_health.spec.ts:61:1`)
- **tests\visual\gen3d.provider_health.spec.ts:109:1 › live mode shows idle dots when no probes have been run** (`tests\visual\gen3d.provider_health.spec.ts:109:1`)
- **tests\visual\health-page.spec.ts:18:1 › mock-mode renders a Service Health tab with cards** (`tests\visual\health-page.spec.ts:18:1`)
- **tests\visual\health-page.spec.ts:33:1 › live-mode fetches /api/health/services and renders the response** (`tests\visual\health-page.spec.ts:33:1`)
- **tests\visual\health-page.spec.ts:90:1 › re-probe now button triggers another fetch** (`tests\visual\health-page.spec.ts:90:1`)
- **tests\visual\health-page.spec.ts:125:1 › pause auto-refresh toggles aria-pressed** (`tests\visual\health-page.spec.ts:125:1`)


## Evidence chain

- Hermes evidence chain: PASS
- Task ID: W18-A15-FULL-REGRESSION-RUNNER-2026-05-11
- hermes_run_gate: invoked for `gui_truth_proof_real` post-run
- Locks: `w18-a15` on watchdog + report scripts + this handoff doc; released on PR open

## Artifacts

- machine summary (archived): `03_implementation/ui/tests/w18-a15-evidence/regression-summary.json`
- machine summary (live, gitignored): `03_implementation/ui/test-results/w18-a15/summary.json`
- watchdog log: `03_implementation/ui/tests/w18-a15-evidence/watchdog.log`
- watchdog state: `03_implementation/ui/tests/w18-a15-evidence/watchdog-state.json`
- e2e run log: `03_implementation/ui/tests/w18-a15-evidence/e2e-run.log`
- visual run log: `03_implementation/ui/tests/w18-a15-evidence/visual-run.log`
- breadth run log: `03_implementation/ui/tests/w18-a15-evidence/breadth-run.log`
- W18-A9 lane run log: `03_implementation/ui/tests/w18-a15-evidence/w18-a9-run.log`
- W18-A11 lane run log: `03_implementation/ui/tests/w18-a15-evidence/w18-a11-run.log`
- archived visual oracle stats: `03_implementation/ui/tests/w18-a15-evidence/visual-oracle-summary.json`
- per-config artifacts: `03_implementation/ui/test-results/<config>/` (screenshots, trace.zip, error-context.md for every failure)

The W15-A9 visual oracle summary file at `03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json` is intentionally **not** modified by this PR — it is a per-run side artifact that the visual config rewrites every run; committing it would cause cross-lane cascade conflicts. The W18-A15 archived snapshot lives alongside the Playwright stdout in this branch's evidence dir.

