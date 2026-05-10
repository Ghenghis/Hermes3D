// Wave 15 A14 — confirm freeze/thaw element is present in autopilot DOM.
import { chromium } from "@playwright/test";
const BASE = process.env.W15_PREVIEW_URL || "http://127.0.0.1:4173";
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1536, height: 1024 } });
  page.on("console", (msg) => { if (msg.type() === "error") console.error(`[err] ${msg.text()}`); });
  await page.goto(`${BASE}/#autopilot`, { waitUntil: "networkidle", timeout: 30_000 });
  await page.waitForTimeout(1500);
  const present = {
    planner: await page.locator('[data-testid="autopilot-planner-queue"]').count(),
    agents: await page.locator('[data-testid="autopilot-agent-activity"]').count(),
    freezeThaw: await page.locator('[data-testid="autopilot-freeze-thaw"]').count(),
    freezeBtn: await page.locator('[data-testid="autopilot-freeze-button"]').count(),
    thawBtn: await page.locator('[data-testid="autopilot-thaw-button"]').count(),
  };
  console.log("DOM presence:", JSON.stringify(present, null, 2));
  // Scroll the freeze/thaw into view and capture.
  const el = page.locator('[data-testid="autopilot-freeze-thaw"]').first();
  await el.scrollIntoViewIfNeeded({ timeout: 5000 }).catch(() => {});
  await page.screenshot({ path: "G:/Github/Hermes3D/03_implementation/proof/screenshots/w15-a14/autopilot-freeze-thaw-detail.png", clip: await el.boundingBox().then((b) => ({ x: Math.max(b.x - 12, 0), y: Math.max(b.y - 12, 0), width: Math.min(b.width + 24, 1536), height: Math.min(b.height + 24, 1024) })) }).catch(async (e) => {
    console.error("bbox screenshot failed:", e.message);
    await page.screenshot({ path: "G:/Github/Hermes3D/03_implementation/proof/screenshots/w15-a14/autopilot-after-scroll.png" });
  });
} finally {
  await browser.close();
}
