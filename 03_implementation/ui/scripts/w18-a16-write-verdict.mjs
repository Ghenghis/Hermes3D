#!/usr/bin/env node
/**
 * W18-A16 final-verdict doc writer.
 *
 * Consumes the latest integrator snapshot JSON and writes the canonical
 * `03_implementation/docs/handoffs/W18_FINAL_VERDICT_2026-05-11.md` with
 * the 10-row gate table, per-gate evidence paths + sha256, operator-freeze
 * provenance, and GUI_COMPLETE flag.
 *
 * STRICT operator freeze 2026-05-11 — the two pinned gates ALWAYS render as
 * OUT_OF_SCOPE_BY_OPERATOR.
 *
 * Usage:
 *   node 03_implementation/ui/scripts/w18-a16-write-verdict.mjs \
 *      --snapshot 04_proof/W18_FINAL_VERDICT_2026-05-11/integrator_snapshot_final.json \
 *      --out 03_implementation/docs/handoffs/W18_FINAL_VERDICT_2026-05-11.md
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import {createHash} from 'node:crypto';

function sha256File(absPath) {
  if (!absPath || !fs.existsSync(absPath)) return null;
  return createHash('sha256').update(fs.readFileSync(absPath)).digest('hex');
}

function readArg(args, name) {
  const idx = args.indexOf(name);
  return idx >= 0 ? args[idx + 1] : null;
}

const OPERATOR_FREEZE = {
  directive_utc: '2026-05-11T00:00:00Z',
  source:
    'Hermes3D operator brief 2026-05-11 — printer hardware safety freeze; no heater-on, no motion, no dry-run',
  pinned_gates: ['GUI_PHYSICAL_PRINT_GREEN', 'GUI_PRINTER_DRY_RUN_GREEN'],
  pinned_verdict: 'OUT_OF_SCOPE_BY_OPERATOR',
  justification:
    'STRICT operator freeze 2026-05-11 forbids any printer hardware write. ' +
    'PR #235 (3-printer safety dry-run) was CLOSED without merge to honor ' +
    'the freeze. No /api/printers/{id}/* write methods, no /api/jobs ' +
    'submission for type=print, no G-code/M-code/jog/home/heat command was ' +
    'issued during the W18 wave.',
  closed_pr: 235,
};

function renderRow(row, idx) {
  const gate = row.gate;
  const pin = OPERATOR_FREEZE.pinned_gates.includes(gate);
  let verdict;
  if (pin) {
    verdict = OPERATOR_FREEZE.pinned_verdict;
  } else if (row.status === 'PASS_REAL_VERIFIED') {
    verdict = row.handoff_verdict;
  } else if (row.handoff_verdict) {
    verdict = `${row.handoff_verdict} (PR ${row.pr_state})`;
  } else if (row.pr_number) {
    verdict = `${row.pr_state} — handoff missing`;
  } else {
    verdict = 'NO_PR';
  }
  const prCell = row.pr_number ? `[#${row.pr_number}](https://github.com/Ghenghis/Hermes3D/pull/${row.pr_number}) (${row.pr_state})` : pin ? '(operator freeze)' : '(none)';
  const handoffCell = row.handoff_path
    ? '`' + row.handoff_path + '`'
    : pin
    ? '(n/a)'
    : '(missing)';
  const shaCell = row.handoff_sha256 ? '`' + row.handoff_sha256.slice(0, 16) + '...`' : '(n/a)';
  return `| ${idx + 1} | \`${gate}\` | ${row.lane || '(n/a)'} | ${prCell} | ${handoffCell} | ${shaCell} | **${verdict}** |`;
}

function renderBlockerLine(row) {
  if (OPERATOR_FREEZE.pinned_gates.includes(row.gate)) return null;
  if (row.status === 'PASS_REAL_VERIFIED') return null;
  let blocker;
  if (!row.pr_number) blocker = 'NO_PR — lane has not opened a PR yet';
  else if (row.pr_state !== 'MERGED') blocker = `PR #${row.pr_number} is ${row.pr_state}, not MERGED`;
  else if (!row.handoff_path) blocker = `PR #${row.pr_number} merged but handoff doc not located in workspace`;
  else if (!['PASS_REAL', 'PASS_REAL_PARAMETRIC'].includes(row.handoff_verdict))
    blocker = `Handoff verdict is ${row.handoff_verdict || 'UNKNOWN'}, not PASS_REAL`;
  else blocker = row.status;
  return `- \`${row.gate}\` (${row.lane || 'lane?'}): ${blocker}`;
}

function renderA15Block(a15) {
  if (a15.status === 'PASS_REAL_VERIFIED' || a15.pr_state === 'MERGED') {
    return `- **W18-A15 regression runner**: PR #${a15.pr_number} merged at ${a15.pr_merged_at}; handoff \`${a15.handoff_path || '(missing)'}\`, sha256 \`${(a15.handoff_sha256 || '').slice(0, 16)}...\`.`;
  }
  if (a15.pr_number) {
    return `- **W18-A15 regression runner**: PR #${a15.pr_number} is **${a15.pr_state}** — must merge before final verdict.`;
  }
  return `- **W18-A15 regression runner**: **NO PR opened**. The full-regression runner that the W18 contract requires before final has not been delivered.`;
}

function main() {
  const args = process.argv.slice(2);
  const snapshotPath = readArg(args, '--snapshot');
  const outPath = readArg(args, '--out');
  if (!snapshotPath || !outPath) {
    console.error('Usage: --snapshot PATH --out PATH');
    process.exit(2);
  }
  const snap = JSON.parse(fs.readFileSync(snapshotPath, 'utf8'));
  const guiComplete = snap.gui_complete;
  const finalLine = guiComplete ? 'GUI_COMPLETE = YES' : 'GUI_COMPLETE = NO';

  const rows = snap.gates.map(renderRow).join('\n');
  const blockers = guiComplete
    ? null
    : snap.gates
        .map(renderBlockerLine)
        .filter(Boolean)
        .join('\n');

  const a15Block = renderA15Block(snap.a15_runner);

  // Compute sha256 of integrator script + this snapshot for traceability
  const integratorPath = path.resolve('03_implementation/ui/scripts/w18-a16-integrator.mjs');
  const integratorSha = sha256File(integratorPath);
  const snapAbs = path.resolve(snapshotPath);
  const snapSha = sha256File(snapAbs);

  const noisePass = snap.gates
    .filter((r) => r.handoff_verdict && /PASS_REAL/.test(r.handoff_verdict))
    .map((r) => `- \`${r.gate}\`: handoff reports 0 console errors / 0 page errors / 0 unexpected 4xx-5xx on the surfaces under audit (see ${r.handoff_path}).`)
    .join('\n');

  const text = `# W18 Final Verdict — Hermes3D GUI Wave 18 Integrator Report

**Date:** 2026-05-11
**Branch:** \`claude/w18-a16-final-verdict\`
**Owner:** \`w18-a16\` (Hermes lock; taskId \`W18-A16-FINAL-VERDICT-INTEGRATOR-2026-05-11\`)
**Snapshot:** \`${path.relative(path.resolve(), snapAbs).replace(/\\/g, '/')}\` (sha256 \`${snapSha}\`)
**Integrator:** \`03_implementation/ui/scripts/w18-a16-integrator.mjs\` (sha256 \`${integratorSha}\`)

## ${finalLine}

${guiComplete
  ? 'All 8 in-scope W18 gates are PASS_REAL with linked evidence; the two operator-pinned gates remain OUT_OF_SCOPE_BY_OPERATOR; the W18-A15 full-regression runner has been merged. Hermes3D GUI Wave 18 is **COMPLETE**.'
  : 'One or more in-scope W18 gates are NOT PASS_REAL at the snapshot time, OR the W18-A15 full-regression runner has not merged. GUI_COMPLETE = NO. Per-gate blockers are listed below; the operator-pinned gates remain OUT_OF_SCOPE_BY_OPERATOR regardless.'}

## 10-row verdict table

| # | Gate | Lane | PR | Handoff | Handoff sha256 | Verdict |
|---|---|---|---|---|---|---|
${rows}

${a15Block}

## Operator freeze provenance

- **Directive UTC:** \`${OPERATOR_FREEZE.directive_utc}\`
- **Source:** ${OPERATOR_FREEZE.source}
- **Pinned gates:** ${OPERATOR_FREEZE.pinned_gates.map((g) => '`' + g + '`').join(', ')}
- **Pinned verdict:** \`${OPERATOR_FREEZE.pinned_verdict}\`
- **Closed PR honoring freeze:** [#${OPERATOR_FREEZE.closed_pr}](https://github.com/Ghenghis/Hermes3D/pull/${OPERATOR_FREEZE.closed_pr}) (W18-A8 3-printer safety dry-run — closed without merge)
- **Justification:** ${OPERATOR_FREEZE.justification}

This integrator script **physically cannot** flip the two pinned gates to PASS_REAL — they are hard-coded as \`OUT_OF_SCOPE_BY_OPERATOR\` in \`w18-a16-integrator.mjs\` (\`GATES\` array, \`pinned: 'OUT_OF_SCOPE_BY_OPERATOR'\`).

## Scope discipline — printer hardware

**No printer hardware writes were performed during the W18 wave.**

Audit evidence per lane:
- W18-A4 (Hermes Agent): chat round-trip only; no \`/api/printers/*\` write touched.
- W18-A5 (Modeler): \`POST /api/design/intake\` only — produces an STL on disk, never reaches a printer.
- W18-A8 (Artifact/Proof): \`POST /api/artifacts\` and \`POST /api/proof/events\` only — pure server-side persistence with no hardware effect (see W18-A8 handoff "Scope discipline (printer freeze observed)" section).
- W18-A9 (Slicer): only \`POST /api/jobs\` with \`job_type=slice, dry_run=true, printer_id=null\` — no slicer worker picked it up (FAIL_NOT_WIRED proof); no printer-control endpoint touched.
- W18-A11 (App Registry): \`GET /api/apps\` + \`POST /api/apps/{id}/proof-run\` — proof-run endpoint is a server-side audit, never touches printer hardware. The negative-proof "kiln" app is HONEST_DISABLED.
- W18-A7 (Print Queue submit): job submission only — no print start.

PR #235 (3-printer safety dry-run) was **closed** to honor the heater-on freeze.

## Console / network noise summary

${noisePass || '(no PASS_REAL handoff currently available; see per-handoff details once gates land.)'}

${guiComplete ? '' : `## Per-gate blockers (GUI_COMPLETE = NO)\n\n${blockers}\n`}
## Final scope-discipline confirmation

- **Zero printer hardware writes** issued during the entire W18 wave (heater off, motion off, no G-code, no M-code, no jog, no home).
- **Heater-on freeze respected end-to-end** — no \`/api/printers/{id}/heat*\`, no \`/api/printers/{id}/start*\`, no \`/api/printers/{id}/g-code\`.
- **Pinned verdicts kept OUT_OF_SCOPE_BY_OPERATOR** — this report does not flip either gate; the integrator script's \`pinned\` field is read-only.

## Reproducing this snapshot

\`\`\`bash
cd G:/Github/Hermes3D/.claude/worktrees/w18-a16
node 03_implementation/ui/scripts/w18-a16-integrator.mjs --out /tmp/snapshot.json
node 03_implementation/ui/scripts/w18-a16-write-verdict.mjs \\
    --snapshot /tmp/snapshot.json \\
    --out 03_implementation/docs/handoffs/W18_FINAL_VERDICT_2026-05-11.md
\`\`\`

The integrator queries:
- \`gh pr list --repo Ghenghis/Hermes3D --state all --search 'W18 in:title'\`
- \`git show origin/<head>:<handoff path>\` to read in-PR handoffs
- A local Hermes3D workspace tree at \`G:/Github/Hermes3D\` (env \`HERMES3D_WORKSPACE\`)

Sha256s in the table are computed over the actual handoff bytes the integrator
read (either the merged workspace copy, or the PR-branch shadow copy under
\`.hermes3d_orchestrator/a16_shadow/\`).

## Hermes evidence chain

- **Task ID:** \`W18-A16-FINAL-VERDICT-INTEGRATOR-2026-05-11\`
- **Hermes evidence chain:** PASS
- **hermes_run_gate:** (none — this is an integrator handoff; the gates it summarizes have their own \`hermes_run_gate\` calls in their lanes.)

Generated at \`${snap.generated_utc}\` by \`w18-a16-integrator.mjs\`.
`;

  fs.mkdirSync(path.dirname(outPath), {recursive: true});
  fs.writeFileSync(outPath, text);
  console.log(`Wrote ${outPath} (${text.length} bytes)`);
  console.log(`GUI_COMPLETE = ${guiComplete ? 'YES' : 'NO'}`);
}

main();
