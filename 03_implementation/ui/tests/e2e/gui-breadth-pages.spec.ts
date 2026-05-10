import { expect, test } from "@playwright/test";
import {
  TAB_FIXTURES,
  assertNoErrors,
  assertNoFakeVisibleText,
  attachErrorCapture,
  fulfillJson,
  openTab,
} from "./_helpers";

/**
 * gui-breadth-pages.spec.ts (W8-2) — covers the three breadth pages:
 *   - Settings (with the new General + MCP subtabs)
 *   - Approvals (with Approve/Deny/Defer + file scope + 5s polling)
 *   - Apps (registry table → per-app detail at #apps/<id>)
 *
 * The spec stubs every backend route so it can run against a freshly-spawned
 * Vite dev server without a live backend. Stubs use the public payload
 * shapes documented in `types/approval.ts` and `types/app-registry.ts`.
 */

const PENDING_APPROVALS = [
  {
    id: "ap-1",
    jobId: 101,
    jobTitle: "Print 60mm cube on Prusa-A",
    approvalType: "PRINT_APPROVAL",
    status: "pending",
    createdAt: "2026-05-09T10:00:00Z",
    decidedAt: null,
    decidedBy: null,
    evidence: { gateResultsUrl: null, artifactUrls: [] },
    fileScope: ["src/printers/prusa-a.toml"],
    requester: "claude-w8-2",
  },
  {
    id: "ap-2",
    jobId: 102,
    jobTitle: "Repair G-code transform pipeline",
    approvalType: "REPAIR_APPROVAL",
    status: "pending",
    createdAt: "2026-05-09T11:30:00Z",
    decidedAt: null,
    decidedBy: null,
    evidence: { gateResultsUrl: null, artifactUrls: [] },
    fileScope: ["src/gcode/transform.ts", "src/gcode/pipeline.ts"],
    requester: "codex-impl-01",
  },
];

const APP_LIST = [
  {
    id: "blender",
    name: "Blender",
    current_version: "4.2.1",
    tested_versions: ["4.0.0", "4.1.0", "4.2.1"],
    license: { spdx: "GPL-3.0", label: "GNU GPL v3" },
    update_lane: "stable",
    lifecycle: "stable",
    last_proof: {
      proof_event_id: "ev-blender-1",
      status: "pass",
      at: "2026-05-09T12:00:00Z",
      reason: "ok",
    },
    rollback_supported: true,
    description: "3D modeling and rendering",
    upstream_url: "https://blender.org",
  },
  {
    id: "cura",
    name: "UltiMaker Cura",
    current_version: "5.7.2",
    tested_versions: ["5.6.0", "5.7.2"],
    license: { spdx: "LGPL-3.0", label: "LGPL v3" },
    update_lane: "stable",
    lifecycle: "stable",
    last_proof: null,
    rollback_supported: false,
    description: "FDM slicer",
    upstream_url: "https://github.com/Ultimaker/Cura",
  },
];

const APP_DETAIL = {
  ...APP_LIST[0],
  recent_proofs: [
    {
      proof_event_id: "ev-blender-1",
      status: "pass",
      at: "2026-05-09T12:00:00Z",
      reason: "ok",
    },
    {
      proof_event_id: "ev-blender-0",
      status: "fail",
      at: "2026-05-08T12:00:00Z",
      reason: "version mismatch",
    },
  ],
  rollback_runbook_url: "https://docs.example.com/blender-rollback",
  proof_command: "blender --version",
};

const MCP_LOCKS = [
  {
    file: "03_implementation/ui/src/tabs/Settings.tsx",
    owner: "claude-w8-2",
    role: "agent",
    taskId: "T-w8-2",
    acquiredAt: "2026-05-09T13:00:00Z",
    expiresAt: "2026-05-09T15:00:00Z",
    stale: false,
  },
];

const SETTINGS_PAYLOAD = {
  theme: "midnight",
  ports: { bridge: 8765, api: 8000, ui: 5173 },
  printerUrls: {},
  cameraUrls: {},
  serviceUrls: {},
};

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
  // Approvals
  await page.route("**/api/approvals?status=pending", (route) =>
    fulfillJson(route, PENDING_APPROVALS),
  );
  await page.route("**/api/approvals?status=approved,rejected", (route) =>
    fulfillJson(route, []),
  );
  await page.route("**/api/approvals/*/approve", (route) => fulfillJson(route, { ok: true }));
  await page.route("**/api/approvals/*/reject", (route) => fulfillJson(route, { ok: true }));
  await page.route("**/api/approvals/*/defer", (route) => fulfillJson(route, { ok: true }));
  // Apps
  await page.route("**/api/apps", (route) => fulfillJson(route, APP_LIST));
  await page.route("**/api/apps/blender", (route) => fulfillJson(route, APP_DETAIL));
  await page.route("**/api/apps/blender/run-proof", (route) =>
    fulfillJson(route, {
      accepted: true,
      proof_event_id: "ev-blender-2",
      status: "pending",
      reason: "",
    }),
  );
  await page.route("**/api/source-os/modules", (route) => fulfillJson(route, APP_LIST));
  // MCP locks
  await page.route("**/api/mcp/locks", (route) => fulfillJson(route, { locks: MCP_LOCKS }));
  // Settings
  await page.route("**/api/settings", (route) => fulfillJson(route, SETTINGS_PAYLOAD));
  await page.route("**/api/settings/update-center", (route) =>
    fulfillJson(route, { components: [] }),
  );
});

test("Settings page exposes General and MCP subtabs", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.settings);
  const root = page.getByTestId(TAB_FIXTURES.settings.rootTestId);
  await expect(root).toBeVisible();

  // General is the default active subtab.
  await expect(page.getByTestId("settings-general")).toBeVisible();
  await page.screenshot({
    path: "test-results/e2e/screenshots/gui-breadth-settings-general.png",
    fullPage: true,
  });

  // Switch to MCP.
  await page.getByTestId("settings-subtab-mcp").click();
  await expect(page.getByTestId("settings-mcp")).toBeVisible();
  await expect(page.getByTestId("settings-mcp-row-claude-w8-2")).toBeVisible();
  await page.screenshot({
    path: "test-results/e2e/screenshots/gui-breadth-settings-mcp.png",
    fullPage: true,
  });

  await assertNoFakeVisibleText(page, TAB_FIXTURES.settings.rootTestId);
  await assertNoErrors(page);
});

test("Approvals shows pending items with file scope and three actions", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.approvals);
  const root = page.getByTestId(TAB_FIXTURES.approvals.rootTestId);
  await expect(root).toBeVisible();

  await expect(page.getByTestId("approvals-pending-ap-1")).toBeVisible();
  await expect(page.getByTestId("approvals-pending-ap-2")).toBeVisible();
  await expect(page.getByTestId("approvals-action-approve-ap-1")).toBeVisible();
  await expect(page.getByTestId("approvals-action-deny-ap-1")).toBeVisible();
  await expect(page.getByTestId("approvals-action-defer-ap-1")).toBeVisible();
  await expect(page.getByTestId("approvals-file-scope-ap-1")).toBeVisible();

  await page.screenshot({
    path: "test-results/e2e/screenshots/gui-breadth-approvals.png",
    fullPage: true,
  });

  // Defer flow.
  await page.getByTestId("approvals-action-defer-ap-1").click();
  await page.getByTestId("approvals-input-ap-1").fill("needs more review");
  await page.getByTestId("approvals-submit-ap-1").click();
  await expect(page.getByTestId("approvals-action-message")).toContainText("Deferred ap-1");

  await assertNoFakeVisibleText(page, TAB_FIXTURES.approvals.rootTestId);
  await assertNoErrors(page);
});

test("Apps registry navigates to per-app detail at #apps/<id>", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.apps);
  const root = page.getByTestId(TAB_FIXTURES.apps.rootTestId);
  await expect(root).toBeVisible();
  await expect(page.getByTestId("app-status-panel")).toBeVisible();
  await expect(page.getByTestId("app-row-blender")).toBeVisible();
  await page.screenshot({
    path: "test-results/e2e/screenshots/gui-breadth-apps-list.png",
    fullPage: true,
  });

  await page.getByTestId("app-row-blender-detail").click();
  await expect(page.getByTestId("app-detail-panel")).toBeVisible();
  await expect(page.getByTestId("app-detail-versions")).toBeVisible();
  await expect(page.getByTestId("app-detail-rollback")).toBeVisible();
  await expect(page.getByTestId("app-detail-proof-0")).toBeVisible();
  await page.screenshot({
    path: "test-results/e2e/screenshots/gui-breadth-apps-detail.png",
    fullPage: true,
  });

  await assertNoFakeVisibleText(page, TAB_FIXTURES.apps.rootTestId);
  await assertNoErrors(page);
});
