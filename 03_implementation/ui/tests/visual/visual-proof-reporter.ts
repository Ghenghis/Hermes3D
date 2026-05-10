/**
 * W6-6 Custom Playwright reporter for visual-proof.spec.ts.
 *
 * Reads the test annotations emitted by visual-proof.spec.ts and produces a
 * single JSON summary at:
 *   03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json
 *
 * Each row records:
 *   { target, status, route, reference, tolerance,
 *     diff_pixels?, total_pixels?, ratio?,
 *     evidence_path, diff_path?, error?, started_at, finished_at }
 *
 * Status values:
 *   - "match"               : visual diff <= tolerance
 *   - "diff"                : visual diff > tolerance (FAIL)
 *   - "missing-baseline"    : no reference PNG found at the expected path
 *   - "skipped-future"      : status="future" target owned by another lane
 *   - "skipped-missing-reference": reference path was not on disk
 *   - "error"               : runtime error (timeout, navigation crash, etc.)
 *
 * Sources:
 *  - Playwright reporter API:
 *      https://playwright.dev/docs/api/class-reporter
 *  - Playwright snapshot/visual-comparison docs:
 *      https://playwright.dev/docs/test-snapshots
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type {
  FullConfig,
  FullResult,
  Reporter,
  TestCase,
  TestResult,
} from "@playwright/test/reporter";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(HERE, "..", "..", "..", "..");
const SUMMARY_DIR = path.join(
  REPO_ROOT,
  "03_implementation",
  "docs",
  "evidence",
  "visual_proof_2026-05-09",
);
const SUMMARY_PATH = path.join(SUMMARY_DIR, "summary.json");

interface VisualRow {
  target: string;
  status:
    | "match"
    | "diff"
    | "missing-baseline"
    | "skipped-future"
    | "skipped-missing-reference"
    | "error";
  route: string | null;
  reference: string | null;
  tolerance: number | null;
  diff_pixels?: number;
  total_pixels?: number;
  ratio?: number;
  evidence_path: string | null;
  diff_path: string | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

function safeJsonParse<T>(s: string): T | null {
  try {
    return JSON.parse(s) as T;
  } catch {
    return null;
  }
}

class VisualProofReporter implements Reporter {
  private rows: VisualRow[] = [];
  private startedAt: string = "";

  onBegin(_config: FullConfig): void {
    this.startedAt = new Date().toISOString();
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    // Each visual-proof.spec.ts test pushes contract annotations:
    //   visual-proof-target  -> sent immediately on test start
    //   visual-proof-result  -> sent only on a successful match
    //   visual-proof         -> single annotation when skipped
    const annotations = test.annotations.concat(result.annotations ?? []);
    let target: string | null = null;
    let route: string | null = null;
    let reference: string | null = null;
    let tolerance: number | null = null;
    let matched = false;
    let skippedReason: string | null = null;
    let skippedKind: "future" | "missing-reference" | null = null;

    for (const ann of annotations) {
      const desc = ann.description ?? "";
      const parsed =
        typeof desc === "string" ? safeJsonParse<Record<string, unknown>>(desc) : null;
      if (!parsed) continue;
      if (typeof parsed.target === "string") target = parsed.target;
      if (typeof parsed.route === "string") route = parsed.route;
      if (typeof parsed.reference === "string") reference = parsed.reference;
      if (typeof parsed.tolerance === "number") tolerance = parsed.tolerance;

      if (ann.type === "visual-proof-result" && parsed.status === "match") {
        matched = true;
      }
      if (ann.type === "visual-proof") {
        if (parsed.status === "skipped-future") {
          skippedKind = "future";
          if (typeof parsed.reason === "string") skippedReason = parsed.reason;
        } else if (parsed.status === "skipped-missing-reference") {
          skippedKind = "missing-reference";
        }
      }
    }

    if (!target) {
      // Not one of our visual targets; ignore.
      return;
    }

    const startedAt = new Date(result.startTime).toISOString();
    const finishedAt = new Date(result.startTime.getTime() + result.duration).toISOString();

    let status: VisualRow["status"];
    let errorMessage: string | null = null;
    let evidencePath: string | null = null;
    let diffPath: string | null = null;
    let diffPixels: number | undefined;
    let totalPixels: number | undefined;
    let ratio: number | undefined;

    // Look for the diff/actual attachments Playwright emits when the screenshot
    // assertion fails. These give us diff_pixels and the diff PNG path.
    for (const att of result.attachments ?? []) {
      if (!att.name) continue;
      if (/expected/.test(att.name) && att.path) {
        // The expected image is the reference PNG itself; record its path so
        // reviewers can hop directly to Images-GUI/.
      } else if (/actual/.test(att.name) && att.path) {
        evidencePath = path.relative(REPO_ROOT, att.path).replace(/\\/g, "/");
      } else if (/diff/.test(att.name) && att.path) {
        diffPath = path.relative(REPO_ROOT, att.path).replace(/\\/g, "/");
      }
    }

    // Inspect the test error for diff_pixels / ratio info that Playwright
    // emits on toHaveScreenshot failure.
    if (result.status === "failed" || result.status === "timedOut") {
      const msg = result.error?.message ?? "";
      errorMessage = msg.split("\n").slice(0, 2).join(" ").slice(0, 600);
      // Playwright failure messages contain phrases like:
      //   "12345 pixels (ratio 0.06 of all image pixels) are different."
      const pixMatch = msg.match(/(\d+)\s+pixels?\s+\(ratio\s+([0-9.]+)/i);
      if (pixMatch) {
        diffPixels = Number(pixMatch[1]);
        ratio = Number(pixMatch[2]);
      }
      // Missing baseline messages:
      //   "A snapshot doesn't exist at ..., writing actual."
      //   "Error: A snapshot doesn't exist at ..."
      if (/snapshot doesn't exist|does not exist/i.test(msg)) {
        status = "missing-baseline";
      } else if (diffPixels !== undefined) {
        status = "diff";
      } else {
        status = "error";
      }
    } else if (result.status === "passed" && matched) {
      status = "match";
    } else if (result.status === "skipped") {
      status =
        skippedKind === "future"
          ? "skipped-future"
          : skippedKind === "missing-reference"
            ? "skipped-missing-reference"
            : "skipped-future";
      if (skippedReason) errorMessage = skippedReason;
    } else if (result.status === "passed") {
      // Passed without a match annotation — defensive fallback.
      status = "match";
    } else {
      status = "error";
    }

    this.rows.push({
      target,
      status,
      route,
      reference,
      tolerance,
      diff_pixels: diffPixels,
      total_pixels: totalPixels,
      ratio,
      evidence_path: evidencePath,
      diff_path: diffPath,
      error: errorMessage,
      started_at: startedAt,
      finished_at: finishedAt,
    });
  }

  async onEnd(result: FullResult): Promise<void> {
    fs.mkdirSync(SUMMARY_DIR, { recursive: true });

    const counts = this.rows.reduce(
      (acc, row) => {
        acc[row.status] = (acc[row.status] ?? 0) + 1;
        acc.total += 1;
        return acc;
      },
      { total: 0 } as Record<string, number>,
    );

    const summary = {
      schema_version: 1,
      generated_at: new Date().toISOString(),
      started_at: this.startedAt,
      run_status: result.status,
      owner: "claude-w6-6-visual-proof",
      lane: "W6-6 Playwright visual proof against Images-GUI/",
      counts,
      rows: this.rows.sort((a, b) => a.target.localeCompare(b.target)),
    };

    fs.writeFileSync(SUMMARY_PATH, JSON.stringify(summary, null, 2) + "\n");
    // Also write a brief stdout summary so CI logs surface the totals.
    const summaryLine =
      `[visual-proof] total=${counts.total} ` +
      Object.entries(counts)
        .filter(([k]) => k !== "total")
        .map(([k, v]) => `${k}=${v}`)
        .join(" ");
    process.stdout.write(`${summaryLine}\n`);
    process.stdout.write(`[visual-proof] summary written to ${SUMMARY_PATH}\n`);
  }
}

export default VisualProofReporter;
