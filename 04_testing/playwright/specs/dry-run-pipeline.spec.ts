import { test, expect } from '../fixtures/console-strict.js';

test.describe.configure({ retries: 2 });

test('Dry-Run Pipeline tab walks the orchestrator state machine', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('tab', { name: /Pipeline.*Dry-Run/i }).click();

  // The prompt textbox is pre-filled; ensure the button triggers the run.
  await page.locator('#dr-run').click();

  // Scope all summary assertions to the app-owned summary markdown
  // (#dr-summary) so we don't collide with the launcher intro or other tabs.
  const summary = page.locator('#dr-summary');
  await expect(summary).toContainText(/\bJob\b/i, { timeout: 20_000 });
  await expect(summary).toContainText(/Final stage/i);
  await expect(summary).toContainText(/History/i);
  // The state-machine arrow → must be present in the history line.
  await expect(summary).toContainText('→');

  // Visual proof artifact (no pixel-diff; see truth-gate-tab.spec.ts).
  await page.screenshot({
    path: 'test-results/visual/dry-run-pipeline.png',
    fullPage: true,
  });
});
