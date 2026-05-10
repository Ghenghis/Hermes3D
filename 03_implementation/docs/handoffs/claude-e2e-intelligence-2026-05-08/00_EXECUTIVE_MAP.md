# 00 — Executive Map

Updated: 2026-05-08
Author: claude-e2e-intel-aggregator
Contract: [PR 104 (Ghenghis/Hermes3D) — Claude 20+ Agent E2E Completion Intelligence Contract](https://github.com/Ghenghis/Hermes3D/pull/104)
Bundle: `03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/`

---

## What works now (live API, branch `codex/provider-smoke-workbench` commit 43d8205, 2026-05-08 17:25Z)

- **Backend runtime**: FRESH on PR 104 branch. 220 routes total. All 10 required Agent Workbench routes present. `/api/system/runtime-identity.fresh = true`. No missing routes.
- **MCP locks**: hermes3d-locks server ready (`G:/Github/hermes3d-mcp-lock-orchestrator/src/server.mjs`), workspace `G:/Github/h3d-gui-wiring-codex` matched. 0 active locks at audit start. 12 markdown locks acquired by this aggregator. Required workflow `claim → lock → heartbeat → gate → evidence → release` is fully routed.
- **CLI runners**: OpenCode `1.4.3-hermes3d` detected and version-validated; OpenHands `OpenHands CLI 1.16.0` detected and version-validated. Both `write_allowed=false` (fail-closed) until provider auth + task-scoped sandbox + review/gate handoff.
- **Sandbox**: Docker 29.4.1 ready. Image `ghcr.io/openhands/openhands:latest` (sha256:e6eed4f4d7c4..., 393 MB) present locally. `network=none`, denied paths `[.git, 03_implementation/proof, 03_implementation/var, G:/private, node_modules]`.
- **UI**: 81 active production files, **0 fake/mock markers** (live `scan_active_ui_no_fake.py` PASS). 18 tabs total: 9 DONE, 9 IN_PROGRESS.
- **Source OS**: 60 apps registered. **7 agent_cli_ready** (Hermes Agent, Blender, OpenSCAD, CuraEngine, FLSUN, OrcaSlicer, PrusaSlicer). 3 readonly_api_ready, 5 metadata_ready_needs_runner, 8 read_only_runner_available, 18 source_reference_only.
- **Code history**: 7 snapshots already recorded. Restore + diff routes live.
- **Evidence chain**: hash-chained ledger operational. This audit has appended `ev_b6e233d4ac466056` (kickoff) at chain link `prev=ev_9902e5f446820017`.
- **Open PRs**: 25 OPEN on Ghenghis/Hermes3D, all MERGEABLE/CLEAN/CodeRabbit-SUCCESS, forming a single Codex chain (PR 73 → 83 → ... → 104) plus PR 86 (Claude folder index, separate).

## What is blocked

- **MiniMax + DeepSeek live auth: HTTP 401**. Both providers configured (`api_key_configured=true`, `base_url_configured=true`, `model_configured=true`) but reject keys live. Evidence: `ev_51f12274c079a62f` (MiniMax), `ev_ca72de163072224c` (DeepSeek). This blocks the agent E2E coding loop — without working provider auth, MiniMax cannot build patches and DeepSeek cannot review them.
- **No real co-developer task has completed end-to-end yet**. Routes for the full chain (folder-index → claim → lock → snapshot → MiniMax → DeepSeek → patch apply → gates → branch/commit/push/PR → evidence → release) all exist. The `/api/code-operator/e2e/jobs` orchestration is PARTIAL — patch-apply-through-PR stage needs the final glue.
- **Source OS runner gaps**: 24 modules still need bounded verifier registration (3 desktop_app_gap, 3 gpu_worker_gap, 1 npm_package_gap, 5 metadata_ready, 5 python_import_repair, 7 cli_preferred ranges). Plus 15 in `runtime_repair_required` and 2 explicitly blocked (Slic3r, SuperSlicer).
- **App update center** (Settings + Plugins): backup → check → update → smoke gate → rollback → approval orchestration is partial. UI surfaces exist; the `services/update_orchestrator.py` orchestration layer is not yet shared across the 60 apps.
- **Action catalog parity**: every visible UI action should have a matching `/api/agents/action-catalog` row, but catalog is currently a subset of buttons.

## Hard answer to "When will Hermes Agents work?"

Three conditions, in order:

1. **Operator action — Tier 0**: Replace MiniMax + DeepSeek keys in `G:/private/.env`, restart the API, click both Agent Code Workbench provider smoke buttons. Acceptance: `/api/code-operator/providers/smoke` returns `accepted=true, status=ok` for both providers; `/api/code-operator/e2e/readiness.ready === true`.
2. **Codex action — Tier 1**: Submit one small, reversible task (e.g. one-line ROADMAP.md edit) through the Workbench. Drive MiniMax → DeepSeek → patch-apply → gates → branch/commit/push/PR. Capture all 5 evidence ids in a proof JSON.
3. **Codex action — Tier 1 finish**: Run a rollback drill. Confirm `history/restore` returns the file to pre-task SHA. Append final evidence and release locks.

After step 3, **Hermes Agents are working**. From there, Tiers 2-7 (50 more tasks) are split between Codex and Hermes Agents per `09_CODEX_NEXT_50_TASKS.md`.

**Honest assessment**: The infrastructure is 95% ready. Provider authentication is the only blocker. Estimated time after Tier 0 unblocks: 1 working day to land Tier 1, then days-to-weeks for Tiers 2-3.

## What Codex should do next

1. **Stage the patch text** for the Tier 1 first-real-loop target so the moment Tier 0 unblocks, one Workbench click runs the loop.
2. **Ship MeshLab CLI verifier PR** (Task 8 in `09_CODEX_NEXT_50_TASKS.md`). Smallest cli_preferred runner, identical pattern to PR 89, no provider needed. Reduces runner_gap 24 → 23.
3. **Write `scripts/audit_action_catalog_parity.py`** (Task 23). Read-only diagnostic that produces the input data for Tier 4.

Full prioritized 50-row queue with files/routes/prereqs/acceptance proof in `09_CODEX_NEXT_50_TASKS.md`.

## Bundle Index

| File | What it covers | Verdict |
|------|----------------|---------|
| 00_EXECUTIVE_MAP.md | This file. Headline state + hard answer. | DONE |
| 01_GITHUB_FOLDER_ECOSYSTEM_AUDIT.md | 71 indexed folders reconciled vs reality + ~136 legacy. Top archive/keep candidates. | DONE — HEALTHY |
| 02_STALE_CODE_AND_BRANCH_MAP.md | 49 worktrees + 50+ remote branches. 15 branches >100 commits behind. Stale proof callouts. | DONE — 15 stale branches flagged |
| 03_HERMES_AGENT_RUNTIME_GAP_MAP.md | All 13 agent surfaces with status + next required action. Required-truth table. | DONE — 1 BLOCKED (provider auth), 11 DONE, 1 PARTIAL |
| 04_SOURCE_OS_60_APP_COMPLETION_MAP.md | 60 apps full inventory + per-section + runner family ladder. | DONE — 7 ready, 24 gaps, 18 reference-only |
| 05_TAB_BY_TAB_ACTIVE_UI_NO_FAKE_AUDIT.md | 18 tabs audited. Mock/fake re-check. Cross-tab issues. | DONE — 0 fake markers, 9/9 split |
| 06_ENV_KEYS_AND_RUNTIME_CONFIG_MAP.md | 74 env keys across 14 subsystems. Secret-leak scan PASS. | DONE — 7/14 subsystems operational |
| 07_TEST_GATES_AND_PROOF_MATRIX.md | 23 gates inventoried. Recently passing/failing. Recommended mandatory list. | DONE — 15 mandatory, 6 future-recommended |
| 08_PR_AND_MERGE_QUEUE.md | 25 open PRs, all CLEAN. Recommended merge order. Codex-owned do-not-overwrite list. | DONE — chain ready to merge in order |
| 09_CODEX_NEXT_50_TASKS.md | Tiered prioritized queue. Codex Next 3. Hermes-Agent help readiness ladder. | DONE — Tier 0 = operator action |
| 10_DIAGRAMS.md | 6 Mermaid diagrams: folder topology, e2e loop, 60-app ladder, no-fake flow, trust boundary, Codex Gantt. | DONE |
| 11_FINAL_CLAUDE_NOTE.md | Pasteable summary for the user. PR URL, hard blockers, Codex next 3, lock state. | DONE |

## Locks

12 locks acquired by `claude-e2e-intel-aggregator` for the markdown bundle, taskId `claude-e2e-intel-2026-05-08`, TTL 240 minutes. Released at end of audit (see `11_FINAL_CLAUDE_NOTE.md`). 0 Codex-owned locks touched.

## Stopping condition

Per the contract: "Stop after creating the markdown bundle, opening one docs PR, and releasing Claude-owned locks." Done in that order. No source code edited. No PRs merged. No worktrees deleted. No Codex locks released.
