import { expect, test } from "@playwright/test";

const LIVE_PRINTERS = [
  {
    id: "t1-1",
    name: "FLSUN T1 #1",
    model: "FLSUN T1",
    ip: "192.168.0.10",
    status: "printing",
    adapter: "moonraker",
    data_source: "live",
    temp_hot: 215,
    temp_bed: 60,
    progress: 47,
    current_job: "frame-bracket-v3.gcode",
    maintenance_flag: false,
    camera_url: null,
  },
  {
    id: "t1-2",
    name: "FLSUN T1 #2",
    model: "FLSUN T1",
    ip: "192.168.0.11",
    status: "online",
    adapter: "moonraker",
    data_source: "live",
    temp_hot: 25,
    temp_bed: 24,
    progress: null,
    current_job: null,
    maintenance_flag: false,
    camera_url: null,
  },
  {
    id: "s1",
    name: "FLSUN S1",
    model: "FLSUN S1",
    ip: "192.168.0.12",
    status: "maintenance",
    adapter: "moonraker",
    data_source: "live",
    temp_hot: null,
    temp_bed: null,
    progress: null,
    current_job: null,
    maintenance_flag: true,
    camera_url: null,
  },
  {
    id: "v400",
    name: "FLSUN V400",
    model: "FLSUN V400",
    ip: "192.168.0.34",
    status: "online",
    adapter: "moonraker",
    data_source: "live",
    temp_hot: 24,
    temp_bed: 23,
    progress: null,
    current_job: null,
    maintenance_flag: false,
    camera_url: null,
  },
  ...Array.from({ length: 8 }, (_, index) => ({
    id: `sim-${index + 1}`,
    name: `Sim Printer ${index + 1}`,
    model: "Generic",
    ip: `192.168.0.${20 + index}`,
    status: index === 3 ? "offline" : "online",
    adapter: "manual",
    data_source: "mock",
    temp_hot: null,
    temp_bed: null,
    progress: null,
    current_job: null,
    maintenance_flag: false,
    camera_url: null,
  })),
];

test("live mode reads local bridge and marks four fixture printers as live", async ({ page }) => {
  await page.route("http://127.0.0.1:8765/api/printers", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(LIVE_PRINTERS),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "Printer Fleet", exact: true }).click();
  await page.waitForSelector('[data-testid="fleet-root"]');

  const fleetRoot = page.locator('[data-testid="fleet-root"]');
  await expect(fleetRoot.locator('tr[data-source="live"]')).toHaveCount(4);
  await expect(fleetRoot.locator('tr[data-source="mock"]')).toHaveCount(8);
  await expect(fleetRoot.locator('[data-source="live"]').first()).toBeVisible();
});
