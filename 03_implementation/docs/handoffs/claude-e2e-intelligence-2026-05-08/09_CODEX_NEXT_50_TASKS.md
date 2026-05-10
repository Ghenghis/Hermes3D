# 09 — Codex Next 50 Tasks

> Generated 2026-05-08 from live `/api/code-operator/e2e/readiness`, `/api/roadmap/tab-completion`, `/api/modules/runtime/runner-contracts`, and `03_implementation/proof/SOURCE_APP_RUNTIME_ACTION_PLAN.md`. Source-of-truth roadmap is `G:\Github\h3d-gui-wiring-codex\03_implementation\ROADMAP.md`. Live API: `http://127.0.0.1:8765` on branch `codex/provider-smoke-workbench` commit 43d8205. **PR 104 is currently OPEN** (mergeable, CodeRabbit SUCCESS, base `codex/hermes-agent-e2e-workbench`); the Codex chain `73→83→84→85→87→88→…→104` still needs to land in chain order. The 60-app target stays at 60 source-backed rows; do not expand the count.

## What is true right now

- Runtime API on PR 104 ships all 10 Agent Workbench routes; `/api/code-operator/*` exposes patch apply, gates, MCP locks, branch/commit/PR, providers/smoke, e2e/readiness, and history snapshots.
- Live `e2e/readiness` returns `status: blocked, ready: false`. `provider_lanes[*].status = auth_failed` for both **MiniMax** (`api.minimax.io`, `MiniMax-M2.7`) and **DeepSeek** (`api.deepseek.com`, `deepseek-v4-pro`); HTTP 401 redacted, evidence `ev_51f12274c079a62f` and `ev_ca72de163072224c`. **MCP locks ready** (server `hermes3d-locks` at `G:\Github\hermes3d-mcp-lock-orchestrator`), code-history has 7 snapshots, sandbox image present (393 MB), OpenCode 1.4.3-hermes3d + OpenHands 1.16.0 detected, write runs still policy-blocked.
- Verifier registry: 60 module rows. Counts from live runner-contracts: agent_executable=7, runner_gaps=24, by_runner_status: agent_cli_ready=7, blocked=2, desktop_app_runner_gap=3, gpu_worker_runner_gap=3, launcher_metadata_only=3, metadata_ready_needs_runner=5, npm_package_runner_gap=1, readonly_api_ready=3, runtime_repair_required=15, source_reference_only=18.
- 18 UI tabs: 9 DONE (Dashboard, Simple, Observe, Printers, Agents rail, Artifacts, Jobs, Approvals, Voice STT lane), 9 IN_PROGRESS (Source OS, Settings, Plugins, Autopilot, Learning, Voice, Design, 3D Generation, Roadmap).

## The bottleneck (read first)

**Codex cannot help finish the Hermes Agent co-development loop until the operator replaces both API keys.** All Tier 1+ Codex work below is real work even with providers down — Codex does not need MiniMax/DeepSeek to write Codex's own PRs. But the **agent coding loop tier (Tier 1)** is dead until keys come back from 401. Tier 0 is therefore the only blocking item the operator must do; everything else Codex moves forward on regardless.

---

## Tier 0 — USER ACTION REQUIRED (P0, blocks Tier 1 agent loop only)

The user must replace the `MINIMAX_*` and `DEEPSEEK_*` lines in `G:/private/.env`, restart the API process (`run.bat` or the supervisor), and rerun the Agent Code Workbench provider smoke buttons. Acceptance: `POST /api/code-operator/providers/smoke {"provider_id":"minimax"}` and `..."deepseek"` both return `accepted=true, status=ok`, evidence written, `e2e/readiness.ready === true`. Until this is true, **no agent-built PRs land**, but Codex's hand-written PRs continue.

## Tier 1 — Agent coding loop e2e (P0, Codex). Tasks 1–7

After Tier 0 unblocks, Codex's job is to land the **first end-to-end MiniMax-builds + DeepSeek-reviews + locks + gates + PR-shipped** smoke inside one session, on a small, reversible target. Until then, Codex stages the contract scaffolding so the moment keys flip green, the loop runs.

## Tier 2 — Source OS source-ready runner gaps (P0, Codex). Tasks 8–14

The 7 outstanding runner-gap families that need bounded verifier registration following the existing PR chain. PRs 89/91/93/95/97/99/101 set the pattern: each PR adds **one launch-kind family**, ships verifier + verify-route + setup-plan + UI badge.

## Tier 3 — Source OS / Settings / Plugins App Update Center (P1, Codex). Tasks 15–22

Backup → check → update → smoke gate → rollback → approval, executed for every of the 60 app families. PR 69 wired Settings/Plugins UI surfaces; the orchestration layer is partial.

## Tier 4 — Agent action catalog parity (P1, Codex). Tasks 23–32

Every visible UI action must have one matching `/api/agents/action-catalog` entry calling the same backend route. Today's cataloged actions are a subset of buttons in the live `<App>` shell.

## Tier 5 — Density/responsive pass on every tab (P2, Codex). Tasks 33–39

Per-tab density + draggable panels + Simple/Main parity tighten-up matching the dashboard reference.

## Tier 6 — Docs/proof sync (P2, Codex). Tasks 40–44

README, ROADMAP, action plans, proof manifests must point at PR 104 evidence chain head and the corrected catalog totals.

## Tier 7 — Future / waiting on Tier 0+1 success (P3, Codex). Tasks 45–50

Provider coverage expansion (Design/Gen3D), fleet onboarding wizard, idle automation execution, voice/observe operator assist. Each waits either on Tier 0 (provider keys) or Tier 1 (agent loop proven once).

---

## Tasks Table (50 rows)

| # | P | Task | Files / Routes | Prereq | Acceptance proof | Risk | Hermes Agents helping yet? |
|----|----|------|----------------|--------|------------------|------|---------------------------|
| 0 | P0 | **OPERATOR** Replace MiniMax + DeepSeek keys in `G:/private/.env`, restart API, click both smoke buttons | `G:/private/.env`, restart `run.bat` | none | `e2e/readiness.ready=true`, `provider_lanes[*].live_status=ok`, fresh evidence_id pair | low | n/a |
| 1 | P0 | Pick the smallest reversible code change as first agent-built PR target (e.g. typo in `03_implementation/ROADMAP.md` "blocker" wording, or one log message) | `03_implementation/ROADMAP.md` only | task 0 | task chosen, file path written into task notes, single-line patch ready | low | no |
| 2 | P0 | Through Agent Code Workbench: claim Hermes task `h3d-agent-first-real-loop`, lock the file, snapshot, run MiniMax coding pass | `/api/code-operator/teams/run-coding-pass`, `mcp-locks/claim-task`, `mcp-locks/lock-files`, `history/snapshots` | tasks 0+1 | task active, lock owned, snapshot id recorded | med | no — running them |
| 3 | P0 | Run DeepSeek review pass against the MiniMax patch proposal | `/api/code-operator/teams/run-review-pass`, `patch/proposals` | task 2 | review verdict accepted/blocked recorded; evidence appended | med | no — running them |
| 4 | P0 | Apply only the reviewed patch via `patch/apply-reviewed`, run `git-diff-check` and `tests.unit` gates | `patch/apply-reviewed`, `gates/run` | task 3 | patch sha-checked, both gates PASS, ev_*` chained | med | no — running them |
| 5 | P0 | Branch + commit-owned + push + open PR through git lane | `/api/code-operator/git/branch`, `git/commit-owned`, `git/push`, `git/pr` | task 4 | PR URL on Ghenghis/Hermes3D opens cleanly, body cites all evidence ids | med | no — running them |
| 6 | P0 | Restore-rollback drill: snapshot restore the touched file, prove rollback parity | `history/restore`, `mcp-locks/release-files`, `mcp-locks/release-task` | task 5 | restore returns 200, file back to pre-task sha, evidence recorded | low | no |
| 7 | P0 | Document the first agent-built PR in `03_implementation/proof/HERMES_AGENT_FIRST_LOOP_PROOF_2026-05-08.json` and link from `09_CODEX_NEXT_50_TASKS.md` | proof folder, this file | task 5 | proof JSON committed, all 5 evidence ids cross-linked | low | yes |
| 8 | P0 | **Cli-preferred-gap**: register MeshLab CLI verifier (locate `meshlabserver.exe` or fall back to read-only metadata) | `03_implementation/src/hermes3d/services/runtime/verifiers/meshlab_cli.py` (new), `/api/modules/meshlab/runtime/verify` | PR 87/89 pattern | verify returns ready+executed=true, proof gate `agent-cli-verifier-v1` | low | yes after Tier 1 |
| 9 | P0 | **Cli-preferred-gap**: Slic3r + Strec3D + SuperSlicer verifiers (3 modules, share runner family with PrusaSlicer) | same family services dir, `/api/modules/{slic3r,strec3d,superslicer}/runtime/verify` | task 8 | 3 verify routes ready, smoke proof event chain | low | yes after Tier 1 |
| 10 | P0 | **Desktop-app-gap**: FreeCAD + SolveSpace + MatterControl bridge verifiers (use `--help` headless or `--version`) | `verifiers/desktop_bridge.py` extension, 3 verify routes | task 8 | 3 desktop verifiers green or fail-closed with exact reason | med | yes after Tier 1 |
| 11 | P0 | **Gpu-worker-gap**: Microsoft TRELLIS.2 + Tencent Hunyuan3D 2.1 + TripoSR dependency/model-cache verifiers (read-only python import + cache path stat, no GPU job launch) | `verifiers/gpu_dependency.py` (new), 3 verify routes, ROADMAP entry | tasks 8 + 11's plan | 3 verifiers report ready/blocked w/ model path proof | med | yes after Tier 1 |
| 12 | P0 | **Npm-package-gap**: Azure Speech SDK JS package metadata verifier (build PR 101's pattern; not the secrets path) | `verifiers/npm_package.py` extension, `/api/modules/azure_speech_sdk_js/runtime/verify` | PR 101 pattern | verify returns ready+executed=true, no key leak | low | yes after Tier 1 |
| 13 | P0 | **Python-worker-gap**: CadQuery + Open3D + build123d + numpy-stl + pymesh isolated python-import verifiers (PR 99 pattern, 5 modules) | `verifiers/python_import_repair.py` extension, 5 verify routes | PR 99 pattern | 5 verify routes ready, manifest updated | low | yes after Tier 1 |
| 14 | P0 | **Service-gap and web-app-gap**: Manyfold + Open Filament Database + FDM Monster + OctoPrint + ComfyUI + ComfyUI TRELLIS wrapper + Fluidd + Mainsail + Kiri:Moto/GridSpace local-http-health verifiers (6 service + 3 web_app = 9 modules; PR 91/93 pattern) | `verifiers/local_http_health.py` extension, 9 verify routes | PR 91/93 pattern | 9 verify routes return ready/blocked with port probe proof | med | yes after Tier 1 |
| 15 | P1 | App Update Center: scaffold one shared `services/update_orchestrator.py` (backup → check → update → smoke gate → rollback) | `services/update_orchestrator.py` (new), `/api/modules/{id}/update/*` | tasks 8–14 | one module passes full backup→update→smoke→rollback drill end-to-end | med | yes after Tier 1 |
| 16 | P1 | Update Center: per-app SmokeGate adapter contract for slicer family (Cura/PrusaSlicer/OrcaSlicer/Slic3r/SuperSlicer/FLSUN) | `services/smoke_gates/slicer.py` (new), `update/apply` | task 15 | 6 slicer modules carry post-update smoke evidence | med | yes after Tier 1 |
| 17 | P1 | Update Center: per-app SmokeGate adapter for modeler family (Blender/OpenSCAD/CadQuery/build123d/manifold/trimesh/Open3D/MeshLab) | `services/smoke_gates/modeler.py` (new) | task 15 | 8 modeler modules carry post-update smoke evidence | med | yes after Tier 1 |
| 18 | P1 | Update Center: per-app SmokeGate for service family (Moonraker/Fluidd/Mainsail/OctoPrint/OctoFarm/FDM Monster/Manyfold/Open Filament DB/ComfyUI/ComfyUI TRELLIS) | `services/smoke_gates/service.py` (new) | task 15 | 10 service modules carry post-update smoke evidence | med | yes after Tier 1 |
| 19 | P1 | Update Center: agent runtime self-update lane (Hermes Agent runtime + Atomic Hermes patterns + OpenCode + OpenHands) — backup before, smoke after, rollback if fail | `/api/agents/update/*`, `services/update_orchestrator.py` | task 15 | live agent self-update drill written to proof | high | yes after Tier 1 |
| 20 | P1 | Update Center: All-app release watch (GitHub latest-release polling, cached, no frontend loops) | `services/release_watch.py` (new), `/api/modules/update/readiness` | task 15 | 60 modules show latest_release/latest_commit or exact blocked reason | low | yes after Tier 1 |
| 21 | P1 | Update Center: approval policy stage (queue → user approve/deny → execute) wired into `/api/approvals/*` | `routes/approvals.py`, `routes/modules.py` | tasks 19+20 | one approval round-trip writes proof events end-to-end | med | yes after Tier 1 |
| 22 | P1 | Update Center: Settings/Plugins UI density polish + count truth (Plugins must show all 60 with backup/check/update/rollback badges) | `ui/src/views/SettingsView.tsx`, `PluginsView.tsx` | tasks 15–21 | screenshot proof, density matches dashboard reference | low | yes after Tier 1 |
| 23 | P1 | Action catalog audit: scan every UI button in `ui/src/views/*.tsx` and emit a coverage delta against `/api/agents/action-catalog` | `scripts/audit_action_catalog_parity.py` (new) | none | report shows every visible button mapped to a catalog id or exact blocked reason | low | yes after Tier 1 |
| 24 | P1 | Action catalog: add catalog rows for missing Source OS controls (Verify All, Setup Queue, Setup Plan, per-row Backup/Check/Update/Rollback) | `routes/agents/action_catalog.py`, `services/action_catalog/sources.py` | task 23 | catalog count grows by ≥7; live `/action-catalog` includes them | low | yes after Tier 1 |
| 25 | P1 | Action catalog: add catalog rows for Settings update center actions | same family as 24 | task 23 | catalog covers all `/api/settings/update-center/*` routes | low | yes after Tier 1 |
| 26 | P1 | Action catalog: add catalog rows for Autopilot guardrails + idle queue + write-plan/write-report | `services/action_catalog/autopilot.py` | task 23 | 4 new actions, proof events recorded | low | yes after Tier 1 |
| 27 | P1 | Action catalog: add catalog rows for Voice STT/TTS/transcripts + voice/proof-events | `services/action_catalog/voice.py` | task 23 | 5 new actions, transcript artifact proof | low | yes after Tier 1 |
| 28 | P1 | Action catalog: add catalog rows for Design intake/specs/templates/providers + Gen3D run/services/templates | `services/action_catalog/design_gen3d.py` | task 23 | 8 new actions, fail-closed when provider not configured | low | yes after Tier 1 |
| 29 | P1 | Action catalog: add catalog rows for printers/onboard/probe/upload/start/move/test (S1 lock enforced) | `services/action_catalog/printers.py` | task 23 | 7 new actions, S1 actions return blocked reason text | low | yes after Tier 1 |
| 30 | P1 | Action catalog: add catalog rows for code-operator/* (already partially live) — make every `/api/code-operator/*` route reachable from agent chat | `services/action_catalog/code_operator.py` | task 23 | every route in `/api/code-operator/*` has a catalog row | med | yes after Tier 1 |
| 31 | P1 | Action catalog: every catalog row must declare `safety_policy`, `approval_required`, `proof_event`, `rollback_or_no_rollback_reason` | `models/action_contract.py`, all `services/action_catalog/*.py` | tasks 23–30 | catalog audit script PASS; rows missing fields fail closed | med | yes after Tier 1 |
| 32 | P1 | Action catalog: pre-push gate runs catalog parity scan and fails if buttons grow without coverage | `policies/gates/action_catalog_parity.json` (new), CI hook | tasks 23–31 | gate runs in pre-push, breaking PR shows clear delta | low | yes after Tier 1 |
| 33 | P2 | Density pass: Source OS — match Simple dashboard density, no card empties, draggable lists | `ui/src/views/SourceOSView.tsx`, `ui/src/components/ResizablePanel.tsx` | none | screenshot proof at 1280/1440/1920 widths | low | yes after Tier 1 |
| 34 | P2 | Density pass: Settings — every section uses available width, persisted resize | `ui/src/views/SettingsView.tsx` | none | screenshot proof | low | yes after Tier 1 |
| 35 | P2 | Density pass: Plugins | `ui/src/views/PluginsView.tsx` | none | screenshot proof | low | yes after Tier 1 |
| 36 | P2 | Density pass: Autopilot + Learning (idle workbench) | `ui/src/views/AutopilotView.tsx`, `LearningView.tsx` | none | screenshot proof | low | yes after Tier 1 |
| 37 | P2 | Density pass: Voice (transcript history table density + waveform sizing) | `ui/src/views/VoiceView.tsx` | none | screenshot proof | low | yes after Tier 1 |
| 38 | P2 | Density pass: Design + 3D Generation (template gallery cards) | `DesignView.tsx`, `Gen3DView.tsx` | none | screenshot proof | low | yes after Tier 1 |
| 39 | P2 | Density pass: Roadmap (this ledger as a live UI panel, not just markdown) | `ui/src/views/RoadmapView.tsx` | tasks 33–38 | UI panel reads `/api/roadmap/tab-completion` and matches markdown | low | yes after Tier 1 |
| 40 | P2 | Docs sync: README pointing at correct tab counts (18), printer policy (T1×2 + S1 locked + V400), 60-app target, current evidence chain head | `README.md`, `Hermes3D-OS.md` | tasks 7+22 | doc-sync gate PR shows zero drift | low | yes after Tier 1 |
| 41 | P2 | Docs sync: ROADMAP.md current proof IDs sweep — refresh every `proof event:` line to match `/api/proof/events` head | `03_implementation/ROADMAP.md` | none | line-by-line diff shows no stale IDs | low | yes after Tier 1 |
| 42 | P2 | Docs sync: regenerate `SOURCE_APP_RUNTIME_ACTION_PLAN.md` after tasks 8–14 land | `scripts/write_source_runtime_action_plan.py` | tasks 8–14 | runner_gaps count drops; regenerated md committed | low | yes after Tier 1 |
| 43 | P2 | Docs sync: regenerate `SOURCE_APP_60_COMPLETION_AUDIT.json`, `SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json`, `SOURCE_APP_CLI_SURFACE_AUDIT.json` | scripts in `03_implementation/scripts/audit_*.py` | tasks 8–14 | three JSON proofs regenerated | low | yes after Tier 1 |
| 44 | P2 | Docs sync: PROOF_MANIFEST_2026-05-08.json captures the day's PR chain (PR 104, agent first loop, runner-gap PRs, update center PRs) | `03_implementation/proof/PROOF_MANIFEST_2026-05-08.json` (new) | tasks 7+22+42 | manifest includes ≥10 evidence ids | low | yes after Tier 1 |
| 45 | P3 | Provider coverage: Design — wire OpenSCAD provider lane behind `/api/design/providers`, fall-back to existing local templates if blocked | `services/design/providers/openscad.py` (new), `routes/design.py` | tasks 17 | OpenSCAD-backed design intake completes one real STL, not just a template | med | yes after Tier 1 |
| 46 | P3 | Provider coverage: Gen3D — wire ComfyUI provider lane behind `/api/gen3d/services`, fall-back to local cube template | `services/gen3d/providers/comfyui.py` (new), `routes/gen3d.py` | tasks 14+18 | ComfyUI service-backed gen3d completes a real STL | med | yes after Tier 1 |
| 47 | P3 | Provider coverage: Gen3D — TRELLIS.2 wrapper provider lane, fail-closed when GPU not present | `services/gen3d/providers/trellis.py` (new) | tasks 11+46 | trellis run blocked-reason path or success | med | yes after Tier 1 |
| 48 | P3 | Fleet onboarding wizard: end-to-end add-a-printer wizard (probe Moonraker → camera URL → safety → save → proof event) without TOML edit | `ui/src/views/PrintersView.tsx`, `routes/printers.py` (`onboard`) | task 39 | one new printer onboarded by wizard, S1 policy preserved | med | yes after Tier 1 |
| 49 | P3 | Idle automation execution: connect Autopilot idle queue to safe agent runners; fail-closed when system not quiet (queued jobs, S1 active, pending approvals) | `services/idle_workbench.py`, `routes/autopilot.py` | tasks 11+19+26 | one idle research candidate generated, gated, recorded | high | yes after Tier 1 |
| 50 | P3 | Voice + Observe operator assist: voice → snapshot → plate clearance → agent context, end-to-end during a real T1 print (S1 stays read-only) | `services/voice/operator_assist.py`, `routes/observe.py` | tasks 27+29+39 | one voice→snapshot→agent-action chain recorded with proof | high | yes after Tier 1 |

---

## Codex Next 3 (point Codex here)

1. **Task 1+2+3 (combined)**: Pick the smallest reversible target (single-line edit in `03_implementation/ROADMAP.md` "Remaining Blocker" section pointing at PR 104), then drive **MiniMax coding pass → DeepSeek review pass** through the Workbench and capture both evidence ids. (Cannot proceed past this until **Tier 0 user action** is done — but Codex stages the patch text and the Workbench UI flow now so the moment keys flip, it's one click.)
2. **Task 8 (MeshLab CLI verifier)**: while waiting on Tier 0, ship the MeshLab verifier PR. It is the smallest of the cli_preferred_gap rows, follows PR 89 pattern exactly, requires no provider, and reduces runner_gap from 24 → 23 with a clean evidence chain.
3. **Task 23 (action catalog parity audit script)**: write `scripts/audit_action_catalog_parity.py`. It is read-only, useful regardless of provider state, and outputs the data that Tasks 24–30 consume. Output the parity report as a proof JSON so Tier 4 PRs can reference it directly.

If Tier 0 has already cleared by the time Codex picks this up, the order becomes 1 → 2 → 3 above (literal numbers). If not, the order becomes 8 → 23 → 1-staged.

---

## Hermes-Agent-help-readiness ladder

| Tier | Help readiness | Why |
|------|----------------|-----|
| Tier 0 (operator key swap) | Never (this is operator-only) | Hermes Agents cannot edit `G:/private/.env`; it is path-denied in sandbox `denied_paths`. |
| Tier 1 (agent loop e2e, tasks 1–7) | After Tier 0 | The whole point of Tier 1 is **proving** Hermes Agents can co-build. They become the workers as soon as Tier 0 clears. Codex is the human-supervised driver for the first loop only; subsequent loops can hand off. |
| Tier 2 (runner gaps, tasks 8–14) | After Tier 1 | Once one agent-built PR lands, the same agent loop ships these 7 family PRs faster than Codex hand-builds. They follow an identical PR pattern (PR 89 → 91 → 93 → …) so the agent template is the same. |
| Tier 3 (update center, tasks 15–22) | After Tier 1 | High-risk shared service (rollback paths) — agent loop must be proven once, then it can build update orchestrator under MCP locks. |
| Tier 4 (action catalog, tasks 23–32) | After Tier 1 | Pure schema/scaffolding work, ideal for agent loop. |
| Tier 5 (density pass, tasks 33–39) | After Tier 1 | UI tweaks are a great agent-loop target — small reversible diffs, screenshot proof gate. |
| Tier 6 (docs/proof sync, tasks 40–44) | After Tier 1 | Read-mostly with bounded diff; agent loop is well-suited. |
| Tier 7 (future, tasks 45–50) | After Tier 1 + the relevant Tier 2/3 prereq | Provider lanes need Tier 2 (verifiers) + Tier 3 (orchestrator) green; idle/voice operator assist need Tier 4 (catalog) + Tier 5 (UI). |

In short: **only Tier 0 is operator-only**. The instant Tier 0 turns green, the rest of this 50-row queue can be split between Codex and Hermes Agents, with Codex driving the first agent-built PR (Tier 1) and then the agents taking over progressively heavier loads.

### Critical Files for Implementation

- G:\Github\h3d-gui-wiring-codex\03_implementation\ROADMAP.md
- G:\Github\h3d-gui-wiring-codex\03_implementation\proof\SOURCE_APP_RUNTIME_ACTION_PLAN.md
- G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\api\routes\code_operator.py
- G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\api\routes\agents.py
- G:\Github\h3d-gui-wiring-codex\03_implementation\src\hermes3d\services\code_history.py
