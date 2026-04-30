import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, expect } from '../fixtures/console-strict.js';

test.describe.configure({ retries: 2 });

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CUBE_STL = path.resolve(__dirname, '../fixtures/cube.stl');

test('Truth Gate Validator tab runs Truth Gate on uploaded STL', async ({ page }) => {
  await page.goto('/');

  // Switch to the Truth Gate Validator tab. Gradio renders tab labels as
  // <button role="tab"> with the tab title text.
  const tab = page.getByRole('tab', { name: /Truth Gate Validator/i });
  await expect(tab).toBeVisible();
  await tab.click();

  // Locate the file input. Gradio File component exposes a hidden <input type=file>.
  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.setInputFiles(CUBE_STL);

  // Click the run button.
  await page.getByRole('button', { name: /Run Truth Gate/i }).click();

  // Wait for either PASS or FAIL appearing in the markdown output. The
  // launcher emits "**Overall**: `PASS`" / `FAIL` / `WARN`.
  const overall = page.locator('text=/Overall.*\\b(PASS|FAIL|WARN)\\b/i');
  await expect(overall).toBeVisible({ timeout: 20_000 });

  // Real DOM assertion: the report table header must be present.
  await expect(page.locator('text=/Check.*Status.*Measured.*Threshold/i')).toBeVisible();

  // Assert the JSON code block contains the expected schema field.
  await expect(page.locator('text=/"overall_status"/')).toBeVisible();

  await expect(page).toHaveScreenshot('truth-gate-tab.png', {
    fullPage: true,
    mask: [page.locator('text=/\\d+\\s+bytes/')],
  });
});
