import { expect, test } from "@playwright/test";
import {
  TAB_FIXTURES,
  assertNoErrors,
  assertNoFakeVisibleText,
  attachErrorCapture,
  fulfillJson,
} from "./_helpers";

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

test("Roadmap is excluded from primary nav but reachable via hash route", async ({ page }) => {
  await page.route("**/api/roadmap/status", (route) => fulfillJson(route, []));
  await page.route("**/api/roadmap/tab-completion", (route) =>
    fulfillJson(route, {
      updated_at: "2026-05-05",
      roadmap_path: "03_implementation/ROADMAP.md",
      contract: ["Visible controls must call live routes or expose exact blocked reasons."],
      tabs: [],
      next_packages: [],
      references: [],
      finish_queue: [],
    }),
  );
  await page.route("**/api/modules/runtime/setup-queue", (route) =>
    fulfillJson(route, {
      accepted: true,
      status: "planned",
      count: 0,
      counts: {
        runtime_ready: 0,
        source_ready: 0,
        runner_not_registered: 0,
        source_install_available: 0,
        runtime_repair_required: 0,
        blocked: 0,
      },
      execution_mode: "plan_only_until_safe_runner_registered",
      agent_gate: "Hermes Agents may consume this queue after proof.",
      records: [],
      proof_event_id: null,
    }),
  );
  await page.route("**/api/proof/events", (route) => fulfillJson(route, { saved: true }));

  await page.goto("/");
  await expect(page.getByRole("button", { name: "Roadmap", exact: true })).toHaveCount(0);

  await page.goto("/#roadmap");
  await expect(page.getByTestId(TAB_FIXTURES.roadmap.rootTestId)).toBeVisible();
  await assertNoFakeVisibleText(page, TAB_FIXTURES.roadmap.rootTestId);
  await assertNoErrors(page);
});
