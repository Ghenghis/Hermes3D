# merge-pr27

- **PR #**: 27
- **PR title**: feat(gate): mcp-scan-static — extended tool-poisoning analyzer (HP-V0.6-GATE-MCPSCAN)
- **PR repo**: Ghenghis/HermesProof (NOT Ghenghis/Hermes3D)
- **PR state**: MERGED (mergedAt 2026-05-03T14:31:05Z)
- **Target branch**: main
- **Source branch**: feat/gate-mcp-scan-static
- **PR URL**: https://github.com/Ghenghis/HermesProof/pull/27
- **Worktree path**: G:\Github\merge-pr27

## Branch & last commit

- **Branch**: `feat/gate-mcp-scan-static`
- **HEAD**: `398c9b9` — `merge: forward merge post-PR#24 (SBOM import union)`
- **Working tree**: clean (no uncommitted files, no remaining `<<<<<<<` markers)

## Net diff vs main (4 files / +500 / -2)

| File | Change |
| --- | --- |
| `package.json` | +2 / -2 (UNION) |
| `scripts/mcp-scan-static-gate.mjs` | +250 (new) |
| `scripts/mcp-scan-static-gate.test.mjs` | +221 (new) |
| `scripts/truth-gates.mjs` | +29 (UNION — registers `security.mcp_scan_pass`) |

## Conflict resolutions performed in this worktree

| Merge commit | Source merged in | Files conflict-resolved | Resolution |
| --- | --- | --- | --- |
| `23b56ca` | first sync of main into branch | `.github/workflows/hermesproof-review-check.yml`, `.github/workflows/stream-watchdog-cron.yml`, `CHANGELOG.md`, `PROOF/latest.json`, `PROOF/latest.json.cosign.bundle`, `PROOF_E2E_REPORT.md`, `README.md`, `examples/**/streamhooks/*`, `handoffs/STREAM/CLAUDE_INBOX.md` | UNION for workflows + CHANGELOG; TAKE-THEIRS for `PROOF/*` regenerated artifacts and README; new examples adopted as-is from main |
| `a537a21` | `origin/main` re-sync | `.github/workflows/truth-gates.yml`, `PROOF/latest.json*`, `PROOF_E2E_REPORT.md`, `README.md`, `scripts/coordination-smoke-test.mjs`, `scripts/truth-gates.mjs` | UNION on `scripts/truth-gates.mjs` (gate registry) and `coordination-smoke-test.mjs`; TAKE-THEIRS on README + PROOF |
| `398c9b9` | post-PR#24 cascade (SBOM import) | `.github/workflows/truth-gates.yml`, `scripts/coordination-smoke-test.mjs`, `scripts/sbom-generator.mjs`, `scripts/truth-gates.mjs` | UNION (added SBOM imports + gate registration alongside the mcp-scan additions) |

The recurring `truth-gates.mjs` and `coordination-smoke-test.mjs` conflicts match the documented cascade-merge pattern in memory.

## Status

**COMPLETE** — PR #27 merged into HermesProof:main on 2026-05-03T14:31:05Z. Worktree is post-merge.

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <style>
    .branch { font: 12px sans-serif; fill: #1f2937; }
    .label  { font: 11px sans-serif; fill: #374151; }
    .merged { font: bold 12px sans-serif; fill: #047857; }
    rect { rx: 6; ry: 6; }
  </style>
  <rect x="10"  y="20"  width="160" height="40" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="22"  y="44" class="branch">feat/gate-mcp-scan-static</text>
  <rect x="180" y="120" width="140" height="60" fill="#fef3c7" stroke="#b45309"/>
  <text x="190" y="142" class="branch">merge-pr27 worktree</text>
  <text x="190" y="160" class="label">UNION conflicts</text>
  <text x="190" y="174" class="label">(truth-gates, coord-smoke)</text>
  <rect x="330" y="20"  width="160" height="40" fill="#dcfce7" stroke="#166534"/>
  <text x="345" y="44" class="merged">main (MERGED)</text>
  <text x="345" y="58" class="label" style="fill:#374151">PR #27 · 2026-05-03</text>
  <line x1="170" y1="40" x2="180" y2="120" stroke="#1d4ed8" stroke-width="2"/>
  <line x1="320" y1="150" x2="330" y2="40" stroke="#166534" stroke-width="2"/>
  <text x="50"  y="240" class="label">source branch</text>
  <text x="200" y="240" class="label">forward-merge / UNION resolve</text>
  <text x="370" y="240" class="label">target = main</text>
  <text x="10"  y="280" class="label">3 cascade syncs absorbed sibling PR #24 (SBOM) before squash-merge.</text>
</svg>
