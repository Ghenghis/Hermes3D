/**
 * W21-MVP-5 — proof that the previously-stale tabs (Files, Artifacts,
 * Agents) re-fetch on the configured polling cadence and re-render
 * when the "backend" returns different data.
 *
 * Strategy
 * --------
 * Each spec stubs the relevant endpoint with a closure-flag the test
 * controls. While the flag is ``false`` the stub returns the first-
 * tick payload; flipping it to ``true`` switches subsequent responses
 * to the second-tick payload. The test mounts the tab, waits for the
 * first-tick UI, flips the flag, then asserts the second-tick UI
 * appears within one poll cycle (PANEL_POLL_MS = 15 s + buffer).
 *
 * Why not a per-call counter? Dashboard mounts on ``/`` and may
 * pre-fetch ``/api/artifacts`` before the operator opens the
 * Artifacts tab — so a naive ``callCount === 1`` rule races with
 * the dashboard's own request and the second-tick rows show up on
 * the very first render. A flag flipped from the test avoids the
 * race entirely.
 *
 * No printer hardware. No fake data: every stubbed row mirrors the
 * live ``artifacts`` / ``agents`` schema verbatim.
 */
import { expect, test, type Route } from "@playwright/test";
import { TAB_FIXTURES, attachErrorCapture, fulfillJson, openTab } from "./_helpers";

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

// 30 s test work + 25 s polling window + buffer.
test.setTimeout(75_000);

// ---------------------------------------------------------------------------
// Artifacts — /api/artifacts list should refresh after the panel poll
// ---------------------------------------------------------------------------

test("Artifacts tab refreshes its list after the polling cadence", async ({ page }) => {
  let secondTickEnabled = false;
  let calls = 0;
  await page.route("**/api/artifacts**", async (route: Route) => {
    const url = route.request().url();
    // Lineage / proof_dir / proof file routes share the prefix; only
    // intercept the bare list endpoint.
    if (url.includes("/api/artifacts/list") || url.includes("/lineage") || url.includes("/proof/")) {
      await route.fallback();
      return;
    }
    calls += 1;
    const tick1 = {
      id: "a-tick1",
      job_id: "job-w21mvp5",
      evidence_type: "mesh",
      agent: "test",
      stage: "MODELING",
      gate: "MODEL_APPROVAL",
      label: "tick1.stl",
      name: "tick1.stl",
      file_path: "/tmp/tick1.stl",
      file_size: 100,
      notes: "{}",
      created_at: "2026-05-12 00:00:00",
    };
    const tick2 = {
      id: "a-tick2",
      job_id: "job-w21mvp5",
      evidence_type: "report",
      agent: "test",
      stage: "MODELING",
      gate: "MODEL_APPROVAL",
      label: "tick2.report.json",
      name: "tick2.report.json",
      file_path: "/tmp/tick2.report.json",
      file_size: 200,
      notes: "{}",
      created_at: "2026-05-12 00:00:01",
    };
    await fulfillJson(route, secondTickEnabled ? [tick1, tick2] : [tick1]);
  });

  await page.goto("/");
  await openTab(page, TAB_FIXTURES.artifacts);
  const root = page.getByTestId("artifacts-root");
  await expect(root).toBeVisible();

  // First render carries tick1, NOT tick2.
  await expect(root).toContainText("tick1.stl");
  await expect(root).not.toContainText("tick2.report.json");

  // Operator-side "backend change": flip the closure flag so the next
  // poll returns the second-tick payload.
  secondTickEnabled = true;

  // Wait for the polling re-fetch (PANEL_POLL_MS = 15 s) to land the
  // second row in the DOM.
  await expect(root).toContainText("tick2.report.json", { timeout: 25_000 });

  // Both rows visible — polling appended, not replaced.
  await expect(root).toContainText("tick1.stl");
  expect(calls).toBeGreaterThanOrEqual(2);
});

// ---------------------------------------------------------------------------
// Files — adapters.getArtifacts is the live source for the Files tab.
// The tab lives in the utility group, so we navigate via ``/#files``.
// ---------------------------------------------------------------------------

test("Files tab refreshes its artifact preview after the polling cadence", async ({ page }) => {
  let secondTickEnabled = false;
  let calls = 0;
  await page.route("**/api/artifacts**", async (route: Route) => {
    const url = route.request().url();
    if (url.includes("/api/artifacts/list") || url.includes("/lineage") || url.includes("/proof/")) {
      await route.fallback();
      return;
    }
    calls += 1;
    const tick1 = {
      id: "f-tick1",
      job_id: "job-files-poll",
      evidence_type: "mesh",
      agent: "test",
      stage: "MODELING",
      gate: "MODEL_APPROVAL",
      label: "files_tick1.stl",
      name: "files_tick1.stl",
      file_path: "/tmp/files_tick1.stl",
      file_size: 50,
      notes: "{}",
      created_at: "2026-05-12 00:00:00",
    };
    const tick2 = {
      id: "f-tick2",
      job_id: "job-files-poll",
      evidence_type: "mesh",
      agent: "test",
      stage: "MODELING",
      gate: "MODEL_APPROVAL",
      label: "files_tick2.stl",
      name: "files_tick2.stl",
      file_path: "/tmp/files_tick2.stl",
      file_size: 80,
      notes: "{}",
      created_at: "2026-05-12 00:00:01",
    };
    await fulfillJson(route, secondTickEnabled ? [tick1, tick2] : [tick1]);
  });

  // Files lives in the utility group at the bottom of the sidebar; its
  // main sidebar button is hidden when the utility group is collapsed.
  // Run #2 (commit 781ad72) showed ``page.goto("/#files")`` alone does
  // not mount ``files-root`` reliably on a fresh page-load — App.tsx
  // reads ``window.location.hash`` in a useEffect that may not see the
  // initial hash before Zustand hydration sets activeTabId. The
  // proven pattern (W18-A1 PICKUP walker, lines 716-719) is: mount
  // the SPA on ``/`` first, then SET ``window.location.hash`` from
  // inside the page so a real ``hashchange`` event fires.
  await page.goto("/");
  await expect(page.getByTestId("dashboard-root")).toBeVisible({ timeout: 15_000 });
  await page.evaluate(() => {
    window.location.hash = "#files";
  });
  const root = page.getByTestId("files-root");
  await expect(root).toBeVisible({ timeout: 15_000 });

  await expect(root).toContainText("files_tick1.stl");
  await expect(root).not.toContainText("files_tick2.stl");

  secondTickEnabled = true;
  await expect(root).toContainText("files_tick2.stl", { timeout: 25_000 });
  expect(calls).toBeGreaterThanOrEqual(2);
});

// ---------------------------------------------------------------------------
// Agents — /api/agents roster should refresh after the poll. Asserts on
// the ``id`` field (rendered by AgentCommandCenter) — the UI does NOT
// render ``display_name`` so we anchor on what is actually visible.
// ---------------------------------------------------------------------------

test("Agents tab refreshes its roster after the polling cadence", async ({ page }) => {
  let secondTickEnabled = false;
  let calls = 0;
  await page.route("**/api/agents", async (route: Route) => {
    calls += 1;
    const tick1Agent = {
      id: "agent-w21mvp5-tick1",
      role: "agent-w21mvp5-tick1",
      status: "active",
      model_provider: "minimax",
      configured: true,
    };
    const tick2Agent = {
      id: "agent-w21mvp5-tick2",
      role: "agent-w21mvp5-tick2",
      status: "idle",
      model_provider: "deepseek",
      configured: true,
    };
    await fulfillJson(route, secondTickEnabled ? [tick1Agent, tick2Agent] : [tick1Agent]);
  });

  await page.goto("/");
  await openTab(page, TAB_FIXTURES.agents);
  const root = page.getByTestId("agents-root");
  await expect(root).toBeVisible();

  // First render: only tick1.
  await expect(root).toContainText("agent-w21mvp5-tick1");
  await expect(root).not.toContainText("agent-w21mvp5-tick2");

  secondTickEnabled = true;

  // Poll should refresh the roster within one cycle.
  await expect(root).toContainText("agent-w21mvp5-tick2", { timeout: 25_000 });
  await expect(root).toContainText("agent-w21mvp5-tick1");
  expect(calls).toBeGreaterThanOrEqual(2);
});
