import { expect, test, type Page, type Route } from "@playwright/test";
import fs from "node:fs";
import type { Printer } from "../../src/types/printer";
import type { SourceModuleUpdateReadiness, SourceOSModule } from "../../src/types/source-os";

const TABS = [
  ["Source OS", "source-os-root"],
  ["Dashboard", "dashboard-root"],
  ["Autopilot", "autopilot-root"],
  ["Design", "design-root"],
  ["3D Generation", "gen3d-root"],
  ["Jobs", "jobs-root"],
  ["Printers", "printers-root"],
  ["Observe", "observe-root"],
  ["Voice", "voice-root"],
  ["Agents", "agents-root"],
  ["Learning", "learning-root"],
  ["Artifacts", "artifacts-root"],
  ["Approvals", "approvals-root"],
  ["Plugins", "plugins-root"],
  ["Settings", "settings-root"],
] as const;

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });
  await page.exposeFunction("__hermes3dErrors", () => errors);
});

test("all left-rail primary tabs route to live-backed components without browser errors", async ({ page }) => {
  // Known-offline routes in CI: stub with 200 empty payloads so the page
  // doesn't surface 502/ERR_CONNECTION_REFUSED console errors that would
  // otherwise fail the strict `errors.toEqual([])` assertion below.
  await page.route("**/api/agents/update/status", (route) => fulfillJson(route, { items: [] }));
  await page.route("**/api/agents/update/check", (route) => fulfillJson(route, { items: [] }));
  await page.route("**/api/source-os/upgrade-readiness", (route) => fulfillJson(route, []));
  await page.route("**/api/proof/events", (route) => fulfillJson(route, { saved: true }));

  await page.goto("/");

  for (const [label, root] of TABS) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.getByTestId(root), `${label} root`).toBeVisible({ timeout: 15_000 });
  }

  const errors = (await readErrors(page)).filter((message) => !isOfflineNetworkError(message));
  expect(errors, errors.join("\n")).toEqual([]);
});

test("primary navigation excludes Roadmap but hash route remains available", async ({ page }) => {
  await page.route("**/api/roadmap/status", (route) => fulfillJson(route, []));
  await page.route("**/api/roadmap/tab-completion", (route) => fulfillJson(route, {
    updated_at: "2026-05-05",
    roadmap_path: "03_implementation/ROADMAP.md",
    contract: ["Visible controls must call live routes or expose exact blocked reasons."],
    tabs: [
      { tab: "dashboard", label: "Dashboard", state: "done", summary: "Live backend data." },
      { tab: "gen3d", label: "3D Generation", state: "in_progress", summary: "Local generator proof exists." },
    ],
    next_packages: [
      {
        id: "wp-source-updates",
        title: "Source OS + Plugins: App Update Center",
        tabs: ["source_os", "plugins", "settings"],
        state: "next",
        summary: "Update center work package.",
        acceptance: ["No update action runs without backup metadata."],
      },
      {
        id: "wp-operator-assist",
        title: "Voice + Observe: Operator Assist",
        tabs: ["voice", "observe", "agents"],
        state: "next",
        summary: "Operator assist work package.",
        acceptance: ["No speech key appears in frontend bundles or logs."],
      },
    ],
    references: [],
    finish_queue: [],
  }));
  await page.route("**/api/modules/runtime/setup-queue", (route) => fulfillJson(route, {
    accepted: true,
    status: "planned",
    count: 60,
    counts: {
      runtime_ready: 5,
      source_ready: 55,
      runner_not_registered: 55,
      source_install_available: 0,
      runtime_repair_required: 0,
      blocked: 0,
    },
    execution_mode: "plan_only_until_safe_runner_registered",
    agent_gate: "Hermes Agents may consume this queue after proof.",
    records: [],
    proof_event_id: null,
  }));
  await page.route("**/api/proof/events", (route) => fulfillJson(route, { saved: true }));
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Roadmap", exact: true })).toHaveCount(0);
  await page.goto("/#roadmap");
  await expect(page.getByTestId("roadmap-root")).toBeVisible();
  await expect(page.getByText("Tab Completion Ledger", { exact: true })).toBeVisible();
  await expect(page.getByText("Next 5 Work Packages", { exact: true })).toBeVisible();
  await expect(page.getByTestId("roadmap-source-runtime-gap")).toContainText("60 source-backed modules");
  await expect(page.getByTestId("roadmap-source-runtime-gap")).toContainText("55");
  await expect(page.getByText("Source OS + Plugins: App Update Center", { exact: true })).toBeVisible();
  await expect(page.getByText("Voice + Observe: Operator Assist", { exact: true })).toBeVisible();
});

test("Autopilot consumes ready/message readiness rows and blocks false action responses", async ({ page }) => {
  await page.route("http://127.0.0.1:8765/api/autopilot/readiness", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: "printer_connectivity", name: "Printer Connectivity", ready: true, message: "" },
        { id: "api_token_set", name: "API Token Set", ready: false, message: "Token missing from runtime env.", fix_target: "settings" },
      ]),
    });
  });
  await page.route("http://127.0.0.1:8765/api/autopilot/guardrails", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("http://127.0.0.1:8765/api/autopilot/write-plan", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ accepted: false, status: "not_configured", message: "Plan writer is not configured." }),
    });
  });

  await page.goto("/#autopilot");
  const root = page.getByTestId("autopilot-root");
  await expect(root).toBeVisible();
  await expect(root.getByText("1/2 READY", { exact: true })).toBeVisible();
  await expect(root.getByText("Token missing from runtime env.", { exact: true })).toBeVisible();

  await root.getByRole("button", { name: "Fix", exact: true }).click();
  await expect(page.getByTestId("settings-root")).toBeVisible();
  await page.getByRole("button", { name: "Autopilot", exact: true }).click();
  await expect(root).toBeVisible();

  const proofEventRequest = page.waitForRequest("http://127.0.0.1:8765/api/proof/events", { timeout: 500 }).then(() => true).catch(() => false);
  await root.getByRole("button", { name: "Write Agent Plan", exact: true }).click();
  await expect(root.getByText("Blocked: Plan writer is not configured.", { exact: true })).toBeVisible();
  await expect(root.getByText(/Accepted:/)).toHaveCount(0);
  await expect(proofEventRequest).resolves.toBe(false);
});

test("Gen3D treats false-ish generation responses as blocked", async ({ page }) => {
  const proofEvents: unknown[] = [];
  await page.route("**/api/generation/run", (route) => fulfillJson(route, {
    queued: false,
    status: "not_configured",
    reason: "No real generation service is configured.",
  }, 202));
  await page.route("**/api/providers/health", (route) => fulfillJson(route, { providers: [] }));
  await page.route("**/api/proof/events", async (route) => {
    proofEvents.push(JSON.parse(route.request().postData() ?? "{}"));
    await fulfillJson(route, { saved: true });
  });

  await page.goto("/#gen3d");
  const root = page.getByTestId("gen3d-root");
  await expect(root).toBeVisible();
  await root.getByRole("button", { name: "Generate", exact: true }).click();
  await expect(root.getByText("Blocked: No real generation service is configured.", { exact: true })).toBeVisible();
  await expect(root.getByText(/Accepted:/)).toHaveCount(0);
  expect(proofEvents).toContainEqual(expect.objectContaining({
    type: "generation.run.requested",
    payload: expect.objectContaining({ accepted: false }),
  }));
});

test("Gen3D renders accepted local generation artifacts with proof", async ({ page }) => {
  const generationRequests: Array<Record<string, unknown>> = [];
  await page.route("**/api/providers/health", (route) => fulfillJson(route, { providers: [] }));
  await page.route("**/api/generation/run", async (route) => {
    generationRequests.push(JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>);
    await fulfillJson(route, {
      id: "gen-job-1",
      job_id: "gen-job-1",
      status: "completed",
      accepted: true,
      created: true,
      template: "calibration_cube",
      artifact: { id: "mesh-1", label: "calibration_cube_abc123.stl", file_path: "G:\\proof\\calibration_cube_abc123.stl", file_size: 684 },
      package_3mf: { id: "package-1", label: "calibration_cube_abc123.3mf", file_path: "G:\\proof\\calibration_cube_abc123.3mf", file_size: 4096 },
      preview: { id: "preview-1", label: "calibration_cube_abc123.preview.svg", file_path: "G:\\proof\\calibration_cube_abc123.preview.svg", file_size: 1024 },
      proof: { id: "proof-1", label: "calibration_cube_abc123.proof.json", event_id: "proof-gen-1" },
      runtime_evidence: { id: "runtime-1", label: "calibration_cube_abc123.runtime.json", file_path: "G:\\proof\\calibration_cube_abc123.runtime.json", file_size: 1310 },
      truth_gate: { status: "pass", duration_s: 0.2 },
    }, 202);
  });
  await page.route("**/api/proof/events", (route) => fulfillJson(route, { saved: true }));

  await page.goto("/#gen3d");
  const root = page.getByTestId("gen3d-root");
  await expect(root).toBeVisible();
  await root.getByLabel("Generation size mm").fill("24");
  await root.getByRole("button", { name: "Generate", exact: true }).click();
  await expect(root.getByText(/Accepted: calibration_cube_abc123\.stl; 3MF calibration_cube_abc123\.3mf; proof proof-gen-1/)).toBeVisible();
  await expect(root.getByText("calibration_cube_abc123.stl", { exact: true })).toBeVisible();
  const packageLabel = root.getByText(/calibration_cube_abc123\.3mf/).last();
  await packageLabel.scrollIntoViewIfNeeded();
  await expect(packageLabel).toBeVisible();
  const previewLabel = root.getByText("calibration_cube_abc123.preview.svg", { exact: true });
  await previewLabel.scrollIntoViewIfNeeded();
  await expect(previewLabel).toBeVisible();
  const runtimeLabel = root.getByText(/calibration_cube_abc123\.runtime\.json/).last();
  await runtimeLabel.scrollIntoViewIfNeeded();
  await expect(runtimeLabel).toBeVisible();
  expect(generationRequests).toHaveLength(1);
  expect(generationRequests[0].prompt).toBe("calibration cube");
  expect((generationRequests[0].constraints as Record<string, unknown>).size_mm).toBe(24);
});

test("Design blocks intake when the real CAD toolchain is unavailable", async ({ page }) => {
  await page.route("**/api/design/toolchain/status", (route) => fulfillJson(route, {
    overall: "blocked",
    updated_at: new Date(0).toISOString(),
    stages: [
      { id: "intake", name: "Intake", status: "ready", detail: null },
      { id: "cad", name: "CAD Worker", status: "not_installed", detail: "CadQuery/OpenSCAD worker not installed." },
    ],
  }));

  await page.goto("/#design");
  const root = page.getByTestId("design-root");
  await expect(root).toBeVisible();
  await root.getByLabel("Design name").fill("bracket");
  await root.getByLabel("Design intent, constraints, notes").fill("small printer bracket");
  await expect(root.getByRole("button", { name: "Start Design", exact: true })).toBeDisabled();
  await expect(root.getByText(/CAD Worker is not_installed/)).toBeVisible();
});

test("Design surfaces local source and executable proof while blocking missing executor", async ({ page }) => {
  await page.route("**/api/design/toolchain/status", (route) => fulfillJson(route, {
    overall: "blocked",
    execution_ready: false,
    updated_at: new Date(0).toISOString(),
    blockers: ["Prompt-to-CAD executor is blocked until a real worker dispatch route is wired."],
    stages: [
      { id: "intake", name: "Design intake", status: "ready", detail: "Endpoint available.", source: "backend" },
      { id: "openscad_cli", name: "OpenSCAD CAD CLI", status: "ready", detail: "OpenSCAD version 2021.01 Path: C:\\Program Files\\OpenSCAD\\openscad.exe", source: "local_tooling_audit", proof_path: "proof/LOCAL_TOOLING_AUDIT.json" },
      { id: "design_dispatch", name: "Prompt-to-CAD executor", status: "blocked", detail: "Worker dispatch route is not wired.", source: "backend" },
    ],
    tools: [
      { id: "openscad_cli", name: "OpenSCAD CLI", status: "ready", path: "C:\\Program Files\\OpenSCAD\\openscad.exe", detail: "OpenSCAD version 2021.01", capabilities: ["scad_to_stl", "render_png"] },
      { id: "prusaslicer_cli", name: "PrusaSlicer CLI", status: "ready", path: "C:\\Program Files\\Prusa3D\\PrusaSlicer\\prusa-slicer-console.exe", detail: "PrusaSlicer-2.9.5-beta2", capabilities: ["slice_to_gcode"] },
    ],
    sources: [
      { id: "cadquery", name: "CadQuery", status: "ready", repo_url: "https://github.com/CadQuery/cadquery.git", path: "source-lab/sources/modelers/CadQuery", detail: "installed; f86ff79fb1c6" },
      { id: "flsun_slicer", name: "FLSUN Slicer", status: "ready", repo_url: "https://github.com/Flsun3d/FlsunSlicer.git", path: "source-lab/sources/slicers/FLSUN-Slicer", detail: "installed; fb02854cb014" },
    ],
    proof_sources: {
      local_tooling: "proof/LOCAL_TOOLING_AUDIT.json",
      source_registry: "proof/SOURCE_REGISTRY_TRUTH_AUDIT.json",
    },
  }));

  await page.goto("/#design");
  const root = page.getByTestId("design-root");
  await expect(root).toBeVisible();
  await expect(root.getByText("Execution blocked", { exact: true })).toBeVisible();
  await expect(root.getByText("OpenSCAD CLI", { exact: true })).toBeVisible();
  await expect(root.getByText("PrusaSlicer CLI", { exact: true })).toBeVisible();
  await expect(root.getByText("CadQuery", { exact: true })).toBeVisible();
  await expect(root.getByText("FLSUN Slicer", { exact: true })).toBeVisible();
  await expect(root.getByText("local_tooling: proof/LOCAL_TOOLING_AUDIT.json", { exact: true })).toBeVisible();
  await expect(root.getByRole("button", { name: "Start Design", exact: true })).toBeDisabled();
});

test("Design submits supported parametric template with real executor constraints", async ({ page }) => {
  const intakeRequests: Array<Record<string, unknown>> = [];
  const proofEvents: Array<Record<string, unknown>> = [];
  await page.route("**/api/printers", (route) => fulfillJson(route, [
    printerRow({ id: "flsun_t1_a", name: "T1 #1", model: "FLSUN T1", ip: "192.168.0.10" }),
  ]));
  await page.route("**/api/design/toolchain/status", (route) => fulfillJson(route, {
    overall: "ready",
    execution_ready: true,
    updated_at: new Date(0).toISOString(),
    blockers: [],
    supported_templates: [
      { id: "desk_organizer", name: "Parametric Desk Organizer", outputs: ["stl", "proof_envelope"] },
    ],
    stages: [
      { id: "intake", name: "Design intake", status: "ready", detail: "Endpoint available.", source: "backend" },
      { id: "design_dispatch", name: "Prompt-to-CAD executor", status: "ready", detail: "Parametric desk organizer executor is wired.", source: "backend" },
    ],
    tools: [],
    sources: [],
    proof_sources: {},
  }));
  await page.route("**/api/design/intake", async (route) => {
    intakeRequests.push(JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>);
    await fulfillJson(route, {
      id: "design-job-1",
      job_id: "design-job-1",
      status: "completed",
      accepted: true,
      created: true,
      template: "desk_organizer",
      artifact: { id: "artifact-stl", label: "desk_organizer_abc123.stl", file_path: "G:\\proof\\desk_organizer_abc123.stl", file_size: 1000, sha256: "a".repeat(64) },
      proof: { id: "artifact-proof", label: "desk_organizer_abc123.proof.json", event_id: "proof-design-1", sha256: "b".repeat(64) },
      truth_gate: { status: "pass", duration_s: 1.2 },
    }, 201);
  });
  await page.route("**/api/proof/events", async (route) => {
    proofEvents.push(JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>);
    await fulfillJson(route, { saved: true });
  });

  await page.goto("/#design");
  const root = page.getByTestId("design-root");
  await expect(root).toBeVisible();
  await root.getByLabel("Design name").fill("Desk organizer for printer tools");
  await root.getByLabel("Design intent, constraints, notes").fill("desk organizer with trays and pen holders");
  await root.getByLabel("Width mm").fill("150");
  await root.getByLabel("Depth mm").fill("90");
  await root.getByLabel("Trays").fill("2");
  await root.getByRole("button", { name: "Start Design", exact: true }).click();
  await expect(root.getByText(/Design intake accepted: desk_organizer_abc123\.stl; proof proof-design-1/)).toBeVisible();
  expect(intakeRequests).toHaveLength(1);
  const constraints = intakeRequests[0].constraints as Record<string, unknown>;
  expect(intakeRequests[0].prompt).toContain("desk organizer");
  expect(constraints.template).toBe("desk_organizer");
  expect(constraints.target_printer_id).toBe("flsun_t1_a");
  expect(constraints.width_mm).toBe(150);
  expect(constraints.depth_mm).toBe(90);
  expect(constraints.tray_count).toBe(2);
  expect(proofEvents).toContainEqual(expect.objectContaining({
    type: "design.intake.submitted",
    payload: expect.objectContaining({ accepted: true }),
  }));
});

test("Plugins do not activate backend-not-configured plugins", async ({ page }) => {
  const proofEventRequest = page.waitForRequest("http://127.0.0.1:8765/api/proof/events", { timeout: 500 }).then(() => true).catch(() => false);
  await page.route("**/api/plugins", (route) => fulfillJson(route, [
    {
      id: "local-modeling-llm",
      display: "Local Modeling LLM",
      description: "Local modeling LLM",
      state: "READY",
      configured: false,
      status: "not_configured",
      reason: "Configure a local/provider URL before activation.",
      dependencies: [],
      configSchema: null,
      healthUrl: null,
      installVia: "none",
      sourceOsModuleId: null,
    },
  ]));

  await page.goto("/#plugins");
  const root = page.getByTestId("plugins-root");
  await expect(root).toBeVisible();
  const plugin = root.locator("section").filter({ hasText: "Local Modeling LLM" });
  await expect(plugin.getByRole("button", { name: "Activate", exact: true })).toBeDisabled();
  await expect(proofEventRequest).resolves.toBe(false);
});

test("Jobs disables Cancel for printing jobs that the backend cannot cancel", async ({ page }) => {
  const job = {
    id: "print-1",
    name: "Active print",
    status: "printing",
    printer_id: "flsun_t1_a",
    created_at: new Date(0).toISOString(),
    progress: 25,
  };
  await page.route("**/api/jobs?status=queued", (route) => fulfillJson(route, [job]));
  await page.route("**/api/jobs/print-1", (route) => fulfillJson(route, {
    ...job,
    job_type: "print",
    dry_run: false,
    steps: [],
    artifacts: [],
    events: [],
  }));

  await page.goto("/#jobs");
  const root = page.getByTestId("jobs-root");
  await expect(root).toBeVisible();
  await root.getByRole("button", { name: /Active print/ }).click();
  await expect(root.getByRole("button", { name: "Cancel", exact: true })).toBeDisabled();
});

test("Jobs detail renders proof-gated pipeline and current blocker", async ({ page }) => {
  const job = {
    id: "approval-1",
    name: "Bracket approval",
    status: "waiting_approval",
    printer_id: "flsun_t1_a",
    created_at: new Date(0).toISOString(),
    progress: 40,
  };
  await page.route("**/api/jobs?status=queued", (route) => fulfillJson(route, [job]));
  await page.route("**/api/printers", (route) => fulfillJson(route, [
    printerRow({ id: "flsun_t1_a", name: "T1 #1", model: "FLSUN T1", ip: "192.168.0.10" }),
  ]));
  await page.route("**/api/jobs/approval-1", (route) => fulfillJson(route, {
    ...job,
    job_type: "print",
    dry_run: false,
    steps: [
      { id: "s1", name: "Model intake", status: "done", started_at: null, ended_at: null },
      { id: "s2", name: "Slice G-code", status: "done", started_at: null, ended_at: null },
      { id: "s3", name: "Print approval", status: "pending", started_at: null, ended_at: null },
    ],
    artifacts: [
      { id: "a1", evidence_type: "gcode", label: "bracket.gcode", file_path: "G:\\proof\\bracket.gcode" },
    ],
    events: [
      { id: "e1", event_type: "gate_blocked", message: "Waiting for PRINT_APPROVAL", created_at: new Date(0).toISOString() },
    ],
  }));
  await page.route("**/api/proof/events", (route) => fulfillJson(route, { saved: true }));

  await page.goto("/#jobs");
  const root = page.getByTestId("jobs-root");
  await root.getByRole("button", { name: /Bracket approval/ }).click();
  await expect(root.getByText("Proof-Gated Pipeline", { exact: true })).toBeVisible();
  await expect(root.getByText("PRINT_APPROVAL", { exact: true })).toHaveCount(2);
  await expect(root.getByText("Print approval required", { exact: true })).toBeVisible();
  await expect(root.getByText("gate_blocked: Waiting for PRINT_APPROVAL", { exact: true })).toBeVisible();
  await expect(root.getByRole("button", { name: "Request Repair", exact: true })).toBeDisabled();
  await expect(root.getByRole("button", { name: "Apply Repair", exact: true })).toBeDisabled();
  await expect(root.getByRole("button", { name: "Retry", exact: true })).toBeDisabled();
  await expect(root.getByRole("button", { name: "Rollback", exact: true })).toBeDisabled();
});

test("Jobs transition controls call repair and rollback proof routes", async ({ page }) => {
  const job = {
    id: "failed-1",
    name: "Failed slice",
    status: "failed",
    printer_id: "flsun_t1_a",
    created_at: new Date(0).toISOString(),
    progress: 40,
  };
  let proposed = false;
  let rollbackCalled = false;
  await page.route("**/api/jobs?status=queued", (route) => fulfillJson(route, [job]));
  await page.route("**/api/printers", (route) => fulfillJson(route, [
    printerRow({ id: "flsun_t1_a", name: "T1 #1", model: "FLSUN T1", ip: "192.168.0.10" }),
  ]));
  await page.route("**/api/jobs/failed-1", (route) => fulfillJson(route, {
    ...job,
    job_type: "print",
    dry_run: false,
    steps: [
      { id: "s1", name: "Slice verification", status: "failed", started_at: null, ended_at: null, error: "Bounds check failed" },
    ],
    artifacts: [
      { id: "rollback-a1", evidence_type: "rollback_checkpoint", label: "checkpoint.json", file_path: "G:\\proof\\checkpoint.json", gate: "ROLLBACK_TARGET" },
    ],
    events: [],
    approvals: proposed ? [
      { id: "repair-approval-1", approval_type: "REPAIR_APPROVAL", status: "pending", requested_at: new Date(0).toISOString(), decided_at: null },
    ] : [],
    transition_state: {
      failed_step_id: "s1",
      failed_step: { id: "s1", name: "Slice verification", status: "failed", error: "Bounds check failed" },
      pending_repair_approval_id: proposed ? "repair-approval-1" : null,
      approved_repair_approval_id: null,
      rollback_targets: [{ id: "rollback-a1", label: "checkpoint.json", file_path: "G:\\proof\\checkpoint.json", evidence_type: "rollback_checkpoint", gate: "ROLLBACK_TARGET" }],
      can_request_repair: !proposed,
      can_apply_repair: false,
      can_retry: false,
      can_rollback: true,
      blocker: { gate: proposed ? "REPAIR_APPROVAL" : "REPAIR_PROPOSAL", reason: proposed ? "Repair approval is pending operator decision." : "A failed step needs a repair proposal." },
    },
  }));
  await page.route("**/api/jobs/failed-1/repair/propose", async (route) => {
    proposed = true;
    const payload = route.request().postDataJSON() as { reason?: string };
    expect(payload.reason).toBe("Bounds check failed");
    await fulfillJson(route, { job_id: "failed-1", status: "pending", approval_id: "repair-approval-1", proof_event_id: "proof-repair-1", created: true });
  });
  await page.route("**/api/jobs/failed-1/rollback", async (route) => {
    rollbackCalled = true;
    const payload = route.request().postDataJSON() as { target_artifact_id?: string };
    expect(payload.target_artifact_id).toBe("rollback-a1");
    await fulfillJson(route, { job_id: "failed-1", status: "rolled_back", target_artifact_id: "rollback-a1", proof_event_id: "proof-rollback-1" });
  });

  await page.goto("/#jobs");
  const root = page.getByTestId("jobs-root");
  await root.getByRole("button", { name: /Failed slice/ }).click();
  page.once("dialog", (dialog) => dialog.accept("Bounds check failed"));
  await root.getByRole("button", { name: "Request Repair", exact: true }).click();
  await expect(root.getByText(/Repair approval repair-approval-1 is pending/)).toBeVisible();
  await root.getByRole("button", { name: "Rollback", exact: true }).click();
  await expect(root.getByText(/Rollback moved job to rolled_back/)).toBeVisible();
  expect(rollbackCalled).toBe(true);
});

test("dashboard resizes to operator window without body scroll or phantom bottom space", async ({ page }) => {
  const viewports = [
    { width: 1366, height: 768 },
    { width: 1920, height: 1080 },
    { width: 2560, height: 1440 },
  ];

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto("/#dashboard");
    await expect(page.getByTestId("dashboard-root")).toBeVisible();
    const metrics = await page.evaluate(() => {
      const root = document.querySelector('[data-testid="dashboard-root"]');
      const rect = root?.getBoundingClientRect();
      return {
        bodyOverflowY: document.documentElement.scrollHeight - window.innerHeight,
        rootBottomGap: rect ? Math.round(window.innerHeight - rect.bottom) : 9999,
        rootTop: rect ? Math.round(rect.top) : 0,
        rootHeight: rect ? Math.round(rect.height) : 0,
      };
    });
    expect(metrics.bodyOverflowY).toBeLessThanOrEqual(2);
    expect(metrics.rootBottomGap).toBeGreaterThanOrEqual(8);
    expect(metrics.rootBottomGap).toBeLessThanOrEqual(18);
    expect(metrics.rootHeight).toBeGreaterThan(viewport.height - metrics.rootTop - 24);
  }
});

test("simple dashboard matches operator window sizing without body scroll", async ({ page }) => {
  const viewports = [
    { width: 1366, height: 768 },
    { width: 1920, height: 1080 },
    { width: 2560, height: 1440 },
  ];

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto("/#dashboard");
    const simpleRoot = page.getByTestId("simple-version-root");
    const alreadySimple = await simpleRoot.isVisible({ timeout: 500 }).catch(() => false);
    if (!alreadySimple) {
      await page.getByRole("button", { name: "Simple", exact: true }).click();
    }
    await expect(simpleRoot).toBeVisible();
    const metrics = await page.evaluate(() => {
      const root = document.querySelector('[data-testid="simple-version-root"]');
      const grid = document.querySelector('[data-testid="simple-dashboard-grid"]');
      const rootRect = root?.getBoundingClientRect();
      const gridRect = grid?.getBoundingClientRect();
      return {
        bodyOverflowX: Math.ceil(document.documentElement.scrollWidth - window.innerWidth),
        bodyOverflowY: Math.ceil(document.documentElement.scrollHeight - window.innerHeight),
        gridBottomGap: gridRect ? Math.round(window.innerHeight - gridRect.bottom) : 9999,
        gridOverflowX: grid ? Math.ceil(grid.scrollWidth - grid.clientWidth) : 9999,
        gridOverflowY: grid ? Math.ceil(grid.scrollHeight - grid.clientHeight) : 9999,
        rootBottomGap: rootRect ? Math.round(window.innerHeight - rootRect.bottom) : 9999,
      };
    });
    expect(metrics.bodyOverflowX).toBeLessThanOrEqual(2);
    expect(metrics.bodyOverflowY).toBeLessThanOrEqual(2);
    expect(metrics.rootBottomGap).toBeGreaterThanOrEqual(0);
    expect(metrics.rootBottomGap).toBeLessThanOrEqual(2);
    expect(metrics.gridBottomGap).toBeGreaterThanOrEqual(16);
    expect(metrics.gridBottomGap).toBeLessThanOrEqual(24);
    expect(metrics.gridOverflowX).toBeLessThanOrEqual(2);
    expect(metrics.gridOverflowY).toBeLessThanOrEqual(2);
  }
});

test("simple mode sidebar routes to live tabs without leaving simple shell", async ({ page }) => {
  await page.goto("/#dashboard");
  const simpleRoot = page.getByTestId("simple-version-root");
  const alreadySimple = await simpleRoot.isVisible({ timeout: 500 }).catch(() => false);
  if (!alreadySimple) {
    await page.getByRole("button", { name: "Simple", exact: true }).click();
  }
  await expect(simpleRoot).toBeVisible();
  await expect(simpleRoot.getByTestId("simple-nav-roadmap")).toHaveCount(0);
  await simpleRoot.getByTestId("simple-nav-autopilot").click();
  await expect(simpleRoot).toBeVisible();
  await expect(page.getByTestId("simple-live-tab-root")).toBeVisible();
  await expect(page.getByTestId("autopilot-root")).toBeVisible();
  expect(new URL(page.url()).hash).toBe("#autopilot");
  await simpleRoot.getByTestId("simple-nav-source_os").click();
  await expect(simpleRoot).toBeVisible();
  await expect(page.getByTestId("simple-live-tab-root")).toBeVisible();
  await expect(page.getByTestId("source-os-root")).toBeVisible();
  expect(new URL(page.url()).hash).toBe("#sources");
  await simpleRoot.getByTestId("simple-nav-agents").click();
  await expect(simpleRoot).toBeVisible();
  await expect(page.getByTestId("simple-live-tab-root")).toBeVisible();
  await expect(page.getByTestId("agents-root")).toBeVisible();
  expect(new URL(page.url()).hash).toBe("#agents");
  await simpleRoot.getByTestId("simple-nav-dashboard").click();
  await expect(simpleRoot).toBeVisible();
  await expect(page.getByTestId("simple-dashboard-grid")).toBeVisible();
  expect(new URL(page.url()).hash).toBe("#dashboard");
  await expect(page.getByTestId("app-shell-root")).toHaveCount(0);
});

test("hash route sync mounts the requested tab after direct navigation", async ({ page }) => {
  await page.goto("/#observe");
  await expect(page.getByTestId("observe-root")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("dashboard-root")).toHaveCount(0);
  await page.goto("/#dashboard");
  await expect(page.getByTestId("dashboard-root")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("observe-root")).toHaveCount(0);
  // W6-3 dashboard 3-modes feature appends a :<mode> suffix (e.g.
  // #dashboard:advanced) when the user has a saved mode. Accept either
  // the bare `#dashboard` or `#dashboard:<mode>` forms.
  expect(new URL(page.url()).hash).toMatch(/^#dashboard(?::[a-z0-9-]+)?$/);
});

test("printer panel reflects operator IPs and keeps S1 test locked", async ({ page }) => {
  test.setTimeout(60_000);
  await page.request.put("http://127.0.0.1:8765/api/printers/flsun_t1_a/status", {
    data: { status: "online", actor: "playwright" },
  });
  await page.request.put("http://127.0.0.1:8765/api/printers/flsun_t1_b/status", {
    data: { status: "online", actor: "playwright" },
  });
  await page.request.put("http://127.0.0.1:8765/api/printers/flsun_v400/status", {
    data: { status: "online", actor: "playwright" },
  });
  await page.request.put("http://127.0.0.1:8765/api/printers/flsun_s1/status", {
    data: { status: "online", actor: "playwright" },
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Printers", exact: true }).click();
  const root = page.getByTestId("printers-root");
  await expect(root).toBeVisible();

  for (const ip of ["192.168.0.10", "192.168.0.11", "192.168.0.12", "192.168.0.34"]) {
    await expect(root.getByText(ip, { exact: true })).toBeVisible({ timeout: 20_000 });
  }

  const s1Panel = root.locator("section").filter({ hasText: "FLSUN S1" });
  await expect(s1Panel.getByText(/ONLINE \/ LOCKED/i)).toBeVisible();
  await expect(s1Panel.getByRole("button", { name: "Test", exact: true })).toBeDisabled();

  const t1Panel = root.locator("section").filter({ hasText: "T1 #1" });
  await expect(t1Panel.getByRole("button", { name: "Test", exact: true })).toBeEnabled();
  await t1Panel.getByRole("button", { name: "Test", exact: true }).click();
  await expect(t1Panel.getByText(/MOONRAKER (OK|FAIL)/i)).toBeVisible({ timeout: 20_000 });
});

test("Printers appends onboarded fleet rows after the fixed operator printers", async ({ page }) => {
  await page.route("**/api/printers", async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await fulfillJson(route, [
      printerRow({ id: "flsun_t1_a", name: "T1 #1", model: "FLSUN T1", ip: "192.168.0.10" }),
      printerRow({ id: "flsun_t1_b", name: "T1 #2", model: "FLSUN T1", ip: "192.168.0.11" }),
      printerRow({ id: "flsun_s1", name: "FLSUN S1", model: "FLSUN S1", ip: "192.168.0.12", maintenance_flag: true, write_enabled: false, safety_policy: "locked" }),
      printerRow({ id: "flsun_v400", name: "FLSUN V400", model: "FLSUN V400", ip: "192.168.0.34" }),
      printerRow({ id: "garage_t1", name: "Garage T1", model: "FLSUN T1", ip: "192.168.0.50", onboarded: true, safety_policy: "read_only", write_enabled: false }),
    ]);
  });
  await page.route("**/api/printers/s1/lock", (route) => fulfillJson(route, {
    printer_id: "flsun_s1",
    locked: true,
    reason: "Maintenance lock: do not test or move.",
    locked_by: "backend-safety-policy",
    ip: "192.168.0.12",
  }));
  await page.route("**/api/proof/events", (route) => fulfillJson(route, { saved: true }));

  await page.goto("/#printers");
  const root = page.getByTestId("printers-root");
  await expect(root).toBeVisible();
  await expect(root.getByText("Garage T1", { exact: true })).toBeVisible();
  await expect(root.getByText("192.168.0.50", { exact: true })).toBeVisible();
  await expect(root.getByText("Onboarding:")).toBeVisible();
  const onboardedPanel = root.locator("section").filter({ hasText: "Garage T1" });
  await expect(onboardedPanel.getByRole("button", { name: "Upload G-code", exact: true })).toBeDisabled();
  const s1Panel = root.locator("section").filter({ hasText: "FLSUN S1" });
  await expect(s1Panel.getByRole("button", { name: "Test", exact: true })).toBeDisabled();
});

test("Printer Upload + Start sends approved job id to backend gates", async ({ page }) => {
  let uploadBody: Record<string, unknown> | null = null;
  await page.route("**/api/printers", async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await fulfillJson(route, [
      printerRow({ id: "flsun_t1_a", name: "T1 #1", model: "FLSUN T1", ip: "192.168.0.10" }),
    ]);
  });
  await page.route("**/api/proof/events", (route) => fulfillJson(route, { saved: true }));
  await page.route("**/api/printers/flsun_t1_a/upload-gcode", async (route) => {
    uploadBody = JSON.parse(route.request().postData() ?? "{}");
    await fulfillJson(route, {
      printer_id: "flsun_t1_a",
      accepted: true,
      uploaded: true,
      started: true,
      job_id: uploadBody?.job_id,
      item_path: "hermes3d/proof.gcode",
      bounds_passed: true,
    });
  });

  await page.goto("/#printers");
  const t1Panel = page.getByTestId("printers-root").locator("section").filter({ hasText: "T1 #1" });
  await expect(t1Panel).toBeVisible();
  await t1Panel.getByLabel("Local G-code path for backend upload").fill("G:\\proof\\part.gcode");
  await expect(t1Panel.getByRole("button", { name: "Upload + Start", exact: true })).toBeDisabled();
  await t1Panel.getByLabel("T1 #1 approved job ID").fill("job-approved-1");
  await t1Panel.getByRole("button", { name: "Upload + Start", exact: true }).click();
  await expect(t1Panel.getByText(/Started hermes3d\/proof.gcode/)).toBeVisible();
  expect(uploadBody).toEqual(expect.objectContaining({
    start: true,
    job_id: "job-approved-1",
    actor: "local-operator",
  }));
});

test("Source OS shows source-backed modules from the backend", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Source OS", exact: true }).click();
  const root = page.getByTestId("source-os-root");
  await expect(root).toBeVisible();
  await expect(root.getByText(/source-backed modules from the local API module registry/i)).toBeVisible();
  await expect(root.getByTestId("source-runtime-readiness")).toBeVisible();
  await expect(root.getByRole("button", { name: /Slicers/i })).toBeVisible();
});

test("Source OS wires source app backup, update check, and gated update execution", async ({ page }) => {
  const modules = [
    sourceOSModule({ id: "printrun", display: "Printrun", installState: "installed" }),
  ];
  let backupAvailable = false;
  let checkRequests = 0;
  let applyRequests = 0;
  let verifyAllRequests = 0;
  let setupQueueGetRequests = 0;
  let setupQueuePostRequests = 0;
  await page.route("**/api/modules", (route) => fulfillJson(route, modules));
  await page.route("**/api/modules/update/readiness**", (route) => {
    const deep = new URL(route.request().url()).searchParams.get("deep") === "true";
    return fulfillJson(route, sourceUpdateReadiness(deep, { backupAvailable, latestCheck: checkRequests > 0 }));
  });
  await page.route("**/api/modules/runtime/verify-all", (route) => {
    verifyAllRequests += 1;
    return fulfillJson(route, {
      accepted: true,
      status: "completed",
      count: 1,
      counts: {
        ready: 1,
        source_ready: 0,
        setup_required: 0,
        not_installed: 0,
        blocked: 0,
      },
      all_runtime_ready: true,
      records: [],
      proof_event_id: "proof-batch",
    });
  });
  await page.route("**/api/modules/runtime/setup-queue", (route) => {
    if (route.request().method() === "POST") {
      setupQueuePostRequests += 1;
    } else {
      setupQueueGetRequests += 1;
    }
    return fulfillJson(route, {
      accepted: true,
      status: "planned",
      count: 1,
      counts: {
        runtime_ready: 0,
        source_ready: 1,
        runner_not_registered: 1,
        source_install_available: 0,
        runtime_repair_required: 0,
        blocked: 0,
      },
      execution_mode: "plan_only_until_safe_runner_registered",
      agent_gate: "Hermes Agents may consume this queue after proof.",
      records: [],
      proof_event_id: "proof-setup-queue",
    });
  });
  await page.route("**/api/modules/runtime/cli-surface", (route) => fulfillJson(route, {
    status: "ready",
    count: 1,
    proof_source: "03_implementation/proof/SOURCE_APP_CLI_SURFACE_AUDIT.json",
    summary: {
      agent_enabled_cli: 0,
      candidate_needs_verifier: 1,
      no_local_cli_signal: 0,
    },
    records: [
      {
        module_id: "printrun",
        display: "Printrun",
        section: "utilities",
        launch_kind: "desktop_or_cli",
        install_state: "installed",
        agent_execution_tier: "cli_preferred_gap",
        cli_surface_status: "cli_candidate_needs_verifier",
        agent_enabled: false,
        runtime_status: "source_ready",
        verifier: "source checkout",
        verifier_kind: "desktop_or_cli",
        proof_gate_version: "",
        path: "G:\\tmp\\printrun",
        source_signals: [
          {
            kind: "readme_cli_signal",
            source: "README.md",
            name: "docs",
            command: "pronsole command-line interface",
          },
        ],
        next_action: "Add a non-destructive CLI verifier before exposing this to Hermes Agents.",
      },
    ],
  }));
  await page.route("**/api/modules/printrun/update/backup", (route) => {
    backupAvailable = true;
    return fulfillJson(route, {
      backup_id: "backup-1",
      module_id: "printrun",
      commit: "abc123",
      branch: "main",
      exact_tag: null,
      nearest_tag: "v1.0.0",
      dirty: false,
      bundle_path: "G:\\tmp\\backup-1.bundle",
      dirty_zip_path: null,
      created_at: new Date(0).toISOString(),
      proof_event_id: "proof-backup",
    });
  });
  await page.route("**/api/modules/printrun/update/check", (route) => {
    checkRequests += 1;
    return fulfillJson(route, {
      module_id: "printrun",
      status: "current",
      current_commit: "abc123",
      remote_commit: "def456789012",
      branch: "main",
      remote_ref: "refs/heads/main",
      backup_available: backupAvailable,
      checked_at: new Date(0).toISOString(),
      proof_event_id: "proof-check",
    });
  });
  await page.route("**/api/modules/printrun/update/apply", (route) => {
    applyRequests += 1;
    return fulfillJson(route, {
      accepted: true,
      updated: false,
      status: "current",
      module_id: "printrun",
      backup_id: "backup-1",
      commit: "abc123",
      proof_event_id: "proof-update",
    });
  });
  await page.route("**/api/modules/printrun/runtime/verify", (route) => fulfillJson(route, {
    accepted: true,
    runtime_ready: true,
    status: "ready",
    module_id: "printrun",
    runtime: {
      status: "ready",
      label: "Runtime ready",
      kind: "desktop_app",
      verifier: "Printrun Windows launcher",
      path: "G:\\Github\\apps\\Pronterface.exe",
      detected: true,
      executed: false,
      return_code: null,
      capabilities: ["serial_gui_app"],
      reason: null,
      setup_steps: [],
      proof_source: "03_implementation/proof/LOCAL_TOOLING_AUDIT.json",
      output_head: [],
    },
    proof_event_id: "proof-runtime",
  }));
  await page.route("**/api/modules/printrun/runtime/setup-plan", (route) => fulfillJson(route, {
    accepted: true,
    status: "planned",
    module_id: "printrun",
    record: {
      module_id: "printrun",
      display: "Printrun",
      runner_status: "runner_not_registered",
      next_action: "register safe module runner",
      setup_steps: ["Register a safe verifier for this module before marking runtime ready."],
    },
    proof_event_id: "proof-setup-plan",
  }));
  await page.route("**/api/plugins", (route) => fulfillJson(route, [
    {
      id: "moonraker",
      display: "Moonraker",
      description: "Moonraker API adapter",
      state: "ACTIVE",
      configured: true,
      status: "configured",
      reason: null,
      dependencies: [],
      configSchema: null,
      healthUrl: null,
      installVia: "none",
      sourceOsModuleId: null,
    },
  ]));

  await page.goto("/#source_os");
  const sourceRoot = page.getByTestId("source-os-root");
  await expect(sourceRoot.getByTestId("source-update-readiness")).toContainText("1 apps");
  await expect(sourceRoot.getByTestId("source-update-readiness")).toContainText("1 ready");
  await expect(sourceRoot.getByTestId("source-runtime-readiness")).toContainText("0 runtime ready");
  await expect(sourceRoot.getByTestId("source-runtime-readiness")).toContainText("1 CLI signals");
  await expect(sourceRoot.getByTestId("source-runtime-readiness")).toContainText("1 source ready");
  await sourceRoot.getByRole("button", { name: "Verify All", exact: true }).click();
  await expect(sourceRoot.getByText(/Verify All accepted/)).toBeVisible();
  expect(verifyAllRequests).toBe(1);
  await sourceRoot.getByRole("button", { name: "Setup Queue", exact: true }).click();
  await expect(sourceRoot.getByText(/Setup Queue accepted/)).toBeVisible();
  await expect(sourceRoot.getByText(/proof-setup-queue/)).toBeVisible();
  expect(setupQueuePostRequests).toBe(1);
  await expect(sourceRoot.locator("aside")).not.toContainText("UNKNOWN");
  await expect(sourceRoot.locator("aside")).toContainText(/source/i);
  await expect(sourceRoot.locator("aside")).toContainText(/CLI signal/i);
  await expect(sourceRoot.getByText("Hermes Agent CLI")).toBeVisible();
  await expect(sourceRoot.getByText(/detected; verifier required/i)).toBeVisible();
  await expect(sourceRoot.getByText(/CLI\/service signal/i)).toBeVisible();
  await sourceRoot.getByRole("button", { name: "Verify", exact: true }).click();
  await expect(sourceRoot.getByText(/Verify accepted/)).toBeVisible();
  await sourceRoot.getByRole("button", { name: "Setup Plan", exact: true }).click();
  await expect(sourceRoot.getByText(/Setup Plan accepted/)).toBeVisible();
  await expect(sourceRoot.getByText(/proof-setup-plan/)).toBeVisible();
  await expect(sourceRoot.getByRole("button", { name: "Update", exact: true })).toBeDisabled();
  await sourceRoot.getByRole("button", { name: "Backup", exact: true }).click();
  await expect(sourceRoot.getByText(/Backup accepted/)).toBeVisible();
  await expect(sourceRoot.getByText("backup-1", { exact: true })).toBeVisible();
  await sourceRoot.getByRole("button", { name: "Deep Check", exact: true }).click();
  await expect(sourceRoot.getByText("main", { exact: true })).toBeVisible();
  await expect(sourceRoot.getByRole("button", { name: "Update", exact: true })).toBeEnabled();
  await sourceRoot.getByRole("button", { name: "Check Update", exact: true }).click();
  await expect(sourceRoot.getByText(/Check Update accepted/)).toBeVisible();
  await expect(sourceRoot.getByText("current · def456789012", { exact: true })).toBeVisible();
  // Guard with waitForResponse so the counter is checked only AFTER the
  // apply endpoint actually responds.  Without this, the still-visible
  // "Check Update accepted" toast from the previous step satisfies the
  // /Update accepted/ regex before the real POST /update/apply completes.
  const applyResponsePromise = page.waitForResponse("**/api/modules/printrun/update/apply");
  await sourceRoot.getByRole("button", { name: "Update", exact: true }).click();
  await applyResponsePromise;
  await expect(sourceRoot.getByText(/Update accepted/)).toBeVisible();
  expect(applyRequests).toBe(1);

  await page.goto("/#plugins");
  const pluginsRoot = page.getByTestId("plugins-root");
  await expect(pluginsRoot.getByTestId("plugins-update-readiness")).toContainText("1 apps");
  await expect(pluginsRoot.getByTestId("plugins-update-readiness")).toContainText("1 ready");
  await expect(pluginsRoot.getByTestId("plugins-runtime-setup-queue")).toContainText("1 apps");
  await expect(pluginsRoot.getByTestId("plugins-runtime-setup-queue")).toContainText("1 needs runner");
  expect(setupQueueGetRequests).toBeGreaterThanOrEqual(1);
  await pluginsRoot.getByRole("button", { name: "Plan Setup Queue", exact: true }).click();
  await expect(pluginsRoot.getByText(/proof-setup-queue/)).toBeVisible();
  expect(setupQueuePostRequests).toBe(2);
  await pluginsRoot.getByRole("button", { name: "Deep Check", exact: true }).click();
  await expect(pluginsRoot.getByTestId("plugins-update-readiness")).toContainText("deep");
});

test("Source OS blocks false-ish 200 OK module action payloads", async ({ page }) => {
  const modules = [
    sourceOSModule({ id: "printrun", display: "Printrun", installState: "installed" }),
    sourceOSModule({ id: "rollback-runner", display: "Rollback Runner", installState: "rollback_available", health: "degraded" }),
  ];
  const readiness = sourceUpdateReadiness(false);
  readiness.count = 2;
  readiness.records = [
    readiness.records[0],
    {
      ...readiness.records[0],
      module_id: "rollback-runner",
      display: "Rollback Runner",
      install_state: "rollback_available",
      backup_available: true,
      latest_backup: {
        backup_id: "rollback-backup-1",
        module_id: "rollback-runner",
        commit: "abc123",
        branch: "main",
        exact_tag: null,
        nearest_tag: null,
        dirty: false,
        bundle_path: "G:\\tmp\\rollback-backup-1.bundle",
        dirty_zip_path: null,
        created_at: new Date(0).toISOString(),
      },
    },
  ];

  await page.route("**/api/modules", (route) => fulfillJson(route, modules));
  await page.route("**/api/modules/update/readiness**", (route) => fulfillJson(route, readiness));
  await page.route("**/api/modules/printrun/launch", (route) => fulfillJson(route, {
    module_id: "printrun",
    success: false,
    status: "not_configured",
    notes: "No real launch bridge is configured for this module.",
  }));
  await page.route("**/api/modules/printrun/stop", (route) => fulfillJson(route, {
    detail: {
      module_id: "printrun",
      stopped: false,
      status: "not_configured",
      reason: "Nested stop bridge is not configured.",
    },
  }));
  await page.route("**/api/modules/rollback-runner/rollback", (route) => fulfillJson(route, {
    module_id: "rollback-runner",
    rollback_started: false,
    reason: "No checkpoint recorded.",
  }));

  await page.goto("/");
  await page.getByRole("button", { name: "Source OS", exact: true }).click();
  const root = page.getByTestId("source-os-root");
  await expect(root).toBeVisible();
  await expect(root.getByText("No real dispatch gate endpoint is connected for this source module.")).toBeVisible();
  await expect(root.getByText("Install or detect module first")).toHaveCount(0);

  await root.getByRole("button", { name: "Launch", exact: true }).click();
  await expect(root.getByText("Launch blocked: No real launch bridge is configured for this module.")).toBeVisible();
  await expect(root.getByText(/Launch (accepted|completed)/)).toHaveCount(0);

  await root.getByRole("button", { name: "Stop", exact: true }).click();
  await expect(root.getByText("Stop blocked: Nested stop bridge is not configured.")).toBeVisible();
  await expect(root.getByText(/Stop (accepted|completed)/)).toHaveCount(0);

  await root.locator("aside").getByRole("button").filter({ hasText: "Rollback Runner" }).click();
  await root.getByRole("button", { name: "Rollback", exact: true }).click();
  await expect(root.getByText("Rollback blocked: No checkpoint recorded.")).toBeVisible();
  await expect(root.getByText(/Rollback (accepted|completed)/)).toHaveCount(0);
});

test("Observe renders live camera feed cards and exposes V400 USB webcam endpoint", async ({ page }) => {
  await page.request.put("http://127.0.0.1:8765/api/settings", {
    data: { cameraUrls: { flsun_v400: "http://192.168.0.34/webcam/?action=stream" } },
  });
  await page.request.put("http://127.0.0.1:8765/api/observe/cameras/flsun_s1/view", {
    data: { rotate_deg: 90, fit: "cover", card_size: "wide", review_overlay: "plate_frame" },
  });
  await page.goto("/#observe");
  const root = page.getByTestId("observe-root");
  await expect(root).toBeVisible();

  for (const name of ["T1 #1", "T1 #2", "FLSUN S1"]) {
    const card = root.locator("section").filter({ hasText: name });
    await expect(card.getByRole("img", { name: `${name} live camera feed` })).toBeVisible({ timeout: 20_000 });
    await expect(card.getByText("Integrated camera", { exact: true })).toBeVisible();
  }
  await root.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(root.getByRole("button", { name: "Refreshing", exact: true })).toBeVisible();
  await expect(root.getByTestId("observe-status-banner")).toHaveText("Camera feeds refreshed: 4/4 configured feeds.", { timeout: 30_000 });
  expect(new URL(page.url()).hash).toBe("#observe");

  const s1Card = root.locator("section").filter({ hasText: "FLSUN S1" });
  await expect(s1Card.getByText("printer actions locked", { exact: true })).toBeVisible();
  await expect(s1Card.getByText("plate locked", { exact: true })).toBeVisible();
  await expect(s1Card.getByRole("img", { name: "FLSUN S1 live camera feed" })).toHaveCSS("transform", /matrix\(0, [\d.]+, -[\d.]+, 0,/);
  await s1Card.getByTitle("Camera display controls").click();
  await expect(s1Card.getByText("Feed type", { exact: true })).toBeVisible();
  await expect(s1Card.getByText("Brightness", { exact: true })).toBeVisible();
  await expect(s1Card.getByText("Contrast", { exact: true })).toBeVisible();
  await expect(s1Card.getByText("S1 preset", { exact: true })).toBeVisible();
  const s1Image = s1Card.getByRole("img", { name: "FLSUN S1 live camera feed" });
  const initialTransform = await s1Image.evaluate((node) => getComputedStyle(node).transform);
  await s1Card.getByTitle("Zoom in").click();
  await expect.poll(async () => s1Image.evaluate((node) => getComputedStyle(node).transform)).not.toBe(initialTransform);
  const zoomedTransform = await s1Image.evaluate((node) => getComputedStyle(node).transform);
  await s1Card.getByTitle("Rotate right 90 degrees").click();
  await expect.poll(async () => s1Image.evaluate((node) => getComputedStyle(node).transform)).not.toBe(zoomedTransform);
  await s1Card.getByRole("button", { name: "S1 90", exact: true }).click();

  await root.getByRole("button", { name: "T1 #1", exact: true }).click();
  await root.getByRole("button", { name: "selected", exact: true }).click();
  await expect(root.getByRole("img", { name: "T1 #1 live camera feed" })).toHaveCount(0);
  await expect(root.getByRole("img", { name: "FLSUN S1 live camera feed" })).toBeVisible();

  const v400Card = root.locator("section").filter({ hasText: "FLSUN V400" });
  await expect(v400Card.getByText("USB webcam", { exact: true })).toBeVisible();
  await expect(v400Card.getByRole("img", { name: "FLSUN V400 live camera feed" })).toBeVisible({ timeout: 20_000 });
  await expect(v400Card.getByText("USB webcam not configured", { exact: true })).toHaveCount(0);
  await expect(v400Card.getByRole("button", { name: "Open", exact: true })).toBeEnabled();
  await expect(v400Card.getByRole("button", { name: "Probe", exact: true })).toBeEnabled();
});

test("Settings exposes camera URL fields for printer feed setup", async ({ page }) => {
  await page.goto("/#settings");
  await expect(page.getByTestId("settings-root")).toBeVisible();
  await page.getByTestId("settings-subtab-printers").click();
  const root = page.getByTestId("settings-printers");
  await expect(root).toBeVisible();
  await expect(root.getByLabel("FLSUN V400 camera URL")).toBeVisible({ timeout: 30_000 });
  await expect(root.getByLabel("FLSUN S1 camera URL")).toHaveValue(/192\.168\.0\.12/, { timeout: 30_000 });
});

test("Settings printer onboarding reports exact failed Moonraker probe", async ({ page }) => {
  await page.route("**/api/printers", async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await fulfillJson(route, [
      printerRow({ id: "flsun_t1_a", name: "T1 #1", model: "FLSUN T1", ip: "192.168.0.10" }),
      printerRow({ id: "flsun_t1_b", name: "T1 #2", model: "FLSUN T1", ip: "192.168.0.11" }),
      printerRow({ id: "flsun_s1", name: "FLSUN S1", model: "FLSUN S1", ip: "192.168.0.12", maintenance_flag: true, write_enabled: false, safety_policy: "locked" }),
      printerRow({ id: "flsun_v400", name: "FLSUN V400", model: "FLSUN V400", ip: "192.168.0.34" }),
    ]);
  });
  await page.route("**/api/settings", (route) => fulfillJson(route, {
    theme: "midnight",
    ports: { bridge: 8765, api: 8765, ui: 5173 },
    printerUrls: {},
    cameraUrls: {},
    serviceUrls: {},
  }));
  await page.route("**/api/printers/onboard", (route) => fulfillJson(route, {
    detail: {
      error: "ONBOARDING_PROBE_FAILED",
      failed_probe: "server_info",
      reason: "Network error on http://192.168.0.50/server/info",
      probes: [{ name: "server_info", ok: false, reason: "Network error on http://192.168.0.50/server/info" }],
    },
  }, 502));

  await page.goto("/#settings");
  await page.getByTestId("settings-subtab-printers").click();
  const form = page.getByTestId("printer-onboarding-form");
  await expect(form).toBeVisible();
  await form.getByLabel("New printer name").fill("Garage T1");
  await form.getByLabel("New printer Moonraker URL").fill("http://192.168.0.50");
  await form.getByRole("button", { name: "Add", exact: true }).click();
  await expect(form.getByText(/Onboarding blocked at server_info/)).toBeVisible();
});

test("Settings Environment shows runtime readiness truth ledger", async ({ page }) => {
  await page.route("**/api/env/status", (route) => fulfillJson(route, {
    variables: [
      { name: "AZURE_SPEECH_KEY", set: true, sensitive: true, description: "Azure Speech key for local voice runtime." },
      { name: "HERMES3D_AGENT_RUNTIME_URL", set: false, sensitive: false, description: "Hermes Agent runtime URL." },
    ],
  }));
  await page.route("**/api/system/runtime-readiness", (route) => fulfillJson(route, {
    updated_at: new Date(0).toISOString(),
    summary: { total: 3, ready: 1, partial: 1, blocked: 1, locked: 0 },
    runtimes: [
      { id: "azure_speech", label: "Azure Speech TTS/STT", category: "voice", status: "ready", source: "private_env", reason: "Azure Speech key and region are available to the backend only.", required_env: ["AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"], proof: "/api/voice/providers" },
      { id: "source_update_execution", label: "Source app update execution", category: "updates", status: "partial", source: "backend", reason: "Readiness checks are live; update execution is still gated.", required_env: [], proof: "/api/modules/update/readiness" },
      { id: "hermes_agent_runtime", label: "Hermes Agent runtime", category: "agents", status: "blocked", source: "env/private_env", reason: "Set HERMES3D_AGENT_RUNTIME_URL to a trusted runtime.", required_env: ["HERMES3D_AGENT_RUNTIME_URL"], proof: "/api/agents/health" },
    ],
  }));
  await page.route("**/api/modules/runtime/setup-queue", (route) => fulfillJson(route, {
    accepted: true,
    status: "planned",
    count: 60,
    counts: {
      runtime_ready: 5,
      source_ready: 55,
      runner_not_registered: 55,
      source_install_available: 0,
      runtime_repair_required: 0,
      blocked: 0,
    },
    execution_mode: "plan_only_until_safe_runner_registered",
    agent_gate: "No source module setup runner executes until it is registered with a safe verifier and proof gate.",
    records: [],
    proof_event_id: route.request().method() === "POST" ? "proof-setup-queue" : null,
  }));

  await page.goto("/#settings");
  await page.getByTestId("settings-subtab-environment").click();
  const panel = page.getByTestId("settings-panel-environment");
  await expect(panel.getByText("Runtime Readiness", { exact: true })).toBeVisible();
  await expect(panel.getByText("1 ready", { exact: true })).toBeVisible();
  await expect(panel.getByText("1 partial", { exact: true })).toBeVisible();
  await expect(panel.getByText("1 blocked", { exact: true })).toBeVisible();
  await expect(panel.getByText("Azure Speech TTS/STT", { exact: true })).toBeVisible();
  await expect(panel.getByText("Hermes Agent runtime", { exact: true })).toBeVisible();
  await expect(panel.getByText("HERMES3D_AGENT_RUNTIME_URL", { exact: true }).first()).toBeVisible();
  await expect(panel.getByTestId("settings-runtime-setup-queue")).toContainText("60 apps");
  await expect(panel.getByTestId("settings-runtime-setup-queue")).toContainText("55 need runners");
  await panel.getByRole("button", { name: "Plan setup queue", exact: true }).click();
  await expect(panel.getByText(/proof-setup-queue/)).toBeVisible();
});

test("Learning saves use the learning config API instead of generic settings", async ({ page }) => {
  const learningSaves: unknown[] = [];
  const settingsPuts: string[] = [];

  await page.route("**/api/settings", async (route) => {
    if (route.request().method() === "PUT") {
      settingsPuts.push(route.request().url());
    }
    await route.continue();
  });
  await page.route("**/api/learning/config", async (route) => {
    const request = route.request();
    if (request.method() === "PUT") {
      learningSaves.push(JSON.parse(request.postData() ?? "{}"));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          enabled: true,
          active: false,
          idle_minutes: 30,
          runner_status: "not_configured",
          reason: "Idle learning runner is not configured.",
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ enabled: false, active: false, idle_minutes: 30, runner_status: "not_configured" }),
    });
  });
  await page.route("**/api/learning/reports", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/learning/idle-workbench", (route) => fulfillJson(route, idleWorkbench([], [])));

  await page.goto("/#learning");
  await expect(page.getByTestId("learning-root")).toBeVisible();
  await page.getByLabel("Mode").selectOption("idle");
  await expect(page.getByLabel("Mode")).toHaveValue("idle");
  await expect(page.getByText("Saved Idle selection; runtime blocked: Idle learning runner is not configured.")).toBeVisible();
  await expect(page.getByText("Idle selected; not_configured", { exact: true })).toBeVisible();
  await expect(page.getByText("Hermes runtime not configured", { exact: true })).toBeVisible();
  await expect(page.getByText("0/5 execution-ready; queue remains review-gated", { exact: true })).toBeVisible();
  await expect(page.getByText("Research reports", { exact: true })).toBeVisible();

  expect(learningSaves).toEqual([{ enabled: true, idle_minutes: 30 }]);
  expect(settingsPuts).toEqual([]);
});

test("Learning mode remains selectable when config API is unavailable", async ({ page }) => {
  await page.route("**/api/learning/config", async (route) => {
    if (route.request().method() === "PUT") {
      await fulfillJson(route, { detail: { reason: "Learning config API offline." } }, 503);
      return;
    }
    await fulfillJson(route, { detail: { reason: "Learning config API offline." } }, 503);
  });
  await page.route("**/api/learning/reports", (route) => fulfillJson(route, []));
  await page.route("**/api/learning/idle-workbench", (route) => fulfillJson(route, idleWorkbench([], [])));

  await page.goto("/#learning");
  const mode = page.locator("section#learning\\.config select");
  await expect(mode).toBeEnabled();
  await mode.selectOption("idle");
  await expect(mode).toHaveValue("idle");
  await expect(page.getByText("Save blocked: Learning config API offline.")).toBeVisible();
});

test("Learning idle workbench queues candidates through the live API", async ({ page }) => {
  const candidates: Array<Record<string, unknown>> = [
    idleCandidate({ id: "cand-source-os", title: "Audit Source OS update center", status: "queued" }),
  ];
  const reviewRequests: string[] = [];
  await page.route("**/api/learning/config", (route) => fulfillJson(route, { enabled: false, idle_minutes: 30 }));
  await page.route("**/api/learning/reports", (route) => fulfillJson(route, []));
  await page.route("**/api/proof/events", (route) => fulfillJson(route, { saved: true }));
  await page.route(/.*\/api\/learning\/idle-workbench(?:\/.*)?$/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === "GET" && path === "/api/learning/idle-workbench") {
      await fulfillJson(route, idleWorkbench(candidates, [
        { type: "printer", id: "flsun_t1_a", label: "T1 #1", status: "printing", reason: "Printer is active; agent build/download/install/merge work stays blocked." },
      ]));
      return;
    }
    if (request.method() === "POST" && path === "/api/learning/idle-workbench/candidates") {
      const body = JSON.parse(request.postData() ?? "{}") as Record<string, unknown>;
      const created = idleCandidate({
        id: "cand-created",
        title: String(body.title),
        summary: String(body.summary),
        kind: String(body.kind),
        status: "queued",
      });
      candidates.unshift(created);
      await fulfillJson(route, { accepted: true, status: "queued", proof_event_id: "proof-created", candidate: created, blockers: [] }, 201);
      return;
    }
    if (request.method() === "POST" && path.endsWith("/run")) {
      candidates[0] = {
        ...candidates[0],
        status: "blocked",
        blocked_reason: "Idle learning runner is not configured. Hermes Agent runtime is not configured.",
        proof_event_ids: ["proof-created", "proof-run-blocked"],
      };
      await fulfillJson(route, {
        accepted: false,
        status: "blocked",
        reason: "Idle learning runner is not configured. Hermes Agent runtime is not configured.",
        proof_event_id: "proof-run-blocked",
        candidate: candidates[0],
        blockers: [],
      });
      return;
    }
    if (request.method() === "POST" && path.endsWith("/request-review")) {
      reviewRequests.push(path);
      candidates[0] = { ...candidates[0], status: "ready_for_review", approval_id: "approval-idle-1" };
      await fulfillJson(route, { accepted: true, status: "ready_for_review", approval_id: "approval-idle-1", proof_event_id: "proof-review", candidate: candidates[0] });
      return;
    }
    if (request.method() === "POST" && path.endsWith("/decision")) {
      candidates[0] = { ...candidates[0], status: "approved" };
      await fulfillJson(route, { accepted: true, status: "approved", decision: "keep", proof_event_id: "proof-keep", candidate: candidates[0] });
      return;
    }
    await route.continue();
  });

  await page.goto("/#learning");
  const root = page.getByTestId("learning-root");
  await expect(root).toBeVisible();
  await expect(root.locator("article").filter({ hasText: "Audit Source OS update center" })).toBeVisible();
  await expect(root.getByText(/T1 #1/)).toBeVisible();
  await root.getByLabel("Candidate title").fill("Review FLSUN slicer profiles");
  await root.getByLabel("Kind").selectOption("research");
  await root.getByLabel("Target tab").fill("source_os");
  await root.getByLabel("Summary").fill("Compare detected local slicer profile paths against source registry proofs.");
  await root.getByRole("button", { name: "Queue Candidate", exact: true }).click();
  await expect(root.locator("article").filter({ hasText: "Review FLSUN slicer profiles" })).toBeVisible();
  const createdCard = root.locator("article").filter({ hasText: "Review FLSUN slicer profiles" });
  await createdCard.getByRole("button", { name: "Run", exact: true }).click();
  await expect(root.getByText(/Run blocked: Idle learning runner is not configured/)).toBeVisible();
  await expect(createdCard.getByText(/blocked/)).toBeVisible();
  await createdCard.getByRole("button", { name: "Review", exact: true }).click();
  await expect(createdCard.getByText("Approval: approval-idle-1", { exact: true })).toBeVisible();
  await createdCard.getByRole("button", { name: "Keep", exact: true }).click();
  await expect(createdCard.getByText(/approved/)).toBeVisible();
  expect(reviewRequests).toHaveLength(1);
});

test("Agents tab shows the same idle workbench queue as Learning", async ({ page }) => {
  await page.route("**/api/agents", (route) => fulfillJson(route, [
    { id: "research-agent", name: "Research Agent", status: "paused", model_provider: "not_configured" },
  ]));
  await page.route("**/api/notifications", (route) => fulfillJson(route, { notifications: [], total: 0, unread: 0 }));
  await page.route(/.*\/api\/learning\/idle-workbench$/, (route) => fulfillJson(route, idleWorkbench([
    idleCandidate({ id: "cand-agents", title: "Check Hermes Agent weekly update", status: "ready_for_review" }),
  ], [])));

  await page.goto("/#agents");
  const root = page.getByTestId("agents-root");
  await expect(root).toBeVisible();
  await expect(root.getByText("Check Hermes Agent weekly update", { exact: true })).toBeVisible();
  await root.getByRole("button", { name: "Open Learning", exact: true }).click();
  await expect(page.getByTestId("learning-root")).toBeVisible();
});

test("Agents tab exposes the Hermes Agent OS operator action catalog", async ({ page }) => {
  const actionRuns: unknown[] = [];
  const catalog = {
    status: "in_progress",
    summary: "Hermes Agents can use any Hermes3D OS feature only after a cataloged backend action, safety policy, proof event, and ready or blocked state.",
    contract_version: "agent-operator-contract-v1",
    counts: { ready: 2, partial: 1, blocked: 1 },
    total: 4,
    ready_now: ["agents.health.refresh", "source.runtime_gaps.refresh"],
    blocked_or_partial: ["source.update_all", "printers.s1_actions"],
    contracts: [
      {
        id: "agents.health.refresh",
        label: "Refresh Hermes Agent runtime health",
        tab: "agents",
        status: "ready",
        kind: "read",
        risk: "low",
        route: "GET /api/agents/health",
        agent_callable: true,
        proof_required: true,
        approval_required: false,
        rollback_required: false,
        summary: "Checks the configured local/private agent runtime bridge.",
        blocked_reason: null,
      },
      {
        id: "source.runtime_gaps.refresh",
        label: "Refresh Source OS runner gaps",
        tab: "source_os",
        status: "ready",
        kind: "read",
        risk: "low",
        route: "GET /api/modules/runtime/gaps",
        agent_callable: true,
        proof_required: true,
        approval_required: false,
        rollback_required: false,
        summary: "Shows source-app runner gaps.",
        blocked_reason: null,
      },
      {
        id: "source.update_all",
        label: "Update all Source OS apps",
        tab: "source_os",
        status: "partial",
        kind: "mutate",
        risk: "high",
        route: "PENDING",
        agent_callable: false,
        proof_required: true,
        approval_required: true,
        rollback_required: true,
        summary: "Blocked until backup, approval, smoke gate, and rollback policy are complete.",
        blocked_reason: "App update center is partial.",
      },
      {
        id: "printers.s1_actions",
        label: "Move/upload/test/print on S1",
        tab: "printers",
        status: "blocked",
        kind: "mutate",
        risk: "critical",
        route: "HTTP 423 policy",
        agent_callable: false,
        proof_required: true,
        approval_required: true,
        rollback_required: true,
        summary: "S1 read-only camera/status remains allowed.",
        blocked_reason: "User policy locks S1 movement, upload, test, and print.",
      },
    ],
  };

  await page.route("**/api/agents", (route) => fulfillJson(route, [
    { id: "factory-operator", name: "Factory Operator", status: "idle", model_provider: "configured" },
  ]));
  await page.route("**/api/notifications", (route) => fulfillJson(route, { notifications: [], total: 0, unread: 0 }));
  await page.route(/.*\/api\/learning\/idle-workbench$/, (route) => fulfillJson(route, idleWorkbench([], [])));
  await page.route("**/api/agents/action-catalog", (route) => fulfillJson(route, catalog));
  await page.route("**/api/agents/actions/agents.health.refresh", async (route) => {
    actionRuns.push(JSON.parse(route.request().postData() ?? "{}"));
    await fulfillJson(route, {
      action_id: "agents.health.refresh",
      accepted: true,
      status: "completed",
      proof_event_id: "proof-catalog-1",
      contract: catalog.contracts[0],
      result: { status: "ready", ready: true },
    });
  });

  await page.goto("/#agents");
  const root = page.getByTestId("agents-root");
  await expect(root).toBeVisible();
  const panel = root.locator("section").filter({ hasText: "FULL OS OPERATOR COVERAGE" });
  await expect(panel.getByText("total 4", { exact: true })).toBeVisible();
  await expect(panel.getByText("ready 2", { exact: true })).toBeVisible();
  await expect(panel.getByText("partial 1", { exact: true })).toBeVisible();
  await expect(panel.getByText("blocked 1", { exact: true })).toBeVisible();
  await expect(panel.getByText("Update all Source OS apps", { exact: true })).toBeVisible();
  await expect(panel.getByText("Move/upload/test/print on S1", { exact: true })).toBeVisible();
  await panel.getByRole("button", { name: "Refresh Hermes Agent runtime health", exact: true }).click();
  await expect(panel.getByText(/proof-catalog-1/)).toBeVisible();
  expect(actionRuns).toEqual([{ reason: "operator requested from Agents tab", payload: {} }]);
});

test("Agent settings disables runtime controls when Hermes Agent is not configured", async ({ page }) => {
  const healthRequests: string[] = [];
  const configSaves: unknown[] = [];

  await page.route("**/api/agents/health", async (route) => {
    healthRequests.push(route.request().method());
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        healthy: false,
        status: "not_configured",
        agents: {},
        setup: { env: "HERMES3D_AGENT_RUNTIME_URL" },
      }),
    });
  });
  await page.route("**/api/agents/config", async (route) => {
    configSaves.push(JSON.parse(route.request().postData() ?? "{}"));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ saved: true, redacted: [] }),
    });
  });

  await page.goto("/#settings");
  await page.getByTestId("settings-subtab-agents").click();
  const section = page.getByTestId("agent-config-section");
  await expect(section).toBeVisible();
  await expect(section.getByTestId("agent-backend-reason")).toContainText("HERMES3D_AGENT_RUNTIME_URL");
  await expect(section.getByTestId("agent-auto-update-policy")).toContainText("Failsafe: create a git bundle backup before update");

  await expect(section.getByRole("button", { name: "Policy editor blocked" })).toBeDisabled();
  await expect(section.getByRole("button", { name: "Refresh agent health" })).toBeEnabled();
  await expect(section.getByText(/Controls disabled: Agent runtime is not configured/)).toBeVisible();

  expect(healthRequests.length).toBeGreaterThanOrEqual(1);
  expect(configSaves).toHaveLength(0);
});

test("Agent settings controls are disabled with backend reason when health endpoint is unavailable", async ({ page }) => {
  await page.route("**/api/agents/health", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "agent health route missing" }),
    });
  });

  await page.goto("/#settings");
  await page.getByTestId("settings-subtab-agents").click();
  const section = page.getByTestId("agent-config-section");
  await expect(section).toBeVisible();
  await expect(section.getByTestId("agent-backend-reason")).toContainText("agent health route missing");
  await expect(section.getByRole("button", { name: "Policy editor blocked" })).toBeDisabled();
  await expect(section.getByRole("button", { name: "Refresh agent health" })).toBeEnabled();
});

test("Agent settings exposes Hermes Agent staged update with backup and rollback proof", async ({ page }) => {
  await page.goto("/#settings");
  await expect(page.getByTestId("settings-root")).toBeVisible();
  await page.getByTestId("settings-subtab-agents").click();
  const update = page.getByTestId("agent-auto-update-policy");
  await expect(update).toBeVisible();
  await expect(update.getByText(/Hermes Agent auto-update/i)).toBeVisible();
  await expect(update.getByText(/Failsafe: create a git bundle backup before update/i)).toBeVisible({ timeout: 30_000 });
  await expect(update.getByText(/v2026\.4\.30|unknown/i)).toBeVisible();
  await expect(update.getByRole("button", { name: "Backup now", exact: true })).toBeVisible();
  await expect(update.getByRole("button", { name: "Update one release + gates", exact: true })).toBeVisible();
  await expect(update.getByRole("button", { name: "Rollback", exact: true })).toBeVisible();

  const desktop = page.getByTestId("hermes-desktop-update-policy");
  await expect(desktop).toBeVisible();
  await expect(desktop.getByText(/Hermes Desktop Windows updater/i)).toBeVisible();
  await expect(desktop.getByText(/http:\/\/127\.0\.0\.1:8642/i)).toBeVisible({ timeout: 30_000 });
  await expect(desktop.getByRole("button", { name: "Backup Desktop source", exact: true })).toBeVisible();
  await expect(desktop.getByRole("button", { name: "Download installer + verify SHA-256", exact: true })).toBeVisible();
});

test("Hermes Agent chat mirror is available from every dashboard surface", async ({ page }) => {
  await page.goto("/#dashboard");
  await expect(page.getByTestId("agent-chat-mirror")).toBeVisible();
  await expect(page.getByTitle("Attach Hermes3D model, image, G-code, CAD, audio, config, or project file")).toBeVisible();
  await expect(page.getByTitle(/Record a voice note and dictate with browser mic|Mic recording and dictation are unavailable/)).toBeVisible();
  await page.getByRole("button", { name: "Observe", exact: true }).click();
  await expect(page.getByTestId("observe-root")).toBeVisible();
  await expect(page.getByTestId("agent-chat-mirror")).toBeVisible();
  await expect(page.getByLabel("Resize left panel")).toBeVisible();
});

test("Hermes Agent chat stores audio attachments as inspectable artifacts", async ({ page }) => {
  const filename = `voice-note-proof-${Date.now()}.webm`;
  const upload = await page.request.post(`http://127.0.0.1:8765/api/agents/print-safety-agent/attachments?filename=${filename}`, {
    headers: { "content-type": "audio/webm" },
    data: Buffer.from("hermes3d voice note proof"),
  });
  expect(upload.status()).toBe(201);
  const body = await upload.json();
  expect(body.uploaded).toBe(true);
  expect(body.artifact.evidence_type).toBe("agent_attachment");
  expect(body.artifact.stage).toBe("AGENT_CHAT");
  expect(JSON.parse(body.artifact.notes).sha256).toMatch(/^[a-f0-9]{64}$/);

  await page.goto("/#artifacts");
  const root = page.getByTestId("artifacts-root");
  await expect(root).toBeVisible();
  await expect(root.getByText(filename, { exact: true })).toBeVisible({ timeout: 15_000 });
});

test("Voice STT endpoint fails closed with proof when audio or runtime setup is missing", async ({ page }) => {
  const response = await page.request.post("http://127.0.0.1:8765/api/voice/stt?locale=en-US", {
    headers: {
      "content-type": "audio/webm",
      "x-hermes-filename": "empty-voice-note.webm",
    },
    data: Buffer.from(""),
  });
  expect([400, 409]).toContain(response.status());
  const body = await response.json();
  const detail = body.detail ?? body;
  expect(detail.status).toMatch(/empty_audio|not_configured/);
  expect(detail.proof_event_id).toMatch(/^[a-f0-9]{32}$/);
  expect(detail.transcript ?? body.transcript ?? "").toBe("");
});

test("Hermes Agent chat exposes approve and deny controls for real pending actions", async ({ page }) => {
  const decisions: string[] = [];
  await page.route("**/api/agents", (route) => fulfillJson(route, [
    { id: "print-safety-agent", name: "Print Safety Agent", status: "paused", model_provider: "not_configured" },
  ]));
  await page.route("**/api/agents/print-safety-agent/history", (route) => fulfillJson(route, [
    {
      id: "action-message-1",
      persona_id: "print-safety-agent",
      role: "assistant",
      message_type: "ACTION_REQUIRED",
      content: "Print Safety Agent requires operator approval before upload.",
      action_id: "action-123",
      created_at: new Date(0).toISOString(),
    },
  ]));
  await page.route("**/api/agents/print-safety-agent/confirm-action/action-123", async (route) => {
    decisions.push(route.request().url());
    await fulfillJson(route, { persona_id: "print-safety-agent", action_id: "action-123", decision: "confirmed", recorded: true, session_id: "session-1" });
  });

  await page.goto("/#dashboard");
  const chat = page.getByTestId("agent-chat-mirror");
  await expect(chat).toBeVisible();
  await expect(chat.getByText("Print Safety Agent requires operator approval before upload.")).toBeVisible();
  await expect(chat.getByRole("button", { name: "Approve", exact: true })).toBeVisible();
  await expect(chat.getByRole("button", { name: "Deny", exact: true })).toBeVisible();
  await chat.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(chat.getByText("Agent action approved: action-123.")).toBeVisible();
  expect(decisions).toHaveLength(1);
});

test("Hermes Agent chat consumes OpenAI-compatible runtime SSE chunks", async ({ page }) => {
  await page.route("**/api/agents", (route) => fulfillJson(route, [
    { id: "print-safety-agent", name: "Print Safety Agent", status: "active", model_provider: "configured" },
  ]));
  await page.route("**/api/voice/agents", (route) => fulfillJson(route, [
    { id: "print-safety-agent", agent_id: "print-safety-agent", name: "Print Safety Agent", agent_name: "Print Safety Agent", voice: "en-US-AriaNeural", voice_name: "en-US-AriaNeural", provider: "azure" },
  ]));
  await page.route("**/api/agents/print-safety-agent/history", (route) => fulfillJson(route, []));
  await page.route("**/api/agents/print-safety-agent/chat", async (route) => {
    const frames = [
      { id: "chunk-test", object: "chat.completion.chunk", choices: [{ index: 0, delta: { content: "Runtime " }, finish_reason: null }] },
      { id: "chunk-test", object: "chat.completion.chunk", choices: [{ index: 0, delta: { content: "reply" }, finish_reason: null }] },
    ];
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: frames.map((frame) => `data: ${JSON.stringify(frame)}\n\n`).join("") + "data: [DONE]\n\n",
    });
  });
  await page.route("**/api/voice/preview", async (route) => {
    await fulfillJson(route, {
      queued: true,
      voice: "en-US-AriaNeural",
      status: "ready",
      mime_type: "audio/mpeg",
      audio_base64: "SUQz",
      bytes: 3,
      proof_event_id: "0123456789abcdef0123456789abcdef",
    });
  });

  await page.goto("/#dashboard");
  const chat = page.getByTestId("agent-chat-mirror");
  await expect(chat).toBeVisible();
  await chat.getByLabel("Message selected Hermes agent").fill("stream probe");
  await chat.getByTitle("Send to selected Hermes agent").click();
  await expect(chat.getByText("Runtime reply", { exact: true })).toBeVisible();
  await expect(chat.getByText(/Agent reply spoken with en-US-AriaNeural/)).toBeVisible();
});

test("Agents tab lets Hermes Agents run bounded Playwright proof scopes", async ({ page }) => {
  const requests: unknown[] = [];
  await page.route("**/api/agents", (route) => fulfillJson(route, [
    { id: "oliver-qa-agent", name: "Oliver QA Agent", status: "idle", model_provider: "configured" },
  ]));
  await page.route("**/api/notifications", (route) => fulfillJson(route, { notifications: [], total: 0, unread: 0 }));
  await page.route(/.*\/api\/learning\/idle-workbench$/, (route) => fulfillJson(route, idleWorkbench([], [])));
  await page.route("**/api/agents/oliver-qa-agent/playwright-run", async (route) => {
    requests.push(JSON.parse(route.request().postData() ?? "{}"));
    await fulfillJson(route, {
      accepted: true,
      status: "pass",
      scope: "observe",
      exit_code: 0,
      artifact_id: "artifact-playwright-1",
      proof_event_id: "proof-playwright-1",
      command_label: "npx playwright test --config=playwright.e2e.config.ts --grep Observe",
    });
  });

  await page.goto("/#agents");
  const root = page.getByTestId("agents-root");
  await expect(root).toBeVisible();
  await root.getByRole("button", { name: "run", exact: true }).click();
  await expect(root.getByTestId("agent-playwright-proof-status")).toContainText("PASS: observe");
  await expect(root.getByTestId("agent-playwright-proof-status")).toContainText("proof-playwright-1");
  expect(requests).toEqual([{ scope: "observe", reason: "operator requested from Agents tab" }]);
});

test("Hermes Desktop compatibility routes expose the real v0.3.4 chat contract", async ({ page }) => {
  const status = await page.request.get("http://127.0.0.1:8765/api/desktop/compat");
  expect(status.ok()).toBe(true);
  const statusBody = await status.json();
  expect(statusBody.desktop_url).toBe("http://127.0.0.1:8642");
  expect(statusBody.chat_path).toBe("/v1/chat/completions");
  expect(statusBody.bridge_available).toBe(true);

  const health = await page.request.get("http://127.0.0.1:8765/health");
  expect(health.ok()).toBe(true);
  const healthBody = await health.json();
  expect(healthBody.desktop_contract).toBe("fathah/hermes-desktop@v0.3.4");

  const chat = await page.request.post("http://127.0.0.1:8765/v1/chat/completions", {
    data: {
      model: "hermes-agent",
      stream: false,
      messages: [{ role: "user", content: "Hermes Desktop contract probe" }],
    },
  });
  const chatBody = await chat.json();
  if (chat.status() === 503) {
    expect(chatBody.detail.status).toBe("not_configured");
    expect(chatBody.detail.reason).toContain("live Hermes Agent execution is blocked");
  } else {
    expect(chat.ok()).toBe(true);
    expect(chatBody.object).toBe("chat.completion");
    expect(String(chatBody.choices?.[0]?.message?.content ?? "").trim().length).toBeGreaterThan(0);
  }
});

test("Dashboard visual smoke captures a live page screenshot", async ({ page }) => {
  fs.mkdirSync("artifacts", { recursive: true });
  await page.goto("/");
  await page.getByRole("button", { name: "Dashboard", exact: true }).click();
  await expect(page.getByTestId("dashboard-root")).toBeVisible();
  await page.screenshot({ path: "artifacts/dashboard-live-smoke.png", fullPage: false });
});

async function readErrors(page: Page): Promise<string[]> {
  return page.evaluate(async () => {
    const reader = window as unknown as { __hermes3dErrors: () => Promise<string[]> };
    return reader.__hermes3dErrors();
  });
}

// Allowlist for known-offline browser console messages in CI: GitHub rate-limit
// 502s, dev-server proxy refusals, and similar transient connectivity errors
// surfaced by `fetch()` failures. The page itself handles these gracefully;
// they're only noise in the strict `errors.toEqual([])` smoke assertion.
const OFFLINE_NETWORK_PATTERNS: readonly RegExp[] = [
  /Failed to load resource: the server responded with a status of 502/i,
  /Failed to load resource: net::ERR_CONNECTION_REFUSED/i,
  /Failed to load resource: net::ERR_NAME_NOT_RESOLVED/i,
  /TypeError: Failed to fetch/i,
];

function isOfflineNetworkError(message: string): boolean {
  return OFFLINE_NETWORK_PATTERNS.some((pattern) => pattern.test(message));
}

function sourceOSModule(overrides: Pick<SourceOSModule, "id" | "display" | "installState"> & Partial<SourceOSModule>): SourceOSModule {
  return {
    id: overrides.id,
    display: overrides.display,
    priority: "required",
    license: "MIT",
    section: "utilities",
    repo: "https://example.test/hermes3d/mock.git",
    localPath: "G:\\tmp\\hermes3d-mock",
    installState: overrides.installState,
    installProgress: 100,
    detectedVersion: "test-revision",
    health: "healthy",
    launchKind: "desktop_app",
    bridgeTasks: [],
    proofs: [],
    dispatchGates: [],
    providers: [],
    activeProvider: null,
    runtime: {
      status: "source_ready",
      label: "Source ready",
      kind: "desktop_app",
      verifier: "source checkout",
      path: "G:\\tmp\\hermes3d-mock",
      detected: true,
      executed: false,
      return_code: null,
      capabilities: [],
      reason: "Source checkout is present; runtime verifier has not been registered yet.",
      setup_steps: ["Register a safe verifier for this module before marking runtime ready."],
      proof_source: "03_implementation/proof/SOURCE_REGISTRY_TRUTH_AUDIT.json",
      output_head: [],
    },
    ...overrides,
  };
}

function sourceUpdateReadiness(
  deep: boolean,
  options: { backupAvailable?: boolean; latestCheck?: boolean } = {},
): SourceModuleUpdateReadiness {
  const backupAvailable = options.backupAvailable ?? false;
  return {
    status: "ready",
    strategy: "server_side_lightweight_readiness_by_default; update execution requires backup, proof gates, and rollback route",
    section: null,
    deep,
    count: 1,
    ready_for_update_check: 1,
    blocked: 0,
    outdated_cached: deep ? 0 : 0,
    dirty: 0,
    records: [
      {
        module_id: "printrun",
        display: "Printrun",
        section: "utilities",
        repo: "https://example.test/printrun.git",
        local_path: "G:\\tmp\\printrun",
        install_state: "installed",
        detected_version: "test-revision",
        git_ready: true,
        source_update_supported: true,
        reason: null,
        current: {
          commit: deep ? "abc123" : null,
          branch: deep ? "main" : null,
          exact_tag: null,
          nearest_tag: deep ? "v1.0.0" : null,
          upstream: deep ? "origin/main" : null,
          remote: deep ? "https://example.test/printrun.git" : null,
        },
        dirty: false,
        dirty_entries: [],
        cached_behind_count: deep ? 0 : null,
        latest_backup: backupAvailable
          ? {
            backup_id: "backup-1",
            module_id: "printrun",
            commit: "abc123",
            branch: "main",
            exact_tag: null,
            nearest_tag: "v1.0.0",
            dirty: false,
            bundle_path: "G:\\tmp\\backup-1.bundle",
            dirty_zip_path: null,
            created_at: new Date(0).toISOString(),
          }
          : null,
        backup_available: backupAvailable,
        latest_check: options.latestCheck
          ? {
            module_id: "printrun",
            status: "current",
            current_commit: "abc123",
            remote_commit: "def456789012",
            branch: "main",
            remote_ref: "refs/heads/main",
            backup_available: backupAvailable,
            checked_at: new Date(0).toISOString(),
            proof_event_id: "proof-check",
          }
          : null,
        deep_checked: deep,
        update_action: deep ? "check_ready" : "deep_check_required",
        safety: "readiness only; no fetch, checkout, pull, install, or build runs from this endpoint",
      },
    ],
  };
}

function printerRow(overrides: Partial<Printer> & Pick<Printer, "id" | "name" | "model" | "ip">): Printer {
  return {
    id: overrides.id,
    name: overrides.name,
    model: overrides.model,
    ip: overrides.ip,
    status: overrides.status ?? "online",
    adapter: overrides.adapter ?? "moonraker",
    data_source: overrides.data_source ?? "config",
    temp_hot: overrides.temp_hot ?? null,
    temp_bed: overrides.temp_bed ?? null,
    progress: overrides.progress ?? null,
    current_job: overrides.current_job ?? null,
    maintenance_flag: overrides.maintenance_flag ?? false,
    camera_url: overrides.camera_url ?? `http://${overrides.ip}/webcam/?action=stream`,
    moonraker_url: overrides.moonraker_url ?? `http://${overrides.ip}`,
    source_refs: overrides.source_refs ?? {},
    safety_policy: overrides.safety_policy,
    write_enabled: overrides.write_enabled,
    onboarded: overrides.onboarded,
    status_source: overrides.status_source,
  };
}

function idleWorkbench(candidates: Array<Record<string, unknown>>, blockers: Array<Record<string, unknown>>) {
  return {
    status: "ready",
    review_policy: "Research may be queued while printers are busy. Build, download, install, update, merge, and printer actions stay blocked until printers/jobs/approvals are clear and proof gates exist.",
    blockers,
    candidates,
    automation: {
      runner_status: "not_configured",
      runner_reason: "Idle learning runner is not configured.",
      agent_runtime_status: "not_configured",
      agent_runtime_reason: "Hermes Agent runtime is not configured.",
      capabilities: [
        idleCapability("research", "Research reports", "research-agent", blockers, false),
        idleCapability("documentation", "Documentation updates", "documentation-agent", blockers, true),
        idleCapability("workflow", "Workflow improvements", "factory-operator", blockers, true),
        idleCapability("app_update", "App updates", "factory-operator", blockers, true),
        idleCapability("printer_maintenance", "Printer maintenance", "print-safety-agent", blockers, true),
      ],
    },
    daily_prompt: {
      question: "What should Hermes3D improve while the workstation is idle?",
      last_candidate_at: null,
      suggested_kinds: ["research", "app_update", "printer_maintenance", "documentation", "workflow"],
    },
  };
}

function idleCapability(kind: string, label: string, agentId: string, blockers: Array<Record<string, unknown>>, blocksOnLiveSystem: boolean) {
  return {
    kind,
    label,
    agent_id: agentId,
    queue_enabled: true,
    execution_status: "blocked",
    missing: [
      "Idle learning runner is not configured.",
      "Hermes Agent runtime is not configured.",
      ...(blocksOnLiveSystem && blockers.length > 0 ? ["Live blockers must clear before execution."] : []),
    ],
    proof_required: true,
    safety_scope: "queue-only until runtime, blockers, approvals, and proof gates are green",
  };
}

function idleCandidate(overrides: Record<string, unknown>) {
  return {
    id: "candidate-id",
    title: "Candidate",
    kind: "research",
    agent_id: "research-agent",
    status: "queued",
    risk_level: "low",
    summary: "Review a real Hermes3D improvement opportunity.",
    source: "operator",
    source_url: null,
    target_tab: "learning",
    target_files: [],
    branch_ref: null,
    gate_status: {},
    proof_event_ids: ["proof-id"],
    approval_id: null,
    blocked_reason: null,
    created_by: "operator",
    created_at: new Date(0).toISOString(),
    updated_at: new Date(0).toISOString(),
    ...overrides,
  };
}

async function fulfillJson(route: Route, json: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(json),
  });
}
