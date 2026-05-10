#!/usr/bin/env node
/**
 * W15-A13 navigation smoke — verifies clicking an AppCard sets
 * `window.location.hash = "apps/{id}"` so the AppRegistryTab detail
 * panel (W8-2) takes over the apps surface.
 */

import { chromium } from "playwright";

const BASE = process.env.W15_A13_BASE_URL ?? "http://localhost:4173";

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1672, height: 941 } });
  const page = await context.newPage();
  await page.goto(BASE, { waitUntil: "domcontentloaded", timeout: 15000 });
  await page.evaluate(() => window.localStorage.removeItem("h3d.sourceOs.view"));
  await page.goto(`${BASE}/#sources`, { waitUntil: "domcontentloaded", timeout: 15000 });
  await page.waitForSelector('[data-testid="source-os-60-app-matrix"]', { timeout: 15000 });
  await page.waitForTimeout(800);
  // Pick the first AppCard whose testid starts with app-card- and is NOT
  // a launch button.
  const card = page.locator('article[data-testid^="app-card-"]').first();
  const cardId = await card.getAttribute("data-testid");
  await card.click();
  await page.waitForTimeout(400);
  const hash = await page.evaluate(() => window.location.hash);
  const ok = hash.startsWith("#apps/");
  // eslint-disable-next-line no-console
  console.log(JSON.stringify({ cardId, hash, ok }));
  await browser.close();
  process.exit(ok ? 0 : 1);
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});
