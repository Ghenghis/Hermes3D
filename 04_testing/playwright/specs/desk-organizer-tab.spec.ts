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

  await page.getByRole('button', { name: /Generate \+ Validate \+ Sign/i }).click();

  // The summary markdown contains "Organizer generated" plus an STL path.
  await expect(page.locator('text=/Organizer generated/i')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('text=/Spec signature/i')).toBeVisible();
  await expect(page.locator('text=/Signed proof envelope/i')).toBeVisible();

  // The STL download component renders an <a> with a downloadable href.
  const stlLink = page.locator('a[href*=".stl"]').first();
  await expect(stlLink).toBeVisible({ timeout: 15_000 });

  await expect(page).toHaveScreenshot('desk-organizer-tab.png', {
    fullPage: true,
    mask: [
      // Mask dynamic temp paths and byte counts.
      page.locator('text=/hermes3d_[a-z0-9]+/'),
      page.locator('text=/\\d+\\s+bytes/'),
    ],
  });
});
