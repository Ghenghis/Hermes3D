# _codex_audit_worktrees

- **Owner**: Codex-audit
- **Worktree count**: 4
- **Git type**: all `.git` files (linked worktrees) under `G:\Github\Hermes3D\.git\worktrees\`
- **Snapshot date**: 2026-05-07

> All 4 worktrees are at detached HEAD. The pr35 pair points at the same SHA (the recovered settings-tab branch); the pr37 pair has diverged (one main, one merge commit on top).

## Subdirectory inventory

| Subdir | Branch (sibling ref at SHA) | Last commit | Date | Purpose (1 line) |
| --- | --- | --- | --- | --- |
| Hermes3D-pr35-audit | (detached) 14b7688 — `feat/cp-h3d-settings-tab-recovered` | 14b7688 | 2026-05-03 | audit checkout of PR #35: AboutSubtab `shell`->`frame`/`frontend` rename |
| Hermes3D-pr35-main | (detached) 14b7688 — `feat/cp-h3d-settings-tab-recovered` | 14b7688 | 2026-05-03 | parallel "main"-side checkout of PR #35 (same SHA as audit) |
| Hermes3D-pr37-audit | (detached) 72d79e6 — no sibling ref | 72d79e6 | 2026-05-03 | audit checkout of PR #37: merge of partial scaffolds onto base |
| Hermes3D-pr37-main | (detached) fd3d4c9 — `feat/cp-h3d-partial-scaffolds` | fd3d4c9 | 2026-05-03 | "main"-side checkout of PR #37: tool_registry + security shell + ServiceHealthPage |

## Active vs Stale (window: 2026-04-30 .. 2026-05-07)

- **Active (commit within last 7 days)**: 4/4 (all 2026-05-03 — within the 7-day window).
- **Stale (>7 days)**: 0.

> These worktrees are tied to specific PRs (#35 and #37). They are likely to be reaped after the PRs land; not "in active development" but still inside the 7-day window.

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400">
  <rect x="0" y="0" width="600" height="400" fill="#0b1020"/>
  <rect x="20" y="14" width="560" height="40" rx="6" fill="#1f2a44" stroke="#fb923c"/>
  <text x="300" y="40" text-anchor="middle" fill="#ffedd5" font-family="monospace" font-size="14">_codex_audit_worktrees (4 worktrees, owner: Codex-audit)</text>

  <rect x="40" y="80" width="240" height="130" rx="8" fill="#241a10" stroke="#fb923c"/>
  <text x="160" y="100" text-anchor="middle" fill="#fed7aa" font-family="monospace" font-size="12">PR #35 pair</text>
  <g font-family="monospace" font-size="10" fill="#cbd5e1">
    <rect x="60" y="116" width="200" height="36" rx="4" fill="#11261d" stroke="#facc15"/>
    <text x="68" y="132">pr35-audit</text>
    <text x="68" y="146" fill="#94a3b8">(detached) 14b7688</text>
    <rect x="60" y="160" width="200" height="36" rx="4" fill="#11261d" stroke="#facc15"/>
    <text x="68" y="176">pr35-main</text>
    <text x="68" y="190" fill="#94a3b8">same SHA — paired checkouts</text>
  </g>

  <rect x="320" y="80" width="240" height="130" rx="8" fill="#241a10" stroke="#fb923c"/>
  <text x="440" y="100" text-anchor="middle" fill="#fed7aa" font-family="monospace" font-size="12">PR #37 pair</text>
  <g font-family="monospace" font-size="10" fill="#cbd5e1">
    <rect x="340" y="116" width="200" height="36" rx="4" fill="#11261d" stroke="#facc15"/>
    <text x="348" y="132">pr37-audit</text>
    <text x="348" y="146" fill="#94a3b8">(detached) 72d79e6 (merge)</text>
    <rect x="340" y="160" width="200" height="36" rx="4" fill="#11261d" stroke="#facc15"/>
    <text x="348" y="176">pr37-main</text>
    <text x="348" y="190" fill="#94a3b8">(detached) fd3d4c9</text>
  </g>

  <text x="300" y="240" text-anchor="middle" fill="#cbd5e1" font-family="monospace" font-size="11">audit-vs-main paired checkouts: side-by-side diffability</text>

  <g font-family="monospace" font-size="10" fill="#94a3b8">
    <text x="300" y="280" text-anchor="middle">parent repo: G:\Github\Hermes3D (.git/worktrees/Hermes3D-pr3{5,7}-{audit,main})</text>
    <text x="300" y="300" text-anchor="middle">all 4 last commit 2026-05-03 — quiet for ~4 days, but inside 7-day window</text>
  </g>

  <g font-family="monospace" font-size="10" fill="#94a3b8">
    <rect x="14" y="356" width="14" height="10" fill="none" stroke="#facc15"/><text x="32" y="365">all 4 detached HEAD (PR audit pattern)</text>
    <rect x="280" y="356" width="14" height="10" fill="none" stroke="#fb923c"/><text x="298" y="365">2 PRs x (audit, main) checkouts</text>
  </g>
</svg>
```
