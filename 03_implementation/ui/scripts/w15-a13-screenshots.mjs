#!/usr/bin/env node
/**
 * W15-A13 screenshot capture — Source OS 60-App Matrix.
 *
 * Captures two viewports against the local preview server (port 4173):
 *   - 1672x941 — matches `source-os-60-app-coverage-matrix.png`.
 *   - 1586x992 — matches `source-os-remaining-categories.png`.
 *
 * Also writes a `console_errors.json` summary so the audit can claim
 * "0 console errors" honestly.
 */

import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(__dirname, "..", "tests", "visual", "__w15-a13__");
const BASE = process.env.W15_A13_BASE_URL ?? "http://localhost:4173";

const targets = [
  {
    name: "source-os-60-app-coverage-matrix",
    viewport: { width: 1672, height: 941 },
    hash: "#sources",
  },
  {
    name: "source-os-remaining-categories",
    viewport: { width: 1586, height: 992 },
    hash: "#sources",
  },
  {
    name: "source-os-core-categories",
    viewport: { width: 1536, height: 1024 },
    hash: "#sources",
  },
];

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const consoleSummary = {};
  let failed = false;
  for (const target of targets) {
    const context = await browser.newContext({ viewport: target.viewport });
    const page = await context.newPage();
    const consoleErrors = [];
    const network404 = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    const failedRequests = [];
    page.on("response", (resp) => {
      if (resp.status() === 404) network404.push(resp.url());
      if (resp.status() >= 400) failedRequests.push({ url: resp.url(), status: resp.status() });
    });
    page.on("requestfailed", (req) => {
      failedRequests.push({ url: req.url(), status: "request-failed", reason: req.failure()?.errorText });
    });
    try {
      // Land on the origin first so we can clear localStorage before any
      // stale `h3d.sourceOs.view = "registry"` carries forward.
      await page.goto(BASE, { waitUntil: "domcontentloaded", timeout: 15000 });
      await page.evaluate(() => {
        try {
          window.localStorage.removeItem("h3d.sourceOs.view");
        } catch {
          // ignore
        }
      });
      await page.goto(`${BASE}/${target.hash}`, { waitUntil: "domcontentloaded", timeout: 15000 });
      // Wait for the source-os-root + the new matrix testid.
      await page.waitForSelector('[data-testid="source-os-root"]', { timeout: 15000 });
      // Best-effort — the matrix may not render if backend is offline; do
      // not fail screenshot on a missing card grid.
      await page
        .waitForSelector('[data-testid="source-os-60-app-matrix"]', { timeout: 8000 })
        .catch(() => undefined);
      // Give the fetch effect a moment to finish.
      await page.waitForTimeout(1500);
      // Record the 60/60 truth claim emitted by the matrix.
      consoleSummary[`${target.name}__truth`] = await page
        .locator('[data-testid="matrix-truth-claim"]')
        .first()
        .textContent()
        .catch(() => null);
      consoleSummary[`${target.name}__cardCount`] = await page
        .locator('[data-testid^="app-card-"]')
        .count()
        .catch(() => null);
      const outPath = join(OUT_DIR, `${target.name}.png`);
      await page.screenshot({ path: outPath, fullPage: false });
      consoleSummary[target.name] = {
        viewport: target.viewport,
        path: outPath,
        consoleErrors,
        network404,
        failedRequests,
        passed: consoleErrors.length === 0,
      };
      if (consoleErrors.length > 0) failed = true;
      // eslint-disable-next-line no-console
      console.log(`[w15-a13] captured ${target.name} → ${outPath} (errors=${consoleErrors.length})`);
    } catch (caught) {
      consoleSummary[target.name] = {
        viewport: target.viewport,
        error: caught instanceof Error ? caught.message : String(caught),
      };
      failed = true;
      // eslint-disable-next-line no-console
      console.log(`[w15-a13] FAILED ${target.name}: ${caught.message ?? caught}`);
    } finally {
      await context.close();
    }
  }
  await writeFile(join(OUT_DIR, "console_errors.json"), JSON.stringify(consoleSummary, null, 2));
  await browser.close();
  process.exit(failed ? 1 : 0);
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});
