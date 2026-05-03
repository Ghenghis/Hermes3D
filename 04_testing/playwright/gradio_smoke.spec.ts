import { test, expect } from '@playwright/test';

/**
 * Layer-D3 — Gradio launcher headless smoke (Phase 5.1).
 *
 * Complements the existing Layer-D suite under `specs/` (which exercises
 * specific tabs in depth) with a single broad smoke that hits the launcher
 * happy path and asserts the major panels are visible.
 *
 * Booted by `bash scripts/run-e2e.sh` — same as Layer-D — and runs against
 * the Gradio launcher at `process.env.HERMES3D_UI_URL` (default
 * `http://127.0.0.1:7860`).
 *
 * Why a separate spec + config (vs. just adding under specs/):
 *   - Layer-D's existing config (`playwright.config.ts`, testDir `./specs`)
 *     stays unchanged — no risk to the 7 already-passing specs.
 *   - This smoke is intentionally non-blocking on first 5 CI runs
 *     (`continue-on-error: true` in `.github/workflows/ci.yml`) so flake
 *     data can be collected before promoting it to a hard gate (per
 *     ADR-013 §4).
 *
 * Hard scope:
 *   - Read-only navigation only. No tool invocations, no print actions,
 *     no provider config edits, no file uploads.
 *   - No deps on real printers, real LLM providers, or network egress.
 *   - Pure UI presence + navigation + console-error count.
 */

const PANEL_NAMES = [
  /Dashboard/i,
  /Print[\s-]?Queue/i,
  /Fleet/i,
  /Proof/i,
];

test.describe('Gradio launcher — Layer D3 smoke', () => {
  test('boots, mounts shell, exposes the core panels, no uncaught errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => pageErrors.push(String(err)));

    const response = await page.goto('/', { waitUntil: 'networkidle' });
    expect(response, 'launcher returned a response').not.toBeNull();
    expect(response?.ok(), 'launcher returned 2xx').toBeTruthy();

    // Either the page title or an `<h1>` should self-identify. Gradio's
    // own DOM may render the title slowly, so we tolerate either signal.
    const title = (await page.title()).toLowerCase();
    const titleMatches = /hermes\s*3d/i.test(title);
    if (!titleMatches) {
      const h1 = await page.locator('h1').first().innerText().catch(() => '');
      expect(h1, 'h1 contains "Hermes3D"').toMatch(/hermes\s*3d/i);
    }

    // Wait for the Gradio shell to mount. Gradio renders inside
    // `<gradio-app>` (web component) on most versions; tolerate either
    // the WC tag or a top-level `[data-testid="gradio-app"]`.
    await page.waitForSelector('gradio-app, [data-testid="gradio-app"], main', {
      timeout: 15_000,
    });

    // Every major panel name must be visible somewhere in the tab strip.
    // `getByRole('tab')` is the stable selector when Gradio renders tabs.
    // Fallback to a generic text query if the role isn't yet attached.
    for (const name of PANEL_NAMES) {
      const tab = page.getByRole('tab', { name }).first();
      const text = page.getByText(name).first();
      await expect(tab.or(text), `panel "${name.source}" visible`).toBeVisible({
        timeout: 10_000,
      });
    }

    // Capture an artifact for reviewer eyeball regardless of pass/fail.
    await page.screenshot({
      path: 'test-results/gradio-smoke-shell.png',
      fullPage: false,
    });

    // Soft assertions on console: warn but don't fail on noisy 3rd-party
    // logs (Gradio emits a few during boot). We DO fail on uncaught
    // page-level errors (`window.onerror` / unhandled rejection).
    if (consoleErrors.length > 0) {
      // eslint-disable-next-line no-console
      console.warn(`Gradio smoke saw ${consoleErrors.length} console.error entries:`, consoleErrors.slice(0, 5));
    }
    expect(pageErrors, 'no uncaught page errors during boot').toEqual([]);
  });

  test('basic tab navigation does not throw', async ({ page }) => {
    const pageErrors: string[] = [];
    page.on('pageerror', (err) => pageErrors.push(String(err)));

    await page.goto('/', { waitUntil: 'networkidle' });

    // Click each tab if present; tolerate Gradio versions where labels
    // aren't role=tab.
    for (const name of PANEL_NAMES) {
      const candidate = page.getByRole('tab', { name }).first();
      const fallback = page.getByText(name).first();
      const target = (await candidate.count()) > 0 ? candidate : fallback;
      if (await target.count() === 0) continue;
      await target.click({ trial: false, timeout: 5_000 }).catch(() => {});
      await page.waitForTimeout(200);
    }

    expect(pageErrors, 'no uncaught errors during tab tour').toEqual([]);
  });
});
