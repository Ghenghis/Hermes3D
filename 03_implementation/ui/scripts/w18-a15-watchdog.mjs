#!/usr/bin/env node
// W18-A15 watchdog — polls W18 PRs until enough lanes merge or timeout.
// Triggers regression-run phase when:
//   - 8+ of {A1-pickup, A4, A5, A7, A8, A9, A10-pickup, A11, A13, A14-pickup} are MERGED, OR
//   - 4 hours elapsed since start.
// Hard cap 6 hours.
//
// Usage: node scripts/w18-a15-watchdog.mjs
// Env:
//   POLL_INTERVAL_MS   default 300000 (5 min)
//   TRIGGER_LANES      default 8
//   TRIGGER_HOURS      default 4
//   MAX_HOURS          default 6

import { execSync } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const POLL_MS = Number(process.env.POLL_INTERVAL_MS || 300000);
const TRIGGER_LANES = Number(process.env.TRIGGER_LANES || 8);
const TRIGGER_HOURS = Number(process.env.TRIGGER_HOURS || 4);
const MAX_HOURS = Number(process.env.MAX_HOURS || 6);

const TARGET_LANES = [
  'a1-pickup', 'a4', 'a5', 'a7', 'a8', 'a9',
  'a10-pickup', 'a11', 'a13', 'a14-pickup',
];

function laneOfBranch(branch) {
  // Branch examples:
  //   claude/w18-a4-agent-workflow         -> a4
  //   claude/w18-a14-no-skip-harness       -> a14
  //   claude/w18-a10-pickup-visual-oracle  -> a10-pickup
  //   claude/w18-a1-pickup-route-walker    -> a1-pickup
  const m = branch.match(/^claude\/w18-(a\d+(?:-pickup)?)/i);
  return m ? m[1].toLowerCase() : null;
}

function snapshot() {
  const raw = execSync(
    'gh pr list --search "W18 in:title" --repo Ghenghis/Hermes3D --state all --limit 100 --json number,title,headRefName,state,mergedAt,url',
    { encoding: 'utf8' },
  );
  const prs = JSON.parse(raw);
  const lanes = {};
  for (const p of prs) {
    const lane = laneOfBranch(p.headRefName);
    if (!lane) continue;
    if (!lanes[lane]) lanes[lane] = [];
    lanes[lane].push(p);
  }
  const mergedLanes = [];
  const openLanes = [];
  const closedLanes = [];
  for (const lane of TARGET_LANES) {
    const prs = lanes[lane] || [];
    const merged = prs.find(p => p.mergedAt);
    const open = prs.find(p => p.state === 'OPEN');
    if (merged) mergedLanes.push({ lane, pr: merged });
    else if (open) openLanes.push({ lane, pr: open });
    else closedLanes.push({ lane, prs });
  }
  return { allPrs: prs, lanes, mergedLanes, openLanes, closedLanes };
}

const start = Date.now();
const evidenceDir = join(process.cwd(), 'tests', 'w18-a15-evidence');
mkdirSync(evidenceDir, { recursive: true });
const logPath = join(evidenceDir, 'watchdog.log');
const statePath = join(evidenceDir, 'watchdog-state.json');

function logLine(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  try { execSync(`echo "${line.replace(/"/g, '\\"')}" >> "${logPath}"`); } catch {}
}

async function main() {
  logLine(`W18-A15 watchdog started. trigger=${TRIGGER_LANES} lanes OR ${TRIGGER_HOURS}h | max=${MAX_HOURS}h | poll=${POLL_MS}ms`);
  logLine(`Target lanes: ${TARGET_LANES.join(', ')}`);

  let iter = 0;
  while (true) {
    iter += 1;
    const elapsedH = (Date.now() - start) / 3_600_000;
    let snap;
    try {
      snap = snapshot();
    } catch (e) {
      logLine(`gh pr list failed: ${e.message}`);
      await new Promise(r => setTimeout(r, POLL_MS));
      continue;
    }

    const mergedCount = snap.mergedLanes.length;
    const openCount = snap.openLanes.length;

    logLine(`iter=${iter} elapsed=${elapsedH.toFixed(2)}h merged=${mergedCount}/${TARGET_LANES.length} open=${openCount}`);
    for (const m of snap.mergedLanes) {
      logLine(`  MERGED ${m.lane} -> PR #${m.pr.number}`);
    }
    for (const o of snap.openLanes) {
      logLine(`  open   ${o.lane} -> PR #${o.pr.number} (${o.pr.state})`);
    }

    const state = {
      iter,
      now: new Date().toISOString(),
      elapsedHours: elapsedH,
      mergedCount,
      openCount,
      mergedLanes: snap.mergedLanes.map(x => ({ lane: x.lane, pr: x.pr.number, url: x.pr.url })),
      openLanes: snap.openLanes.map(x => ({ lane: x.lane, pr: x.pr.number, url: x.pr.url })),
    };
    writeFileSync(statePath, JSON.stringify(state, null, 2));

    // Trigger conditions
    if (mergedCount >= TRIGGER_LANES) {
      logLine(`TRIGGER: merged-count ${mergedCount} >= ${TRIGGER_LANES}. Begin regression-run.`);
      process.exit(0);
    }
    if (elapsedH >= TRIGGER_HOURS) {
      logLine(`TRIGGER: elapsed ${elapsedH.toFixed(2)}h >= ${TRIGGER_HOURS}h. Begin regression-run with current state.`);
      process.exit(0);
    }
    if (elapsedH >= MAX_HOURS) {
      logLine(`HARD-STOP: elapsed ${elapsedH.toFixed(2)}h >= ${MAX_HOURS}h. Aborting watchdog.`);
      process.exit(2);
    }

    await new Promise(r => setTimeout(r, POLL_MS));
  }
}

main().catch(e => { logLine(`fatal: ${e.message}`); process.exit(1); });
