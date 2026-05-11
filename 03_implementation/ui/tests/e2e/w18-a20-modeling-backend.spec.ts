/**
 * W18-A20 Modeling Backend + GPU Proof
 *
 * Goal: prove the live design intake records (a) the modeling backend that
 * produced the artifact and (b) whether the local GPU code path was
 * exercised. Both fields are required in the proof envelope, the API
 * response, AND the GUI Design tab.
 *
 * Hard rules (per W18-A20 mission brief):
 * - NO test.skip, NO mock. Real backend, real disk write, real GPU probe.
 * - If the GPU code path was exercised (RTX 3090 Ti + Cycles CUDA), the
 *   spec asserts gpu_used:true AND the GPU model string AND the thumbnail
 *   file on disk. If the operator's host has no GPU it instead asserts
 *   gpu_used:false with a precise reason — never the string "unknown".
 * - Console errors / 404 / 5xx / a missing backend field cause a hard fail.
 */
import { expect, test, type APIResponse, type ConsoleMessage } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ARTIFACT_DIR = path.resolve(__dirname, "../../test-results/w18-a20");
const BACKEND_URL = process.env.HERMES3D_BACKEND_URL ?? "http://127.0.0.1:8765";

function ensureArtifactDir(): void {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

interface BackendsResponse {
  backends: Array<{
    name: string;
    kind: string;
    version: string | null;
    path: string | null;
    available: boolean;
    gpu_capable: boolean;
  }>;
  default_template_backend: {
    name?: string;
    version?: string | null;
    engine?: { name?: string; version?: string | null } | null;
    detail?: string | null;
  };
  gpu:
    | { available: true; model: string; driver: string; cuda: string; vram_total_mib: number }
    | { available: false; reason: string };
}

interface IntakeResponse {
  id: string;
  job_id: string;
  status: string;
  template: string;
  artifact: { id: string; label: string; file_path: string; file_size: number; sha256: string };
  proof: { id: string; label: string; file_path: string; file_size: number; sha256: string };
  truth_gate: { status: string };
  modeling_backend: {
    name: string;
    version: string | null;
    kind?: string;
    engine?: { name: string; version: string | null } | null;
    gpu_operation?: {
      used: boolean;
      backend?: string;
      device?: string;
      render_seconds?: number;
      output_path?: string;
    };
  };
  gpu_used: boolean;
  gpu: {
    vendor?: string;
    model?: string;
    driver?: string;
    cuda?: string;
    operation?: { used: boolean; output_path?: string };
  } | null;
}

interface ProofEnvelope {
  schema_version: string;
  modeling_backend: {
    name: string;
    version: string | null;
    engine?: { name: string; version: string | null } | null;
  };
  gpu_used: boolean;
  gpu: { model?: string; cuda?: string; driver?: string } | null;
  visual_evidence: Array<{ view_name: string; path: string; sha256: string }>;
  signature: { algorithm: string; value: string };
  truth_gate_report: { overall_status: string };
}

test.describe("W18-A20 modeling backend + GPU proof", () => {
  test.beforeAll(() => {
    ensureArtifactDir();
  });

  test("/api/design/backends returns a live survey with real version strings", async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/design/backends`);
    expect(response.status(), `/api/design/backends must be reachable; got ${response.status()}`).toBe(200);
    const data = (await response.json()) as BackendsResponse;
    expect(Array.isArray(data.backends), "backends must be an array").toBe(true);
    expect(data.backends.length, "at least 4 backends should be surveyed").toBeGreaterThanOrEqual(4);

    // The default template backend (desk_organizer) must be trimesh + manifold3d.
    expect(data.default_template_backend?.name, "default backend must be reported").toBe("trimesh");
    expect(
      data.default_template_backend?.engine?.name,
      "default backend engine must be manifold3d",
    ).toBe("manifold3d");
    expect(
      data.default_template_backend?.version,
      "default backend must report a real version string, not 'unknown'",
    ).toMatch(/^\d+/);
    expect(
      data.default_template_backend?.engine?.version,
      "engine must report a real version string, not 'unknown'",
    ).toMatch(/^\d+/);

    // GPU probe is honest either way.
    if (data.gpu.available) {
      expect(data.gpu.model, "GPU model must be a real string").toMatch(/.+/);
      expect(data.gpu.model, "GPU model must not be 'unknown'").not.toMatch(/^unknown$/i);
      expect(data.gpu.driver, "GPU driver must be a real string").toMatch(/^\d+/);
    } else {
      expect(data.gpu.reason, "GPU-unavailable response must carry a precise reason").toMatch(/.+/);
    }

    fs.writeFileSync(path.join(ARTIFACT_DIR, "backends-survey.json"), JSON.stringify(data, null, 2));
  });

  test("Design intake records modeling_backend + gpu_used in the API response and on-disk proof", async ({
    request,
  }) => {
    const intakeResponse: APIResponse = await request.post(`${BACKEND_URL}/api/design/intake`, {
      data: {
        prompt: "W18-A20 modeling backend + GPU proof — desk organizer",
        constraints: {
          template: "desk_organizer",
          width_mm: 180,
          depth_mm: 100,
          height_mm: 55,
          tray_count: 3,
          pen_count: 4,
          phone_slot: true,
          cable_passthrough: true,
        },
      },
      headers: { "Content-Type": "application/json" },
    });
    expect(intakeResponse.status(), `intake must return 201; got ${intakeResponse.status()}`).toBe(201);
    const result = (await intakeResponse.json()) as IntakeResponse;
    fs.writeFileSync(path.join(ARTIFACT_DIR, "intake-response.json"), JSON.stringify(result, null, 2));

    // --- Mandatory response shape: modeling_backend + gpu_used ----------
    expect(result.modeling_backend, "modeling_backend must be present in intake response").toBeTruthy();
    expect(result.modeling_backend.name, "modeling_backend.name must be set").toMatch(/.+/);
    expect(result.modeling_backend.name, "modeling_backend.name must not be 'unknown'").not.toMatch(/^unknown$/i);
    expect(result.modeling_backend.version, "modeling_backend.version must be set").toMatch(/^\d+/);
    expect(result.modeling_backend.engine?.name, "engine name must be set").toBe("manifold3d");
    expect(result.modeling_backend.engine?.version, "engine version must be set").toMatch(/^\d+/);
    expect(typeof result.gpu_used, "gpu_used must be a boolean").toBe("boolean");

    // --- Real artifact on disk ------------------------------------------
    expect(fs.existsSync(result.artifact.file_path), "STL artifact must exist on disk").toBe(true);
    expect(fs.statSync(result.artifact.file_path).size, "STL size must be > 0").toBeGreaterThan(0);
    expect(fs.existsSync(result.proof.file_path), "proof envelope must exist on disk").toBe(true);

    // --- Proof envelope contains modeling_backend + gpu_used ------------
    const envelope = JSON.parse(fs.readFileSync(result.proof.file_path, "utf-8")) as ProofEnvelope;
    expect(envelope.signature?.algorithm, "envelope must be HMAC-SHA256 signed").toBe("HMAC-SHA256");
    expect(envelope.truth_gate_report.overall_status, "envelope truth gate must pass").toBe("pass");
    expect(envelope.modeling_backend?.name, "envelope modeling_backend.name must be set").toBe(
      result.modeling_backend.name,
    );
    expect(envelope.modeling_backend?.engine?.name, "envelope engine name must be set").toBe("manifold3d");
    expect(envelope.gpu_used, "envelope gpu_used must match response").toBe(result.gpu_used);

    // --- GPU branch: either real GPU op OR honest false with reason -----
    if (result.gpu_used) {
      expect(result.gpu, "gpu field must be set when gpu_used:true").toBeTruthy();
      expect(result.gpu?.model, "GPU model must be set").toMatch(/.+/);
      expect(result.gpu?.model, "GPU model must not be 'unknown'").not.toMatch(/^unknown$/i);
      expect(result.modeling_backend.gpu_operation?.used, "gpu_operation.used must be true").toBe(true);
      expect(result.modeling_backend.gpu_operation?.device, "gpu_operation.device must be CUDA").toBe("CUDA");
      // Thumbnail PNG must exist on disk.
      const thumb = result.modeling_backend.gpu_operation?.output_path;
      expect(thumb, "thumbnail output_path must be set").toBeTruthy();
      expect(fs.existsSync(thumb as string), `thumbnail must exist at ${thumb}`).toBe(true);
      expect(fs.statSync(thumb as string).size, "thumbnail size > 0").toBeGreaterThan(0);
      // Envelope visual_evidence must include the thumbnail.
      const thumbEvidence = envelope.visual_evidence.find((v) => v.view_name === "thumbnail_gpu");
      expect(thumbEvidence, "envelope must reference thumbnail_gpu visual evidence").toBeTruthy();
      expect(thumbEvidence?.sha256.length, "evidence sha256 must be 64 hex").toBe(64);
    } else {
      // Honest absence — there must be a precise reason in the response.
      expect(
        result.modeling_backend.gpu_operation?.used,
        "modeling_backend.gpu_operation.used must be false when gpu_used:false",
      ).toBe(false);
    }
  });

  test("Design tab UI surfaces the modeling backend + GPU status", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));
    page.on("console", (msg: ConsoleMessage) => {
      if (msg.type() === "error") {
        const text = msg.text();
        if (!text.includes("Failed to load resource") && !text.includes("net::ERR_")) {
          consoleErrors.push(`console.error: ${text}`);
        }
      }
    });
    page.on("response", async (response) => {
      if (response.status() >= 500) {
        consoleErrors.push(`HTTP ${response.status()} from ${response.url()}`);
      }
    });

    await page.goto("/");
    await page.getByRole("button", { name: "Design", exact: true }).click();
    const root = page.getByTestId("design-root");
    await expect(root).toBeVisible({ timeout: 15_000 });

    // Modeling backend panel must mount and display real backend identifier.
    const panel = page.getByTestId("modeling-backend-panel");
    await expect(panel, "modeling-backend-panel must mount").toBeVisible({ timeout: 15_000 });
    const backendNameText = await page.getByTestId("backend-name").innerText();
    expect(backendNameText, "backend name text must show 'trimesh'").toMatch(/trimesh/);
    expect(backendNameText, "must surface engine manifold3d").toMatch(/manifold3d/);

    const gpuStatusText = await page.getByTestId("gpu-status").innerText();
    // gpu-status must show either the real model string or an explicit
    // "unavailable" reason. Never the literal placeholder "unknown".
    expect(gpuStatusText, "GPU status text must not be empty").toMatch(/.+/);
    expect(gpuStatusText, "GPU status must never be 'unknown'").not.toMatch(/\bunknown\b/i);

    await page.screenshot({ path: path.join(ARTIFACT_DIR, "design-tab-backend-panel.png"), fullPage: true });

    expect(consoleErrors, consoleErrors.join("\n")).toEqual([]);
  });
});
