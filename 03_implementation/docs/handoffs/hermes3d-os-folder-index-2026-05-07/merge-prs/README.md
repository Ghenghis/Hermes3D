# merge-pr* worktrees — index

Read-only audit of the four `G:\Github\merge-pr*` worktrees. All four belong to **`Ghenghis/HermesProof`** (NOT `Ghenghis/Hermes3D` — folder names map to HermesProof PR numbers). All four PRs are MERGED. The worktrees are quiescent post-merge artifacts of the v0.6 truth-gate wave that landed on 2026-05-03.

## Summary table

| Folder | PR # | Title | State | Target | Source branch | Merged at | Resolution status | Notes |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| `merge-pr23` | 23 | feat(gate): dependency.fresh — direct deps within 18 months (advisory) | MERGED | main | `feat/gate-dep-fresh` | 2026-05-03T14:13:56Z | COMPLETE | First v0.6 gate to land; only 1 forward-merge required (lightest cascade burden). Bundled `licenses.scan` + `dependency.fresh`. |
| `merge-pr24` | 24 | feat(gate): sbom.cyclonedx_generated — emit CycloneDX 1.5 SBOM on every run | MERGED | main | `feat/gate-sbom` | 2026-05-03T14:24:37Z | COMPLETE | 2 forward-merges; only worktree with explicit **TAKE-THEIRS** in commit subject (`README conflict → theirs`). |
| `merge-pr27` | 27 | feat(gate): mcp-scan-static — extended tool-poisoning analyzer (HP-V0.6-GATE-MCPSCAN) | MERGED | main | `feat/gate-mcp-scan-static` | 2026-05-03T14:31:05Z | COMPLETE | 3 forward-merges; absorbed sibling PR #24 (SBOM imports) before squash-merge. |
| `merge-pr33` | 33 | feat(supervisor): auto-reconnect MCP server wrapper (HP-V0.6-AUTO-RECONNECT) | MERGED | main | `feat/mcp-supervisor-auto-reconnect` | 2026-05-03T15:09:56Z | COMPLETE | Heaviest cascade — 4 forward-merges to absorb sibling PRs #23/#24/#31/#39 before squash-merge. |

## Recurring conflict pattern observed across all 4 worktrees

Matches `reference_cascade_merge_pattern.md` from auto-memory. Every squash-merge to main re-conflicted the next branch on this set:

| File | Resolution | Why |
| --- | --- | --- |
| `package.json` | UNION | Each branch adds new scripts/deps; merge UNIONs the `scripts` and `dependencies` blocks. |
| `scripts/truth-gates.mjs` | UNION | Each branch registers a new gate (`dependency.fresh`, `sbom.cyclonedx_generated`, `security.mcp_scan_pass`, supervisor health); registry concatenates. |
| `scripts/coordination-smoke-test.mjs` | UNION | New per-gate asserts append to the test list. |
| `PROOF/latest.json`, `PROOF/latest.json.cosign.bundle`, `PROOF_E2E_REPORT.md` | TAKE-THEIRS | Regenerated artifacts — always adopt main's freshly-signed copy after merge. |
| `README.md` | mostly UNION; **TAKE-THEIRS** in `merge-pr24` only | Badge / section additions are unioned; only `merge-pr24` had divergent enough README to call it out as theirs. |
| `examples/**/streamhooks/*`, `.github/workflows/stream-watchdog-cron.yml`, `handoffs/STREAM/*_INBOX.md` | TAKE-THEIRS (adopt new files from main) | StreamHooks scaffolding landed on main during this wave; feature branches did not author it, so they accept main's copy. |

## Working-tree state (as of 2026-05-07 audit)

All 4 are **clean** — no uncommitted changes, no remaining `<<<<<<<` markers, no in-flight rebase/merge. Safe to delete the worktrees once it is confirmed nobody is reusing them.

```
merge-pr23  branch=feat/gate-dep-fresh                      HEAD=b2a518b  status=clean  COMPLETE
merge-pr24  branch=feat/gate-sbom                           HEAD=2455244  status=clean  COMPLETE
merge-pr27  branch=feat/gate-mcp-scan-static                HEAD=398c9b9  status=clean  COMPLETE
merge-pr33  branch=feat/mcp-supervisor-auto-reconnect       HEAD=1ff4e64  status=clean  COMPLETE
```

## Master timeline (SVG)

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="700" height="400">
  <style>
    .title  { font: bold 14px sans-serif; fill: #111827; }
    .branch { font: 12px sans-serif; fill: #1f2937; }
    .label  { font: 11px sans-serif; fill: #374151; }
    .merged { font: bold 12px sans-serif; fill: #047857; }
    .time   { font: 10px monospace; fill: #6b7280; }
    rect { rx: 5; ry: 5; }
  </style>

  <text x="20" y="22" class="title">HermesProof v0.6 truth-gate wave — 2026-05-03 (4 PRs into main)</text>

  <line x1="80" y1="350" x2="660" y2="350" stroke="#9ca3af" stroke-width="2"/>
  <text x="20"  y="354" class="label">main</text>

  <!-- PR #23 -->
  <rect x="100" y="70"  width="130" height="36" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="110" y="92"  class="branch">feat/gate-dep-fresh</text>
  <line x1="165" y1="106" x2="165" y2="350" stroke="#1d4ed8" stroke-width="1.5"/>
  <circle cx="165" cy="350" r="5" fill="#166534"/>
  <text x="120" y="370" class="merged">PR#23</text>
  <text x="120" y="384" class="time">14:13:56Z</text>

  <!-- PR #24 -->
  <rect x="250" y="70"  width="120" height="36" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="265" y="92"  class="branch">feat/gate-sbom</text>
  <line x1="310" y1="106" x2="310" y2="350" stroke="#1d4ed8" stroke-width="1.5"/>
  <circle cx="310" cy="350" r="5" fill="#166534"/>
  <text x="275" y="370" class="merged">PR#24</text>
  <text x="270" y="384" class="time">14:24:37Z</text>
  <text x="240" y="130" class="label" style="fill:#b91c1c">README → theirs</text>

  <!-- PR #27 -->
  <rect x="390" y="70"  width="170" height="36" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="402" y="92"  class="branch">feat/gate-mcp-scan-static</text>
  <line x1="475" y1="106" x2="475" y2="350" stroke="#1d4ed8" stroke-width="1.5"/>
  <circle cx="475" cy="350" r="5" fill="#166534"/>
  <text x="445" y="370" class="merged">PR#27</text>
  <text x="440" y="384" class="time">14:31:05Z</text>
  <text x="395" y="130" class="label">absorbs PR#24 SBOM (UNION)</text>

  <!-- PR #33 -->
  <rect x="500" y="170" width="170" height="36" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="505" y="192" class="branch">feat/mcp-supervisor-auto-reconnect</text>
  <line x1="585" y1="206" x2="585" y2="350" stroke="#1d4ed8" stroke-width="1.5"/>
  <circle cx="585" cy="350" r="5" fill="#166534"/>
  <text x="555" y="370" class="merged">PR#33</text>
  <text x="550" y="384" class="time">15:09:56Z</text>
  <text x="495" y="230" class="label">absorbs #23/#24/#31/#39 (UNION)</text>

  <!-- legend -->
  <rect x="20"  y="160" width="14" height="14" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="40"  y="172" class="label">feature branch / worktree</text>
  <circle cx="27" cy="200" r="5" fill="#166534"/>
  <text x="40"  y="204" class="label">squash-merge into main</text>
  <text x="20"  y="240" class="label">UNION = both sides kept</text>
  <text x="20"  y="256" class="label" style="fill:#b91c1c">TAKE-THEIRS = main wins</text>
  <text x="20"  y="272" class="label">PROOF/* always TAKE-THEIRS</text>
  <text x="20"  y="288" class="label">(regenerated each merge)</text>

  <text x="20" y="396" class="time">Cascade order #23 → #24 → #27 → #33 means each later branch had to forward-merge its predecessors and UNION the recurring truth-gates.mjs / coordination-smoke-test.mjs / package.json triple.</text>
</svg>

## Cross-reference

- Auto-memory: `reference_cascade_merge_pattern.md` (UNION resolution for `package.json` + `truth-gates.mjs`)
- Auto-memory: `reference_mechanical_review_checks.md` (PR body fields required for `hermesproof-review-check.yml`)
- Producing repo: `https://github.com/Ghenghis/HermesProof`
