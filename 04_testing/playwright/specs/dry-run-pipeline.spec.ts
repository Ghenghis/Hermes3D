import { test, expect } from '../fixtures/console-strict.js';

test.describe.configure({ retries: 2 });

test('Dry-Run Pipeline tab walks the orchestrator state machine', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('tab', { name: /Pipeline.*Dry-Run/i }).click();

  // The prompt textbox is pre-filled; ensure the button triggers the run.
  await page.getByRole('button', { name: /Walk state machine/i }).click();

  // Real DOM assertions: the launcher emits Job, Final stage, and History lines.
  await expect(page.locator('text=/\\bJob\\b/i')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('text=/Final stage/i')).toBeVisible();
  await expect(page.locator('text=/History/i')).toBeVisible();
  // The state-machine arrow → must be present in the history line.
  await expect(page.locator('text=/→/')).toBeVisible();

  await expect(page).toHaveScreenshot('dry-run-pipeline.png', {
    fullPage: true,
    mask: [
      // Job IDs and history are dynamic.
      page.locator('text=/Job.*`[a-z0-9-]+`/i'),
    ],
  });
});
