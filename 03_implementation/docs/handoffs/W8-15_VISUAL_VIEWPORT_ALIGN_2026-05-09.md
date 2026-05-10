# W8-15 — Visual-Proof Viewport Alignment (2026-05-09)

**Owner:** claude-w8-15-viewport-align
**Branch:** `claude/w8-15-visual-viewport-align` (off `claude/w8-14-visual-proof-harness-fix`)
**Lock task:** `W8-15-VIEWPORT-ALIGN-2026-05-09`
**Predecessors:**
- W6-6 PR (commits `71dba58`, `378f7b3`) — Playwright visual-proof harness
- W8-12 PR #188 — Vite Fast-Refresh fix (lets the SPA mount)
- W8-14 PR #194 — outputPath escape + networkidle timeout fix; produced first real diff data

## Decision

W8-14 diagnosed all 11 live targets reporting a **uniform ~0.28-0.31 diff ratio** as a single shared root cause: the Playwright viewport was 1920x1080 but the Images-GUI/ reference PNGs were captured at 1536x1024. `toHaveScreenshot` is **not resolution-tolerant** — it reports a pixel diff regardless of content when capture and reference dimensions disagree.

Two options were considered:
- **A.** Set Playwright viewport to 1536x1024 to match references. Single config edit.
- **B.** Re-capture all 31 references at 1920x1080. Requires updating PR #128's Images-GUI pack — out of scope.

**Picked A.** The reference pack is the single source of truth (PR #128 user-approved baseline); the harness conforms. Cheaper, surgical, no baseline churn.

## Patch

`03_implementation/ui/playwright.visual.config.ts:67`

```diff
-    viewport: { width: 1920, height: 1080 },
+    viewport: { width: 1536, height: 1024 },
```

Project name and second `use.viewport` (in the `projects[]` block) updated identically; expanded comment cites the Playwright TestOptions docs.

`03_implementation/ui/tests/visual/visual-targets.json` — top-level `viewport` updated to `{ "width": 1536, "height": 1024 }` and a `reference_viewport: "1536x1024"` field added for clarity. The spec already reads viewport from the config, not the manifest, so this is documentation-only inside the manifest.

`03_implementation/ui/tests/visual/visual-proof.spec.ts` — verified no hardcoded `1920` / `1080` literals; only the TypeScript interface `viewport: { width: number; height: number }` exists, which is generic.

## Re-run Delta

| status | Before W8-15 (PR #194) | After W8-15 |
|---|---|---|
| match | 0 | **9** |
| diff | 11 | **1** |
| error | 0 | **1** |
| skipped-future | 20 | 20 |
| total | 31 | 31 |

Source: `03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json` (overwritten by the new run).

**Ran:** `cd 03_implementation/ui && CI=1 npx playwright test --config playwright.visual.config.ts` — 23.5s. Webserver `scripts/start-e2e-stack.mjs` mounted backend (FastAPI via `create_gui_app()`) + Vite dev (port 5173); the visual reporter wrote the summary at the end of the run.

## Remaining-Diff Targets

Two targets still fail. **Both are reference-dimension mismatches**, not viewport, content, or timing issues — those references were captured at sizes other than the dominant 1536x1024.

### 1. `04_source_os_60_app_coverage_matrix`

| field | value |
|---|---|
| status | diff |
| reference | `Images-GUI/04-source-os/source-os-60-app-coverage-matrix.png` |
| reference_dim | 1672x941 |
| viewport_dim | 1536x1024 |
| diff_pixels_count | 320,638 |
| ratio | 0.19 (tolerance 0.12) |
| diff_image_path | `03_implementation/ui/test-results/visual/visual-proof-visual-04-sou-8fd96-rence-within-tolerance-0-12-visual-chromium-1536x1024/tests/visual/__refs__/04-source-os/source-os-60-app-coverage-matrix-diff.png` |
| evidence_id | `summary.json[target=04_source_os_60_app_coverage_matrix]` |
| hypothesis | Reference captured at a different host/zoom/window size from the rest of the pack. Not font rendering (Playwright preloads fonts; W8-14 verified). Not animation (`animations: "disabled"`). Not stale UI (route mounts the same component as the matching `04_source_os_core_categories` which is 1536x1024). The 0.19 ratio is consistent with the Playwright capture being letterboxed/cropped against a wider, shorter reference. |
| next_fix_attempt | Re-capture this single reference at 1536x1024 in PR #128 v2 (Images-GUI pack maintainer; out of W8-15 scope). Alternative: bump tolerance to 0.20 in `visual-targets.json` for this one entry only — but that masks the underlying capture inconsistency, so re-capture is preferred. |

### 2. `04_source_os_remaining_categories`

| field | value |
|---|---|
| status | error (Playwright bails before computing diff_pixels because dim mismatch + size constraint) |
| reference | `Images-GUI/04-source-os/source-os-remaining-categories.png` |
| reference_dim | 1586x992 |
| viewport_dim | 1536x1024 |
| diff_pixels_count | n/a (capture aborted before diff) |
| diff_image_path | `03_implementation/ui/test-results/visual/visual-proof-visual-04-sou-b6dc2-rence-within-tolerance-0-12-visual-chromium-1536x1024/tests/visual/__refs__/04-source-os/source-os-remaining-categories-diff.png` |
| evidence_id | `summary.json[target=04_source_os_remaining_categories]` |
| hypothesis | Same as above — reference captured at a non-canonical size. The 50px width and 32px height delta suggest a different browser chrome (taller URL bar / different OS). |
| next_fix_attempt | Re-capture at 1536x1024 in PR #128 v2 (out of W8-15 scope). |

Both fixes are reference-pack maintenance, owned by PR #128 follow-up — **not** W8-15 (per brief: "DO NOT update reference PNGs").

## Files Touched

- `03_implementation/ui/playwright.visual.config.ts` — `use.viewport` and `projects[0].use.viewport` 1920x1080 -> 1536x1024; project renamed `visual-chromium-1920x1080` -> `visual-chromium-1536x1024`; added comment citing W8-14 root-cause + Playwright TestOptions doc.
- `03_implementation/ui/tests/visual/visual-targets.json` — `viewport` 1920x1080 -> 1536x1024; added `reference_viewport: "1536x1024"` for reviewer clarity.
- `03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json` — overwritten by the verification run (now records `match=9 diff=1 error=1 skipped-future=20`).
- `03_implementation/docs/handoffs/W8-15_VISUAL_VIEWPORT_ALIGN_2026-05-09.md` — NEW (this doc).

`03_implementation/ui/tests/visual/visual-proof.spec.ts` was inspected and confirmed clean — no hardcoded viewport literals to update.

## Constraints Honored

- No secrets touched; `.env` files untouched.
- Hermes3D MCP locks acquired/released via `claude-w8-15-viewport-align` owner.
- W6-6 design preserved: manifest schema, reporter contract, fail-on-missing-baseline policy, `updateSnapshots: "none"`.
- W8-14 design preserved: globalSetup mirror, `__refs__/` resolution, `domcontentloaded`+500ms quiet wait.
- No `--update-snapshots` invoked (the brief explicitly forbids re-capturing references).
- No paid services.

## Sources

1. Playwright `TestOptions.viewport` reference — defines viewport semantics (single source of truth for the size used during navigation): https://playwright.dev/docs/api/class-testoptions#test-options-viewport
2. `Images-GUI/` folder pack (PR #128) — file dimensions verified via raw PNG IHDR read:
   - 9 of 11 live references are 1536x1024 (the canonical size)
   - `source-os-60-app-coverage-matrix.png` is 1672x941 (outlier)
   - `source-os-remaining-categories.png` is 1586x992 (outlier)
