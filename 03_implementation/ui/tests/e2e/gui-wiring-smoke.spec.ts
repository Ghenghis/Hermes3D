/**
 * W6-5 Playwright smoke spec.
 *
 * Asserts the GUI wiring layer renders the Hermes Agent banner with a
 * version tag pulled from `/api/agents/update/status`. The route is
 * intercepted with a real-shape stub so the test is independent of which
 * Hermes Agent tag the local checkout actually has.
 *
 * No-fake-data contract: the stub uses production-shape JSON (matches the
 * backend's `_repo_state` payload). If the route handler returned a Hermes
 * tag here, the banner must render it verbatim.
 */
import { expect, test } from "@playwright/test";
import { fulfillJson } from "./_helpers";

const STUB_STATUS = {
  available: true,
  repo_url: "https://github.com/NousResearch/Hermes-Agent.git",
  checkout_path: "G:/Github/hermes-agent-fresh",
  repo_ready: true,
  current: {
    repo_ready: true,
    commit: "abcdef0123456",
    exact_tag: "v0.13.0",
    nearest_tag: "v0.13.0",
    branch: "main",
    dirty: false,
    dirty_entries: [],
  },
  latest_release: {
    tag: "v2026.5.7",
    name: "Tenacity Release",
    published_at: "2026-05-07T00:00:00Z",
    html_url: "https://github.com/NousResearch/Hermes-Agent/releases/tag/v2026.5.7",
    source: "github_releases",
  },
  outdated: true,
  outdated_by: 1,
  pending_tags: ["v2026.5.7"],
  backup_available: false,
  latest_backup: null,
  strategy: "staged_backup_then_tag_checkout",
  rollback: "Rollback checks out the recorded backup tag/commit.",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/agents/update/status", async (route) => {
    await fulfillJson(route, STUB_STATUS);
  });
});

test("Hermes Agent banner renders v0.13 tag from /api/agents/update/status", async ({ page }) => {
  await page.goto("/");
  const banner = page.getByTestId("hermes-agent-banner");
  await expect(banner).toBeVisible({ timeout: 15_000 });
  // Banner reports the live `exact_tag` (NOT a hardcoded string).
  await expect(banner).toHaveAttribute("data-version", "v0.13.0");
  await expect(banner).toContainText("v0.13.0");
});

test("Banner reports outdated state when latest_release tag > exact_tag", async ({ page }) => {
  await page.goto("/");
  const banner = page.getByTestId("hermes-agent-banner");
  await expect(banner).toBeVisible({ timeout: 15_000 });
  // Outdated = true -> banner exposes an `update` chip + amber tone.
  await expect(banner).toHaveAttribute("data-outdated", "true");
  await expect(banner).toContainText("update");
});

test("Banner falls back to 'offline' when status endpoint 5xx", async ({ page }) => {
  await page.unroute("**/api/agents/update/status");
  await page.route("**/api/agents/update/status", async (route) => {
    await route.fulfill({ status: 503, body: "{}" });
  });
  await page.goto("/");
  const banner = page.getByTestId("hermes-agent-banner");
  await expect(banner).toBeVisible({ timeout: 15_000 });
  await expect(banner).toHaveAttribute("data-version", "offline");
});
