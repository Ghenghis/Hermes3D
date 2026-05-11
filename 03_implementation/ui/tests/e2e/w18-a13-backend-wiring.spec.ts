/**
 * W18-A13 — Playwright e2e proof for the backend-wiring fixes.
 *
 * Each block drives one of the four FE surfaces touched by the
 * W18-A3 audit and asserts the fix is observable from the rendered
 * DOM. Routes are stubbed with real-shape JSON (mirroring the live
 * backend envelope) so the proof is deterministic and runs against
 * the Vite preview at :5173.
 *
 * Covers:
 *  - Service Health page: 404 from the bridge → honest-blocked banner
 *    with the http_404 reason (FAIL_NOT_WIRED → fixed).
 *  - Service Health page: backend ``{accepted:false,reason:"…"}`` →
 *    banner with the backend reason verbatim.
 *  - Settings → MCP subtab: backend ``{items:[…], total:N}`` with
 *    per-item ``files: [str]`` → one row per file is visible
 *    (FAIL_NOT_WIRED shape mismatch → fixed).
 *  - Autopilot SAFE ACTIONS → "Next gate" 409 honest-blocked →
 *    "Honest-blocked" prefix + the truthful next.message is surfaced
 *    (FAIL_NOT_WIRED 409 swallowing → fixed).
 *
 * Operator freeze:
 *  No printer-control writes are performed. The Autopilot test fakes
 *  the readiness gate via route stubs only.
 */
import { expect, test, type Route, type Page } from "@playwright/test";
import { attachErrorCapture, fulfillJson, readErrors } from "./_helpers";

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

/**
 * W18-A13 — local error allowlist.
 *
 * The W18-A13 specs intentionally stub the backend to return 404 / 409
 * so the FE banners and honest-blocked surfaces can be exercised. Chromium
 * emits a console "Failed to load resource: the server responded with a
 * status of <code>" line for each stubbed non-2xx, which the shared
 * `assertNoErrors` helper would treat as a hard failure. This local
 * variant tolerates the specific stubbed status codes while still
 * enforcing zero unexpected console errors / page errors.
 */
async function assertNoUnexpectedErrors(
  page: Page,
  allowedStatusCodes: ReadonlyArray<number> = [],
): Promise<void> {
  const errors = await readErrors(page);
  const remaining = errors.filter((line) => {
    return !allowedStatusCodes.some((code) =>
      line.includes(`Failed to load resource: the server responded with a status of ${code}`),
    );
  });
  expect(remaining, remaining.join("\n")).toEqual([]);
}

// ---------------------------------------------------------------------------
// Service Health — honest-blocked banner
// ---------------------------------------------------------------------------

test("W18-A13: ServiceHealthPage renders honest-blocked banner on 404", async ({ page }) => {
  await page.route("**/api/health/services", (route: Route) =>
    route.fulfill({ status: 404, contentType: "text/plain", body: "Not Found" }),
  );
  await page.goto("/#health");
  await expect(page.getByTestId("service-health-root")).toBeVisible({ timeout: 15_000 });
  const banner = page.getByTestId("service-health-blocked-banner");
  await expect(banner).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("service-health-blocked-reason")).toHaveText("http_404");
  await page.screenshot({
    path: "test-results/w18-a13/service-health-404.png",
    fullPage: true,
    animations: "disabled",
  });
  // 404 from the stubbed route emits a console "Failed to load resource"
  // line — that's the precise condition we're testing the banner under,
  // so the local allowlist tolerates it.
  await assertNoUnexpectedErrors(page, [404]);
});

test("W18-A13: ServiceHealthPage surfaces backend reason on accepted=false", async ({ page }) => {
  await page.route("**/api/health/services", (route: Route) =>
    fulfillJson(route, {
      accepted: false,
      status: "blocked",
      reason: "no_health_probes_registered",
      results: [],
    }),
  );
  await page.goto("/#health");
  await expect(page.getByTestId("service-health-root")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("service-health-blocked-banner")).toBeVisible();
  await expect(page.getByTestId("service-health-blocked-reason")).toHaveText(
    "no_health_probes_registered",
  );
  await page.screenshot({
    path: "test-results/w18-a13/service-health-blocked.png",
    fullPage: true,
    animations: "disabled",
  });
  await assertNoUnexpectedErrors(page);
});

// ---------------------------------------------------------------------------
// Settings → MCP subtab — items[] / files[] envelope
// ---------------------------------------------------------------------------

test("W18-A13: McpSubtab reads data.items and expands files[] into rows", async ({ page }) => {
  await page.route("**/api/mcp/locks", (route: Route) =>
    fulfillJson(route, {
      accepted: true,
      status: "ready",
      reason: null,
      items: [
        {
          lock_id: "lock-w18-a13-A",
          owner: "w18-a13",
          files: [
            "03_implementation/ui/src/api/adapters.live.ts",
            "03_implementation/ui/src/api/hermes3dClient.ts",
          ],
          role: "agent",
          task_id: "W18-A13-BACKEND-WIRING-FIXES-2026-05-11",
          acquired_utc: "2026-05-11T10:30:00Z",
          expires_utc: new Date(Date.now() + 60 * 60_000).toISOString(),
          is_stale: false,
        },
        {
          lock_id: "lock-w18-a13-B",
          owner: "w18-a3",
          files: ["03_implementation/docs/handoffs/W18-A3_AUDIT.md"],
          role: "audit",
          task_id: null,
          acquired_utc: "2026-05-11T10:30:00Z",
          expires_utc: null,
          is_stale: true,
        },
      ],
      total: 2,
    }),
  );
  // The settings root hosts the MCP subtab; deep-link to the MCP
  // subtab so the SettingsPage URL-hash sync mounts <McpSubtab />.
  await page.goto("/#settings/mcp");
  await expect(page.getByTestId("settings-mcp")).toBeVisible({ timeout: 15_000 });
  // Three rows (one for each file across both locks):
  const rowsA = page.locator('[data-testid="settings-mcp-row-w18-a13"]');
  await expect(rowsA).toHaveCount(2);
  const rowsB = page.locator('[data-testid="settings-mcp-row-w18-a3"]');
  await expect(rowsB).toHaveCount(1);
  // Stale badge present:
  await expect(page.getByText("1 stale")).toBeVisible();
  await page.screenshot({
    path: "test-results/w18-a13/mcp-subtab-items-files.png",
    fullPage: true,
    animations: "disabled",
  });
  await assertNoUnexpectedErrors(page);
});

// ---------------------------------------------------------------------------
// Autopilot — 409 honest-blocked surface
// ---------------------------------------------------------------------------

test("W18-A13: Autopilot 409 renders Honest-blocked + truthful next.message", async ({ page }) => {
  // The Autopilot tab loads readiness + guardrails on mount. Stub both
  // with "all ready" so the SAFE ACTIONS button is enabled — the next-
  // gate POST is the one we want to exercise.
  await page.route("**/api/autopilot/readiness", (route: Route) =>
    fulfillJson(route, [
      {
        id: "model_dir",
        name: "Model directory",
        status: "ready",
        detail: null,
        fix_target: "settings",
      },
      {
        id: "gcode_dir",
        name: "G-code directory",
        status: "ready",
        detail: null,
        fix_target: "settings",
      },
    ]),
  );
  await page.route("**/api/autopilot/guardrails", (route: Route) =>
    fulfillJson(route, []),
  );
  // The honest-blocked 409 response from the next-gate handler.
  await page.route("**/api/autopilot/next-gate", (route: Route) =>
    route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({
        detail: {
          next: {
            id: "slicer_plugin",
            name: "Slicer plugin",
            ready: false,
            message: "No slicer plugin active.",
          },
        },
      }),
    }),
  );
  // Suppress the window.confirm() so the spec is non-interactive.
  await page.exposeFunction("__hermes3dConfirmYes", () => true);
  await page.addInitScript(() => {
    // Replace confirm with a stub returning true so postAction proceeds.
    window.confirm = () => true;
  });
  await page.goto("/#autopilot");
  await expect(page.getByTestId("autopilot-root")).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Autopilot To Next Safe Gate" }).click();
  const msg = page.getByTestId("autopilot-action-message");
  await expect(msg).toBeVisible({ timeout: 5_000 });
  await expect(msg).toContainText("Honest-blocked");
  await expect(msg).toContainText("Slicer plugin");
  await expect(msg).toContainText("No slicer plugin active.");
  await page.screenshot({
    path: "test-results/w18-a13/autopilot-409-honest-blocked.png",
    fullPage: true,
    animations: "disabled",
  });
  // 409 from the stubbed next-gate route is the honest-blocked verdict
  // we're testing for; the corresponding console "Failed to load…409"
  // line is allowed.
  await assertNoUnexpectedErrors(page, [409]);
});
