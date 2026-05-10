# merge-pr23

- **PR #**: 23
- **PR title**: feat(gate): dependency.fresh — direct deps within 18 months (advisory)
- **PR repo**: Ghenghis/HermesProof (NOT Ghenghis/Hermes3D)
- **PR state**: MERGED (mergedAt 2026-05-03T14:13:56Z)
- **Target branch**: main
- **Source branch**: feat/gate-dep-fresh
- **PR URL**: https://github.com/Ghenghis/HermesProof/pull/23
- **Worktree path**: G:\Github\merge-pr23

## Branch & last commit

- **Branch**: `feat/gate-dep-fresh`
- **HEAD**: `b2a518b` — `merge: resolve conflict with main — forward merge`
- **Working tree**: clean (no uncommitted files, no remaining `<<<<<<<` markers)

## Net diff vs main (3 files / +94 / -5)

| File | Change |
| --- | --- |
| `README.md` | +9 / -5 (UNION — added gate badge + section) |
| `scripts/coordination-smoke-test.mjs` | +57 (new asserts) |
| `scripts/truth-gates.mjs` | +33 (UNION — registers `dependency.fresh` and `licenses.scan`) |

PR #23 is the smallest of the four — it bundled both `licenses.scan` and `dependency.fresh` gates (see preceding feature commits `64000ca` and `6036329` on the branch) and was the **first** to merge in the v0.6 wave (2026-05-03T14:13:56Z), so it carried the lightest cascade burden.

## Conflict resolutions performed in this worktree

| Merge commit | Source merged in | Files conflict-resolved | Resolution |
| --- | --- | --- | --- |
| `b2a518b` | first and only sync of main into branch | `.github/workflows/hermesproof-review-check.yml`, `.github/workflows/stream-watchdog-cron.yml`, `CHANGELOG.md`, `PROOF/latest.json` (large, +852 lines), `PROOF/latest.json.cosign.bundle`, `PROOF_E2E_REPORT.md`, `examples/**/streamhooks/*` (cursor / kilocode / vscode / windsurf example folders), `handoffs/STREAM/CLAUDE_INBOX.md`, `handoffs/STREAM/CODEX_INBOX.md` | UNION for workflows + CHANGELOG; TAKE-THEIRS for `PROOF/*` (regenerated artifacts) and the new example folders (adopted from main as-is); UNION for the recurring `README.md` + `scripts/coordination-smoke-test.mjs` + `scripts/truth-gates.mjs` triple |

Only one merge — this branch was first to land, so it did not need to absorb sibling-PR cascades. The recurring conflict pair `truth-gates.mjs` + `coordination-smoke-test.mjs` matches the documented HermesProof cascade-merge pattern (`reference_cascade_merge_pattern.md`).

## Status

**COMPLETE** — PR #23 merged into HermesProof:main on 2026-05-03T14:13:56Z. First of the v0.6 gate wave to land. Worktree is post-merge.

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <style>
    .branch { font: 12px sans-serif; fill: #1f2937; }
    .label  { font: 11px sans-serif; fill: #374151; }
    .merged { font: bold 12px sans-serif; fill: #047857; }
    rect { rx: 6; ry: 6; }
  </style>
  <rect x="10"  y="20"  width="160" height="40" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="32"  y="44" class="branch">feat/gate-dep-fresh</text>
  <rect x="180" y="120" width="140" height="60" fill="#fef3c7" stroke="#b45309"/>
  <text x="190" y="142" class="branch">merge-pr23 worktree</text>
  <text x="190" y="160" class="label">UNION conflicts</text>
  <text x="190" y="174" class="label">(single sync, lightest)</text>
  <rect x="330" y="20"  width="160" height="40" fill="#dcfce7" stroke="#166534"/>
  <text x="345" y="44" class="merged">main (MERGED)</text>
  <text x="345" y="58" class="label" style="fill:#374151">PR #23 · 2026-05-03</text>
  <line x1="170" y1="40" x2="180" y2="120" stroke="#1d4ed8" stroke-width="2"/>
  <line x1="320" y1="150" x2="330" y2="40" stroke="#166534" stroke-width="2"/>
  <text x="50"  y="240" class="label">source branch</text>
  <text x="200" y="240" class="label">single forward-merge / UNION</text>
  <text x="370" y="240" class="label">target = main (FIRST)</text>
  <text x="10"  y="280" class="label">First v0.6 gate wave PR — landed before #24/#27/#33, so no sibling cascade absorbed.</text>
</svg>
