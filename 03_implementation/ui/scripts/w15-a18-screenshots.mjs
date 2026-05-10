/**
 * W15-A18 — capture 3 Voice subtab screenshots.
 *
 * Usage:
 *   1. `npm run build`
 *   2. `npx vite preview --port 5173 --host 127.0.0.1`
 *   3. `node scripts/w15-a18-screenshots.mjs`
 *
 * Output written to `tests/visual/__refs__/w15-a18-voice/*.png`.
 */
import { chromium } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const uiRoot = path.resolve(path.dirname(scriptPath), "..");
const outDir = path.join(uiRoot, "tests", "visual", "__refs__", "w15-a18-voice");
fs.mkdirSync(outDir, { recursive: true });

const BASE = process.env.W15_BASE_URL ?? "http://127.0.0.1:5173";
const VIEWPORT = { width: 1920, height: 1080 };

const subtabs = [
  { hash: "voice/browser", file: "01-browser.png", label: "Browser Voice" },
  { hash: "voice/transcript-history", file: "02-transcript-history.png", label: "Transcript History" },
  { hash: "voice/proof-review", file: "03-proof-review.png", label: "Proof Review" },
];

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: VIEWPORT,
  deviceScaleFactor: 1,
});
const page = await context.newPage();

const errors = [];
page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(`console.error: ${msg.text()}`);
});

let total = 0;
for (const { hash, file, label } of subtabs) {
  const url = `${BASE}/#${hash}`;
  // Use full nav so the hashchange/popstate handlers run on a fresh state.
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="voice-root"]', { timeout: 15_000 });
  // Allow async catalog/provider loaders to settle so the rail isn't empty.
  await page.waitForTimeout(800);
  const out = path.join(outDir, file);
  await page.screenshot({ path: out, fullPage: false });
  console.log(`[w15-a18] captured ${label} → ${out}`);
  total += 1;
}

console.log(`[w15-a18] total screenshots: ${total}`);
console.log(`[w15-a18] console/page errors observed: ${errors.length}`);
if (errors.length > 0) {
  for (const e of errors) console.log(`  - ${e}`);
}

await browser.close();
