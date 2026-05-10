# W8-14 — Visual-Proof Harness Fix (2026-05-09)

**Owner:** claude-w8-14-harness-fix
**Branch:** `claude/w8-14-visual-proof-harness-fix` (off `claude/w8-12-vite-refresh-fix`)
**Lock task:** `W8-14-VISUAL-PROOF-HARNESS-FIX-2026-05-09`
**Predecessors:**
- W6-6 PR — Playwright visual-proof harness (commits `71dba58`, `378f7b3`)
- W8-12 PR #188 — Vite Fast-Refresh fix that lets the SPA actually mount
- W6-6 first-run summary (PR #189): `0 match / 0 diff / 11 error / 20 skipped` (all 11 errors were `outputPath is not allowed outside of the parent directory` or 30s `networkidle` timeouts)

## Bugs Fixed

### Bug 1 — `outputPath is not allowed outside of the parent directory`

**Root cause.** W6-6 set `snapshotPathTemplate: "{arg}{ext}"` and the spec computed an array of path segments that walked back UP from the Playwright config dir (`03_implementation/ui/`) to the repo root and INTO `Images-GUI/`. Playwright resolves `snapshotPathTemplate` against `configDir` and runs a safety check that rejects any output path which escapes the test root. That check is documented as part of the snapshotPathTemplate resolution rules and cannot be disabled.

**Fix.** Mirror `Images-GUI/` into `03_implementation/ui/tests/visual/__refs__/` at config time, then have the spec emit forward-only segments into that mirror.

- New file `03_implementation/ui/tests/visual/global-setup.ts`
  - Walks `Images-GUI/` (recursive) and copies every PNG into `tests/visual/__refs__/<same-relative-path>`.
  - Idempotent: per-file size + mtime equality skip; first run copies all 31, subsequent runs effectively no-op.
  - Prunes orphan PNGs from `__refs__/` if their source is removed.
  - `Images-GUI/` is the source of truth — copies are one-way only, never reversed.
- `playwright.visual.config.ts` registers `globalSetup: "./tests/visual/global-setup.ts"`.
- `visual-proof.spec.ts::snapshotPathSegments()` strips the leading `Images-GUI/` from each manifest reference and joins the remainder under `REFS_LOCAL_ROOT` (= `tests/visual/__refs__/`). The returned chain is relative to UI_ROOT and stays entirely INSIDE the test root.
- New `tests/visual/.gitignore` excludes `__refs__/**/*.png` so the mirror never gets committed; `__refs__/.gitkeep` keeps the directory present in fresh checkouts.

**Verification.** Single-target run logs `[visual-proof globalSetup] mirrored 31 PNGs from Images-GUI/ to 03_implementation/ui/tests/visual/__refs__/ (copied=31 skipped=0 pruned=0) in 48ms`. Subsequent runs hit `(copied=0 skipped=31 pruned=0)`. Playwright now resolves the snapshot to `tests\visual\__refs__\01-dashboard-modes\advanced-dashboard-a.png` and runs the comparison.

### Bug 2 — `networkidle` 30s timeouts

**Root cause.** The Hermes3D SPA opens long-poll and SSE channels (recovery_controller, agent updates, A2A heartbeats) that never go idle within Playwright's 30s default. `waitForLoadState("networkidle")` resolves only after **500 ms with zero network requests**, which never occurs on this app. Six of the W6-6 "errors" were `Test timeout of 30000ms exceeded` — all caused by `networkidle` blocking the test thread.

**Fix.** In `visual-proof.spec.ts::waitForStable()`, drop `waitForLoadState("networkidle")` and rely on `waitForLoadState("domcontentloaded")` + `page.waitForTimeout(quietMs)` (default 500 ms). The per-target `wait_test_id` `toBeVisible` (15s timeout) already proves the route mounted; the 500 ms quiet period absorbs reflow/paint settling.

This matches Playwright's own guidance — the docs flag `networkidle` as **DISCOURAGED** for SPAs of this shape (see source 2 below).

**Verification.** Pre-fix: target `00_user_hermes3d` and `01_dashboard_advanced_a` hit the 30s timeout. Post-fix: same two targets complete in 2-3 seconds and report real diff data.

## Re-run Delta

| | Before W8-14 (PR #189) | After W8-14 |
|---|---|---|
| match | 0 | 0 |
| diff | 0 | **11** |
| error | 11 | **0** |
| skipped-future | 20 | 20 |
| total | 31 | 31 |

All 11 live targets now produce REAL pixel-diff data. The harness end-to-end works.

Summary: `03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json`

## Persistence Record — 11 unfixed diffs

All 11 live targets currently exceed tolerance because the reference PNGs were captured at 1536x1024 while the harness viewport is 1920x1080. This is a **single shared root cause** (viewport mismatch), not 11 independent UI defects. Fix is owned by W6-3 / W6-4 / W6-9 — not W8-14.

| target | diff_pixels | ratio | tolerance | next_fix_attempt |
|---|---|---|---|---|
| 00_user_hermes3d | 597,881 | 0.29 | 0.15 | Re-capture reference at 1920x1080 OR set viewport to 1536x1024 in `playwright.visual.config.ts` use block |
| 01_dashboard_advanced_a | 594,010 | 0.29 | 0.10 | Same — viewport mismatch (W6-3) |
| 02_primary_autopilot_design_gen3d_jobs | 593,688 | 0.29 | 0.12 | Same — viewport mismatch (W6-3) |
| 02_primary_printers_observe_agents_learning | 573,216 | 0.28 | 0.12 | Same — viewport mismatch (W6-3) |
| 02_primary_artifacts_approvals_plugins_roadmap | 637,483 | 0.31 | 0.12 | Same — viewport mismatch (W6-3) |
| 03_settings_subtabs_all | 586,980 | 0.29 | 0.12 | Same — viewport mismatch (W6-3) |
| 03_voice_communication_subtabs | 611,086 | 0.30 | 0.12 | Same — viewport mismatch (W6-3) |
| 04_source_os_60_app_coverage_matrix | 574,432 | 0.28 | 0.12 | Same — viewport mismatch (W6-3) |
| 04_source_os_core_categories | 592,168 | 0.29 | 0.12 | Same — viewport mismatch (W6-3) |
| 04_source_os_remaining_categories | 587,367 | 0.29 | 0.12 | Same — viewport mismatch (W6-3) |
| 07_plugins_skills_mcp_app_connectors | 608,243 | 0.30 | 0.12 | Same — viewport mismatch (W6-3) |

`evidence_path` and `diff_path` for each row point to `test-results/visual/visual-proof-visual-…-actual.png` and `…-diff.png` respectively. `evidence_id` = `summary.json[target=<name>]`.

**Recommended follow-up lane (out of W8-14 scope):** W6-3 picks the canonical viewport. Either (a) regenerate the reference pack at 1920x1080 and update the manifest, or (b) drop `playwright.visual.config.ts use.viewport` to 1536x1024 to match the existing references. Option (b) is cheaper and preserves the user-approved baselines.

## Files Touched

- `03_implementation/ui/playwright.visual.config.ts` — added `globalSetup`, expanded header comment with W8-14 rationale + sources.
- `03_implementation/ui/tests/visual/visual-proof.spec.ts` — `waitForStable()` drops `networkidle`; `snapshotPathSegments()` rewrites paths into `__refs__/`; expanded header comment.
- `03_implementation/ui/tests/visual/global-setup.ts` — NEW. Mirrors `Images-GUI/` -> `tests/visual/__refs__/`, idempotent.
- `03_implementation/ui/tests/visual/__refs__/.gitkeep` — NEW. Keeps the mirror directory in git.
- `03_implementation/ui/tests/visual/.gitignore` — NEW. Excludes the mirrored PNGs from commits.
- `03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json` — UPDATED with first real run (11 diff / 0 error vs prior 0 diff / 11 error).

`visual-proof-reporter.ts` and `visual-targets.json` were unchanged — the reporter already handled `diff` rows correctly (it only never had any to report) and the manifest references stay repo-relative as the source-of-truth address.

## Sources

1. Playwright `testConfig.snapshotPathTemplate` — documents the parent-directory safety check that triggered Bug 1: https://playwright.dev/docs/api/class-testconfig#test-config-snapshot-path-template
2. Playwright `page.waitForLoadState` — documents `networkidle` as **DISCOURAGED**, recommends route-level assertions plus `domcontentloaded`: https://playwright.dev/docs/api/class-page#page-wait-for-load-state

## Constraints Honored

- No secrets touched; `.env` files untouched.
- Hermes3D MCP locks acquired/released via `claude-w8-14-harness-fix` owner.
- W6-6's overall design preserved (manifest format, reporter contract, fail-on-missing-baseline policy, `updateSnapshots: "none"`).
- No `--update-snapshots` invoked.
- No paid services.
