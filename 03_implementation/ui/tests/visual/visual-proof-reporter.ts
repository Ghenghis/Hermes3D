/**
 * W6-6 / W15-A9 Playwright reporter for visual-proof.spec.ts.
 *
 * Reads test annotations emitted by visual-proof.spec.ts and produces a JSON
 * summary at:
 *   03_implementation/docs/evidence/visual_proof_2026-05-09/summary.json
 *
 * W15-A9 extensions over W14:
 *   - region-level rows (one per region in target.regions[]) so the
 *     collage references in Images-GUI/02-primary-pages/ get per-region
 *     diff classification rather than a single composite verdict.
 *   - same-origin 404 events on each row (count + summary) for cap 4.
 *   - console-error events on each row (count + first 5 messages) for cap 3.
 *   - no-fake hits (count + summary) for cap 5.
 *
 * The schema is additive: rows still carry every W14 field, so downstream
 * consumers (W15-A10's expected-red report, the truth-gate parser) continue
 * to work unmodified.
 *
 * Sources:
 *  1. Playwright reporter API:
 *     https://playwright.dev/docs/api/class-reporter
 *  2. Chromatic / Percy visual-test recipe — region + console + 404 fields:
 *     https://www.chromatic.com/docs/visual-tests/
 *
 * No-fake / no-paid contract:
 *  - Reporter writes one JSON file locally; no telemetry, no remote sink.
 *  - All fields are derived from in-process annotations; nothing is invented.
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
const TARGETS_PATH = path.join(HERE, "visual-targets.json");

interface ManifestTarget {
  target: string;
  reference: string;
  route: string;
  status: "live" | "future";
  tolerance: number;
  notes?: string;
  regions?: { name: string; clip?: unknown; reference?: string; tolerance?: number }[];
}

interface ManifestFile {
  targets: ManifestTarget[];
}

let MANIFEST: Record<string, ManifestTarget> = {};
try {
  const raw = JSON.parse(fs.readFileSync(TARGETS_PATH, "utf-8")) as ManifestFile;
  MANIFEST = Object.fromEntries(raw.targets.map((t) => [t.target, t]));
} catch {
  MANIFEST = {};
}

const SUMMARY_DIR = path.join(
  REPO_ROOT,
  "03_implementation",
  "docs",
  "evidence",
  "visual_proof_2026-05-09",
);
const SUMMARY_PATH = path.join(SUMMARY_DIR, "summary.json");

interface RegionRow {
  region: string;
  status: "match" | "diff" | "missing-baseline" | "error" | "not-run";
  tolerance: number | null;
  diff_pixels?: number;
  ratio?: number;
  reference: string | null;
}

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
  viewport: { width: number; height: number } | null;
  theme: string | null;
  clock_time: string | null;
  diff_pixels?: number;
  total_pixels?: number;
  ratio?: number;
  evidence_path: string | null;
  diff_path: string | null;
  // W15-A9 — new event counts. Always present so consumers can filter.
  console_errors: number;
  console_summary: string;
  network_same_origin_errors: number;
  network_total_errors: number;
  network_summary: string;
  no_fake_hits: number;
  no_fake_summary: string;
  // W15-A9 — region-level rollups. Empty when target has no regions[].
  regions: RegionRow[];
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

/**
 * W18-A14 — Build a synthesized row for a target the spec deliberately
 * skipped over (status:"future" or missing reference PNG). The spec no
 * longer declares-and-skips these targets; the reporter injects rows from
 * the manifest so the JSON summary schema is unchanged.
 */
function synthesizedRow(
  m: ManifestTarget,
  kind: "skipped-future" | "skipped-missing-reference",
  ts: string,
): VisualRow {
  return {
    target: m.target,
    status: kind,
    route: m.route ?? null,
    reference: m.reference ?? null,
    tolerance: typeof m.tolerance === "number" ? m.tolerance : null,
    viewport: null,
    theme: null,
    clock_time: null,
    evidence_path: null,
    diff_path: null,
    console_errors: 0,
    console_summary: "",
    network_same_origin_errors: 0,
    network_total_errors: 0,
    network_summary: "",
    no_fake_hits: 0,
    no_fake_summary: "",
    regions: (m.regions ?? []).map((r) => ({
      region: r.name,
      status: "not-run",
      tolerance:
        typeof r.tolerance === "number"
          ? r.tolerance
          : typeof m.tolerance === "number"
            ? m.tolerance
            : null,
      reference: r.reference ?? m.reference ?? null,
    })),
    error:
      kind === "skipped-future"
        ? m.notes ?? "future"
        : `reference PNG missing at ${m.reference}`,
    started_at: ts,
    finished_at: ts,
  };
}

class VisualProofReporter implements Reporter {
  private rows: VisualRow[] = [];
  // W18-A14 — targets the spec filtered out (status:future or missing ref).
  // Tracked so onTestEnd doesn't double-count if a future Playwright behavior
  // produces a row for the same target name.
  private readonly syntheticTargets = new Set<string>();
  private startedAt: string = "";

  onBegin(_config: FullConfig): void {
    this.startedAt = new Date().toISOString();
    // W18-A14 — inject synthesized rows for the targets that visual-proof.spec.ts
    // now filters out via `continue` (status:"future" or missing reference PNG).
    // The spec used to call `test.skip` on these branches; under the no-skip
    // harness it MUST NOT, so the reporter is responsible for keeping the
    // JSON summary schema additive.
    for (const m of Object.values(MANIFEST)) {
      if (m.status === "future") {
        this.rows.push(synthesizedRow(m, "skipped-future", this.startedAt));
        this.syntheticTargets.add(m.target);
        continue;
      }
      const refAbs = path.resolve(REPO_ROOT, m.reference);
      if (!fs.existsSync(refAbs)) {
        this.rows.push(
          synthesizedRow(m, "skipped-missing-reference", this.startedAt),
        );
        this.syntheticTargets.add(m.target);
      }
    }
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    const annotations = test.annotations.concat(result.annotations ?? []);
    let target: string | null = null;
    let route: string | null = null;
    let reference: string | null = null;
    let tolerance: number | null = null;
    let viewport: { width: number; height: number } | null = null;
    let theme: string | null = null;
    let clockTime: string | null = null;
    let matched = false;
    let regionsRollup: Map<string, RegionRow> = new Map();
    let consoleErrors = 0;
    let consoleSummary = "";
    let networkSameOrigin = 0;
    let networkTotal = 0;
    let networkSummary = "";
    let noFakeHits = 0;
    let noFakeSummary = "";
    let skippedReason: string | null = null;
    let skippedKind: "future" | "missing-reference" | null = null;

    // Extract the target name from the describe title: "visual: <target>".
    // This is the only reliable way to identify a skipped test since the
    // wrapped fn body never runs and our annotations never fire.
    for (const titleSeg of test.titlePath()) {
      const m = /^visual:\s+([\w_-]+)$/.exec(titleSeg.trim());
      if (m) {
        target = m[1];
        break;
      }
    }
    if (target && MANIFEST[target]) {
      const manifest = MANIFEST[target];
      route = route ?? manifest.route;
      reference = reference ?? manifest.reference;
      tolerance = tolerance ?? manifest.tolerance;
      if (manifest.status === "future") {
        skippedKind = "future";
        skippedReason = manifest.notes ?? "future";
      } else {
        const refAbs = path.resolve(REPO_ROOT, manifest.reference);
        if (!fs.existsSync(refAbs)) {
          skippedKind = "missing-reference";
        }
      }
      // Pre-populate region rollups so the row records all expected regions
      // even if the test threw before hitting the loop.
      for (const region of manifest.regions ?? []) {
        regionsRollup.set(region.name, {
          region: region.name,
          status: "not-run",
          tolerance: region.tolerance ?? manifest.tolerance ?? null,
          reference: region.reference ?? manifest.reference,
        });
      }
    }

    for (const ann of annotations) {
      const desc = ann.description ?? "";
      const parsed =
        typeof desc === "string" ? safeJsonParse<Record<string, unknown>>(desc) : null;
      if (!parsed) continue;
      if (typeof parsed.target === "string") target = parsed.target;
      if (typeof parsed.route === "string") route = parsed.route;
      if (typeof parsed.reference === "string") reference = parsed.reference;
      if (typeof parsed.tolerance === "number") tolerance = parsed.tolerance;

      if (ann.type === "visual-proof-target") {
        if (
          parsed.viewport &&
          typeof parsed.viewport === "object" &&
          parsed.viewport !== null
        ) {
          const v = parsed.viewport as { width?: unknown; height?: unknown };
          if (typeof v.width === "number" && typeof v.height === "number") {
            viewport = { width: v.width, height: v.height };
          }
        }
        if (typeof parsed.theme === "string") theme = parsed.theme;
        if (typeof parsed.clock_time === "string") clockTime = parsed.clock_time;
      }

      if (ann.type === "visual-proof-result" && parsed.status === "match") {
        matched = true;
      }

      if (ann.type === "visual-proof-region-result") {
        const regionName = typeof parsed.region === "string" ? parsed.region : null;
        if (regionName) {
          const existing = regionsRollup.get(regionName) ?? {
            region: regionName,
            status: "not-run" as RegionRow["status"],
            tolerance:
              typeof parsed.tolerance === "number" ? parsed.tolerance : null,
            reference: null,
          };
          existing.status = parsed.status === "match" ? "match" : "diff";
          if (typeof parsed.tolerance === "number") existing.tolerance = parsed.tolerance;
          regionsRollup.set(regionName, existing);
        }
      }

      if (ann.type === "visual-proof-console") {
        if (typeof parsed.errors === "number") consoleErrors = parsed.errors;
        if (typeof parsed.summary === "string") consoleSummary = parsed.summary;
      }

      if (ann.type === "visual-proof-network") {
        if (typeof parsed.same_origin_errors === "number")
          networkSameOrigin = parsed.same_origin_errors;
        if (typeof parsed.total_errors === "number")
          networkTotal = parsed.total_errors;
        if (typeof parsed.summary === "string") networkSummary = parsed.summary;
      }

      if (ann.type === "visual-proof-no-fake") {
        if (typeof parsed.hits === "number") noFakeHits = parsed.hits;
        if (typeof parsed.summary === "string") noFakeSummary = parsed.summary;
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

    // W18-A14 — if onBegin already synthesized a row for this target
    // (status:"future" or missing reference), don't double-push. Under the
    // no-skip harness the spec filters these targets out before declaring
    // any test, so this branch should only ever fire if a future spec
    // change starts producing test cases for them again.
    if (this.syntheticTargets.has(target)) {
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

    for (const att of result.attachments ?? []) {
      if (!att.name) continue;
      if (/expected/.test(att.name) && att.path) {
        // The expected image is the reference PNG itself.
      } else if (/actual/.test(att.name) && att.path) {
        evidencePath = path.relative(REPO_ROOT, att.path).replace(/\\/g, "/");
      } else if (/diff/.test(att.name) && att.path) {
        diffPath = path.relative(REPO_ROOT, att.path).replace(/\\/g, "/");
      }
    }

    if (result.status === "failed" || result.status === "timedOut") {
      const msg = result.error?.message ?? "";
      errorMessage = msg.split("\n").slice(0, 2).join(" ").slice(0, 600);
      const pixMatch = msg.match(/(\d+)\s+pixels?\s+\(ratio\s+([0-9.]+)/i);
      if (pixMatch) {
        diffPixels = Number(pixMatch[1]);
        ratio = Number(pixMatch[2]);
      }
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
      viewport,
      theme,
      clock_time: clockTime,
      diff_pixels: diffPixels,
      total_pixels: totalPixels,
      ratio,
      evidence_path: evidencePath,
      diff_path: diffPath,
      console_errors: consoleErrors,
      console_summary: consoleSummary,
      network_same_origin_errors: networkSameOrigin,
      network_total_errors: networkTotal,
      network_summary: networkSummary,
      no_fake_hits: noFakeHits,
      no_fake_summary: noFakeSummary,
      regions: Array.from(regionsRollup.values()).sort((a, b) =>
        a.region.localeCompare(b.region),
      ),
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

    // W15-A9 — additional rollups so the summary is actionable without
    // post-processing.
    const gateCounts = this.rows.reduce(
      (acc, row) => {
        acc.console_error_targets += row.console_errors > 0 ? 1 : 0;
        acc.network_4xx_targets += row.network_same_origin_errors > 0 ? 1 : 0;
        acc.no_fake_targets += row.no_fake_hits > 0 ? 1 : 0;
        acc.targets_with_regions += row.regions.length > 0 ? 1 : 0;
        return acc;
      },
      {
        console_error_targets: 0,
        network_4xx_targets: 0,
        no_fake_targets: 0,
        targets_with_regions: 0,
      },
    );

    const summary = {
      schema_version: 2,
      generated_at: new Date().toISOString(),
      started_at: this.startedAt,
      run_status: result.status,
      owner: "claude-w15-a9-oracle",
      lane: "W15-A9 Playwright Oracle Builder (9 capabilities)",
      counts,
      gate_counts: gateCounts,
      rows: this.rows.sort((a, b) => a.target.localeCompare(b.target)),
    };

    fs.writeFileSync(SUMMARY_PATH, JSON.stringify(summary, null, 2) + "\n");
    const summaryLine =
      `[visual-proof] total=${counts.total} ` +
      Object.entries(counts)
        .filter(([k]) => k !== "total")
        .map(([k, v]) => `${k}=${v}`)
        .join(" ");
    process.stdout.write(`${summaryLine}\n`);
    process.stdout.write(
      `[visual-proof] gate-fails: console=${gateCounts.console_error_targets} ` +
        `network=${gateCounts.network_4xx_targets} no-fake=${gateCounts.no_fake_targets}\n`,
    );
    process.stdout.write(`[visual-proof] summary written to ${SUMMARY_PATH}\n`);
  }
}

export default VisualProofReporter;
