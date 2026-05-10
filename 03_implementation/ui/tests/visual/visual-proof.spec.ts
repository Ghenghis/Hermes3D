/**
 * W6-6 Playwright visual-proof harness against the Images-GUI/ reference pack.
 *
 * For each entry in visual-targets.json with status === "live":
 *   1. Navigate to target.route on the live dev server (via webServer)
 *   2. Wait for wait_test_id, networkidle, and a 500ms quiet period
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
 *
 * No-fake / no-paid contract:
 *  - This spec NEVER auto-updates reference PNGs. The visual config sets
 *    updateSnapshots: "none". Refresh requires an explicit operator action
 *    (run with --update-snapshots, then review diff in the PR).
 *  - This spec only reports diff data; component fixes are out of scope and
 *    are owned by W6-3 / W6-4.
 *  - No paid services are used; everything runs against the local dev server
 *    started by scripts/start-e2e-stack.mjs.
 *
 * Snapshot path resolution: snapshotPathTemplate is configured to "{arg}{ext}"
 * so that an array-form arg passed to toHaveScreenshot is path.join'd as-is
 * and then resolved relative to the playwright config dir (UI_ROOT). We pass
 * the array as a relative chain back to the repo root and into Images-GUI/,
 * which keeps the actual reference PNG as the single source of truth.
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
const targetsFile = JSON.parse(fs.readFileSync(TARGETS_PATH, "utf-8")) as VisualTargetsFile;

/**
 * Wait for the SPA to settle: networkidle plus quietMs of no nav.
 * 500ms is the W5-3 smoke convention; tighten via env var if needed.
 */
async function waitForStable(page: Page, quietMs = 500): Promise<void> {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(quietMs);
}

/**
 * Build the snapshot-name array for toHaveScreenshot from a reference path.
 * Reference paths in visual-targets.json are repo-relative (e.g.
 * "Images-GUI/01-dashboard-modes/advanced-dashboard-a.png"). We need a path
 * relative to the playwright config dir (UI_ROOT) so that the configured
 * snapshotPathTemplate "{arg}{ext}" resolves to the actual reference PNG.
 */
function snapshotPathSegments(referenceRepoRel: string): string[] {
  const referenceAbs = path.resolve(REPO_ROOT, referenceRepoRel);
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
