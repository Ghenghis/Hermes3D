/**
 * W18-A7 Print Queue Workflow Proof
 *
 * Drives the live #print_queue tab end-to-end: opens the Submit Job dialog,
 * fills it with a real artifact reference + a real printer id selected from
 * `/api/printers`, submits, and asserts the persisted job appears back in the
 * queue list. The job is ALWAYS `dry_run=true` — this audit covers
 * submission + persistence, NOT physical printing.
 *
 * Status vocabulary (strictly one token in the artifact):
 *   PASS_REAL              — submit succeeded, real job_id returned, GET /api/jobs
 *                            and the UI both show the row.
 *   FAIL_BROKEN            — dialog did not open, submit threw, or the DOM never
 *                            reflected the persisted row.
 *   FAIL_BACKEND_MISSING   — POST /api/jobs returned >=500 / net::ERR_*.
 *
 * No mocks. No route stubs. Backend is the FastAPI server at 127.0.0.1:8765.
 * Artifact reference: `04_testing/fixtures/w18_a7_cube_10mm.gcode`. The
 * fixture file is real and 50+ lines of valid G-code, but the current
 * JobCreate Pydantic model does not have an `artifact_path` column — the
 * fixture path is recorded in the job NAME so the persistence proof can
 * later trace back to it.
 *
 * Hard rules: physical printing is forbidden. Submission stops at status
 * `queued`. The spec records the new job's id, the printer id chosen, and
 * the backend's POST response into an audit JSON for the handoff doc.
 */
import { expect, test, type ConsoleMessage, type Request, type Response } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// ESM-safe equivalent of __dirname (this project's package.json sets
// "type": "module", so the CJS magic vars are not defined under Node).
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

type Status = "PASS_REAL" | "FAIL_BROKEN" | "FAIL_BACKEND_MISSING";

interface Step {
  name: string;
  status: Status;
  reason: string;
  detail?: Record<string, unknown>;
}

interface PrinterRow {
  id: string;
  name: string;
  status?: string;
  safety_policy?: string;
  write_enabled?: boolean;
}

interface JobRow {
  id: string;
  name: string;
  job_type?: string;
  status: string;
  printer_id: string | null;
  dry_run: number | boolean;
  created_at?: string;
}

const OUTPUT_DIR = path.resolve(__dirname, "..", "..", "test-results", "w18-a7");
fs.mkdirSync(OUTPUT_DIR, { recursive: true });
const ARTIFACT_PATH = path.join(OUTPUT_DIR, "audit.json");

const BACKEND = "http://127.0.0.1:8765";
const ARTIFACT_FIXTURE = "04_testing/fixtures/w18_a7_cube_10mm.gcode";

test.describe.configure({ mode: "serial" });

test("W18-A7 — submit a real job into #print_queue and verify persistence", async ({ page, request }) => {
  test.setTimeout(180_000);

  const steps: Step[] = [];
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const networkFailures: Array<{ url: string; status: number; statusText: string; method: string }> = [];

  page.on("console", (msg: ConsoleMessage) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });
  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("response", (res: Response) => {
    if (res.status() >= 500) {
      networkFailures.push({
        url: res.url(),
        status: res.status(),
        statusText: res.statusText(),
        method: res.request().method(),
      });
    }
  });
  page.on("requestfailed", (req: Request) => {
    networkFailures.push({
      url: req.url(),
      status: 0,
      statusText: req.failure()?.errorText ?? "request_failed",
      method: req.method(),
    });
  });

  // --- Step 1: probe backend printers list. ---
  let printers: PrinterRow[] = [];
  try {
    const resp = await request.get(`${BACKEND}/api/printers`);
    expect(resp.ok()).toBe(true);
    printers = (await resp.json()) as PrinterRow[];
    expect(Array.isArray(printers)).toBe(true);
    steps.push({
      name: "printers_list",
      status: "PASS_REAL",
      reason: `GET /api/printers -> ${printers.length} rows`,
      detail: { count: printers.length, ids: printers.map((p) => p.id) },
    });
  } catch (err) {
    steps.push({
      name: "printers_list",
      status: "FAIL_BACKEND_MISSING",
      reason: `GET /api/printers failed: ${(err as Error).message}`,
    });
    writeArtifact(steps, consoleErrors, pageErrors, networkFailures, null);
    throw err;
  }

  // Choose a write-enabled printer that is NOT S1 (S1 is locked).
  const targetPrinter =
    printers.find(
      (p) => p.id !== "flsun_s1" && (p.write_enabled === true || p.safety_policy === "write_enabled"),
    ) ?? printers.find((p) => p.id !== "flsun_s1");
  expect(targetPrinter, "no non-S1 printer available").toBeTruthy();
  const printerId = targetPrinter!.id;

  // --- Step 2: open the SPA, navigate to #print_queue. ---
  try {
    await page.goto("http://localhost:5173/", { waitUntil: "domcontentloaded", timeout: 30_000 });
    await page.waitForSelector('[data-testid$="-root"]', { timeout: 20_000 });
    await page.evaluate(() => {
      window.location.hash = "#print_queue";
    });
    await expect(page.getByTestId("print-queue-root")).toBeVisible({ timeout: 10_000 });
    steps.push({
      name: "navigate_print_queue",
      status: "PASS_REAL",
      reason: "#print_queue tab mounted",
    });
  } catch (err) {
    steps.push({
      name: "navigate_print_queue",
      status: "FAIL_BROKEN",
      reason: `Could not open #print_queue: ${(err as Error).message.split("\n")[0]}`,
    });
    writeArtifact(steps, consoleErrors, pageErrors, networkFailures, null);
    throw err;
  }

  // --- Step 3: open the Submit Job dialog. ---
  try {
    const submitBtn = page.getByTestId("print-queue-submit");
    await expect(submitBtn).toBeVisible({ timeout: 5_000 });
    await submitBtn.click();
    await expect(page.getByTestId("submit-job-dialog")).toBeVisible({ timeout: 5_000 });
    steps.push({
      name: "open_dialog",
      status: "PASS_REAL",
      reason: "Submit Job dialog opened",
    });
  } catch (err) {
    steps.push({
      name: "open_dialog",
      status: "FAIL_BROKEN",
      reason: `Could not open Submit Job dialog: ${(err as Error).message.split("\n")[0]}`,
    });
    writeArtifact(steps, consoleErrors, pageErrors, networkFailures, null);
    throw err;
  }

  // --- Step 4: fill the form. ---
  // Name encodes the artifact path so the persistence proof can trace it.
  const jobName = `W18-A7 ${ARTIFACT_FIXTURE} -> ${printerId}`;
  try {
    await page.getByTestId("submit-job-dialog-name").fill(jobName);
    await page.getByTestId("submit-job-dialog-type").selectOption("slice");
    await page.getByTestId("submit-job-dialog-printer").selectOption(printerId);
    // dry_run defaults to true — keep it. No physical print authorized.
    const dryRun = page.getByTestId("submit-job-dialog-dry-run");
    if (!(await dryRun.isChecked())) await dryRun.check();
    steps.push({
      name: "fill_form",
      status: "PASS_REAL",
      reason: `name=${jobName} printer=${printerId} type=slice dry_run=true`,
    });
  } catch (err) {
    steps.push({
      name: "fill_form",
      status: "FAIL_BROKEN",
      reason: `Could not fill form: ${(err as Error).message.split("\n")[0]}`,
    });
    writeArtifact(steps, consoleErrors, pageErrors, networkFailures, null);
    throw err;
  }

  // --- Step 5: submit and capture the response from POST /api/jobs. ---
  let createdJobId: string | null = null;
  let postResponseBody: unknown = null;
  try {
    const responsePromise = page.waitForResponse(
      (r) => /\/api\/jobs$/.test(r.url()) && r.request().method() === "POST",
      { timeout: 15_000 },
    );
    await page.getByTestId("submit-job-dialog-submit").click();
    const postResp = await responsePromise;
    expect(postResp.status(), `POST /api/jobs status was ${postResp.status()}`).toBe(201);
    postResponseBody = await postResp.json();
    const body = postResponseBody as JobRow;
    expect(body.id, "no job id returned").toBeTruthy();
    expect(typeof body.id).toBe("string");
    expect(body.status).toBe("queued");
    createdJobId = body.id;

    steps.push({
      name: "post_jobs",
      status: "PASS_REAL",
      reason: `POST /api/jobs -> 201 job_id=${createdJobId}`,
      detail: { response: body },
    });
  } catch (err) {
    steps.push({
      name: "post_jobs",
      status: "FAIL_BACKEND_MISSING",
      reason: `POST /api/jobs failed: ${(err as Error).message.split("\n")[0]}`,
    });
    writeArtifact(steps, consoleErrors, pageErrors, networkFailures, createdJobId);
    throw err;
  }

  // --- Step 6: dialog closes after success. ---
  try {
    await expect(page.getByTestId("submit-job-dialog")).toBeHidden({ timeout: 5_000 });
    steps.push({
      name: "dialog_closed",
      status: "PASS_REAL",
      reason: "Dialog closed after successful submit",
    });
  } catch (err) {
    steps.push({
      name: "dialog_closed",
      status: "FAIL_BROKEN",
      reason: `Dialog did not close: ${(err as Error).message.split("\n")[0]}`,
    });
  }

  // --- Step 7: GET /api/jobs?status=queued shows the new row. ---
  try {
    const queuedResp = await request.get(`${BACKEND}/api/jobs?status=queued`);
    expect(queuedResp.ok()).toBe(true);
    const queuedList = (await queuedResp.json()) as JobRow[];
    const persisted = queuedList.find((j) => j.id === createdJobId);
    expect(persisted, `job ${createdJobId} not present in GET /api/jobs?status=queued`).toBeTruthy();
    steps.push({
      name: "backend_list_contains_job",
      status: "PASS_REAL",
      reason: `GET /api/jobs?status=queued contains ${createdJobId}`,
      detail: { persisted_row: persisted },
    });
  } catch (err) {
    steps.push({
      name: "backend_list_contains_job",
      status: "FAIL_BACKEND_MISSING",
      reason: `GET /api/jobs verification failed: ${(err as Error).message.split("\n")[0]}`,
    });
  }

  // --- Step 8: GET /api/jobs/{id} returns the detail row. ---
  try {
    const detailResp = await request.get(`${BACKEND}/api/jobs/${createdJobId}`);
    expect(detailResp.ok()).toBe(true);
    const detail = (await detailResp.json()) as JobRow & {
      steps?: unknown[];
      events?: unknown[];
      artifacts?: unknown[];
    };
    expect(detail.id).toBe(createdJobId);
    expect(detail.status).toBe("queued");
    steps.push({
      name: "backend_detail_endpoint",
      status: "PASS_REAL",
      reason: `GET /api/jobs/${createdJobId} -> 200`,
      detail: {
        id: detail.id,
        status: detail.status,
        printer_id: detail.printer_id,
        steps_count: Array.isArray(detail.steps) ? detail.steps.length : 0,
        events_count: Array.isArray(detail.events) ? detail.events.length : 0,
        artifacts_count: Array.isArray(detail.artifacts) ? detail.artifacts.length : 0,
      },
    });
  } catch (err) {
    steps.push({
      name: "backend_detail_endpoint",
      status: "FAIL_BACKEND_MISSING",
      reason: `GET /api/jobs/${createdJobId} failed: ${(err as Error).message.split("\n")[0]}`,
    });
  }

  // --- Step 9: queue UI refreshes and shows the new job. ---
  try {
    // The UI auto-refreshes every 10s, but the SubmitJobDialog's
    // onSubmitted handler already calls refresh() — give it a beat.
    await page.getByTestId("print-queue-refresh").click().catch(() => undefined);
    const jobTile = page.getByTestId(`print-queue-job-${createdJobId}`);
    await expect(jobTile).toBeVisible({ timeout: 15_000 });
    // Take a screenshot of the queue with the new row for evidence.
    const screenshotPath = path.join(OUTPUT_DIR, "print-queue-after-submit.png");
    await page.screenshot({ path: screenshotPath, fullPage: false });
    steps.push({
      name: "ui_shows_job",
      status: "PASS_REAL",
      reason: `print-queue-job-${createdJobId} tile visible`,
      detail: { screenshot: screenshotPath },
    });
  } catch (err) {
    steps.push({
      name: "ui_shows_job",
      status: "FAIL_BROKEN",
      reason: `UI did not show new job: ${(err as Error).message.split("\n")[0]}`,
    });
  }

  // --- Step 10: assert dry_run was preserved (no print authorized). ---
  try {
    const verifyResp = await request.get(`${BACKEND}/api/jobs/${createdJobId}`);
    const detail = (await verifyResp.json()) as JobRow;
    const dryRunPersisted = detail.dry_run === 1 || detail.dry_run === true;
    expect(
      dryRunPersisted,
      `dry_run was NOT preserved on the row (got ${detail.dry_run}); this would mean the audit accidentally authorized a physical print`,
    ).toBe(true);
    expect(detail.status, "job status changed away from 'queued'").toBe("queued");
    steps.push({
      name: "dry_run_preserved",
      status: "PASS_REAL",
      reason: `dry_run=${detail.dry_run} status=${detail.status} — no physical print authorized`,
    });
  } catch (err) {
    steps.push({
      name: "dry_run_preserved",
      status: "FAIL_BROKEN",
      reason: `dry_run / status check failed: ${(err as Error).message.split("\n")[0]}`,
    });
  }

  writeArtifact(steps, consoleErrors, pageErrors, networkFailures, createdJobId, postResponseBody);

  // Spec PASS requires every step PASS_REAL.
  const failed = steps.filter((s) => s.status !== "PASS_REAL");
  expect(
    failed,
    `FAILED steps: ${failed.map((s) => `${s.name}=${s.status}:${s.reason}`).join(" | ")}`,
  ).toEqual([]);
});

function writeArtifact(
  steps: Step[],
  consoleErrors: string[],
  pageErrors: string[],
  networkFailures: Array<{ url: string; status: number; statusText: string; method: string }>,
  createdJobId: string | null,
  postResponseBody: unknown = null,
) {
  const verdict: Status =
    steps.every((s) => s.status === "PASS_REAL")
      ? "PASS_REAL"
      : steps.some((s) => s.status === "FAIL_BACKEND_MISSING")
        ? "FAIL_BACKEND_MISSING"
        : "FAIL_BROKEN";

  const artifact = {
    generated_utc: new Date().toISOString(),
    base_url: "http://localhost:5173",
    backend_url: BACKEND,
    spec: "tests/e2e/w18-a7-print-queue-workflow.spec.ts",
    artifact_fixture: ARTIFACT_FIXTURE,
    created_job_id: createdJobId,
    post_response: postResponseBody,
    verdict,
    steps,
    raw: {
      consoleErrors,
      pageErrors,
      networkFailures,
    },
  };
  fs.writeFileSync(ARTIFACT_PATH, JSON.stringify(artifact, null, 2), "utf8");
  console.log(
    `[W18-A7] verdict=${verdict} job_id=${createdJobId ?? "(none)"} steps=${steps.length} -> ${ARTIFACT_PATH}`,
  );
}
