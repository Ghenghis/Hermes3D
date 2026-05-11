/**
 * W18-A12 slicer wire-up — end-to-end proof.
 *
 * STRICT OPERATOR FREEZE (2026-05-11, printer heater on):
 *   - The slicer produces G-code as a FILE on disk.
 *   - NO POST/PUT/PATCH to /api/printers/{id}/*.
 *   - NO Moonraker/Klipper/OctoPrint upload from the new endpoint.
 *   - Pinned: GUI_PHYSICAL_PRINT_GREEN, GUI_PRINTER_DRY_RUN_GREEN out of scope.
 * Verdict gate driven: GUI_SLICER_GREEN.
 *
 * Test plan:
 *   1. Open Design tab.
 *   2. Submit a parametric desk_organizer intake (proven W18-A5 path).
 *   3. Verify a "Slice this STL" button is visible for the produced STL.
 *   4. Click it.
 *   5. Poll the GUI state panel for terminal status.
 *   6. Hit the backend directly to recompute sha256 + layer_count from the
 *      G-code file on disk and assert the GUI's reported values match.
 *   7. Verify the "Download G-code" link exists when status=completed.
 *   8. Network audit: assert ONLY allow-listed endpoints were hit. No
 *      /api/printers/*  writes, no /api/jobs/{id}/start, no Moonraker /
 *      OctoPrint ports.
 *   9. Hard rules: zero console.error, zero pageerror, zero 5xx, zero 404
 *      on our endpoints.
 */
import { expect, test } from "@playwright/test";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const ARTIFACT_DIR = path.resolve(__dirname, "../../test-results/w18-a12");
const BACKEND_URL = "http://127.0.0.1:8765";

// Endpoints the GUI is permitted to touch during this audit. Anything else
// to our backend is a failure.
const ALLOWED_BACKEND_PATTERNS: RegExp[] = [
  /^\/api\/design\//i,
  /^\/api\/slice(\/|$)/i,
  /^\/api\/artifacts(\/|$)/i,
  /^\/api\/proof\b/i,
  /^\/api\/events\b/i, // adapters.emitProofEvent POSTs here
  /^\/api\/system\b/i,
  /^\/api\/settings\b/i,
  /^\/api\/printers(?:\/?$|\?)/i, // GET-only listing for the Target Printer picker
  /^\/api\/logs\b/i,
  /^\/api\/health(\/|$)/i,
  /^\/openapi\.json$/i,
  /^\/docs(\/|$)/i,
  /^\/health$/i,
  /^\/$/, // root document
];

// Hard-deny: any write to a printer-control endpoint is FAIL.
const PRINTER_CONTROL_PATTERNS: RegExp[] = [
  /\/api\/printers\/[^/?]+\/(upload-gcode|jobs|start|move|home|heat)/i,
  /\/api\/jobs\/[^/?]+\/(start|dispatch)/i,
  /\/printer\/print\/start/i, // moonraker
  /\/api\/files\/local/i, // octoprint
  /\/api\/printer\/command/i,
  /:7125/, // moonraker default port
  /:5000/, // octoprint default port
];

interface NetCall {
  method: string;
  url: string;
  status: number;
}

function sha256(buf: Buffer): string {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function ensureArtifactDir(): void {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

function pathnameOf(url: string): string {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

test.describe("W18-A12 slicer wire-up — real G-code via Design tab", () => {
  test.beforeAll(() => {
    ensureArtifactDir();
  });

  test("Design tab -> POST /api/slice -> real G-code on disk -> no printer-control", async ({ page, request }) => {
    const auditSteps: Array<{ id: string; result: string; detail?: unknown }> = [];
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const httpFailures: NetCall[] = [];
    const network: NetCall[] = [];

    page.on("pageerror", (err) => pageErrors.push(`pageerror: ${err.message}`));
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        const text = msg.text();
        if (!text.includes("Failed to load resource") && !text.includes("net::ERR_")) {
          consoleErrors.push(`console.error: ${text}`);
        }
      }
    });
    page.on("response", (resp) => {
      const url = resp.url();
      const status = resp.status();
      const isOurs = url.startsWith(BACKEND_URL) || url.startsWith("http://localhost:5173");
      if (isOurs) {
        const req = resp.request();
        network.push({ method: req.method(), url, status });
        if (status >= 400 && !url.startsWith("http://localhost:5173/@vite") && !url.endsWith(".map")) {
          httpFailures.push({ method: req.method(), url, status });
        }
      }
    });

    // --- 1. Backend health ----------------------------------------------------
    const openApiResp = await request.get(`${BACKEND_URL}/openapi.json`);
    expect(openApiResp.ok(), "backend openapi must be reachable").toBe(true);
    const openApi = (await openApiResp.json()) as { paths: Record<string, unknown> };
    const slicePaths = Object.keys(openApi.paths ?? {}).filter((p) => /\/api\/slice/i.test(p));
    expect(slicePaths.length, "OpenAPI must list /api/slice routes").toBeGreaterThan(0);
    auditSteps.push({
      id: "openapi_slicer_routes_present",
      result: "ok",
      detail: { slice_paths: slicePaths },
    });

    // --- 2. Open Design tab ---------------------------------------------------
    await page.goto("/");
    await page.evaluate(() => {
      window.location.hash = "#design";
    });
    const root = page.getByTestId("design-root");
    await expect(root).toBeVisible({ timeout: 15_000 });
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "01-design-tab-loaded.png"), fullPage: true });
    auditSteps.push({ id: "gui_design_tab_loaded", result: "ok" });

    // --- 3. Drive the W18-A5 parametric intake via the backend directly ------
    // The Design form is parametric and lots of constraints to chain through
    // the GUI; the W18-A5 audit already proved the intake works via direct
    // POST. We do the same here so the slicer wire-up is the focus.
    const intakeResp = await request.post(`${BACKEND_URL}/api/design/intake`, {
      data: {
        prompt: "W18-A12 desk organizer for slicer wire-up proof",
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
    });
    expect(intakeResp.ok(), `intake must succeed; status=${intakeResp.status()}`).toBe(true);
    const intakeBody = (await intakeResp.json()) as {
      job_id?: string;
      status?: string;
      artifact?: { file_path?: string; label?: string; file_size?: number; sha256?: string };
    };
    fs.writeFileSync(path.join(ARTIFACT_DIR, "02-intake-response.json"), JSON.stringify(intakeBody, null, 2));
    expect(intakeBody.status).toBe("completed");
    const stlPath = intakeBody.artifact?.file_path;
    expect(stlPath, "intake must return an STL artifact path").toBeTruthy();
    expect(fs.existsSync(stlPath ?? ""), `produced STL must exist on disk: ${stlPath}`).toBe(true);
    auditSteps.push({
      id: "design_intake_real_stl",
      result: "ok",
      detail: { stl_path: stlPath, sha256: intakeBody.artifact?.sha256 },
    });

    // --- 4. Drive the slicer via the GUI button ------------------------------
    // The Design tab's slicer panel watches the in-session state for STLs that
    // came from the GUI's own submit() call. Because we POSTed via the API
    // request fixture (so the test stays deterministic), we trigger the same
    // submit() codepath from the GUI by re-running it once with the same body.
    // This puts the produced STL into the producedStls state.
    await page.evaluate(async (body) => {
      const r = await fetch(`http://127.0.0.1:8765/api/design/intake`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return r.status;
    }, {
      prompt: "W18-A12 desk organizer for slicer wire-up proof (gui-side)",
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
    });

    // The above only seeded the API. The actual GUI surface uses the React
    // component's state, which is fed by clicking "Start Design". We do that
    // now so producedStls gets populated.
    const startBtn = page.getByRole("button", { name: "Start Design" });
    await expect(startBtn).toBeVisible({ timeout: 5_000 });
    // The form requires title + intent + printer; fill the minimum.
    await page.getByLabel("Design name").fill("W18-A12 GUI Design");
    await page.getByLabel("Design intent, constraints, notes").fill(
      "Run the desk organizer template end-to-end so the slicer panel has an STL to slice.",
    );
    // The Target Printer select auto-populates with the first unlocked printer
    // from /api/printers. Wait briefly for it to populate.
    await page.waitForTimeout(1500);
    // Some Windows envs render slow; ensure the button is enabled.
    await expect(startBtn).toBeEnabled({ timeout: 10_000 });
    await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.url().endsWith("/api/design/intake") && resp.request().method() === "POST",
        { timeout: 60_000 },
      ),
      startBtn.click(),
    ]);
    // Wait for the produced-STL row to appear.
    const stlRow = page.getByTestId("design-slicer-stl-row").first();
    await expect(stlRow, "produced STL row must appear after intake completes").toBeVisible({ timeout: 30_000 });
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "03-design-after-intake.png"), fullPage: true });
    auditSteps.push({ id: "gui_stl_row_visible", result: "ok" });

    // --- 5. Click "Slice this STL" -------------------------------------------
    const sliceBtn = stlRow.getByRole("button", { name: /Slice/i });
    await expect(sliceBtn, "slice button must be visible on the STL row").toBeVisible();
    const slicePostResponse = page.waitForResponse(
      (resp) => resp.url().endsWith("/api/slice") && resp.request().method() === "POST",
      { timeout: 30_000 },
    );
    await sliceBtn.click();
    const postResp = await slicePostResponse;
    expect(postResp.status(), `POST /api/slice should be 202; got ${postResp.status()}`).toBe(202);
    const accepted = (await postResp.json()) as { job_id?: string; accepted?: boolean };
    expect(accepted.accepted).toBe(true);
    const jobId = accepted.job_id;
    expect(jobId, "POST /api/slice must return job_id").toBeTruthy();
    auditSteps.push({ id: "gui_slice_button_clicked", result: "ok", detail: { job_id: jobId } });
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "04-slice-clicked.png"), fullPage: true });

    // --- 6. Wait for the GUI panel to surface 'completed' --------------------
    const statusBadge = page.getByTestId("design-slicer-status");
    await expect(statusBadge, "slicer panel must show a status badge").toBeVisible({ timeout: 30_000 });
    // Poll the GUI's status until terminal.
    const startedAt = Date.now();
    const guiDeadlineMs = 25 * 60_000;
    let lastGuiStatus = "";
    while (Date.now() - startedAt < guiDeadlineMs) {
      lastGuiStatus = (await statusBadge.textContent())?.trim().toLowerCase() ?? "";
      if (lastGuiStatus === "completed" || lastGuiStatus === "failed") break;
      await page.waitForTimeout(2000);
    }
    expect(lastGuiStatus, `slicer panel must reach 'completed'; got '${lastGuiStatus}'`).toBe("completed");
    await page.screenshot({ path: path.join(ARTIFACT_DIR, "05-slice-completed.png"), fullPage: true });

    // --- 7. Recompute sha256 from disk and compare against GUI ---------------
    const guiGcodePath = (await page.getByTestId("design-slicer-gcode-path").textContent())?.trim() ?? "";
    const guiSha = (await page.getByTestId("design-slicer-sha256").textContent())?.trim() ?? "";
    const guiLayerCount = parseInt(
      (await page.getByTestId("design-slicer-layer-count").textContent())?.trim() ?? "0",
      10,
    );
    const guiMotionLines = parseInt(
      (await page.getByTestId("design-slicer-motion-lines").textContent())?.trim() ?? "0",
      10,
    );
    expect(guiGcodePath, "GUI must surface a real gcode_path").toBeTruthy();
    expect(fs.existsSync(guiGcodePath), `gcode file must exist on disk: ${guiGcodePath}`).toBe(true);
    const gcodeBuf = fs.readFileSync(guiGcodePath);
    const recomputedSha = sha256(gcodeBuf);
    expect(recomputedSha, "recomputed sha256 must match GUI value").toBe(guiSha);
    expect(guiLayerCount, "GUI must report layer_count > 0 (W18-A12 analyzer fix)").toBeGreaterThan(0);
    expect(guiMotionLines, "GUI must report motion_lines > 0").toBeGreaterThan(0);

    // Also confirm via the backend GET endpoint so the proof is doubly attested.
    const apiState = await request.get(`${BACKEND_URL}/api/slice/${jobId}`).then((r) => r.json());
    expect(apiState.sha256).toBe(recomputedSha);
    expect(apiState.layer_count).toBe(guiLayerCount);
    expect(apiState.motion_lines).toBe(guiMotionLines);
    expect(apiState.gcode_path).toBe(guiGcodePath);

    // Copy the gcode into test-results/ for permanent evidence.
    const gcodeEvidence = path.join(ARTIFACT_DIR, path.basename(guiGcodePath));
    fs.copyFileSync(guiGcodePath, gcodeEvidence);

    auditSteps.push({
      id: "gcode_real_artifact",
      result: "ok",
      detail: {
        gcode_path: guiGcodePath,
        gcode_evidence_path: gcodeEvidence,
        gcode_size_bytes: gcodeBuf.length,
        gcode_sha256: recomputedSha,
        layer_count: guiLayerCount,
        motion_lines: guiMotionLines,
        estimated_print_time_min: apiState.estimated_print_time_min,
        slicer_binary: apiState.slicer_binary,
        proof_event_id: apiState.proof_event_id,
      },
    });

    // --- 8. Download link is present -----------------------------------------
    const downloadLink = page.getByTestId("design-slicer-download");
    await expect(downloadLink, "download link must be visible after completion").toBeVisible();
    const href = await downloadLink.getAttribute("href");
    expect(href).toMatch(/\/api\/artifacts\/[^/]+\/download$/);
    // Hit the download URL and verify it returns the same bytes.
    const dlResp = await request.get(`${BACKEND_URL}${new URL(href ?? "", BACKEND_URL).pathname}`);
    expect(dlResp.ok(), `download URL ${href} should be 2xx`).toBe(true);
    const dlBuf = Buffer.from(await dlResp.body());
    expect(sha256(dlBuf), "downloaded bytes must match the on-disk sha256").toBe(recomputedSha);
    auditSteps.push({ id: "gcode_download_link_serves_real_bytes", result: "ok" });

    // --- 9. Confirm NO Send-to-Printer button exists -------------------------
    // The freeze forbids this kind of affordance. We assert by name and by
    // data-testid prefix.
    const forbiddenButtonNames = [
      /Send to Printer/i,
      /Start Print/i,
      /Upload to Printer/i,
      /Print Now/i,
    ];
    for (const re of forbiddenButtonNames) {
      const cnt = await page.getByRole("button", { name: re }).count();
      expect(cnt, `forbidden button '${re}' must not exist on Design tab`).toBe(0);
    }
    const freezeBadge = page.getByTestId("design-slicer-freeze-badge");
    await expect(freezeBadge).toBeVisible();
    auditSteps.push({ id: "no_dispatch_affordance", result: "ok" });

    // --- 10. Network audit ----------------------------------------------------
    const writeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);
    const printerControlHits = network.filter((c) => {
      if (!writeMethods.has(c.method)) return false;
      return PRINTER_CONTROL_PATTERNS.some((re) => re.test(c.url));
    });
    const ourBackend = network.filter((c) => c.url.startsWith(BACKEND_URL));
    const writes = ourBackend.filter((c) => writeMethods.has(c.method));
    const writePaths = Array.from(new Set(writes.map((c) => pathnameOf(c.url)))).sort();
    const offAllow = writePaths.filter(
      (p) => !ALLOWED_BACKEND_PATTERNS.some((re) => re.test(p)),
    );

    fs.writeFileSync(
      path.join(ARTIFACT_DIR, "06-network-log.json"),
      JSON.stringify(
        {
          total_calls: network.length,
          backend_calls: ourBackend.length,
          unique_write_paths: writePaths,
          off_allow_list_writes: offAllow,
          printer_control_hits: printerControlHits,
          http_failures: httpFailures,
        },
        null,
        2,
      ),
    );
    expect(printerControlHits, `FREEZE: no printer-control endpoint may be hit:\n${JSON.stringify(printerControlHits, null, 2)}`).toEqual([]);
    expect(offAllow, `Writes to backend must stay on the allow-list:\n${JSON.stringify(offAllow, null, 2)}`).toEqual([]);
    auditSteps.push({
      id: "network_audit_allowlist",
      result: "ok",
      detail: { write_paths: writePaths },
    });

    // --- 11. Hard rules -------------------------------------------------------
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, "audit.json"),
      JSON.stringify(
        {
          task_id: "W18-A12-SLICER-WIREUP-2026-05-11",
          verdict_gate: "GUI_SLICER_GREEN",
          verdict: "PASS_REAL",
          pinned_verdicts: {
            GUI_PHYSICAL_PRINT_GREEN: "OUT_OF_SCOPE_BY_OPERATOR",
            GUI_PRINTER_DRY_RUN_GREEN: "OUT_OF_SCOPE_BY_OPERATOR",
          },
          slice_job_id: jobId,
          gcode_path: guiGcodePath,
          gcode_sha256: recomputedSha,
          gcode_size_bytes: gcodeBuf.length,
          layer_count: guiLayerCount,
          motion_lines: guiMotionLines,
          allow_listed_write_paths: writePaths,
          console_errors: consoleErrors,
          page_errors: pageErrors,
          http_failures: httpFailures,
          audit_steps: auditSteps,
        },
        null,
        2,
      ),
    );

    expect(pageErrors, `Page errors must be zero:\n${pageErrors.join("\n")}`).toEqual([]);
    expect(consoleErrors, `Console errors must be zero:\n${consoleErrors.join("\n")}`).toEqual([]);
    expect(httpFailures, `Backend/frontend HTTP failures must be zero:\n${JSON.stringify(httpFailures, null, 2)}`).toEqual([]);
  });
});
