import { test, expect } from '../fixtures/console-strict.js';

test.describe.configure({ retries: 2 });

test('Generate Desk Organizer tab produces a downloadable STL + signed proof', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('tab', { name: /Generate Desk Organizer/i }).click();

  // Sliders default to valid values per the launcher; we only need to nudge
  // one to confirm form interactivity is live.
  const widthSlider = page.getByRole('slider', { name: /Width \(mm\)/i }).first();
  await expect(widthSlider).toBeVisible();
  // Click then arrow-key to bump to a deterministic value (180 -> 185).
  await widthSlider.focus();
  await page.keyboard.press('ArrowRight');

  await page.locator('#og-generate').click();

  // Scope summary assertions to the app-owned summary markdown (#og-summary).
  const summary = page.locator('#og-summary');
  await expect(summary).toContainText(/Organizer generated/i, { timeout: 30_000 });
  await expect(summary).toContainText(/Spec signature/i);
  await expect(summary).toContainText(/Signed proof envelope/i);

  // The STL download component (#og-stl-download) renders a Gradio File with
  // an <a> pointing to the produced .stl. Match the link inside that hook so
  // we don't pick up unrelated links elsewhere on the page.
  const stlLink = page.locator('#og-stl-download a[href*=".stl"]').first();
  await expect(stlLink).toBeVisible({ timeout: 15_000 });

  // Visual proof artifact (no pixel-diff; see truth-gate-tab.spec.ts).
  await page.screenshot({
    path: 'test-results/visual/desk-organizer-tab.png',
    fullPage: true,
  });
});
