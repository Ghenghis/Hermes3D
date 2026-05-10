/**
 * W6-6 Playwright config dedicated to visual proof against Images-GUI/.
 * W8-14 patch: globalSetup mirrors Images-GUI/ into tests/visual/__refs__/
 * because Playwright forbids snapshot paths that escape the test root
 * ("The outputPath is not allowed outside of the parent directory.").
 *
 * Differences from playwright.e2e.config.ts:
 *  - testDir: tests/visual (so the visual harness is a separate suite)
 *  - updateSnapshots: "none"  -> never auto-create or auto-update reference
 *    PNGs; missing baselines fail the test (refresh is an explicit operator
 *    action via --update-snapshots flag)
 *  - snapshotPathTemplate: "{arg}{ext}"  -> when a test calls
 *    toHaveScreenshot([...segments]) Playwright path.joins the segments and
 *    resolves the result against this configDir. After W8-14 the segments
 *    point INSIDE tests/visual/__refs__/ so the resolution is forward-only
 *    and Playwright accepts it.
 *  - globalSetup: tests/visual/global-setup.ts mirrors Images-GUI/ into
 *    tests/visual/__refs__/ (idempotent; size+mtime check skips on re-run).
 *  - reporter: visual-proof-reporter.ts emits the JSON summary to
 *    03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json.
 *
 * Sources:
 *  - Playwright snapshot/visual-comparison docs:
 *      https://playwright.dev/docs/test-snapshots
 *  - testConfig.snapshotPathTemplate reference:
 *      https://playwright.dev/docs/api/class-testconfig#test-config-snapshot-path-template
 *  - Playwright globalSetup reference:
 *      https://playwright.dev/docs/test-global-setup-teardown
 *  - page.waitForLoadState reference (W8-14 used to swap networkidle for
 *    domcontentloaded + 500ms quiet period in visual-proof.spec.ts):
 *      https://playwright.dev/docs/api/class-page#page-wait-for-load-state
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/visual",
  // W8-14: mirror Images-GUI/ -> tests/visual/__refs__/ before any test runs.
  globalSetup: "./tests/visual/global-setup.ts",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  // "none" prevents Playwright from ever writing or updating reference PNGs.
  // To intentionally refresh the baseline an operator must run with
  // --update-snapshots (which overrides this) and review the diff in PR.
  updateSnapshots: "none",
  // {arg}{ext} sends the array passed to toHaveScreenshot directly through
  // path.join + path.resolve(configDir, ...). Combined with W8-14's spec
  // change to emit __refs__/-relative segments, this resolves to a forward-
  // only path under the test root (no parent-dir escape).
  snapshotPathTemplate: "{arg}{ext}",
  reporter: [
    ["list"],
    ["./tests/visual/visual-proof-reporter.ts"],
  ],
  outputDir: "test-results/visual",
  expect: {
    // Diff threshold per pixel; per-target maxDiffPixelRatio overrides this
    // expect-wide knob. Animations disabled to remove a major source of flake.
    toHaveScreenshot: {
      animations: "disabled",
      threshold: 0.2,
      maxDiffPixelRatio: 0.1,
    },
  },
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "off",
  },
  projects: [
    {
      name: "visual-chromium-1920x1080",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1920, height: 1080 },
        deviceScaleFactor: 1,
      },
    },
  ],
  webServer: {
    command: "node scripts/start-e2e-stack.mjs",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
