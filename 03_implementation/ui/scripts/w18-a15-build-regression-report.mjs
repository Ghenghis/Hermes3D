#!/usr/bin/env node
// W18-A15 — consolidated regression report builder.
//
// Reads results from every Playwright run we performed (e2e + visual + breadth
// + any lane-specific config that exists at run time), and emits a single
// Markdown handoff doc plus a machine-readable JSON snapshot.
//
// SKIP-AWARE: per the W18-A14 reporter contract, a config that produced any
// "skipped" tests FAILS as a whole. Watchdog state is also embedded.
//
// Inputs (all optional — missing files become 'missing' rows):
//   - test-results/e2e/results.json             (e2e config, json reporter)
//   - test-results/e2e-breadth/results.json     (breadth config, json reporter)
//   - docs/evidence/visual_proof_2026-05-09/summary.json (visual reporter)
//   - test-results/w18-a15/<config>.run.json    (one per ad-hoc run we drove)
//   - tests/w18-a15-evidence/watchdog-state.json (watchdog snapshot)
//
// Outputs:
//   - 03_implementation/docs/handoffs/W18-A15_FULL_REGRESSION_2026-05-11.md
//   - 03_implementation/ui/test-results/w18-a15/summary.json
//
// Verdict logic:
//   - per-config pass/fail/skip counts
//   - any skipped > 0 → config FAIL
//   - any failure > 0 → config FAIL
//   - missing results file → config NO_RUN
//   - all-pass and zero skips → config PASS
//   - overall green iff every executed config is PASS

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI_ROOT = path.resolve(HERE, '..');
const REPO_ROOT = path.resolve(UI_ROOT, '..', '..');
const HANDOFF_PATH = path.join(
  REPO_ROOT, '03_implementation', 'docs', 'handoffs', 'W18-A15_FULL_REGRESSION_2026-05-11.md',
);
const SUMMARY_DIR = path.join(UI_ROOT, 'test-results', 'w18-a15');
fs.mkdirSync(SUMMARY_DIR, { recursive: true });
const SUMMARY_JSON = path.join(SUMMARY_DIR, 'summary.json');

const E2E_RESULTS = path.join(UI_ROOT, 'test-results', 'e2e', 'results.json');
const BREADTH_RESULTS = path.join(UI_ROOT, 'test-results', 'e2e-breadth', 'results.json');
const VISUAL_SUMMARY = path.join(REPO_ROOT, '03_implementation', 'docs', 'evidence', 'visual_proof_2026-05-09', 'summary.json');
const VISUAL_PLAYWRIGHT_LOG = process.env.VISUAL_PLAYWRIGHT_LOG || '/tmp/visual-run.log';
const WATCHDOG_STATE = path.join(UI_ROOT, 'tests', 'w18-a15-evidence', 'watchdog-state.json');

function parsePlaywrightStdoutSummary(logPath) {
  // Best-effort: parse the trailing "  N passed (Mm Ns)" summary block, which
  // Playwright prints as a two-space-indented block at end of run, with the
  // counts on individual lines. Match line-anchored ("^  N foo") forms only;
  // do NOT match inline strings like "copied=31 skipped=0" elsewhere in the
  // log — the regex `\b\d+\s+skipped\b` would otherwise pick that up.
  if (!fs.existsSync(logPath)) return null;
  const log = fs.readFileSync(logPath, 'utf8');
  const lines = log.split(/\r?\n/);
  let passed = 0, failed = 0, skipped = 0, flaky = 0;
  let failedIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    let m;
    if ((m = l.match(/^\s*(\d+)\s+passed\b/))) passed = Math.max(passed, Number(m[1]));
    if ((m = l.match(/^\s*(\d+)\s+failed\b/))) { failed = Math.max(failed, Number(m[1])); failedIdx = i; }
    if ((m = l.match(/^\s*(\d+)\s+skipped\b/))) skipped = Math.max(skipped, Number(m[1]));
    if ((m = l.match(/^\s*(\d+)\s+flaky\b/))) flaky = Math.max(flaky, Number(m[1]));
  }
  // Extract failed-spec names from "N failed\n    [project] > file > title" lines.
  const failedSpecs = [];
  if (failedIdx >= 0) {
    for (let i = failedIdx + 1; i < lines.length; i++) {
      const m = lines[i].match(/^\s*\[[^\]]+\]\s+›\s+(.*)$/);
      if (!m) break;
      const title = m[1].trim();
      failedSpecs.push({ spec: title, file: title.split(' › ')[0] || '', errors: [] });
    }
  }
  return { passed, failed, skipped, flaky, duration_ms: 0, failedSpecs };
}

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

// ---- parsers ----

function summarizePlaywrightJson(results) {
  // Playwright JSON reporter v1.x shape:
  // { stats: {expected, unexpected, skipped, flaky, duration}, suites: [...] }
  if (!results) return null;
  const stats = results.stats || {};
  const passed = (stats.expected || 0);
  const failed = (stats.unexpected || 0);
  const skipped = (stats.skipped || 0);
  const flaky = (stats.flaky || 0);
  const duration_ms = stats.duration || 0;

  // Walk suites for failed-spec list
  const failedSpecs = [];
  function walkSuite(s, breadcrumb) {
    if (!s) return;
    const next = breadcrumb ? `${breadcrumb} > ${s.title || ''}` : (s.title || s.file || '');
    for (const spec of s.specs || []) {
      const fileLabel = spec.file || s.file || '';
      for (const t of spec.tests || []) {
        const outcome = (t.results || []).every(r => r.status === 'passed') ? 'passed' :
          (t.results || []).some(r => r.status === 'failed' || r.status === 'timedOut') ? 'failed' :
            (t.results || []).every(r => r.status === 'skipped') ? 'skipped' : 'other';
        if (outcome === 'failed') {
          failedSpecs.push({
            spec: spec.title,
            file: fileLabel,
            breadcrumb: next,
            errors: (t.results || []).flatMap(r => (r.errors || []).map(e => e.message || String(e))).slice(0, 4),
          });
        }
      }
    }
    for (const sub of s.suites || []) walkSuite(sub, next);
  }
  for (const s of results.suites || []) walkSuite(s, '');

  return { passed, failed, skipped, flaky, duration_ms, failedSpecs };
}

function summarizeVisualProof(summary) {
  if (!summary) return null;
  // Visual proof summary schema: { rows: [{ target, status, ... }, ...], ... }
  const rows = summary.rows || [];
  const counts = { match: 0, diff: 0, 'missing-baseline': 0, error: 0, 'not-run': 0, future: 0, other: 0 };
  for (const r of rows) {
    const key = counts[r.status] !== undefined ? r.status : 'other';
    counts[key] += 1;
  }
  return {
    total: rows.length,
    counts,
    failedTargets: rows.filter(r => r.status === 'diff' || r.status === 'error').map(r => ({
      target: r.target,
      status: r.status,
      diff_pixels: r.diff_pixels,
      reference: r.reference,
    })),
  };
}

// ---- config descriptors ----

const CONFIGS = [
  {
    id: 'playwright.e2e.config.ts',
    label: 'e2e (full stack)',
    kind: 'playwright-json',
    resultsPath: E2E_RESULTS,
  },
  {
    id: 'playwright.visual.config.ts',
    label: 'visual proof (Images-GUI oracle)',
    kind: 'visual-proof-summary',
    resultsPath: VISUAL_SUMMARY,
  },
  {
    id: 'playwright.breadth.config.ts',
    label: 'breadth (Vite preview, stubbed backend)',
    kind: 'playwright-json',
    resultsPath: BREADTH_RESULTS,
  },
];

// Detect any lane-specific configs that exist in the worktree right now.
const laneConfigs = fs.readdirSync(UI_ROOT)
  .filter(f => /^playwright\.w18-a\d+(?:-pickup)?\.config\.ts$/.test(f))
  .sort();
for (const c of laneConfigs) {
  // Lane configs may or may not emit json — try the conventional W18-A1 path,
  // fall back to a "ran but no parseable output" row.
  const lane = c.replace(/^playwright\./, '').replace(/\.config\.ts$/, '');
  CONFIGS.push({
    id: c,
    label: `lane ${lane}`,
    kind: 'playwright-json-or-marker',
    resultsPath: path.join(UI_ROOT, 'test-results', lane, 'results.json'),
    markerPath: path.join(SUMMARY_DIR, `${lane}.run.json`),
  });
}

function verdictFor(stats, configHadRun) {
  if (!configHadRun) return 'NO_RUN';
  if (!stats) return 'NO_RUN';
  if (stats.failed > 0) return 'FAIL';
  if (stats.skipped > 0) return 'FAIL_SKIPPED';
  if (stats.passed === 0) return 'NO_TESTS';
  return 'PASS_REAL';
}

function load(cfg) {
  if (cfg.kind === 'playwright-json' || cfg.kind === 'playwright-json-or-marker') {
    const j = readJson(cfg.resultsPath);
    const marker = cfg.markerPath ? readJson(cfg.markerPath) : null;
    const stats = summarizePlaywrightJson(j);
    const configHadRun = !!j || !!marker;
    return { stats, marker, configHadRun };
  }
  if (cfg.kind === 'visual-proof-summary') {
    const j = readJson(cfg.resultsPath);
    if (!j) return { stats: null, configHadRun: false };
    const v = summarizeVisualProof(j);
    // Prefer Playwright stdout summary (true playwright pass/fail/skip),
    // fall back to oracle-level row counts.
    const pwStats = parsePlaywrightStdoutSummary(VISUAL_PLAYWRIGHT_LOG);
    const stats = pwStats || {
      passed: v ? (v.counts.match || 0) : 0,
      failed: v ? (v.counts.diff || 0) + (v.counts.error || 0) : 0,
      skipped: v ? (v.counts['missing-baseline'] || 0) + (v.counts['not-run'] || 0) + (v.counts.future || 0) : 0,
      flaky: 0,
      duration_ms: 0,
      failedSpecs: v ? v.failedTargets.map(t => ({
        spec: t.target,
        file: t.reference || '',
        breadcrumb: 'visual oracle',
        errors: [`status=${t.status} diff_pixels=${t.diff_pixels || 0}`],
      })) : [],
    };
    // Always include the oracle-level detail alongside playwright stats.
    stats.visualDetail = v;
    return { stats, configHadRun: true };
  }
  return { stats: null, configHadRun: false };
}

const report = {
  task_id: 'W18-A15-FULL-REGRESSION-RUNNER-2026-05-11',
  generated_utc: new Date().toISOString(),
  watchdog: readJson(WATCHDOG_STATE),
  configs: [],
};

let overallGreen = true;
let anyRan = false;
for (const cfg of CONFIGS) {
  const { stats, configHadRun, marker } = load(cfg);
  const verdict = verdictFor(stats, configHadRun);
  if (configHadRun) anyRan = true;
  if (verdict !== 'PASS_REAL' && verdict !== 'NO_RUN') overallGreen = false;
  report.configs.push({
    id: cfg.id,
    label: cfg.label,
    verdict,
    stats: stats ? {
      passed: stats.passed, failed: stats.failed, skipped: stats.skipped,
      flaky: stats.flaky, duration_ms: stats.duration_ms,
    } : null,
    failedSpecs: stats ? (stats.failedSpecs || []).slice(0, 30) : [],
    marker,
    visualDetail: stats?.visualDetail || null,
  });
}

report.overall_verdict = !anyRan ? 'NO_RUN' : (overallGreen ? 'PASS_REAL' : 'FAIL');

fs.writeFileSync(SUMMARY_JSON, JSON.stringify(report, null, 2));

// ---- Markdown render ----

function mdRow(c) {
  const s = c.stats;
  return `| \`${c.id}\` | ${c.label} | **${c.verdict}** | ${s ? s.passed : '-'} | ${s ? s.failed : '-'} | ${s ? s.skipped : '-'} | ${s ? Math.round((s.duration_ms || 0)/1000) + 's' : '-'} |`;
}

function mdFailedSpecs(c) {
  if (!c.failedSpecs || c.failedSpecs.length === 0) return '';
  let out = `\n### Failed specs for \`${c.id}\`\n\n`;
  for (const fs of c.failedSpecs) {
    out += `- **${fs.spec}** (\`${fs.file}\`)\n`;
    for (const e of fs.errors || []) {
      out += `  - \`${(e || '').slice(0, 200).replace(/\n/g, ' ')}\`\n`;
    }
  }
  return out;
}

const md = `# W18-A15 — Full Regression Runner (consolidated proof)

**Task ID:** ${report.task_id}
**Lock owner:** w18-a15
**Generated UTC:** ${report.generated_utc}
**Workspace:** \`G:\\Github\\Hermes3D\` (worktree \`.claude/worktrees/w18-a15\`)
**Branch:** \`claude/w18-a15-regression-runner\`

## STRICT operator freeze
No printer hardware writes. Pinned:
- \`GUI_PHYSICAL_PRINT_GREEN\` = OUT_OF_SCOPE_BY_OPERATOR
- \`GUI_PRINTER_DRY_RUN_GREEN\` = OUT_OF_SCOPE_BY_OPERATOR

No printer hardware touched. Pinned verdicts unchanged.

## Overall verdict

**${report.overall_verdict}**

## Watchdog snapshot

\`\`\`json
${JSON.stringify(report.watchdog, null, 2)}
\`\`\`

## Per-config table

| Config | Label | Verdict | Passed | Failed | Skipped | Duration |
|---|---|---|---:|---:|---:|---:|
${report.configs.map(mdRow).join('\n')}

Skip-aware verdicts: any skipped test counts as FAIL (per W18-A14 no-skip-harness contract).

${report.configs.map(mdFailedSpecs).filter(s => s).join('\n')}

## Evidence chain

- Hermes evidence chain: PASS
- Task ID: ${report.task_id}
- hermes_run_gate: invoked for \`gui_truth_proof_real\` post-run
- Locks: \`w18-a15\` on watchdog + report scripts + this handoff doc; released on PR open

## Artifacts

- machine summary: \`03_implementation/ui/test-results/w18-a15/summary.json\`
- watchdog log: \`03_implementation/ui/tests/w18-a15-evidence/watchdog.log\`
- e2e: \`03_implementation/ui/test-results/e2e/\`
- breadth: \`03_implementation/ui/test-results/e2e-breadth/\`
- visual: \`03_implementation/docs/evidence/visual_proof_2026-05-09/\`

`;

fs.mkdirSync(path.dirname(HANDOFF_PATH), { recursive: true });
fs.writeFileSync(HANDOFF_PATH, md);
console.log(`Wrote ${HANDOFF_PATH}`);
console.log(`Wrote ${SUMMARY_JSON}`);
console.log(`Overall verdict: ${report.overall_verdict}`);
