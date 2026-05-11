/**
 * W18-A10 PICKUP — Playwright reporter (visual-oracle verdict aggregator).
 *
 * Reads `w18-a10-pickup` annotations emitted by
 * `tests/e2e/w18-a10-pickup-visual-oracle.spec.ts` and writes:
 *  - `W18_A10_PICKUP_SUMMARY.json`  — full row table + bucket counts.
 *  - `W18_A10_PICKUP_TOP10.md`      — top-10 worst pixel-diff rows.
 *
 * Bucket semantics
 * ----------------
 *  - pass:          compare_mode='live'  AND diffRatio <= tolerance.
 *  - diff:          compare_mode='live'  AND diffRatio  > tolerance.
 *  - informational: compare_mode='informational'. Documented PARTIAL.
 *                   May carry `crash_during_capture=true` when the spec's
 *                   try/catch around screenshot / pixel-compare caught
 *                   a crash (PR-#241 fix mode); the row still falls in
 *                   the informational bucket because it did not fail
 *                   Playwright. See the spec for the catch sites.
 *                   Under W18-A10P-CIFIX2, `crash_phase` may also report
 *                   step-budget-exceeded events (`setup`, `screenshot`,
 *                   `pixel-compare`) when a sub-step blew past its
 *                   bounded budget — the wrapper still records the row.
 *  - error:         test threw before recording a comparison. For
 *                   informational variants this should NEVER happen
 *                   after the W18-A10P-CIFIX try/catch wrapping; if it
 *                   does it indicates a regression in the wrapping.
 *
 * GUI_PIXEL_E2E_GREEN
 * -------------------
 *  Verdict-gate truth is built from the `live` bucket only:
 *      pass + diff + error_live = live_count
 *  GUI_PIXEL_E2E_GREEN = (diff == 0 AND error_live == 0)
 *  Informational rows are reported separately and never block the gate
 *  (they are explicit out-of-scope PARTIALs documented in the manifest).
 *  `informational_crash` (rows where capture crashed under try/catch)
 *  is surfaced as a separate counter so the operator can see it without
 *  it gating the verdict.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { FullResult, Reporter, TestCase, TestResult } from "@playwright/test/reporter";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI_ROOT = path.resolve(HERE, "..", "..");
const REPO_ROOT = path.resolve(UI_ROOT, "..", "..");
const SUMMARY_DIR = path.join(UI_ROOT, "tests", "visual-proof");
const SUMMARY_JSON = path.join(SUMMARY_DIR, "W18_A10_PICKUP_SUMMARY.json");
const SUMMARY_TOP10 = path.join(SUMMARY_DIR, "W18_A10_PICKUP_TOP10.md");

interface AnnotationPayload {
  target: string;
  compare_mode: "live" | "informational";
  verdict: "pass" | "diff" | "informational";
  ref?: string;
  route?: string | null;
  viewport?: { width: number; height: number };
  theme?: string | null;
  state?: string | null;
  expected_size?: { width: number; height: number } | null;
  observed_size?: { width: number; height: number } | null;
  diff_pixels?: number | null;
  diff_ratio?: number | null;
  max_diff_ratio?: number;
  size_mismatch?: boolean | null;
  observed_path?: string | null;
  diff_path?: string | null;
  console_errors_count?: number;
  console_errors_sample?: string[];
  nav_error?: string | null;
  blocker?: string | null;
  notes?: string;
  // W18-A10P-CIFIX fields — informational variants that crash under
  // the spec's try/catch wrapping record these so the operator can see
  // which step failed without failing Playwright.
  crash_during_capture?: boolean;
  crash_phase?: string | null;
  crash_message?: string | null;
}

interface Row extends AnnotationPayload {
  bucket: "pass" | "diff" | "informational" | "error";
  playwright_project?: string;
  playwright_status: string;
  error_message?: string;
}

const ROWS: Row[] = [];

class W18A10PickupReporter implements Reporter {
  onTestEnd(test: TestCase, result: TestResult): void {
    let payload: AnnotationPayload | null = null;
    for (const ann of test.annotations) {
      if (ann.type !== "w18-a10-pickup") continue;
      try {
        payload = JSON.parse(ann.description ?? "{}") as AnnotationPayload;
      } catch {
        payload = null;
      }
    }
    const baseTitle = test.title;
    let projectName: string | undefined;
    try {
      projectName = test.parent?.project()?.name;
    } catch {
      projectName = undefined;
    }
    if (payload) {
      let bucket: Row["bucket"];
      if (payload.compare_mode === "informational") {
        // Informational variants are wrapped in try/catch by the spec
        // (W18-A10P-CIFIX). They should always pass Playwright; if one
        // somehow still throws, surface it as "error" so the regression
        // is visible without it gating GUI_PIXEL_E2E_GREEN (the gate
        // only considers `live` rows).
        bucket = result.status === "passed" ? "informational" : "error";
      } else if (result.status !== "passed") {
        bucket = payload.verdict === "diff" ? "diff" : "error";
      } else {
        bucket = "pass";
      }
      ROWS.push({
        ...payload,
        bucket,
        playwright_project: projectName,
        playwright_status: result.status,
        error_message: result.error?.message,
      });
    } else {
      ROWS.push({
        target: baseTitle,
        compare_mode: "live",
        verdict: "diff",
        bucket: "error",
        playwright_project: projectName,
        playwright_status: result.status,
        error_message: result.error?.message ?? "no annotation emitted",
      });
    }
  }

  onEnd(_result: FullResult): void {
    fs.mkdirSync(SUMMARY_DIR, { recursive: true });
    const counts = ROWS.reduce(
      (acc, r) => {
        acc[r.bucket] = (acc[r.bucket] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    const live = ROWS.filter((r) => r.compare_mode === "live");
    const liveErrors = live.filter((r) => r.bucket === "error").length;
    const liveDiffs = live.filter((r) => r.bucket === "diff").length;
    const livePasses = live.filter((r) => r.bucket === "pass").length;
    const informational = ROWS.filter((r) => r.compare_mode === "informational");
    const informationalErrors = informational.filter((r) => r.bucket === "error")
      .length;
    const informationalCrashes = informational.filter(
      (r) => r.crash_during_capture === true,
    ).length;
    const liveDiffPixels = live
      .filter((r) => typeof r.diff_pixels === "number")
      .reduce((s, r) => s + (r.diff_pixels ?? 0), 0);

    // GUI_PIXEL_E2E_GREEN is computed from the `live` bucket ONLY.
    // The W18-A10P-CIFIX project split means informational crashes
    // are recorded as PARTIAL rows (bucket=informational,
    // crash_during_capture=true) and never block this gate.
    const guiPixelE2EGreen = liveDiffs === 0 && liveErrors === 0;

    const summary = {
      wave: "W18",
      agent: "W18-A10-PICKUP",
      lock_owner: "w18-a10-pickup",
      task_id: "W18-A10-PICKUP-VISUAL-ORACLE-2026-05-11",
      generated_utc: new Date().toISOString(),
      total_targets: ROWS.length,
      buckets: {
        pass: counts.pass ?? 0,
        diff: counts.diff ?? 0,
        informational: counts.informational ?? 0,
        error: counts.error ?? 0,
      },
      live_total: live.length,
      live_pass: livePasses,
      live_diff: liveDiffs,
      live_error: liveErrors,
      informational_total: informational.length,
      informational_error: informationalErrors,
      informational_crash: informationalCrashes,
      live_total_diff_pixels: liveDiffPixels,
      gui_pixel_e2e_green: guiPixelE2EGreen,
      printer_freeze: {
        gui_physical_print_green: "OUT_OF_SCOPE_BY_OPERATOR",
        gui_printer_dry_run_green: "OUT_OF_SCOPE_BY_OPERATOR",
        printer_hardware_writes: 0,
      },
      rows: ROWS,
    };

    fs.writeFileSync(SUMMARY_JSON, JSON.stringify(summary, null, 2));

    const worst = [...ROWS]
      .filter((r) => typeof r.diff_pixels === "number")
      .sort((a, b) => (b.diff_pixels ?? 0) - (a.diff_pixels ?? 0))
      .slice(0, 10);

    const md: string[] = [];
    md.push("# W18-A10 PICKUP — Top 10 Worst Mismatches");
    md.push("");
    md.push(`Generated ${summary.generated_utc}`);
    md.push("");
    md.push(
      `Live: pass=${summary.live_pass}  diff=${summary.live_diff}  error=${summary.live_error}  ` +
        `(total live=${summary.live_total})`,
    );
    md.push(
      `Informational: total=${summary.informational_total}  ` +
        `error=${summary.informational_error}  ` +
        `crash_during_capture=${summary.informational_crash}`,
    );
    md.push(`GUI_PIXEL_E2E_GREEN: **${summary.gui_pixel_e2e_green}**`);
    md.push(
      `Printer freeze: GUI_PHYSICAL_PRINT_GREEN=${summary.printer_freeze.gui_physical_print_green}  ` +
        `GUI_PRINTER_DRY_RUN_GREEN=${summary.printer_freeze.gui_printer_dry_run_green}  ` +
        `printer_hardware_writes=${summary.printer_freeze.printer_hardware_writes}`,
    );
    md.push("");
    md.push(
      "| # | target | bucket | diff_pixels | diff_ratio | size_mismatch | route | diff_png |",
    );
    md.push(
      "|---|--------|--------|-------------|------------|---------------|-------|----------|",
    );
    worst.forEach((r, i) => {
      const diffPng = r.diff_path
        ? `[diff](${path.posix.normalize((r.diff_path as string).replace(/\\/g, "/"))})`
        : "-";
      md.push(
        `| ${i + 1} | ${r.target} | ${r.bucket} | ${r.diff_pixels ?? "-"} | ` +
          `${r.diff_ratio?.toFixed(4) ?? "-"} | ${r.size_mismatch ?? "-"} | ` +
          `${r.route ?? "-"} | ${diffPng} |`,
      );
    });
    md.push("");
    fs.writeFileSync(SUMMARY_TOP10, md.join("\n"));

    // eslint-disable-next-line no-console
    console.log(`[w18-a10-pickup] summary -> ${path.relative(REPO_ROOT, SUMMARY_JSON)}`);
  }
}

export default W18A10PickupReporter;
