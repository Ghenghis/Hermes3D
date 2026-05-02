import { expect, test } from "@playwright/test";

test("live mode shows green and amber dots when bridge response provides them", async ({ page }) => {
  const networkUrls: string[] = [];
  let popupCount = 0;

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol === "http:" || url.protocol === "https:") {
      networkUrls.push(request.url());
    }
  });
  page.on("popup", () => {
    popupCount += 1;
  });

  await page.route(/\/api\/providers\/health/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        providers: [
          {
            provider_id: "deepseek",
            status: "amber",
            last_probe_utc: "2026-05-02T10:00:00Z",
            http_status: 200,
            latency_ms: 142,
            stale: true,
          },
          {
            provider_id: "minimax",
            status: "green",
            last_probe_utc: "2026-05-02T11:55:00Z",
            http_status: 200,
            latency_ms: 89,
            stale: false,
          },
        ],
      }),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "3D Generation", exact: true }).click();

  await expect(page.getByTestId("gen3d-provider-health")).toBeVisible();
  await expect(page.getByTestId("gen3d-provider-dot")).toHaveCount(2);
  await expect(page.locator('[data-provider="minimax"][data-status="green"]')).toBeVisible();
  await expect(page.locator('[data-provider="deepseek"][data-status="amber"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate", exact: true })).toBeDisabled();
  expect(popupCount).toBe(0);

  const externalRequests = networkUrls.filter((url) => {
    const host = new URL(url).hostname;
    return host !== "localhost" && host !== "127.0.0.1";
  });
  expect(externalRequests).toEqual([]);
});

test("live mode shows red dot when probe failed", async ({ page }) => {
  const networkUrls: string[] = [];
  let popupCount = 0;

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol === "http:" || url.protocol === "https:") {
      networkUrls.push(request.url());
    }
  });
  page.on("popup", () => {
    popupCount += 1;
  });

  await page.route(/\/api\/providers\/health/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        providers: [
          {
            provider_id: "minimax",
            status: "red",
            last_probe_utc: "2026-05-02T11:55:00Z",
            http_status: 500,
            latency_ms: 41,
            stale: false,
          },
        ],
      }),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "3D Generation", exact: true }).click();

  const dot = page.getByTestId("gen3d-provider-dot");
  await expect(dot).toHaveAttribute("data-status", "red");
  await expect(page.getByRole("button", { name: "Generate", exact: true })).toBeDisabled();
  expect(popupCount).toBe(0);

  const externalRequests = networkUrls.filter((url) => {
    const host = new URL(url).hostname;
    return host !== "localhost" && host !== "127.0.0.1";
  });
  expect(externalRequests).toEqual([]);
});

test("live mode shows idle dots when no probes have been run", async ({ page }) => {
  const networkUrls: string[] = [];
  let popupCount = 0;

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol === "http:" || url.protocol === "https:") {
      networkUrls.push(request.url());
    }
  });
  page.on("popup", () => {
    popupCount += 1;
  });

  await page.route(/\/api\/providers\/health/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        providers: [
          {
            provider_id: "minimax",
            status: "idle",
            last_probe_utc: null,
            http_status: null,
            latency_ms: null,
            stale: false,
          },
          {
            provider_id: "deepseek",
            status: "idle",
            last_probe_utc: null,
            http_status: null,
            latency_ms: null,
            stale: false,
          },
        ],
      }),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "3D Generation", exact: true }).click();

  await expect(page.getByTestId("gen3d-provider-dot")).toHaveCount(2);
  await expect(page.locator('[data-provider="minimax"][data-status="idle"]')).toBeVisible();
  await expect(page.locator('[data-provider="deepseek"][data-status="idle"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate", exact: true })).toBeDisabled();
  expect(popupCount).toBe(0);

  const externalRequests = networkUrls.filter((url) => {
    const host = new URL(url).hostname;
    return host !== "localhost" && host !== "127.0.0.1";
  });
  expect(externalRequests).toEqual([]);
});
