# _codex_worktrees

- **Owner**: Codex
- **Worktree count**: 16 (15 worktree dirs + 1 stray markdown file `CODEX_REBOOT_RESUME_20260503.md` at the top level)
- **Git type**: all `.git` files (linked worktrees) — none are full repos
- **Snapshot date**: 2026-05-07

> Note: 7 worktrees are at detached HEAD (no symbolic branch ref). Where a sibling branch points at the same SHA, it is shown in parentheses.

## Subdirectory inventory

| Subdir | Branch | Last commit | Date | Purpose (1 line) |
| --- | --- | --- | --- | --- |
| Hermes3D-live-printer-tests | codex/bed-adhesion-precondition | 1ae6469 | 2026-05-03 | safety: allow room-temperature bed profiles |
| Hermes3D-overnight-complete | codex/overnight-complete-handoff | 237383b | 2026-05-03 | overnight handoff brief; correct branch name |
| Hermes3D-v5.3-notes | codex/v5.3.0-release-notes-draft | d884878 | 2026-05-03 | draft v5.3.0 release notes |
| HermesProof-audit | (detached) HEAD | da9b428 | 2026-05-03 | refresh truth-gate proof for fc851c0 |
| HermesProof-client-adapters | codex/stream-client-adapters-doc-test-fix | d9e636c | 2026-05-03 | tighten streamhook adapter coverage |
| HermesProof-pr18 | (detached) HEAD | 2aabf20 | 2026-05-03 | align security docs with fail-closed hook |
| HermesProof-pr19 | (detached) HEAD | f5ec246 | 2026-05-03 | env-file fallback existence-aware |
| HermesProof-pr26-fix | ci/mechreview-edited-trigger | e45a0e8 | 2026-05-03 | keep mechanical review pull-request scoped |
| HermesProof-pr28-fix | ci/stream-watchdog-cron | ea9d3ee | 2026-05-03 | harden STREAM watchdog cron |
| HermesProof-pr29-fix | (detached) HEAD | f9e272e | 2026-05-03 | keep unsupported jsdom contrast as warning evidence |
| HermesProof-pr31-trigger | (detached) HEAD | b834f88 | 2026-05-03 | re-run mechanical review after body fix |
| HermesProof-pr32-trigger | (detached) HEAD | 8f72c21 | 2026-05-03 | re-run mechanical review after body fix |
| HermesProof-proof-signing | codex/post-merge-hp-sanity | dac89ec | 2026-05-03 | preserve SPDX license expressions (#39) |
| h3d-post-claude-merged | codex/ui-audit-deps-2026-05-06 | 46565eb | 2026-05-06 | align observe refresh button contract |
| h3d-printer-bed-gates | feat/cp-h3d-printer-bed-gates | 3fde207 | 2026-05-03 | draft v5.3.0 release notes |
| hp-gate-secret-rotation | feat/gate-secret-rotation | c6f1b7f | 2026-05-03 | forward merge post-PR#39 (mcp-scan + test union) |

## Active vs Stale (window: 2026-04-30 .. 2026-05-07)

- **Active (commit within last 7 days)**: 16/16 — all are within the 7-day window (oldest is 2026-05-03).
- **Stale (>7 days)**: 0.
- **Most recent**: `h3d-post-claude-merged` (2026-05-06). Most others are clustered on 2026-05-03 (Codex day-of-work, since cooled down).

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400">
  <rect x="0" y="0" width="600" height="400" fill="#0b1020"/>
  <rect x="20" y="14" width="560" height="40" rx="6" fill="#1f2a44" stroke="#34d399"/>
  <text x="300" y="40" text-anchor="middle" fill="#d1fae5" font-family="monospace" font-size="14">_codex_worktrees (16 worktrees, owner: Codex)</text>
  <g font-family="monospace" font-size="9" fill="#cbd5e1">
    <g><rect x="14" y="70" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="20" y="86">live-printer-tests</text><text x="20" y="98" fill="#94a3b8">codex/bed-adhesion-...</text></g>
    <g><rect x="155" y="70" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="161" y="86">overnight-complete</text><text x="161" y="98" fill="#94a3b8">codex/overnight-complete-...</text></g>
    <g><rect x="296" y="70" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="302" y="86">v5.3-notes</text><text x="302" y="98" fill="#94a3b8">codex/v5.3.0-release-notes</text></g>
    <g><rect x="437" y="70" width="135" height="36" rx="4" fill="#11261d" stroke="#facc15"/><text x="443" y="86">HermesProof-audit</text><text x="443" y="98" fill="#94a3b8">(detached) da9b428</text></g>
    <g><rect x="14" y="112" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="20" y="128">client-adapters</text><text x="20" y="140" fill="#94a3b8">codex/stream-client-...</text></g>
    <g><rect x="155" y="112" width="135" height="36" rx="4" fill="#11261d" stroke="#facc15"/><text x="161" y="128">HermesProof-pr18</text><text x="161" y="140" fill="#94a3b8">(detached) 2aabf20</text></g>
    <g><rect x="296" y="112" width="135" height="36" rx="4" fill="#11261d" stroke="#facc15"/><text x="302" y="128">HermesProof-pr19</text><text x="302" y="140" fill="#94a3b8">(detached) f5ec246</text></g>
    <g><rect x="437" y="112" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="443" y="128">pr26-fix</text><text x="443" y="140" fill="#94a3b8">ci/mechreview-edited-...</text></g>
    <g><rect x="14" y="154" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="20" y="170">pr28-fix</text><text x="20" y="182" fill="#94a3b8">ci/stream-watchdog-cron</text></g>
    <g><rect x="155" y="154" width="135" height="36" rx="4" fill="#11261d" stroke="#facc15"/><text x="161" y="170">pr29-fix</text><text x="161" y="182" fill="#94a3b8">(detached) f9e272e</text></g>
    <g><rect x="296" y="154" width="135" height="36" rx="4" fill="#11261d" stroke="#facc15"/><text x="302" y="170">pr31-trigger</text><text x="302" y="182" fill="#94a3b8">(detached) b834f88</text></g>
    <g><rect x="437" y="154" width="135" height="36" rx="4" fill="#11261d" stroke="#facc15"/><text x="443" y="170">pr32-trigger</text><text x="443" y="182" fill="#94a3b8">(detached) 8f72c21</text></g>
    <g><rect x="14" y="196" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="20" y="212">proof-signing</text><text x="20" y="224" fill="#94a3b8">codex/post-merge-hp-sanity</text></g>
    <g><rect x="155" y="196" width="135" height="36" rx="4" fill="#11261d" stroke="#a78bfa"/><text x="161" y="212">post-claude-merged</text><text x="161" y="224" fill="#94a3b8">codex/ui-audit-deps-...</text></g>
    <g><rect x="296" y="196" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="302" y="212">printer-bed-gates</text><text x="302" y="224" fill="#94a3b8">feat/cp-h3d-printer-bed-...</text></g>
    <g><rect x="437" y="196" width="135" height="36" rx="4" fill="#11261d" stroke="#34d399"/><text x="443" y="212">hp-gate-secret-rotation</text><text x="443" y="224" fill="#94a3b8">feat/gate-secret-rotation</text></g>
  </g>
  <g font-family="monospace" font-size="10" fill="#cbd5e1">
    <text x="20" y="260">Top-level file: CODEX_REBOOT_RESUME_20260503.md (4110 bytes, not a worktree)</text>
  </g>
  <g font-family="monospace" font-size="10" fill="#94a3b8">
    <rect x="14" y="356" width="14" height="10" fill="none" stroke="#34d399"/><text x="32" y="365">9 branch-tracking</text>
    <rect x="150" y="356" width="14" height="10" fill="none" stroke="#facc15"/><text x="168" y="365">6 detached HEAD</text>
    <rect x="290" y="356" width="14" height="10" fill="none" stroke="#a78bfa"/><text x="308" y="365">1 most-recent (5/06)</text>
    <text x="430" y="365">parent: G:\Github\HermesProof + Hermes3D</text>
  </g>
</svg>
```
