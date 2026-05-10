/**
 * Palette preview screenshots (W15-A17).
 *
 * Renders a self-contained card-grid that shows every named palette
 * applied to a representative slice of the GUI (surfaces, text, primary
 * button). Saves a PNG per palette + a collage to
 * `tests/visual/__snapshots__/palette-preview/`.
 *
 * Run via:
 *   npx playwright test tests/visual/palettes-preview.spec.ts --project=chromium
 *
 * This is intentionally NOT a screenshot-comparison test — its only job
 * is to produce artefacts attached to the PR.
 */
import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { NAMED_PALETTES } from "../../src/theme/palettes";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const OUT_DIR = path.join(
  __dirname,
  "__snapshots__",
  "palette-preview",
);

function ensureOutDir(): void {
  fs.mkdirSync(OUT_DIR, { recursive: true });
}

function previewHtml(): string {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>W15-A17 palette preview</title>
    <style>
      * { box-sizing: border-box; }
      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        margin: 0;
        padding: 24px;
        background: var(--h3d-color-background);
        color: var(--h3d-color-text-primary);
      }
      .card {
        background: var(--h3d-color-surface);
        border: 1px solid var(--h3d-color-border);
        border-radius: 8px;
        padding: 18px;
        max-width: 460px;
      }
      h1 { margin: 0 0 4px; font-size: 18px; font-weight: 600; }
      .blurb { color: var(--h3d-color-text-secondary); font-size: 13px; margin-bottom: 16px; }
      .row {
        display: flex; gap: 8px; align-items: center; margin: 6px 0;
        font-size: 13px;
      }
      .swatch {
        width: 36px; height: 16px; border-radius: 3px;
        border: 1px solid var(--h3d-color-border);
      }
      .surface2 {
        background: var(--h3d-color-surface-2);
        border: 1px solid var(--h3d-color-border);
        border-radius: 4px;
        padding: 8px 10px;
        font-size: 12px;
        color: var(--h3d-color-text-secondary);
        margin: 12px 0;
      }
      .btn {
        background: var(--h3d-color-primary);
        color: var(--h3d-color-background);
        font-weight: 600;
        border: none;
        border-radius: 4px;
        padding: 8px 14px;
        font-size: 13px;
        cursor: pointer;
      }
      .id { font-family: ui-monospace, Menlo, monospace; font-size: 11px; color: var(--h3d-color-text-secondary); }
    </style>
  </head>
  <body>
    <div class="card" data-testid="preview-card">
      <h1 id="label"></h1>
      <div class="blurb" id="blurb"></div>
      <div class="row"><div class="swatch" id="sw-bg"></div>background</div>
      <div class="row"><div class="swatch" id="sw-surface"></div>surface</div>
      <div class="row"><div class="swatch" id="sw-primary"></div>primary</div>
      <div class="surface2">Secondary text on a surface-2 panel.</div>
      <button class="btn">Save preferences</button>
      <div class="id" id="id"></div>
    </div>
  </body>
</html>`;
}

test.describe("W15-A17 named palette previews", () => {
  test.beforeAll(() => {
    ensureOutDir();
  });

  for (const palette of NAMED_PALETTES) {
    test(`renders the ${palette.id} palette`, async ({ page }) => {
      await page.setViewportSize({ width: 540, height: 380 });
      await page.setContent(previewHtml());
      await page.evaluate((p) => {
        const root = document.documentElement;
        for (const [k, v] of Object.entries(p.cssVars)) {
          root.style.setProperty(k, v);
        }
        document.getElementById("label")!.textContent = p.label;
        document.getElementById("blurb")!.textContent = p.blurb;
        document.getElementById("id")!.textContent = `palette · ${p.id}`;
        (document.getElementById("sw-bg") as HTMLElement).style.background =
          p.cssVars["--h3d-color-background"];
        (document.getElementById("sw-surface") as HTMLElement).style.background =
          p.cssVars["--h3d-color-surface"];
        (document.getElementById("sw-primary") as HTMLElement).style.background =
          p.cssVars["--h3d-color-primary"];
      }, palette);

      const card = page.getByTestId("preview-card");
      await expect(card).toBeVisible();
      const out = path.join(OUT_DIR, `${palette.id}.png`);
      await card.screenshot({ path: out });
      expect(fs.existsSync(out)).toBe(true);
    });
  }
});
