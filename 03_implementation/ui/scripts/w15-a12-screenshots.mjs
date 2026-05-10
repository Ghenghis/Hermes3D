#!/usr/bin/env node
/**
 * W15-A12 — Dashboard modes screenshot script.
 *
 * Captures Simple/Advanced/Custom dashboards at 1536x1024 against the built
 * vite preview server. Uses Playwright's bundled Chromium. Network failures
 * for live adapters are silently swallowed by the components (they render
 * empty-states with no console errors), so this script only needs a static
 * preview server to validate render structure.
 */
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const uiRoot = path.resolve(here, "..");
const outputDir = path.join(uiRoot, "test-results", "w15-a12-screenshots");
mkdirSync(outputDir, { recursive: true });

const PORT = 5174;
const baseUrl = `http://127.0.0.1:${PORT}`;

function startPreview() {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      "npx",
      ["vite", "preview", "--port", String(PORT), "--host", "127.0.0.1", "--strictPort"],
      { cwd: uiRoot, stdio: ["ignore", "pipe", "pipe"], shell: true },
    );
    let started = false;
    const onData = (chunk) => {
      const text = String(chunk);
      // Strip ANSI color codes then look for the "Local:" listing line.
      const clean = text.replace(/\[[0-9;]*m/g, "");
      if (!started && /127\.0\.0\.1:\s*5174/.test(clean)) {
        started = true;
        // Give vite a beat to start listening on the socket.
        setTimeout(() => resolve(proc), 500);
      }
      process.stdout.write(`[preview] ${text}`);
    };
    proc.stdout.on("data", onData);
    proc.stderr.on("data", (chunk) => process.stderr.write(`[preview-err] ${chunk}`));
    proc.on("exit", (code) => {
      if (!started) reject(new Error(`preview exited with code ${code} before ready`));
    });
    // safety timeout
    setTimeout(() => {
      if (!started) reject(new Error("preview did not start in 30s"));
    }, 30_000);
  });
}

async function run() {
  if (!existsSync(path.join(uiRoot, "dist", "index.html"))) {
    throw new Error("dist/index.html missing — run `npm run build` first");
  }

  const previewProcess = await startPreview();
  let browser;
  const errors = [];
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      viewport: { width: 1536, height: 1024 },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
    page.on("console", (msg) => {
      if (msg.type() !== "error") return;
      const text = msg.text();
      // Filter network-resource failures (preview server has no backend).
      // The Dashboard components are expected to handle these with empty
      // states; they are not JS errors and not in scope for this PR.
      if (/Failed to load resource/.test(text)) return;
      if (/ERR_CONNECTION_REFUSED/.test(text)) return;
      if (/net::ERR_/.test(text)) return;
      errors.push(`console.error: ${text}`);
    });

    const modes = ["simple", "advanced", "custom"];
    for (const mode of modes) {
      await page.goto(`${baseUrl}/#dashboard:${mode}`);
      // Wait for any dashboard root to mount (advanced reuses legacy
      // Dashboard root markup so we accept either testid).
      await page
        .waitForSelector('[data-testid="dashboard-root"], [data-testid="dashboard-advanced-root"]', {
          timeout: 10_000,
        })
        .catch(() => null);
      // Brief settle for live data lazy-resolves.
      await page.waitForTimeout(800);
      const file = path.join(outputDir, `dashboard-${mode}.png`);
      await page.screenshot({ path: file, fullPage: false });
      console.log(`saved ${file}`);
    }
  } finally {
    if (browser) await browser.close();
    previewProcess.kill();
  }

  if (errors.length > 0) {
    console.warn(`Captured ${errors.length} console errors during screenshot:`);
    for (const err of errors) console.warn(`  - ${err}`);
  } else {
    console.log("0 console errors");
  }
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
