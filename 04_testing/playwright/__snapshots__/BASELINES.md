# Snapshot baselines

Visual baselines for the Playwright UI specs live alongside this file in
`__snapshots__/`. Playwright auto-creates per-spec subfolders the first time a
spec runs.

## Generating baselines

The first run on any new machine has no baselines. Generate them with:

```bash
cd 04_testing/playwright
npm test -- --update-snapshots
```

The repo-canonical baselines are produced on Linux + Chromium via
`bash scripts/run-e2e.sh` (CI Layer D). Regenerate from there if a spec drifts.

## When to update

Update baselines **only** when you make an intentional UI change:

1. Make the UI change.
2. Run `npm run test:update`.
3. Inspect the diff in your PR — every changed `.png` should be expected and
   reviewed by a human, not rubber-stamped.
4. Commit the new baselines as part of the same PR.

Reviewers are expected to scrub screenshot diffs in PRs. The
`.gitattributes` entry `*.png binary` (added in PR #2) keeps git diffs
sensible.

## What gets captured

Every `expect(page).toHaveScreenshot(...)` call uses:

- `fullPage: true` — captures the whole document, not just the viewport, so
  tab content below the fold is gated too.
- `mask: [...]` — covers regions known to vary across runs (timestamps,
  generated job IDs, byte counts, temp directory paths). The masks are
  declared per-spec next to the call site so reviewers can see what's
  excluded and why.

Tolerances are configured in `playwright.config.ts` (`maxDiffPixelRatio:
0.02`); raising this should be a deliberate decision, not a flake-quieting
habit.

## Storage policy

Baselines are committed to git. They are part of the kit's deliverable
surface — without them, the screenshot gate is not enforceable on a fresh
clone.
