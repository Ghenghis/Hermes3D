import { expect, test } from "@playwright/test";
import {
  assertNoErrors,
  assertNoFakeVisibleText,
  attachErrorCapture,
  fulfillJson,
} from "./_helpers";

/**
 * W6-8 — App Registry Status panel + detail page E2E.
 *
 * Routes (standalone hash gate, mounted by main.tsx):
 *   #apps           → AppStatusPanel
 *   #apps/<id>      → AppDetailPanel
 *
 * Backend contract under test (canonical W6-7 paths):
 *   GET  /api/source-os/modules                 → list of AppEntry
 *   GET  /api/source-os/modules/{id}            → AppEntry detail
 *   POST /api/source-os/modules/{id}/run-proof  → RegistryRunProofResponse
 */

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

const SAMPLE_APPS = [
  {
    id: "hermes-agent",
    name: "Hermes Agent",
    current_version: "0.12.5",
    tested_versions: ["0.12.5", "0.12.4", "0.11.0"],
    license: { spdx: "Apache-2.0", label: "Apache 2.0" },
    update_lane: "stable",
    lifecycle: "stable",
    last_proof: {
      proof_event_id: "proof-1",
      status: "pass",
      at: "2026-05-09T18:00:00Z",
      reason: "all gates green",
    },
    rollback_supported: true,
    description: "Local agent runtime.",
    proof_command: "python -m hermes_cli.main --help",
  },
  {
    id: "hermes-desktop",
    name: "Hermes Desktop",
    current_version: "0.7.0-canary.3",
    tested_versions: ["0.7.0-canary.2"],
    license: { spdx: "MIT" },
    update_lane: "canary",
    lifecycle: "canary",
    last_proof: {
      proof_event_id: "proof-2",
      status: "pending",
      at: "2026-05-09T17:30:00Z",
      reason: null,
    },
    rollback_supported: false,
    description: "Tauri desktop shell.",
  },
  {
    id: "legacy-bridge",
    name: "Legacy Bridge",
    current_version: "1.4.7",
    tested_versions: ["1.4.7"],
    license: { spdx: "Unknown" },
    update_lane: "frozen",
    lifecycle: "frozen",
    last_proof: {
      proof_event_id: "proof-3",
      status: "fail",
      at: "2026-05-09T12:00:00Z",
      reason: "checksum mismatch on artifact bundle",
    },
    rollback_supported: true,
    description: null,
  },
];

const SAMPLE_DETAIL = {
  ...SAMPLE_APPS[0],
  recent_proofs: [
    {
      proof_event_id: "proof-1",
      status: "pass",
      at: "2026-05-09T18:00:00Z",
      reason: "all gates green",
    },
    {
      proof_event_id: "proof-0",
      status: "pass",
      at: "2026-05-08T18:00:00Z",
      reason: "previous proof",
    },
  ],
  rollback_runbook_url: "https://example.local/runbooks/hermes-agent",
  metadata: { release_channel: "stable" },
};

async function stubApps(page: import("@playwright/test").Page) {
  // appsClient (W9-2k) tries `/api/apps` first then falls back to
  // `/api/source-os/modules`. Stub both so the GUI sees fixture data
  // regardless of which endpoint the client picks. Mirrors the dual
  // stub in `gui-breadth-pages.spec.ts`.
  const runProofPayload = {
    accepted: true,
    proof_event_id: "proof-new",
    status: "pending",
    reason: "queued",
  };
  const proofSweepPayload = {
    accepted: true,
    status: "completed",
    proof_event_id: "proof-sweep-1",
    summary: {
      total: 3,
      pass: 1,
      fail: 1,
      timeout: 0,
      error: 0,
      not_set: 1,
    },
  };
  await page.route("**/api/apps", (route) => {
    if (route.request().method() === "GET") {
      return fulfillJson(route, SAMPLE_APPS);
    }
    return route.continue();
  });
  await page.route("**/api/apps/run-proofs", (route) => {
    if (route.request().method() === "POST") {
      return fulfillJson(route, proofSweepPayload);
    }
    return route.continue();
  });
  await page.route("**/api/apps/hermes-agent", (route) =>
    fulfillJson(route, SAMPLE_DETAIL),
  );
  await page.route("**/api/apps/*/run-proof", (route) => {
    if (route.request().method() === "POST") {
      return fulfillJson(route, runProofPayload);
    }
    return route.continue();
  });
  await page.route("**/api/source-os/modules", (route) => {
    if (route.request().method() === "GET") {
      return fulfillJson(route, SAMPLE_APPS);
    }
    return route.continue();
  });
  await page.route("**/api/source-os/modules/hermes-agent", (route) =>
    fulfillJson(route, SAMPLE_DETAIL),
  );
  await page.route("**/api/source-os/modules/*/run-proof", (route) => {
    if (route.request().method() === "POST") {
      return fulfillJson(route, runProofPayload);
    }
    return route.continue();
  });
}

test("App registry table renders three apps with mixed lifecycles", async ({ page }) => {
  await stubApps(page);
  await page.goto("/#apps");

  const root = page.getByTestId("apps-root");
  await expect(root).toBeVisible();

  const panel = page.getByTestId("app-status-panel");
  await expect(panel).toBeVisible();

  // Three rows, one per fixture app.
  await expect(page.getByTestId("app-row-hermes-agent")).toBeVisible();
  await expect(page.getByTestId("app-row-hermes-desktop")).toBeVisible();
  await expect(page.getByTestId("app-row-legacy-bridge")).toBeVisible();

  // Lifecycle visibility: stable + canary + frozen badges all appear.
  const badges = panel.locator("span", { hasText: /stable|canary|frozen/i });
  await expect(badges.first()).toBeVisible();

  // Rollback button only on apps with rollback_supported = true.
  await expect(page.getByTestId("app-row-hermes-agent-rollback")).toBeVisible();
  await expect(page.getByTestId("app-row-legacy-bridge-rollback")).toBeVisible();
  await expect(page.getByTestId("app-row-hermes-desktop-rollback")).toHaveCount(0);

  await assertNoFakeVisibleText(page, "apps-root");
  await assertNoErrors(page);
});

test("Run proof shows success toast and updates state", async ({ page }) => {
  await stubApps(page);
  await page.goto("/#apps");

  await page.getByTestId("app-row-hermes-agent-run-proof").click();

  // Toast renders inside aria-live region.
  const toast = page.getByTestId("app-status-toast-success");
  await expect(toast).toBeVisible();
  await expect(toast).toContainText(/Hermes Agent/);
  await expect(toast).toContainText(/proof requested/i);

  await assertNoErrors(page);
});

test("Run proof sweep shows persisted summary toast", async ({ page }) => {
  await stubApps(page);
  await page.goto("/#apps");

  await page.getByTestId("app-proof-sweep").click();

  const toast = page.getByTestId("app-status-toast-success");
  await expect(toast).toBeVisible();
  await expect(toast).toContainText(/Proof sweep completed/);
  await expect(toast).toContainText(/1 pass, 1 fail, 0 timeout, 0 error across 3 apps/);

  await assertNoErrors(page);
});

test("View details navigates to detail page and shows recent proofs", async ({ page }) => {
  await stubApps(page);
  await page.goto("/#apps");

  await page.getByTestId("app-row-hermes-agent-detail").click();

  await expect(page).toHaveURL(/#apps\/hermes-agent$/);
  const detail = page.getByTestId("app-detail-panel");
  await expect(detail).toBeVisible();

  const proofs = page.getByTestId("app-detail-proofs");
  await expect(proofs).toBeVisible();
  await expect(page.getByTestId("app-detail-proof-0")).toBeVisible();
  await expect(page.getByTestId("app-detail-proof-1")).toBeVisible();

  // Rollback runbook link is shown for rollback_supported apps.
  await expect(page.getByTestId("app-detail-rollback")).toBeVisible();

  await assertNoFakeVisibleText(page, "apps-root");
  await assertNoErrors(page);
});

test("Full-page screenshot at 1920x1080 — registry overview", async ({ page }) => {
  await stubApps(page);
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/#apps");
  await expect(page.getByTestId("app-status-panel")).toBeVisible();
  // Stabilize layout before screenshot.
  await page.waitForTimeout(200);
  await page.screenshot({
    path: "test-results/app-status-1920x1080.png",
    fullPage: true,
    animations: "disabled",
  });
});
