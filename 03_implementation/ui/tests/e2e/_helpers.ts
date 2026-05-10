import { expect, type Page, type Route } from "@playwright/test";

/**
 * Shared helpers for tab-specific Playwright specs.
 *
 * No-fake contract:
 * - These helpers never invent backend payloads. They only forward real backend
 *   responses or assert visible blocked/empty states truthfully.
 * - Specs that need to stub a route should pass real-shape JSON and call
 *   fulfillJson directly; helpers here keep to navigation, error capture, and
 *   forbidden-term scans of the rendered DOM.
 */

export const FORBIDDEN_VISIBLE_TERMS = [
  "TODO",
  "FIXME",
  "lorem ipsum",
  "placeholder text",
  "sample data",
  "mock data",
  "dummy data",
  "fake data",
] as const;

export interface TabFixture {
  /** Sidebar button label as rendered in routes.tsx. */
  label: string;
  /** Root element data-testid emitted by the tab component. */
  rootTestId: string;
}

export const TAB_FIXTURES: Record<string, TabFixture> = {
  dashboard: { label: "Dashboard", rootTestId: "dashboard-root" },
  source_os: { label: "Source OS", rootTestId: "source-os-root" },
  autopilot: { label: "Autopilot", rootTestId: "autopilot-root" },
  design: { label: "Design", rootTestId: "design-root" },
  gen3d: { label: "3D Generation", rootTestId: "gen3d-root" },
  jobs: { label: "Jobs", rootTestId: "jobs-root" },
  printers: { label: "Printers", rootTestId: "printers-root" },
  observe: { label: "Observe", rootTestId: "observe-root" },
  voice: { label: "Voice", rootTestId: "voice-root" },
  agents: { label: "Agents", rootTestId: "agents-root" },
  learning: { label: "Learning", rootTestId: "learning-root" },
  artifacts: { label: "Artifacts", rootTestId: "artifacts-root" },
  approvals: { label: "Approvals", rootTestId: "approvals-root" },
  apps: { label: "Apps", rootTestId: "apps-root" },
  plugins: { label: "Plugins", rootTestId: "plugins-root" },
  settings: { label: "Settings", rootTestId: "settings-root" },
  roadmap: { label: "Roadmap", rootTestId: "roadmap-root" },
};

/**
 * Console error noise that is known-acceptable in the CI smoke environment
 * because the corresponding backend endpoints are not running. The strict
 * `assertNoErrors` contract still applies to all other errors. Mirrors the
 * route-stub strategy in live-gui.spec.ts so individual tab specs do not have
 * to redundantly stub every shared endpoint just to avoid console noise.
 */
const KNOWN_OFFLINE_ERROR_FRAGMENTS = [
  "Failed to load resource: the server responded with a status of 502",
  "Failed to load resource: net::ERR_CONNECTION_REFUSED",
  "Failed to load resource: net::ERR_FAILED",
] as const;

function isKnownOfflineError(text: string): boolean {
  return KNOWN_OFFLINE_ERROR_FRAGMENTS.some((fragment) => text.includes(fragment));
}

/** Attach console + pageerror capture and expose a window getter. */
export async function attachErrorCapture(page: Page): Promise<void> {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      const text = message.text();
      if (!isKnownOfflineError(text)) {
        errors.push(text);
      }
    }
  });
  await page.exposeFunction("__hermes3dErrors", () => errors);
}

export async function readErrors(page: Page): Promise<string[]> {
  return page.evaluate(async () => {
    const reader = window as unknown as { __hermes3dErrors: () => Promise<string[]> };
    return reader.__hermes3dErrors();
  });
}

export async function fulfillJson(route: Route, json: unknown, status = 200): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(json),
  });
}

/**
 * Click the left-rail sidebar button for a given tab and assert its root mounts.
 * Uses the Roadmap hash route when label === "Roadmap" since it is excluded
 * from primary navigation.
 */
export async function openTab(page: Page, fixture: TabFixture): Promise<void> {
  if (fixture.label === "Roadmap") {
    await page.goto("/#roadmap");
  } else {
    const button = page.getByRole("button", { name: fixture.label, exact: true });
    await expect(button, `${fixture.label} sidebar button`).toBeVisible();
    await button.click();
  }
  await expect(
    page.getByTestId(fixture.rootTestId),
    `${fixture.label} root mounts as ${fixture.rootTestId}`,
  ).toBeVisible({ timeout: 15_000 });
}

/**
 * Read the visible text of the active tab root and assert that no
 * forbidden mock/placeholder phrases appear in production surfaces.
 * Forbidden terms are checked case-insensitively as standalone substrings.
 */
export async function assertNoFakeVisibleText(page: Page, rootTestId: string): Promise<void> {
  const text = await page.getByTestId(rootTestId).innerText();
  const lowered = text.toLowerCase();
  for (const term of FORBIDDEN_VISIBLE_TERMS) {
    expect(
      lowered.includes(term.toLowerCase()),
      `forbidden term "${term}" must not appear in ${rootTestId}`,
    ).toBe(false);
  }
}

/** Assert the page has no JS errors captured by attachErrorCapture. */
export async function assertNoErrors(page: Page): Promise<void> {
  const errors = await readErrors(page);
  expect(errors, errors.join("\n")).toEqual([]);
}
