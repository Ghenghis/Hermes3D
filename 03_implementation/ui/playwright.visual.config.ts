/**
 * W6-6 / W8-14 / W15-A9 Playwright config for the visual-oracle harness.
 *
 * W15-A9 changes versus the W8-14 baseline:
 *  - **Per-target viewport projects (cap 2).** We read every unique
 *    viewport that appears in `visual-targets.json` and emit one Playwright
 *    `project` per (width, height) so a target whose reference PNG was
 *    captured at 1672x941 (an outlier) can be diffed at the same
 *    resolution as its reference. The spec opts into the right project by
 *    matching the `viewport` annotation each test sets in `test.use({...})`.
 *  - **Reporter stays the same module** (`visual-proof-reporter.ts`) but
 *    the per-region + 404 + console-error rows arrive via new annotation
 *    types that the reporter understands.
 *  - **globalSetup unchanged** beyond its existing idempotent Images-GUI
 *    mirror — see `tests/visual/global-setup.ts`.
 *
 * Why per-target projects rather than per-test `test.use`?
 *   Playwright resolves the `viewport` for screenshot tolerance ONLY at
 *   project-level — `test.use({ viewport })` rebuilds the browser context
 *   per test, which works for navigation but does NOT propagate to the
 *   tolerance baseline used by `toHaveScreenshot`. To get a clean
 *   per-target viewport we have to materialize a project for each unique
 *   viewport that the manifest declares.
 *
 * Sources cited (per W15-A9 contract):
 *  1. Playwright per-project configuration:
 *     https://playwright.dev/docs/test-projects
 *  2. Chromatic / Percy visual-test harness pattern — per-viewport
 *     projects + region crops:
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

function projectName(v: ManifestViewport): string {
  return `visual-chromium-${v.width}x${v.height}`;
}

/**
 * Collect every unique viewport across the manifest:
 *   - the top-level default viewport (always included);
 *   - every per-target viewport override on a `live` target.
 *
 * `future` targets are skipped at runtime so we do not need to spawn a
 * project just for their viewport.
 */
function collectViewports(manifest: Manifest): ManifestViewport[] {
  const seen = new Map<string, ManifestViewport>();
  const add = (v: ManifestViewport): void => {
    const key = `${v.width}x${v.height}`;
    if (!seen.has(key)) seen.set(key, v);
  };
  add(manifest.viewport ?? DEFAULT_VIEWPORT);
  for (const t of manifest.targets ?? []) {
    if (t.status === "live" && t.viewport && Number.isFinite(t.viewport.width) && Number.isFinite(t.viewport.height)) {
      add(t.viewport);
    }
  }
  return Array.from(seen.values());
}

const manifest = loadManifest();
const viewports = collectViewports(manifest);

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
    deviceScaleFactor: 1,
    headless: true,
    screenshot: "only-on-failure",
    trace: "off",
    // Default viewport mirrors the manifest's top-level value so projects
    // that do not override it inherit the W8-15 1536x1024 reference shape.
    viewport: manifest.viewport ?? DEFAULT_VIEWPORT,
  },
  // W15-A9 cap 2 — one project per unique manifest viewport. Tests opt in
  // by tagging themselves with the matching project name; the spec selects
  // the right project from the manifest via `test.describe.configure` /
  // `test.use({ viewport })` and matches by the project name we emit here.
  projects: viewports.map((v) => ({
    name: projectName(v),
    use: {
      ...devices["Desktop Chrome"],
      viewport: v,
      deviceScaleFactor: 1,
    },
  })),
  webServer: {
    command: "node scripts/start-e2e-stack.mjs",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
