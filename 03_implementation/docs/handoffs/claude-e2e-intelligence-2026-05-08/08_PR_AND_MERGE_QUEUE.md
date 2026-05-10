# 08 — PR and Merge Queue

**Source**: `gh pr list --repo Ghenghis/Hermes3D --state open --limit 100` taken at 2026-05-08 17:26Z (live during this audit). The earlier intelligence agent for this section returned a stale snapshot claiming the chain was already merged — that contradicts both the `gh` output and the live runtime-identity API which still serves PR 104's branch (`codex/provider-smoke-workbench`) at commit 43d8205. The data below replaces that.

## Headline

**25 OPEN PRs** on Ghenghis/Hermes3D as of 2026-05-08 17:26Z. **All 25 are MERGEABLE / mergeStateStatus=CLEAN** with **CodeRabbit SUCCESS**. Every codex-owned PR is stacked on the next codex-owned PR's base — they merge in chain order (oldest base first) all the way back to `feat/hermes3d-7-complete-gui-repo-wiring`. PR #86 is the only Claude-owned PR (already documenting the folder index); all other 24 are Codex-owned and must not be overwritten or rebased by Claude.

## PR Table — All 25 Open

| PR# | Title | Author | Head | Base | Mergeable | mergeStateStatus | CI | Owner | Overwrite-Protect |
|-----|-------|--------|------|------|-----------|------------------|----|-------|-----|
| 104 | feat(agents): add provider smoke and reviewed ship lane | Ghenghis | codex/provider-smoke-workbench | codex/hermes-agent-e2e-workbench | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 103 | feat(agents): add e2e code workbench | Ghenghis | codex/hermes-agent-e2e-workbench | codex/hermes-agent-e2e-truth-roadmap | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 102 | docs(agents): define e2e proof plan | Ghenghis | codex/hermes-agent-e2e-truth-roadmap | codex/source-os-npm-package-runners | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 101 | feat(source): add npm package metadata preflight | Ghenghis | codex/source-os-npm-package-runners | codex/source-os-slicer-config-runners | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 100 | feat(source): add slicer cli config preflights | Ghenghis | codex/source-os-slicer-config-runners | codex/source-os-python-import-runners | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 99 | feat(source): add python import repair preflights | Ghenghis | codex/source-os-python-import-runners | codex/source-os-executable-runners | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 98 | feat(source): add executable path runner smoke | Ghenghis | codex/source-os-executable-runners | codex/source-os-readonly-runners | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 97 | feat(source): add read-only runner smoke contracts | Ghenghis | codex/source-os-readonly-runners | codex/rust-accel-gcode-stl-proof | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 96 | feat(accel): add Rust metadata proof worker | Ghenghis | codex/rust-accel-gcode-stl-proof | codex/source-os-firmware-inventory | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 95 | feat(source-os): add firmware source inventory verifiers | Ghenghis | codex/source-os-firmware-inventory | codex/unit-gate-reliability | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 94 | test(unit): remove live fleet timeout from offline tests | Ghenghis | codex/unit-gate-reliability | codex/source-os-service-supervisor | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 93 | feat(source-os): supervise service runner starts | Ghenghis | codex/source-os-service-supervisor | codex/source-os-service-start-runners | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 92 | feat(source-os): add safe service start-runner preflights | Ghenghis | codex/source-os-service-start-runners | codex/source-os-service-web-health-runners | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 91 | feat(source-os): add service web health verifiers | Ghenghis | codex/source-os-service-web-health-runners | codex/source-os-printfarm-health-runners | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 90 | feat(source-os): add print-farm health verifiers | Ghenghis | codex/source-os-printfarm-health-runners | codex/source-os-slicer-runner-family | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 89 | feat(source-os): correct slicer runner truth | Ghenghis | codex/source-os-slicer-runner-family | codex/source-os-python-runner-family | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 88 | feat(source-os): register Python/CAD verifier family | Ghenghis | codex/source-os-python-runner-family | codex/source-os-runner-contracts | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 87 | [codex] add Source OS runner contract matrix | Ghenghis | codex/source-os-runner-contracts | codex/hermes-agent-provider-execution | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 86 | docs(handoff): Hermes3D OS folder index 2026-05-07 — 86 markdowns w/ inline SVG | Ghenghis | claude/folder-index-2026-05-07 | feat/hermes3d-7-complete-gui-repo-wiring | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Claude | safe-to-merge |
| 85 | [codex] add Hermes Agent provider execution artifacts | Ghenghis | codex/hermes-agent-provider-execution | codex/hermes-agent-team-assignments | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 84 | [codex] add Hermes Agent provider-team assignment lane | Ghenghis | codex/hermes-agent-team-assignments | codex/hermes-agent-git-operator | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 83 | [codex] add proof-gated Hermes Agent git shipping lane | Ghenghis | codex/hermes-agent-git-operator | codex/hermes-agent-mcp-code-operator | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 73 | [codex] add MCP-locked Hermes Agent code operator | Ghenghis | codex/hermes-agent-mcp-code-operator | feat/hermes3d-7-complete-gui-repo-wiring | MERGEABLE | CLEAN | CodeRabbit SUCCESS | Codex | **DO-NOT-OVERWRITE** |
| 52 | chore: fully exclude apps/ from git (local-only vendored installs) | Ghenghis | chore/exclude-apps-folder | develop | MERGEABLE | CLEAN | full CI suite SUCCESS | Codex/maintenance | **DO-NOT-OVERWRITE** |

(One additional PR may also be considered: this docs PR — the one this audit will open against `feat/hermes3d-7-complete-gui-repo-wiring` — will become PR #105+. Claude-owned, safe-to-merge, no Codex collisions.)

## PR Chain Visual

```
                                         develop
                                            ▲
                       chore/exclude-apps-folder (PR #52)
                                            ▲
                  feat/hermes3d-7-complete-gui-repo-wiring (chain base)
                                            ▲
                               ┌────────────┴──────────────┐
                               │                           │
                  claude/folder-index-2026-05-07     codex/hermes-agent-mcp-code-operator (PR #73)
                            (PR #86)                              ▲
                               │                                  │
                               │            codex/hermes-agent-git-operator (PR #83)
                               │                                  ▲
                               │            codex/hermes-agent-team-assignments (PR #84)
                               │                                  ▲
                               │            codex/hermes-agent-provider-execution (PR #85)
                               │                                  ▲
                               │            codex/source-os-runner-contracts (PR #87)
                               │                                  ▲
                               │            codex/source-os-python-runner-family (PR #88)
                               │                                  ▲
                               │            codex/source-os-slicer-runner-family (PR #89)
                               │                                  ▲
                               │            codex/source-os-printfarm-health-runners (PR #90)
                               │                                  ▲
                               │            codex/source-os-service-web-health-runners (PR #91)
                               │                                  ▲
                               │            codex/source-os-service-start-runners (PR #92)
                               │                                  ▲
                               │            codex/source-os-service-supervisor (PR #93)
                               │                                  ▲
                               │            codex/unit-gate-reliability (PR #94)
                               │                                  ▲
                               │            codex/source-os-firmware-inventory (PR #95)
                               │                                  ▲
                               │            codex/rust-accel-gcode-stl-proof (PR #96)
                               │                                  ▲
                               │            codex/source-os-readonly-runners (PR #97)
                               │                                  ▲
                               │            codex/source-os-executable-runners (PR #98)
                               │                                  ▲
                               │            codex/source-os-python-import-runners (PR #99)
                               │                                  ▲
                               │            codex/source-os-slicer-config-runners (PR #100)
                               │                                  ▲
                               │            codex/source-os-npm-package-runners (PR #101)
                               │                                  ▲
                               │            codex/hermes-agent-e2e-truth-roadmap (PR #102)
                               │                                  ▲
                               │            codex/hermes-agent-e2e-workbench (PR #103)
                               │                                  ▲
                               │            codex/provider-smoke-workbench (PR #104, HEAD)
                               │
                  (this audit's PR will open against feat/hermes3d-7-complete-gui-repo-wiring)
```

## Recommended Merge Order

**Critical**: Each PR's base branch must be on `develop` (or already on the chain ancestor) before that PR can merge cleanly without conflict. The recommended sequence is bottom-up from the chain root:

1. **PR #52** (chore/exclude-apps-folder → develop) — independent, safe to merge anytime.
2. **PR #86** (claude/folder-index-2026-05-07 → feat/hermes3d-7-complete-gui-repo-wiring) — Claude-owned docs PR, can land at chain base independent of Codex chain. Recommend merge before chain to avoid rebase. (Note: also independent of this audit's PR.)
3. **PR #73** (codex/hermes-agent-mcp-code-operator → feat/hermes3d-7-complete-gui-repo-wiring) — chain root.
4. **PR #83** (codex/hermes-agent-git-operator → codex/hermes-agent-mcp-code-operator) — depends on #73.
5. **PR #84** → 5. **PR #85** → 6. **PR #87** → 7. **PR #88** → 8. **PR #89** → 9. **PR #90** → 10. **PR #91** → 11. **PR #92** → 12. **PR #93** → 13. **PR #94** → 14. **PR #95** → 15. **PR #96** → 16. **PR #97** → 17. **PR #98** → 18. **PR #99** → 19. **PR #100** → 20. **PR #101** → 21. **PR #102** → 22. **PR #103** → 23. **PR #104** (chain head).

**Per-PR rebase state**: As each PR merges, GitHub auto-updates each downstream PR's base branch to match. No manual rebase needed for already-CLEAN PRs. If a PR base resolves to `feat/hermes3d-7-complete-gui-repo-wiring` after upstream PR merges, the chain stays clean.

**Special handling**:
- **PR #52** (chore/exclude-apps-folder) is independent; merge first to clear maintenance backlog.
- **PR #86** (Claude-owned docs) can merge before, during, or after Codex chain — does not touch any chain-edited files.
- This audit's PR (Claude-owned, opens against the same chain base) follows the same rule as #86: merges independently.

## Conflict Risk Callouts

PRs touching shared files have higher rebase risk if their merge order changes. Files most touched across the chain:

- **`03_implementation/ROADMAP.md`** — touched by ~10 of the 25 PRs (anytime status text changes between Codex slices). Cascade-resolution pattern: UNION acceptable; latest PR wins.
- **`03_implementation/src/hermes3d/api/routes/code_operator.py`** — touched by PR #73, #83, #84, #87, #102, #103, #104. Cascade pattern: chain order preserves integrity; out-of-order rebase risks function-signature drift.
- **`03_implementation/src/hermes3d/api/routes/agents.py`** — touched by PR #84, #85, #103, #104. Same chain-order rule.
- **`03_implementation/src/hermes3d/services/code_history.py`** — touched by PR #73, #83, #84, #103, #104. Same chain-order rule.
- **`03_implementation/ui/src/api/adapters.live.ts`** — touched by PR #84, #85, #103, #104. Same chain-order rule.
- **`03_implementation/ui/src/tabs/Agents.tsx`** — touched by PR #84, #85, #103, #104. Same chain-order rule.

**Conflict mitigation**: GitHub's auto-base-update keeps the chain clean as long as merges happen in chain order. Manual rebase only needed if an out-of-order merge introduces drift on the next PR.

## Codex-Owned Branches (DO-NOT-OVERWRITE)

Per the contract: "Do not overwrite Codex-owned worktrees/folders. Do not release Codex-owned locks. Do not merge PRs."

The following 24 branches are Codex-owned (head = `codex/*`) and must not be touched by Claude tooling:

- codex/provider-smoke-workbench (PR #104)
- codex/hermes-agent-e2e-workbench (PR #103)
- codex/hermes-agent-e2e-truth-roadmap (PR #102)
- codex/source-os-npm-package-runners (PR #101)
- codex/source-os-slicer-config-runners (PR #100)
- codex/source-os-python-import-runners (PR #99)
- codex/source-os-executable-runners (PR #98)
- codex/source-os-readonly-runners (PR #97)
- codex/rust-accel-gcode-stl-proof (PR #96)
- codex/source-os-firmware-inventory (PR #95)
- codex/unit-gate-reliability (PR #94)
- codex/source-os-service-supervisor (PR #93)
- codex/source-os-service-start-runners (PR #92)
- codex/source-os-service-web-health-runners (PR #91)
- codex/source-os-printfarm-health-runners (PR #90)
- codex/source-os-slicer-runner-family (PR #89)
- codex/source-os-python-runner-family (PR #88)
- codex/source-os-runner-contracts (PR #87)
- codex/hermes-agent-provider-execution (PR #85)
- codex/hermes-agent-team-assignments (PR #84)
- codex/hermes-agent-git-operator (PR #83)
- codex/hermes-agent-mcp-code-operator (PR #73)
- chore/exclude-apps-folder (PR #52)

This audit's PR is **Claude-owned** (`claude/e2e-intelligence-2026-05-08`), opens against `feat/hermes3d-7-complete-gui-repo-wiring`, and only adds 12 markdown files under `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/` — zero overlap with any Codex branch.

## Summary

- **25 open PRs**, all CLEAN, all CodeRabbit SUCCESS, ready to merge in chain order.
- **24 are Codex-owned** stacked PRs forming a single chain from PR #73 to PR #104; **PR #86 is Claude-owned** docs.
- **Recommended merge sequence**: PR #52 first, then PR #86, then PR #73 → 83 → 84 → 85 → 87 → 88 → ... → 104 in numeric order.
- **No conflicts** detected as long as merge order follows the chain.
- **This audit PR** opens against `feat/hermes3d-7-complete-gui-repo-wiring`, joining PR #86 as a docs-only Claude PR.
- **Gate-merge note**: PR 104's "Remaining Blocker" (HTTP 401 from MiniMax + DeepSeek) is an *operational* blocker outside Codex's scope — it does not block PR merge. The PR ships the routes; live provider auth is a separate Tier 0 user action documented in `09_CODEX_NEXT_50_TASKS.md`.
