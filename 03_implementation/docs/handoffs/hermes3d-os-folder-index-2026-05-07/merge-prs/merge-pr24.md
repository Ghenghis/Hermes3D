# merge-pr24

- **PR #**: 24
- **PR title**: feat(gate): sbom.cyclonedx_generated — emit CycloneDX 1.5 SBOM on every run
- **PR repo**: Ghenghis/HermesProof (NOT Ghenghis/Hermes3D)
- **PR state**: MERGED (mergedAt 2026-05-03T14:24:37Z)
- **Target branch**: main
- **Source branch**: feat/gate-sbom
- **PR URL**: https://github.com/Ghenghis/HermesProof/pull/24
- **Worktree path**: G:\Github\merge-pr24

## Branch & last commit

- **Branch**: `feat/gate-sbom`
- **HEAD**: `2455244` — `merge: forward merge with main post-PR#23 (README conflict → theirs)`
- **Working tree**: clean (no uncommitted files, no remaining `<<<<<<<` markers)

## Net diff vs main (4 files / +419 / -2)

| File | Change |
| --- | --- |
| `.github/workflows/truth-gates.yml` | +5 / -0 (UNION — added SBOM artifact upload step) |
| `scripts/coordination-smoke-test.mjs` | +139 (new asserts) |
| `scripts/sbom-generator.mjs` | +246 (new) |
| `scripts/truth-gates.mjs` | +31 (UNION — registers `sbom.cyclonedx_generated`) |

## Conflict resolutions performed in this worktree

| Merge commit | Source merged in | Files conflict-resolved | Resolution |
| --- | --- | --- | --- |
| `d24185f` | first sync of main into branch | `CHANGELOG.md`, `PROOF/latest.json*`, `PROOF_E2E_REPORT.md`, `README.md`, `package.json`, `scripts/coordination-smoke-test.mjs`, `scripts/license-and-deps-gates.mjs`, `scripts/perf-v0.5.1-smoke-test.mjs`, `scripts/truth-gates.mjs`, `src/core/lock-manager.mjs`, `src/core/queue-manager.mjs`, `src/server.mjs` | UNION on code (truth-gates.mjs gate registry, package.json, src/core/* and server changes); TAKE-THEIRS on regenerated PROOF artifacts and README |
| `2455244` | `origin/main` post-PR#23 cascade | `.github/workflows/hermesproof-review-check.yml`, `.github/workflows/stream-watchdog-cron.yml`, `.github/workflows/truth-gates.yml`, `PROOF/latest.json*`, `PROOF_E2E_REPORT.md`, **`README.md`** (commit message explicitly: **"README conflict → theirs"**), all `examples/**/streamhooks/*`, `handoffs/STREAM/CLAUDE_INBOX.md` | UNION for workflows + truth-gates; **TAKE-THEIRS for README.md** (explicit, called out in commit subject); TAKE-THEIRS for regenerated PROOF |

This is the only one of the 4 worktrees with an explicit TAKE-THEIRS resolution flagged in the commit subject — the README diverged enough between branches that `feat/gate-sbom` wholesale adopted main's version.

## Status

**COMPLETE** — PR #24 merged into HermesProof:main on 2026-05-03T14:24:37Z. Worktree is post-merge.

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <style>
    .branch { font: 12px sans-serif; fill: #1f2937; }
    .label  { font: 11px sans-serif; fill: #374151; }
    .merged { font: bold 12px sans-serif; fill: #047857; }
    .theirs { font: bold 11px sans-serif; fill: #b91c1c; }
    rect { rx: 6; ry: 6; }
  </style>
  <rect x="10"  y="20"  width="160" height="40" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="40"  y="44" class="branch">feat/gate-sbom</text>
  <rect x="180" y="110" width="140" height="80" fill="#fef3c7" stroke="#b45309"/>
  <text x="190" y="132" class="branch">merge-pr24 worktree</text>
  <text x="190" y="150" class="label">UNION (code, workflows)</text>
  <text x="190" y="166" class="theirs">TAKE-THEIRS: README.md</text>
  <text x="190" y="182" class="label">TAKE-THEIRS: PROOF/*</text>
  <rect x="330" y="20"  width="160" height="40" fill="#dcfce7" stroke="#166534"/>
  <text x="345" y="44" class="merged">main (MERGED)</text>
  <text x="345" y="58" class="label" style="fill:#374151">PR #24 · 2026-05-03</text>
  <line x1="170" y1="40" x2="180" y2="120" stroke="#1d4ed8" stroke-width="2"/>
  <line x1="320" y1="150" x2="330" y2="40" stroke="#166534" stroke-width="2"/>
  <text x="50"  y="240" class="label">source branch</text>
  <text x="200" y="240" class="label">2 forward-merges, mixed strategy</text>
  <text x="370" y="240" class="label">target = main</text>
  <text x="10"  y="280" class="label">Mixed UNION/TAKE-THEIRS — first occurrence of explicit "→ theirs" callout in commit message.</text>
</svg>
