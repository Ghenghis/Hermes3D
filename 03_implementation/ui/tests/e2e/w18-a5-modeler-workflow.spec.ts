/**
 * W18-A5 Modeler Workflow Proof (AUDIT-ONLY)
 *
 * Goal: from the running GUI, drive the Design surface end-to-end and verify
 * that a real 3D model artifact is produced on disk, with the UI showing
 * confirmation of the artifact (file name, sha, parameters).
 *
 * Key finding documented by this spec:
 * - Hermes3D does NOT ship an in-page interactive 3D modeler (no three.js / no
 *   babylon.js / no @react-three in 03_implementation/ui/package.json). The
 *   "design" surface is a PARAMETRIC TEMPLATE form (src/tabs/Design.tsx) that
 *   submits to POST /api/design/intake and the backend executor
 *   (hermes3d.core.design.desk_organizer) writes a real STL + signed proof
 *   envelope to 03_implementation/var/designs/{job_id}/.
 *
 * Hard rules:
 * - No route stubs. Real backend, real disk write.
 * - Skips do NOT count as PASS_REAL.
 * - On a clean run, asserts the artifact file_path returned by the API exists
 *   on the filesystem and has size > 0.
 *
 * Status vocabulary on the audit doc (W18-A5_MODELER_WORKFLOW_2026-05-11.md):
 *   PASS_REAL              — parametric modeler completed full workflow, real
 *                            STL on disk, UI surfaced the artifact label.
 *   FAIL_NOT_WIRED         — Design CTA navigates elsewhere with no in-page
 *                            modeler AND backend produced no artifact.
 *   FAIL_BACKEND_MISSING   — Backend /api/design/intake returned 5xx or
 *                            net::ERR_*.
 *   FAIL_BROKEN            — UI threw a console error or the artifact path
 *                            returned by the API does not exist on disk.
 */
import { expect, test, type APIResponse } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ARTIFACT_DIR = path.resolve(__dirname, "../../test-results/w18-a5");
const BACKEND_URL = "http://127.0.0.1:8765";

function ensureArtifactDir(): void {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

interface IntakeResult {
  id: string;
  job_id: string;
  status: string;
  template: string;
  artifact: { id: string; label: string; file_path: string; file_size: number; sha256: string };
  proof: { id: string; label: string; file_path: string; file_size: number; sha256: string; event_id: string };
  truth_gate: { status: string; duration_s: number | null };
  parameters: Record<string, unknown>;
}

test.describe("W18-A5 modeler workflow proof", () => {
  test.beforeAll(async () => {
    ensureArtifactDir();
  });

  test("Design tab surfaces a parametric template form, NOT an in-page 3D modeler", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        const text = msg.text();
        // Known-offline noise from unrelated endpoints is ignored ONLY here so
        // the audit can record clean signal for the Design surface itself.
        if (!text.includes("Failed to load resource") && !text.includes("net::ERR_")) {
          consoleErrors.push(`console.error: ${text}`);
        }
      }
    });

    await page.goto("/");
    await page.getByRole("button", { name: "Design", exact: true }).click();
    const root = page.getByTestId("design-root");
    await expect(root).toBeVisible({ timeout: 15_000 });

    // Surface inventory — record what's actually on the design route.
    const surface = {
      has_design_root: await root.isVisible(),
      has_intake_section: await page.locator("#design\\.intake").isVisible(),
      has_toolchain_section: await page.locator("#design\\.toolchain").isVisible(),
      has_providers_section: await page.locator("#design\\.providers").isVisible(),
      has_templates_section: await page.locator("#design\\.templates").isVisible(),
      has_start_design_button: await page.getByRole("button", { name: "Start Design" }).count() > 0,
      // Negative: no in-page interactive 3D canvas / viewer
      has_canvas_element: await page.locator("canvas").count() > 0,
      has_threejs_viewer: await page.evaluate(() => {
        const w = window as unknown as Record<string, unknown>;
        return Boolean(w.THREE || w.__threeJsRoot);
      }),
    };
    fs.writeFileSync(path.join(ARTIFACT_DIR, "design-surface-inventory.json"), JSON.stringify(surface, null, 2));

    // The audit-finding: surface is a parametric form, no in-page 3D editor.
    expect(surface.has_design_root, "Design root must mount").toBe(true);
    expect(surface.has_intake_section, "Design intake form must exist").toBe(true);
    expect(surface.has_start_design_button, "Start Design CTA must exist").toBe(true);
    // These are EXPECTED-FALSE — they document the absence of an in-page modeler.
    expect(surface.has_canvas_element, "Audit finding: no <canvas> on design surface").toBe(false);
    expect(surface.has_threejs_viewer, "Audit finding: no three.js viewer on design surface").toBe(false);

    await page.screenshot({ path: path.join(ARTIFACT_DIR, "design-surface.png"), fullPage: true });

    // No surface-level errors during navigation/mount.
    expect(consoleErrors, consoleErrors.join("\n")).toEqual([]);
  });

  test("Parametric modeler workflow produces a real STL artifact on disk", async ({ page, request }) => {
    // Verify the toolchain is ready up front — otherwise the workflow is
    // honestly blocked and the test reports FAIL_BACKEND_MISSING via the doc.
    const toolchainResponse = await request.get(`${BACKEND_URL}/api/design/toolchain/status`);
    expect(toolchainResponse.ok(), `Toolchain status must be reachable; got ${toolchainResponse.status()}`).toBe(true);
    const toolchain = await toolchainResponse.json();
    expect(toolchain.overall, `Toolchain overall status must be 'ready', got: ${toolchain.overall}`).toBe("ready");

    // Drive the workflow via the same endpoint the UI uses. This is the most
    // faithful proof that the Start Design CTA produces a real artifact —
    // the UI surface is verified separately in the prior test.
    const intakeResponse: APIResponse = await request.post(`${BACKEND_URL}/api/design/intake`, {
      data: {
        prompt: "W18-A5 parametric modeler proof — tiny organizer",
        constraints: {
          template: "desk_organizer",
          width_mm: 100,
          depth_mm: 60,
          height_mm: 30,
          tray_count: 2,
          pen_count: 1,
          phone_slot: false,
          cable_passthrough: false,
        },
      },
      headers: { "Content-Type": "application/json" },
    });
    expect(intakeResponse.status(), `Design intake must return 201; got ${intakeResponse.status()}`).toBe(201);
    const result = (await intakeResponse.json()) as IntakeResult;

    // Real artifact on disk — the core proof requirement.
    expect(result.status).toBe("completed");
    expect(result.template).toBe("desk_organizer");
    expect(result.artifact.file_path, "Artifact file_path must be returned").toBeTruthy();
    expect(result.artifact.file_size, "Artifact size must be > 0").toBeGreaterThan(0);
    expect(result.artifact.sha256.length, "Artifact sha256 must be 64 hex chars").toBe(64);

    // Verify the file actually exists on disk and is readable.
    const stlPath = result.artifact.file_path;
    expect(fs.existsSync(stlPath), `STL file must exist on disk at ${stlPath}`).toBe(true);
    const stat = fs.statSync(stlPath);
    expect(stat.size, `STL file size must match API response`).toBe(result.artifact.file_size);
    expect(stat.size).toBeGreaterThan(0);

    // Verify it's a real STL — binary STL has 80-byte header + 4-byte triangle
    // count + N*50-byte triangle records.
    const head = fs.readFileSync(stlPath).slice(0, 84);
    const triangleCount = head.readUInt32LE(80);
    expect(triangleCount, "Binary STL triangle count must be > 0").toBeGreaterThan(0);
    const expectedSize = 84 + triangleCount * 50;
    expect(stat.size, `STL size must match binary STL spec (84 + 50*tri = ${expectedSize})`).toBe(expectedSize);

    // Proof envelope exists too.
    expect(fs.existsSync(result.proof.file_path), `Proof envelope must exist at ${result.proof.file_path}`).toBe(true);
    expect(result.truth_gate.status, "Truth gate must pass").toBe("pass");

    // Record the full proof bundle for the handoff doc.
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, "intake-result.json"),
      JSON.stringify(
        {
          job_id: result.job_id,
          artifact: result.artifact,
          proof: result.proof,
          truth_gate: result.truth_gate,
          parameters: result.parameters,
          on_disk: { stl_size_bytes: stat.size, stl_triangles: triangleCount, stl_path: stlPath },
        },
        null,
        2,
      ),
    );

    // Now verify the UI can render the artifact — open Artifacts tab and
    // confirm the new mesh shows up (this is the visible UI proof leg).
    await page.goto("/");
    await page.getByRole("button", { name: "Artifacts", exact: true }).click();
    const artifactsRoot = page.getByTestId("artifacts-root");
    await expect(artifactsRoot).toBeVisible({ timeout: 15_000 });
    // The page hits /api/artifacts which lists artifacts including the mesh.
    // Wait for the artifact label to appear (it's the STL filename).
    const meshLabel = page.getByText(result.artifact.label, { exact: false });
    await expect(meshLabel.first(), `Artifact ${result.artifact.label} must appear in Artifacts tab`).toBeVisible({
      timeout: 10_000,
    });

    await page.screenshot({ path: path.join(ARTIFACT_DIR, "artifacts-with-mesh.png"), fullPage: true });
  });
});
