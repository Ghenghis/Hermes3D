// Wave 15 A14 — Primary Tabs A screenshot harness.
//
// Captures 4 PNGs (Autopilot, Design, Gen3D, Jobs) at 1536x1024 against
// the local vite preview at http://127.0.0.1:4173. Saves to
// proof/screenshots/w15-a14/<tab>.png in the repo root.
//
// Run manually:
//   node tests/screenshots/w15-a14-capture.mjs
//
// This script is referenced from the PR body; it is NOT wired into CI.
import { chromium } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "../../../..");
const OUT_DIR = path.join(REPO_ROOT, "03_implementation/proof/screenshots/w15-a14");
fs.mkdirSync(OUT_DIR, { recursive: true });

const TABS = [
  { id: "autopilot", hash: "#autopilot" },
  { id: "design", hash: "#design" },
  { id: "gen3d", hash: "#gen3d" },
  { id: "jobs", hash: "#jobs" },
];

const BASE = process.env.W15_PREVIEW_URL || "http://127.0.0.1:4173";

const browser = await chromium.launch();
try {
  const context = await browser.newContext({ viewport: { width: 1536, height: 1024 } });
  const page = await context.newPage();
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      console.error(`[console.error] ${msg.text()}`);
    }
  });
  for (const tab of TABS) {
    const target = `${BASE}/${tab.hash}`;
    console.log(`-> ${target}`);
    await page.goto(target, { waitUntil: "networkidle", timeout: 30_000 });
    // Allow react state + intervals to settle.
    await page.waitForTimeout(1500);
    const outPath = path.join(OUT_DIR, `${tab.id}.png`);
    await page.screenshot({ path: outPath, fullPage: false });
    console.log(`   wrote ${outPath}`);
    if (tab.id === "autopilot") {
      const fullOut = path.join(OUT_DIR, `${tab.id}-fullpage.png`);
      await page.screenshot({ path: fullOut, fullPage: true });
      console.log(`   wrote ${fullOut}`);
      // Also capture a taller viewport so freeze/thaw fits in one frame.
      const tallContext = await browser.newContext({ viewport: { width: 1536, height: 1400 } });
      const tallPage = await tallContext.newPage();
      await tallPage.goto(target, { waitUntil: "networkidle", timeout: 30_000 });
      await tallPage.waitForTimeout(1500);
      const tallOut = path.join(OUT_DIR, `${tab.id}-1536x1400.png`);
      await tallPage.screenshot({ path: tallOut, fullPage: false });
      console.log(`   wrote ${tallOut}`);
      await tallContext.close();
    }
  }
  await context.close();
} finally {
  await browser.close();
}
