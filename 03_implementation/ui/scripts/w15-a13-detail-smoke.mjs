#!/usr/bin/env node
/**
 * W15-A13 app-detail smoke — confirms navigating to `#apps/{id}` reaches
 * the AppRegistryTab → AppDetailPanel surface (W6-8 / W8-2).
 */

import { chromium } from "playwright";

const BASE = process.env.W15_A13_BASE_URL ?? "http://localhost:4173";
const APP_ID = process.env.W15_A13_APP_ID ?? "azure_speech_sdk_js";

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1672, height: 941 } });
  const page = await context.newPage();
  await page.goto(`${BASE}/#apps/${APP_ID}`, { waitUntil: "domcontentloaded", timeout: 15000 });
  await page.waitForSelector('[data-testid="apps-root"]', { timeout: 15000 });
  await page.waitForSelector('[data-testid="app-detail-panel"], [data-testid="app-detail-loading"]', { timeout: 12000 });
  await page.waitForTimeout(1200);
  const panelPresent = await page.locator('[data-testid="app-detail-panel"]').count();
  // eslint-disable-next-line no-console
  console.log(JSON.stringify({ appId: APP_ID, panelPresent, ok: panelPresent > 0 }));
  await browser.close();
  process.exit(panelPresent > 0 ? 0 : 1);
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});
