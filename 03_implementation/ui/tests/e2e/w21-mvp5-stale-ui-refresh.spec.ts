/**
 * W21-MVP-5 — proof that the previously-stale tabs (Files, Artifacts,
 * Agents) re-fetch on the configured polling cadence and re-render
 * when the "backend" returns different data.
 *
 * Strategy
 * --------
 * Stub the relevant fetch endpoints with a route handler that
 * increments a counter and returns a tick-aware response. Open the
 * tab, observe the initial render, then wait until the poll fires at
 * least once more. The stub returns different rows on the second-plus
 * call so the assertion is "the UI now shows the second response",
 * not "the request was made twice" (route-only green is explicitly
 * forbidden).
 *
 * Cadence: ``PANEL_POLL_MS = 15_000`` in src/hooks/_useQuery.ts. We
 * give Playwright 25 s per polling assertion so the test still
 * tolerates CI hiccups. Total wall time per spec: ~30-45 s.
 *
 * No printer hardware. No fake data: the rows we stub are
 * legitimate-shape artifact / file / agent records that mirror the
 * production schema verbatim.
 */
import { expect, test, type Route } from "@playwright/test";
import { TAB_FIXTURES, attachErrorCapture, fulfillJson, openTab } from "./_helpers";

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

// 30 s + buffer for the 15 s poll cycle.
test.setTimeout(60_000);

// ---------------------------------------------------------------------------
// Artifacts — /api/artifacts list should refresh after the panel poll
// ---------------------------------------------------------------------------

test("Artifacts tab refreshes its list after the polling cadence", async ({ page }) => {
  let callCount = 0;
  await page.route("**/api/artifacts**", async (route: Route) => {
    const url = route.request().url();
    // The lineage endpoint and proof manifest share the /api/artifacts
    // prefix; route only the bare list endpoint here so unrelated calls
    // pass through untouched. Lineage / proof_dir / proof file routes
    // are caught by the `/list` and `/lineage` / `/proof/` suffixes.
    if (url.includes("/api/artifacts/list") || url.includes("/lineage") || url.includes("/proof/")) {
      await route.fallback();
      return;
    }
    callCount += 1;
    // Schema mirrors a live ``artifacts`` row from var/hermes3d.db.
    // evidence_type must be in the UI's ArtifactType allow-list
    // (mesh / report / screenshot / g-code / …). The Files tab
    // renders ``a.name`` which the adapter derives from
    // ``value.name ?? basename(file_path)``.
    const rows = callCount === 1
      ? [{
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
        }]
      : [
          {
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
          },
          {
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
          },
        ];
    await fulfillJson(route, rows);
  });

  await page.goto("/");
  await openTab(page, TAB_FIXTURES.artifacts);
  const root = page.getByTestId("artifacts-root");
  await expect(root).toBeVisible();

  // First render — only tick1 visible.
  await expect(root).toContainText("tick1.stl");
  await expect(root).not.toContainText("tick2.report.json");

  // Wait for at least one polling re-fetch to fire and the UI to
  // re-render with the second-call payload. PANEL_POLL_MS = 15 s.
  await expect(root).toContainText("tick2.report.json", { timeout: 25_000 });

  // Both tick1 + tick2 are now visible (polling appended, not replaced
  // erroneously).
  await expect(root).toContainText("tick1.stl");
  expect(callCount).toBeGreaterThanOrEqual(2);
});

// ---------------------------------------------------------------------------
// Files — adapters.getArtifacts is the live source for the Files tab;
// reuse the artifact stub to prove the Files tab repaints.
// ---------------------------------------------------------------------------

test("Files tab refreshes its artifact preview after the polling cadence", async ({ page }) => {
  let callCount = 0;
  await page.route("**/api/artifacts**", async (route: Route) => {
    const url = route.request().url();
    if (url.includes("/api/artifacts/list") || url.includes("/lineage") || url.includes("/proof/")) {
      await route.fallback();
      return;
    }
    callCount += 1;
    const rows = callCount === 1
      ? [{
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
        }]
      : [
          {
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
          },
          {
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
          },
        ];
    await fulfillJson(route, rows);
  });

  await page.goto("/");
  await openTab(page, TAB_FIXTURES.files);
  const root = page.getByTestId("files-root");
  await expect(root).toBeVisible();

  // Initial render carries tick1.
  await expect(root).toContainText("files_tick1.stl");
  await expect(root).not.toContainText("files_tick2.stl");

  // After the poll fires, the second row appears.
  await expect(root).toContainText("files_tick2.stl", { timeout: 25_000 });
  expect(callCount).toBeGreaterThanOrEqual(2);
});

// ---------------------------------------------------------------------------
// Agents — /api/agents roster + /api/notifications should refresh after the poll
// ---------------------------------------------------------------------------

test("Agents tab refreshes its roster after the polling cadence", async ({ page }) => {
  let callCount = 0;
  await page.route("**/api/agents", async (route: Route) => {
    callCount += 1;
    const agents = callCount === 1
      ? [{
          id: "agent-tick1",
          role: "factory-operator",
          status: "idle",
          display_name: "AGENT_TICK1_PERSONA",
          model_provider: "minimax",
          configured: true,
        }]
      : [
          {
            id: "agent-tick1",
            role: "factory-operator",
            status: "active",
            display_name: "AGENT_TICK1_PERSONA",
            model_provider: "minimax",
            configured: true,
          },
          {
            id: "agent-tick2",
            role: "modeling-agent",
            status: "idle",
            display_name: "AGENT_TICK2_PERSONA",
            model_provider: "deepseek",
            configured: true,
          },
        ];
    await fulfillJson(route, agents);
  });

  await page.goto("/");
  await openTab(page, TAB_FIXTURES.agents);
  const root = page.getByTestId("agents-root");
  await expect(root).toBeVisible();

  // First render — only AGENT_TICK1.
  await expect(root).toContainText("AGENT_TICK1_PERSONA");
  await expect(root).not.toContainText("AGENT_TICK2_PERSONA");

  // After the poll fires, the second agent appears.
  await expect(root).toContainText("AGENT_TICK2_PERSONA", { timeout: 25_000 });
  expect(callCount).toBeGreaterThanOrEqual(2);
});
