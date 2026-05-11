/**
 * W6-6 / W8-14 / W15-A9 / W16-A Playwright config for the visual-oracle
 * harness.
 *
 * W16-A correction (2026-05-10)
 * -----------------------------
 * The W15-A9 design materialized one Playwright `project` per unique
 * viewport from `visual-targets.json` and assumed that the spec's
 * `test.use({ viewport })` would only propagate the viewport to the
 * browser context for navigation, NOT to the `toHaveScreenshot` tolerance
 * baseline. That assumption is wrong: per the official Playwright docs
 * for `TestOptions.viewport` and the canonical "Override viewport size"
 * recipe, `test.use({ viewport })` IS the supported primitive for setting
 * a per-test viewport, and it propagates to the rendered page that
 * `toHaveScreenshot` captures.
 *
 * The real consequence of the multi-project design was a regression: by
 * default Playwright runs EVERY test in EVERY project, so a target whose
 * reference PNG was captured at 1536x1024 ran a second time inside the
 * `visual-chromium-1586x992` project (and a third inside
 * `visual-chromium-1672x941`), inheriting the alien project viewport and
 * failing with "Expected an image 1536px by 1024px, received 1586px by
 * 992px". W15-FINAL-4 A21 saw 22 LIVE rows fail for this reason.
 *
 * Fix: collapse to a single `project` and rely on the spec's
 * unconditional `test.use({ viewport: target.viewport ?? targetsFile.viewport })`
 * + an explicit `page.setViewportSize` before `page.goto` to pin every
 * test to its declared reference shape. The manifest viewport overrides
 * (1672x941, 1586x992) now actually drive the page render rather than
 * spawning a parallel project run.
 *
 * W15-A9 capabilities preserved:
 *  - **Reporter** (`visual-proof-reporter.ts`) unchanged — region + 404 +
 *    console-error rows still arrive via annotations.
 *  - **globalSetup** unchanged — idempotent Images-GUI -> __refs__/ mirror.
 *
 * Sources cited (per W15-A9 / W16-A contract):
 *  1. Playwright `TestOptions.viewport` + `Page.setViewportSize`:
 *     https://playwright.dev/docs/api/class-testoptions#test-options-viewport
 *     https://playwright.dev/docs/api/class-page#page-set-viewport-size
 *  2. Chromatic / Percy visual-test harness pattern — pinning per-test
 *     viewport rather than per-project for variable-size collage refs:
 *     https://www.chromatic.com/docs/visual-tests/
 *
 * No-fake / no-paid contract:
 *  - `updateSnapshots: "none"` keeps the baseline as a manual operator
 *    action; no run can quietly overwrite Images-GUI/.
 *  - No paid services; everything runs against the local dev server.
 */
import { defineConfig, devices } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TARGETS_PATH = path.join(HERE, "tests", "visual", "visual-targets.json");

interface ManifestViewport {
  width: number;
  height: number;
}
interface ManifestTarget {
  target: string;
  status: "live" | "future";
  viewport?: ManifestViewport;
}
interface Manifest {
  viewport: ManifestViewport;
  targets: ManifestTarget[];
}

/** Default viewport used when the manifest is unreadable. Matches W8-15. */
const DEFAULT_VIEWPORT: ManifestViewport = { width: 1536, height: 1024 };

function loadManifest(): Manifest {
  try {
    return JSON.parse(fs.readFileSync(TARGETS_PATH, "utf-8")) as Manifest;
  } catch {
    return {
      viewport: DEFAULT_VIEWPORT,
      targets: [],
    };
  }
}

const manifest = loadManifest();
const defaultViewport: ManifestViewport = manifest.viewport ?? DEFAULT_VIEWPORT;

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
    // W18-A14 — no-skip harness: fail the run if any test is skipped without
    // the `@hardware-not-authorized` marker. See tests/_reporters/w18-no-skip-reporter.ts.
    ["./tests/_reporters/w18-no-skip-reporter.ts"],
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
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "off",
    // Default viewport mirrors the manifest's top-level value. The spec
    // overrides it per-target via `test.use({ viewport })` + an explicit
    // page.setViewportSize, so this is only the inherited default for the
    // tests whose manifest entry has no per-target viewport field.
    viewport: defaultViewport,
  },
  // W16-A — single canonical project. Per-target viewport variation is
  // owned by the spec via `test.use({ viewport })` (canonical Playwright
  // primitive). Materializing a project per unique manifest viewport
  // caused every test to run in every project, so non-override targets
  // re-ran inside outlier-viewport projects and failed with a baseline
  // size mismatch. See module-level docstring for full diagnosis.
  projects: [
    {
      name: "visual-chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: defaultViewport,
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
