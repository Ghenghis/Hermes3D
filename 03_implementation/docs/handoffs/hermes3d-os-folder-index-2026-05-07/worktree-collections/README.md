# Worktree Collections Index

Snapshot date: **2026-05-07**

This directory inventories the three top-level worktree-collection folders under `G:\Github\` that are managed by different agent runners. Each `<folder-name>.md` file in this directory has the per-collection inventory + SVG diagram.

## Totals across all 3 collections

| Collection | Owner | Worktree count | Active (<=7d) | Stale (>7d) | Detached HEAD | Last activity |
| --- | --- | --- | --- | --- | --- | --- |
| [_claude_worktrees](./_claude_worktrees.md) | Claude | 29 | 29 | 0 | 0 | 2026-05-06 |
| [_codex_worktrees](./_codex_worktrees.md) | Codex | 16 | 16 | 0 | 6 | 2026-05-06 |
| [_codex_audit_worktrees](./_codex_audit_worktrees.md) | Codex-audit | 4 | 4 | 0 | 4 | 2026-05-03 |
| **Total** | | **49** | **49** | **0** | **10** | |

Notes:
- Every directory inspected is a *linked* git worktree (`.git` is a file pointing into a parent repo's `.git/worktrees/<name>` gitdir). None are full repos.
- The Claude collection uses symbolic `claude/<lane>` and `claude/<polish-name>-audit` branches. Most Codex worktrees use `codex/<topic>`, `ci/<topic>`, or `feat/cp-h3d-<topic>` branches; the rest are at detached HEAD pinned to a specific SHA.
- The Codex-audit collection deliberately uses paired `*-audit` and `*-main` worktrees per PR for side-by-side diffing. PR #35's pair share an SHA; PR #37's pair diverges (one base, one merge).
- The single non-directory entry in `_codex_worktrees/` is `CODEX_REBOOT_RESUME_20260503.md` (a 4 KB resume note, not a worktree).

## Master SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="800" height="500">
  <rect x="0" y="0" width="800" height="500" fill="#0b1020"/>

  <rect x="20" y="14" width="760" height="44" rx="6" fill="#1f2a44" stroke="#94a3b8"/>
  <text x="400" y="42" text-anchor="middle" fill="#e2e8f0" font-family="monospace" font-size="16">G:\Github\ — worktree collections (49 worktrees, 3 collections, snapshot 2026-05-07)</text>

  <rect x="20" y="78" width="240" height="380" rx="10" fill="#13243f" stroke="#3b82f6" stroke-width="2"/>
  <text x="140" y="106" text-anchor="middle" fill="#dbe7ff" font-family="monospace" font-size="14">_claude_worktrees</text>
  <text x="140" y="124" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="11">Owner: Claude</text>
  <text x="140" y="146" text-anchor="middle" fill="#60a5fa" font-family="monospace" font-size="22">29</text>
  <text x="140" y="166" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="11">worktrees</text>
  <g font-family="monospace" font-size="10" fill="#cbd5e1">
    <text x="40" y="206">- 20 implementation lanes</text>
    <text x="40" y="226">  (claude/app-shell, gen3d,</text>
    <text x="40" y="244">  observe, printers, voice,</text>
    <text x="40" y="262">  source-* x6, etc.)</text>
    <text x="40" y="288">- 6 polish-audit lanes</text>
    <text x="40" y="306">  (docs, merge, nofake,</text>
    <text x="40" y="324">  runtime, safety, security)</text>
    <text x="40" y="350">- 2 handoff/index</text>
    <text x="40" y="370">- 1 CI fix (ts7026)</text>
    <text x="40" y="400">Active: 29/29  Stale: 0</text>
    <text x="40" y="418">Last commit: 2026-05-06</text>
    <text x="40" y="436">Detached HEAD: 0</text>
  </g>

  <rect x="280" y="78" width="240" height="380" rx="10" fill="#11261d" stroke="#34d399" stroke-width="2"/>
  <text x="400" y="106" text-anchor="middle" fill="#d1fae5" font-family="monospace" font-size="14">_codex_worktrees</text>
  <text x="400" y="124" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="11">Owner: Codex</text>
  <text x="400" y="146" text-anchor="middle" fill="#34d399" font-family="monospace" font-size="22">16</text>
  <text x="400" y="166" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="11">worktrees</text>
  <g font-family="monospace" font-size="10" fill="#cbd5e1">
    <text x="300" y="206">- 9 branch-tracking</text>
    <text x="300" y="224">  (codex/*, ci/*,</text>
    <text x="300" y="242">  feat/cp-h3d-*)</text>
    <text x="300" y="268">- 6 detached HEAD</text>
    <text x="300" y="286">  (HermesProof PR #18, #19,</text>
    <text x="300" y="304">  audit, pr29-fix,</text>
    <text x="300" y="322">  pr31/32-trigger)</text>
    <text x="300" y="348">- 1 most-recent (5/06)</text>
    <text x="300" y="366">  h3d-post-claude-merged</text>
    <text x="300" y="392">Active: 16/16  Stale: 0</text>
    <text x="300" y="410">Last commit: 2026-05-06</text>
    <text x="300" y="428">Detached HEAD: 6</text>
    <text x="300" y="446">+ 1 stray .md at root</text>
  </g>

  <rect x="540" y="78" width="240" height="380" rx="10" fill="#241a10" stroke="#fb923c" stroke-width="2"/>
  <text x="660" y="106" text-anchor="middle" fill="#ffedd5" font-family="monospace" font-size="14">_codex_audit_worktrees</text>
  <text x="660" y="124" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="11">Owner: Codex-audit</text>
  <text x="660" y="146" text-anchor="middle" fill="#fb923c" font-family="monospace" font-size="22">4</text>
  <text x="660" y="166" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="11">worktrees</text>
  <g font-family="monospace" font-size="10" fill="#cbd5e1">
    <text x="560" y="206">- PR #35 pair</text>
    <text x="560" y="224">  pr35-audit + pr35-main</text>
    <text x="560" y="242">  (same SHA 14b7688)</text>
    <text x="560" y="268">- PR #37 pair</text>
    <text x="560" y="286">  pr37-audit (72d79e6)</text>
    <text x="560" y="304">  pr37-main  (fd3d4c9)</text>
    <text x="560" y="330">Pattern: audit-vs-main</text>
    <text x="560" y="348">paired checkouts per PR</text>
    <text x="560" y="392">Active: 4/4  Stale: 0</text>
    <text x="560" y="410">Last commit: 2026-05-03</text>
    <text x="560" y="428">Detached HEAD: 4 (all)</text>
  </g>

  <line x1="260" y1="268" x2="280" y2="268" stroke="#475569" stroke-dasharray="3,3"/>
  <line x1="520" y1="268" x2="540" y2="268" stroke="#475569" stroke-dasharray="3,3"/>

  <text x="400" y="486" text-anchor="middle" fill="#64748b" font-family="monospace" font-size="10">All 49 directories are linked git worktrees. Parents: G:\Github\Hermes3D and G:\Github\HermesProof</text>
</svg>
```
