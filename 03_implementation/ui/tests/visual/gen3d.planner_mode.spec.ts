import { expect, test } from "@playwright/test";

const PLAN_DAG = {
  dag_id: "fixture-calibration-cube-dag",
  run_id: "plan-preview-fixture",
  max_depth: 12,
  max_fanout: 4,
  metadata: {
    planner: "deterministic-template",
  },
  nodes: [
    {
      node_id: "gen3d-simulated",
      tool: "gen3d.generate",
      kind: "gen3d.fixture.calibration_cube",
      inputs: {
        prompt: "calibration cube",
        seed: 3201,
      },
      retry_budget: 0,
      gate_set: ["phase3.2.simulated-only"],
      depends_on: [],
    },
  ],
  edges: [],
};

test("live mode shows via-LLM badge when bridge response sets planner_mode=llm", async ({
  page,
}) => {
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

  await page.route(/http:\/\/127\.0\.0\.1:\d+\/api\/plan\/preview/, async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toEqual({ prompt: "calibration cube" });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...PLAN_DAG,
        metadata: { ...PLAN_DAG.metadata, planner_mode: "llm" },
      }),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "3D Generation", exact: true }).click();
  await page.getByLabel("Text Prompt").fill("calibration cube");
  await page.getByRole("button", { name: "Preview plan" }).click();

  const badge = page.getByTestId("gen3d-planner-mode-badge");
  await expect(badge).toBeVisible();
  await expect(badge).toHaveAttribute("data-mode", "llm");
  await expect(badge).toContainText("via LLM");
  const generateButton = page.getByRole("button", { name: "Generate", exact: true });
  await expect(generateButton).toHaveAttribute("aria-disabled", "true");
  await expect(generateButton).toBeDisabled();
  expect(popupCount).toBe(0);

  const externalRequests = networkUrls.filter((url) => {
    const host = new URL(url).hostname;
    return host !== "localhost" && host !== "127.0.0.1";
  });
  expect(externalRequests).toEqual([]);
});

test("live mode shows template badge when bridge response sets planner_mode=template", async ({
  page,
}) => {
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

  await page.route(/http:\/\/127\.0\.0\.1:\d+\/api\/plan\/preview/, async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toEqual({ prompt: "calibration cube" });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...PLAN_DAG,
        metadata: { ...PLAN_DAG.metadata, planner_mode: "template" },
      }),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "3D Generation", exact: true }).click();
  await page.getByLabel("Text Prompt").fill("calibration cube");
  await page.getByRole("button", { name: "Preview plan" }).click();

  const badge = page.getByTestId("gen3d-planner-mode-badge");
  await expect(badge).toBeVisible();
  await expect(badge).toHaveAttribute("data-mode", "template");
  await expect(badge).toContainText("template");
  const generateButton = page.getByRole("button", { name: "Generate", exact: true });
  await expect(generateButton).toHaveAttribute("aria-disabled", "true");
  await expect(generateButton).toBeDisabled();
  expect(popupCount).toBe(0);

  const externalRequests = networkUrls.filter((url) => {
    const host = new URL(url).hostname;
    return host !== "localhost" && host !== "127.0.0.1";
  });
  expect(externalRequests).toEqual([]);
});
