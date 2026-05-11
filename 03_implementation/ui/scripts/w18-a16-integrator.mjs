#!/usr/bin/env node
/**
 * W18-A16 final verdict integrator (read-only).
 *
 * Polls W18 PRs + reads merged handoff docs and prints a JSON status for the
 * 10 in-scope gates plus the W18-A15 regression-runner prerequisite.
 *
 * STRICT operator freeze (2026-05-11):
 *   - GUI_PHYSICAL_PRINT_GREEN and GUI_PRINTER_DRY_RUN_GREEN MUST remain
 *     OUT_OF_SCOPE_BY_OPERATOR; this script never marks them PASS_REAL.
 *
 * Usage:
 *   node 03_implementation/ui/scripts/w18-a16-integrator.mjs [--out PATH]
 */
import {execFileSync, execSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import {fileURLToPath} from 'node:url';

const REPO = 'Ghenghis/Hermes3D';
const WORKSPACE = process.env.HERMES3D_WORKSPACE || 'G:\\Github\\Hermes3D';

// gate -> PR-search + expected handoff path (relative to repo root)
const GATES = [
  {
    id: 'GUI_ROUTE_E2E_GREEN',
    lane: 'W18-A1-pickup',
    titleMatch: /W18-A1.*(pickup|route)/i,
    expectedHandoff: '03_implementation/docs/handoffs/W18-A1_FULL_PRODUCT_ROUTE_WALKER_2026-05-11.md',
    altHandoff: '03_implementation/docs/handoffs/W18-A1_PICKUP_2026-05-11.md',
    expectedVerdicts: ['PASS_REAL'],
  },
  {
    id: 'GUI_BACKEND_WIRING_GREEN',
    lane: 'W18-A13',
    titleMatch: /W18-A13/i,
    expectedHandoff: '03_implementation/docs/handoffs/W18-A13_BACKEND_WIRING_FIXES_2026-05-11.md',
    expectedVerdicts: ['PASS_REAL'],
  },
  {
    id: 'GUI_AGENT_WORKFLOW_GREEN',
    lane: 'W18-A4',
    prNumber: 232,
    titleMatch: /W18-A4/i,
    expectedHandoff: '03_implementation/docs/handoffs/W18-A4_HERMES_AGENT_WORKFLOW_2026-05-11.md',
    expectedVerdicts: ['PASS_REAL'],
  },
  {
    id: 'GUI_60_APPS_GREEN',
    lane: 'W18-A11',
    prNumber: 240,
    titleMatch: /W18-A11/i,
    expectedHandoff: '03_implementation/docs/handoffs/W18-A11_APP_REGISTRY_REAL_DATA_2026-05-11.md',
    expectedVerdicts: ['PASS_REAL'],
  },
  {
    id: 'GUI_MODELER_GREEN',
    lane: 'W18-A5',
    prNumber: 237,
    titleMatch: /W18-A5/i,
    expectedHandoff: '03_implementation/docs/handoffs/W18-A5_MODELER_WORKFLOW_2026-05-11.md',
    expectedVerdicts: ['PASS_REAL', 'PASS_REAL_PARAMETRIC'],
  },
  {
    id: 'GUI_SLICER_GREEN',
    lane: 'W18-A9',
    prNumber: 239,
    titleMatch: /W18-A9/i,
    expectedHandoff: '03_implementation/docs/handoffs/W18-A9_SLICER_REAL_ARTIFACT_2026-05-11.md',
    expectedVerdicts: ['PASS_REAL'],
  },
  {
    id: 'GUI_ARTIFACT_PROOF_GREEN',
    lane: 'W18-A8',
    prNumber: 238,
    titleMatch: /W18-A8.*Artifact/i,
    expectedHandoff: '03_implementation/docs/handoffs/W18-A8_ARTIFACT_FILE_PROOF_2026-05-11.md',
    expectedVerdicts: ['PASS_REAL'],
  },
  {
    id: 'GUI_PIXEL_E2E_GREEN',
    lane: 'W18-A10-pickup',
    titleMatch: /W18-A10.*pickup/i,
    altMatch: /W18-A10/i,
    expectedHandoff: '03_implementation/docs/handoffs/W18-A10_PICKUP_2026-05-11.md',
    altHandoff: '03_implementation/docs/handoffs/W18-A10_VISUAL_ORACLE_EXPANSION_2026-05-11.md',
    expectedVerdicts: ['PASS_REAL'],
  },
  // Pinned out-of-scope by operator freeze
  {
    id: 'GUI_PHYSICAL_PRINT_GREEN',
    lane: '(operator freeze)',
    pinned: 'OUT_OF_SCOPE_BY_OPERATOR',
    justification:
      'STRICT operator freeze 2026-05-11: no printer hardware writes; heater-on freeze respected.',
  },
  {
    id: 'GUI_PRINTER_DRY_RUN_GREEN',
    lane: '(operator freeze)',
    pinned: 'OUT_OF_SCOPE_BY_OPERATOR',
    justification:
      'STRICT operator freeze 2026-05-11: dry-run also forbidden until operator lifts freeze (PR #235 closed without merge).',
  },
];

const A15_PRECONDITION = {
  id: 'W18-A15',
  lane: 'W18-A15-regression-runner',
  titleMatch: /W18-A15/i,
  expectedHandoff: '03_implementation/docs/handoffs/W18-A15_REGRESSION_RUNNER_2026-05-11.md',
};

function gh(args) {
  return execFileSync('gh', args, {encoding: 'utf8', maxBuffer: 32 * 1024 * 1024});
}

function listW18Prs() {
  const out = gh([
    'pr',
    'list',
    '--repo',
    REPO,
    '--state',
    'all',
    '--search',
    'W18 in:title',
    '--json',
    'number,title,state,mergedAt,headRefName,baseRefName,url',
    '--limit',
    '100',
  ]);
  return JSON.parse(out);
}

function sha256OfFile(absPath) {
  if (!fs.existsSync(absPath)) return null;
  const buf = fs.readFileSync(absPath);
  return createHash('sha256').update(buf).digest('hex');
}

function readMaybe(absPath) {
  return fs.existsSync(absPath) ? fs.readFileSync(absPath, 'utf8') : null;
}

function gitShow(ref, repoPath, relPath) {
  try {
    return execFileSync('git', ['-C', repoPath, 'show', `${ref}:${relPath}`], {
      encoding: 'utf8',
      maxBuffer: 16 * 1024 * 1024,
      stdio: ['ignore', 'pipe', 'ignore'],
    });
  } catch {
    return null;
  }
}

function extractVerdict(text, gateId) {
  if (!text) return null;
  // Scope to the first ~80 lines / "header section" of the doc to avoid the
  // status-vocabulary or comparison tables mentioning verdicts as labels.
  const head = text.split(/\r?\n/).slice(0, 80).join('\n');

  // 1. Canonical: `Verdict gate: **GUI_X = STATUS**` or `GUI_X = STATUS`
  if (gateId) {
    const reGate = new RegExp(
      `${gateId}\\s*=\\s*\\*{0,2}([A-Z_]+(?:_PARAMETRIC)?)`,
      'i',
    );
    const m1 = head.match(reGate);
    if (m1) return m1[1].toUpperCase();
  }

  // 2. `**Status:** PASS_REAL` / `Status: PASS_REAL_PARAMETRIC`
  const reStatus = /\*{0,2}Status\*{0,2}\s*[:=]\*{0,2}\s*\*{0,2}`?([A-Z_]+(?:_PARAMETRIC)?)`?\*{0,2}/i;
  const m2 = head.match(reStatus);
  if (m2 && !m2[1].match(/^(GATE|GUI_[A-Z_]+_GREEN)$/i)) return m2[1].toUpperCase();

  // 3. `Verdict: PASS_REAL` / `Final Verdict: ...`
  const reVerdict = /\b(?:final\s+)?verdict\s*[:=]\*{0,2}\s*\*{0,2}`?([A-Z_]+(?:_PARAMETRIC)?)`?\*{0,2}/i;
  const m3 = head.match(reVerdict);
  if (m3 && !m3[1].match(/^(GATE|GUI_[A-Z_]+_GREEN)$/i)) return m3[1].toUpperCase();

  // 4. Last-resort token scan against the head (NOT the whole doc — avoids
  // vocab-table false positives)
  if (/PASS_REAL_PARAMETRIC/.test(head)) return 'PASS_REAL_PARAMETRIC';
  if (/FAIL_NOT_WIRED/.test(head)) return 'FAIL_NOT_WIRED';
  if (/FAIL_REAL/.test(head)) return 'FAIL_REAL';
  if (/PASS_REAL/.test(head)) return 'PASS_REAL';
  if (/BLOCKED/.test(head)) return 'BLOCKED';
  if (/OUT_OF_SCOPE/.test(head)) return 'OUT_OF_SCOPE_BY_OPERATOR';
  return null;
}

function locateHandoff(gate, pr) {
  const candidates = [gate.expectedHandoff, gate.altHandoff].filter(Boolean);
  const merged = pr && pr.state === 'MERGED' && pr.mergedAt;
  // 1. Try main workspace tree (for merged PRs the file is there after rebase/pull)
  for (const rel of candidates) {
    const abs = path.join(WORKSPACE, rel);
    if (fs.existsSync(abs)) return {rel, abs, source: 'workspace'};
  }
  // 2. For merged PRs, git-show from origin/<base> (usually develop)
  if (merged && pr.baseRefName) {
    for (const rel of candidates) {
      const text = gitShow(`origin/${pr.baseRefName}`, WORKSPACE, rel);
      if (text) {
        const shadowDir = path.join(WORKSPACE, '.hermes3d_orchestrator', 'a16_shadow');
        fs.mkdirSync(shadowDir, {recursive: true});
        const shadowPath = path.join(shadowDir, `${pr.number}_merged_${path.basename(rel)}`);
        fs.writeFileSync(shadowPath, text);
        return {rel, abs: shadowPath, source: `pr#${pr.number}@origin/${pr.baseRefName} (post-merge)`};
      }
    }
  }
  // 3. For any PR, git-show on the head ref (covers OPEN PRs and merged-but-unfetched bases)
  if (pr && pr.headRefName) {
    for (const rel of candidates) {
      const text = gitShow(`origin/${pr.headRefName}`, WORKSPACE, rel);
      if (text) {
        const shadowDir = path.join(WORKSPACE, '.hermes3d_orchestrator', 'a16_shadow');
        fs.mkdirSync(shadowDir, {recursive: true});
        const shadowPath = path.join(shadowDir, `${pr.number}_${path.basename(rel)}`);
        fs.writeFileSync(shadowPath, text);
        return {rel, abs: shadowPath, source: `pr#${pr.number}@${pr.headRefName}`};
      }
    }
  }
  return null;
}

function evaluateGate(gate, prs) {
  if (gate.pinned) {
    return {
      gate: gate.id,
      lane: gate.lane,
      verdict: gate.pinned,
      justification: gate.justification,
      pr: null,
      handoff: null,
      handoff_sha256: null,
    };
  }
  // Match PR
  let pr = null;
  if (gate.prNumber) {
    pr = prs.find((p) => p.number === gate.prNumber) || null;
  } else if (gate.titleMatch) {
    pr = prs.find((p) => gate.titleMatch.test(p.title)) || null;
    if (!pr && gate.altMatch) {
      pr = prs.find((p) => gate.altMatch.test(p.title)) || null;
    }
  }
  const merged = pr && pr.state === 'MERGED' && pr.mergedAt;
  const handoff = locateHandoff(gate, pr);
  let handoffText = null;
  let handoffSha = null;
  let verdict = null;
  if (handoff) {
    handoffText = readMaybe(handoff.abs);
    handoffSha = sha256OfFile(handoff.abs);
    verdict = extractVerdict(handoffText, gate.id);
  }
  let status;
  if (!pr) status = 'NO_PR';
  else if (!merged) status = `PR_${pr.state}`;
  else if (!handoff) status = 'MERGED_BUT_HANDOFF_MISSING';
  else if (!gate.expectedVerdicts.includes(verdict))
    status = `MERGED_BUT_VERDICT=${verdict || 'UNKNOWN'}`;
  else status = 'PASS_REAL_VERIFIED';

  return {
    gate: gate.id,
    lane: gate.lane,
    pr_number: pr ? pr.number : null,
    pr_state: pr ? pr.state : null,
    pr_url: pr ? pr.url : null,
    pr_merged_at: pr ? pr.mergedAt : null,
    handoff_path: handoff ? handoff.rel : null,
    handoff_source: handoff ? handoff.source : null,
    handoff_sha256: handoffSha,
    handoff_verdict: verdict,
    expected_verdicts: gate.expectedVerdicts,
    status,
  };
}

function main() {
  const args = process.argv.slice(2);
  let outPath = null;
  let skipFetch = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--out') outPath = args[++i];
    else if (args[i] === '--no-fetch') skipFetch = true;
  }
  if (!skipFetch) {
    try {
      execFileSync('git', ['-C', WORKSPACE, 'fetch', 'origin', '--prune'], {
        stdio: ['ignore', 'ignore', 'pipe'],
      });
    } catch (err) {
      console.error('git fetch warning:', err.message);
    }
  }
  let prs;
  try {
    prs = listW18Prs();
  } catch (err) {
    console.error('gh pr list failed:', err.message);
    process.exit(2);
  }
  const rows = GATES.map((g) => evaluateGate(g, prs));
  const a15 = evaluateGate(
    {
      ...A15_PRECONDITION,
      expectedVerdicts: ['PASS_REAL', 'GREEN', 'PASS_REAL_PARAMETRIC'],
    },
    prs,
  );

  const inScope = rows.filter((r) => !r.gate.match(/PHYSICAL_PRINT|PRINTER_DRY_RUN/));
  const allInScopePass = inScope.every((r) => r.status === 'PASS_REAL_VERIFIED');
  const a15Pass = a15.status === 'PASS_REAL_VERIFIED' || a15.pr_state === 'MERGED';
  const guiComplete = allInScopePass && a15Pass;

  const report = {
    generated_utc: new Date().toISOString(),
    repo: REPO,
    workspace: WORKSPACE,
    gui_complete: guiComplete,
    in_scope_pass_real: allInScopePass,
    a15_runner_merged: a15Pass,
    a15_runner: a15,
    gates: rows,
  };
  const text = JSON.stringify(report, null, 2);
  if (outPath) {
    fs.mkdirSync(path.dirname(outPath), {recursive: true});
    fs.writeFileSync(outPath, text);
  }
  process.stdout.write(text + '\n');
}

main();
