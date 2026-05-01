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

test("live mode previews a planner DAG without execution affordances", async ({ page }) => {
  const networkUrls: string[] = [];
  let popupCount = 0;
  let planPreviewCalls = 0;

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol === "http:" || url.protocol === "https:") {
      networkUrls.push(request.url());
    }
  });
  page.on("popup", () => {
    popupCount += 1;
  });

  await page.route("http://127.0.0.1:8765/api/plan/preview", async (route) => {
    planPreviewCalls += 1;
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toEqual({ prompt: "calibration cube" });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(PLAN_DAG),
    });
  });

  await page.goto("/?adapter=live");
  await page.getByRole("button", { name: "3D Generation", exact: true }).click();
  await page.getByLabel("Text Prompt").fill("calibration cube");
  await page.getByRole("button", { name: "Preview plan" }).click();

  const planPreview = page.getByTestId("gen3d-plan-preview");
  await expect(planPreview).toHaveAttribute("data-run-id", "plan-preview-fixture");
  await expect(page.getByTestId("gen3d-plan-node")).toHaveCount(1);
  await expect(page.getByTestId("gen3d-plan-node").first()).toHaveAttribute(
    "data-tool",
    "gen3d.generate",
  );
  await expect(page.getByRole("button", { name: "Generate", exact: true })).toBeDisabled();
  expect(planPreviewCalls).toBe(1);
  expect(popupCount).toBe(0);

  const externalRequests = networkUrls.filter((url) => {
    const host = new URL(url).hostname;
    return host !== "localhost" && host !== "127.0.0.1";
  });
  expect(externalRequests).toEqual([]);
});
