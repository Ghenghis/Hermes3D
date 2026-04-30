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

  // Locate the file input via the app-owned hook (#tg-stl-input wraps Gradio's
  // hidden <input type=file>).
  const fileInput = page.locator('#tg-stl-input input[type="file"]');
  await fileInput.setInputFiles(CUBE_STL);

  // Click the run button.
  await page.locator('#tg-run').click();

  // Scope the "Overall: PASS|FAIL|WARN" assertion to the summary markdown
  // (#tg-summary). The JSON code block (#tg-json) also contains an
  // overall_status field, which previously caused strict-mode violations.
  const summary = page.locator('#tg-summary');
  await expect(summary).toContainText(/Overall.*\b(PASS|FAIL|WARN)\b/i, {
    timeout: 20_000,
  });

  // The Truth Gate report table renders inside #tg-summary. Verify all four
  // canonical column headers are present; matching role+text is stable across
  // Gradio versions and markdown-renderer changes.
  for (const header of ['Check', 'Status', 'Measured', 'Threshold']) {
    await expect(
      summary.getByRole('columnheader', { name: new RegExp(`^${header}$`) }),
    ).toBeVisible();
  }

  // The JSON code block (#tg-json) carries the full report schema.
  await expect(page.locator('#tg-json')).toContainText('overall_status');

  // Visual proof: capture the rendered page as a per-run artifact. We do not
  // pixel-diff against a baseline (cross-platform font + sub-pixel rendering
  // varies between Windows/Linux runners), but the artifact is preserved for
  // human review and bundled into the proof envelope.
  await page.screenshot({ path: 'test-results/visual/truth-gate-tab.png', fullPage: true });
});
