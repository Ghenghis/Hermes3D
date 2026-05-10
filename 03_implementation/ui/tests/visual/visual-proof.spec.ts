/**
 * W6-6 Playwright visual-proof harness against the Images-GUI/ reference pack.
 * W8-14 patch:
 *   - reference PNGs are now read from tests/visual/__refs__/ (mirrored from
 *     Images-GUI/ by global-setup.ts). Playwright rejects snapshot paths that
 *     escape the test root with "outputPath is not allowed outside of the
 *     parent directory" — keeping references inside the test root sidesteps
 *     that safety check while preserving Images-GUI/ as the source of truth.
 *   - waitForStable() drops `waitForLoadState("networkidle")` (the SPA's
 *     long-poll and SSE channels keep the network busy beyond 30s), in favor
 *     of `domcontentloaded` + a 500ms quiet timeout. Per the Playwright docs
 *     (https://playwright.dev/docs/api/class-page#page-wait-for-load-state)
 *     `networkidle` is "DISCOURAGED" precisely for SPAs of this shape.
 *
 * For each entry in visual-targets.json with status === "live":
 *   1. Navigate to target.route on the live dev server (via webServer)
 *   2. Wait for wait_test_id (15s timeout), domcontentloaded, and a 500ms
 *      quiet period for the SPA to settle.
 *   3. Call expect(page).toHaveScreenshot([...path]) with the target's
 *      tolerance as maxDiffPixelRatio. Playwright uses its bundled
 *      pixelmatch implementation; diff PNGs land under test-results/ when a
 *      target exceeds tolerance.
 *
 * Targets with status === "future" call test.skip() with a reason; the JSON
 * reporter still records a "skipped" row so reviewers see all 31 references.
 *
 * Sources cited:
 *  - Playwright snapshot/visual-comparison docs:
 *      https://playwright.dev/docs/test-snapshots
 *  - Playwright toHaveScreenshot API:
 *      https://playwright.dev/docs/api/class-pageassertions#page-assertions-to-have-screenshot
 *  - Playwright page.waitForLoadState reference (W8-14 networkidle fix):
 *      https://playwright.dev/docs/api/class-page#page-wait-for-load-state
 *
 * No-fake / no-paid contract:
 *  - This spec NEVER auto-updates reference PNGs. The visual config sets
 *    updateSnapshots: "none". Refresh requires an explicit operator action
 *    (run with --update-snapshots, then review diff in the PR).
 *  - The __refs__/ mirror is one-way: Images-GUI/ -> __refs__/. Never the
 *    reverse. globalSetup verifies size+mtime parity on every run.
 *  - This spec only reports diff data; component fixes are out of scope and
 *    are owned by W6-3 / W6-4.
 *  - No paid services are used; everything runs against the local dev server
 *    started by scripts/start-e2e-stack.mjs.
 *
 * Snapshot path resolution: snapshotPathTemplate is "{arg}{ext}" so the array
 * passed to toHaveScreenshot is path.join'd and resolved relative to the
 * playwright config dir (UI_ROOT). After W8-14 we pass a forward-only chain
 * into tests/visual/__refs__/<category>/<file>.png — fully inside the test
 * root, so Playwright accepts it.
 */
import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

interface VisualTarget {
  target: string;
  reference: string;
  route: string;
  status: "live" | "future";
  tolerance: number;
  wait_test_id?: string;
  notes?: string;
}

interface VisualTargetsFile {
  description: string;
  owner: string;
  created: string;
  tolerance_default: number;
  viewport: { width: number; height: number };
  targets: VisualTarget[];
}

const HERE = path.dirname(fileURLToPath(import.meta.url));
const TARGETS_PATH = path.join(HERE, "visual-targets.json");
const UI_ROOT = path.resolve(HERE, "..", "..");
const REPO_ROOT = path.resolve(UI_ROOT, "..", "..");
// W8-14: refs are mirrored INSIDE the test root so snapshotPathTemplate
// "{arg}{ext}" resolves forward-only and Playwright accepts the path.
// global-setup.ts populates this directory before any tests run.
const REFS_LOCAL_ROOT = path.join(HERE, "__refs__");
const targetsFile = JSON.parse(fs.readFileSync(TARGETS_PATH, "utf-8")) as VisualTargetsFile;

/**
 * Wait for the SPA to settle: domcontentloaded plus quietMs of no nav.
 *
 * W8-14: networkidle was removed because the Hermes3D SPA opens long-poll
 * and SSE channels (recovery_controller, agent updates, A2A) that never go
 * idle within Playwright's 30s default. Playwright's docs flag networkidle
 * as DISCOURAGED for SPAs of this shape:
 *   https://playwright.dev/docs/api/class-page#page-wait-for-load-state
 * The wait_test_id assertion in each test (toBeVisible, 15s) plus a 500ms
 * quiet period is sufficient to prove the route mounted and rendered.
 */
async function waitForStable(page: Page, quietMs = 500): Promise<void> {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(quietMs);
}

/**
 * Build the snapshot-name array for toHaveScreenshot from a reference path.
 *
 * Reference paths in visual-targets.json are repo-relative (e.g.
 * "Images-GUI/01-dashboard-modes/advanced-dashboard-a.png"). W8-14 changes
 * the resolution to point at the LOCAL mirror under tests/visual/__refs__/
 * (populated by global-setup.ts). The returned chain is relative to UI_ROOT
 * (the playwright config dir) and stays entirely INSIDE the test root, which
 * sidesteps Playwright's "outputPath is not allowed outside of the parent
 * directory" check on snapshotPathTemplate "{arg}{ext}".
 */
function snapshotPathSegments(referenceRepoRel: string): string[] {
  // Strip the leading "Images-GUI/" segment so the rest maps 1:1 into __refs__/.
  const subPath = referenceRepoRel.replace(/^Images-GUI[\\/]+/i, "");
  const referenceAbs = path.join(REFS_LOCAL_ROOT, subPath);
  const fromUiRoot = path.relative(UI_ROOT, referenceAbs);
  // Keep the .png on the last segment so toHaveScreenshot infers the ext;
  // splitting by both separators tolerates Windows backslashes.
  return fromUiRoot.split(/[\\/]+/);
}

for (const target of targetsFile.targets) {
  const referenceAbs = path.resolve(REPO_ROOT, target.reference);

  test.describe(`visual: ${target.target}`, () => {
    if (target.status === "future") {
      // Future targets are owned by other Wave 6 lanes (W6-3 dashboard mode
      // switcher, W6-4 Action Window, theme switcher, custom dashboards).
      // We register them as skipped tests so the reporter row exists.
      // eslint-disable-next-line playwright/no-skipped-test
      test.skip(
        `${target.target} future-target — owned by Wave 6 lane 3/4 (${target.notes ?? "future"})`,
        async () => {
          test.info().annotations.push({
            type: "visual-proof",
            description: JSON.stringify({
              target: target.target,
              reference: target.reference,
              route: target.route,
              tolerance: target.tolerance,
              status: "skipped-future",
              reason: target.notes ?? "future",
            }),
          });
        },
      );
      return;
    }

    if (!fs.existsSync(referenceAbs)) {
      // eslint-disable-next-line playwright/no-skipped-test
      test.skip(
        `${target.target} missing-reference at ${target.reference}`,
        async () => {
          test.info().annotations.push({
            type: "visual-proof",
            description: JSON.stringify({
              target: target.target,
              reference: target.reference,
              route: target.route,
              tolerance: target.tolerance,
              status: "skipped-missing-reference",
            }),
          });
        },
      );
      return;
    }

    test(`matches reference within tolerance ${target.tolerance}`, async ({ page }) => {
      // Annotate up-front so the reporter has the contract row even if the
      // test fails mid-flight.
      test.info().annotations.push({
        type: "visual-proof-target",
        description: JSON.stringify({
          target: target.target,
          reference: target.reference,
          route: target.route,
          tolerance: target.tolerance,
        }),
      });

      await page.goto(target.route);
      if (target.wait_test_id) {
        await expect(
          page.getByTestId(target.wait_test_id),
          `${target.target} wait_test_id ${target.wait_test_id} mounts`,
        ).toBeVisible({ timeout: 15_000 });
      }
      await waitForStable(page, 500);

      const segments = snapshotPathSegments(target.reference);

      await expect(page).toHaveScreenshot(segments, {
        fullPage: true,
        animations: "disabled",
        maxDiffPixelRatio: target.tolerance,
      });

      // After a successful match, append a final "match" annotation. If the
      // assertion above failed, control never reaches here and the reporter
      // records the row as a "diff" failure.
      test.info().annotations.push({
        type: "visual-proof-result",
        description: JSON.stringify({
          target: target.target,
          status: "match",
          tolerance: target.tolerance,
        }),
      });
    });
  });
}
