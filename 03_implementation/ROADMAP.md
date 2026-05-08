# Hermes3D OS Tab Completion Roadmap

Updated: 2026-05-08
Owner: codex-master
Task: H3D-CODEX-HERMES-AGENT-E2E-ROADMAP

## Contract

Every visible Hermes3D OS surface must be useful, dense, real, and responsive. A control may call a live backend/local/API path, show a verifiable blocked reason, or be disabled until the missing source is configured. It must not pretend success.

Operator layout preference:
- Compact font scale close to the Simple dashboard reference image.
- Dashboard surfaces should fit the active app window without main-body scroll at normal desktop operator viewports.
- Other tabs may scroll when their work naturally needs it, but cards and tables must use all available space without over-large type or decorative emptiness.
- Hermes Agents chat remains accessible from the left rail on all tabs and must not cut off at resized browser heights; user-facing side rails must be draggable, shortenable, resettable, and persisted instead of fixed-width.

Printer policy:
- T1 #1: 192.168.0.10, Moonraker/Klipper, testable.
- T1 #2: 192.168.0.11, Moonraker/Klipper, testable.
- FLSUN S1: 192.168.0.12, camera/read-only allowed, printer actions locked until user changes status.
- FLSUN V400: 192.168.0.34, Moonraker/Klipper, testable; USB webcam camera URL is configured and read through Observe.

## Current Completion Ledger

| Tab or surface | Status | Proof / remaining gap |
| --- | --- | --- |
| Dashboard | DONE | Live backend data, compact dashboard/simple mode, viewport proof in ACTIVE_UI_NO_FAKE_SWEEP.md. |
| Simple GUI | DONE | Pixel-reference inspired compact dashboard is selectable, live-backed, and its left rail mirrors the canonical primary tabs while staying in Simple and embedding real tab components. |
| Observe | DONE | Live camera cards for T1 #1, T1 #2, S1, and V400; Refresh visibly reconnects 4/4 configured feeds without leaving `#observe`; S1 90-degree default, resize/undock/feed controls, and plate-clear actions route through backend policy. |
| Printers | IN_PROGRESS | Correct T1/S1/V400 IP policy, S1 locked, guarded T1 print proof recorded, onboarded-printer rows now appear after the fixed fleet; next gap is fuller profile/source-ref wizard polish. |
| Source OS | IN_PROGRESS | Source registry truth audit currently proves 60/60 source-backed app rows. Runtime Readiness currently shows 36 verifier-backed ready apps, 7 source-ready runner-not-registered rows, 15 runtime-repair rows, and 2 blocked rows with explicit `ready/source/setup/install/blocked` badges, Verify All, Setup Queue, selected-app Verify, selected-app Setup Plan write proof, and Backup/Check Update/Update/Rollback live backend routes. `/api/modules/runtime/runner-contracts` now exposes the canonical 60-row Hermes Agent execution matrix: 7 rows are `agent_executable=true`, 8 rows are `read_only_runner_available=true` through `/api/modules/{module_id}/runtime/read-only-runner`, 3 rows are `executable_path_runner_available=true` through `/api/modules/{module_id}/runtime/executable-path-runner`, 5 rows are `python_import_repair_available=true` through `/api/modules/{module_id}/runtime/python-import-repair-runner`, 2 rows are `cli_install_config_available=true` through `/api/modules/{module_id}/runtime/cli-install-config-runner`, 1 row is `npm_package_preflight_available=true` through `/api/modules/{module_id}/runtime/npm-package-runner`, 24 rows remain runner gaps/repair blockers, and every non-executable row carries required verifier family, safe actions, and blocked reason. The registered verifier set now has 53 enabled probes: 7 agent-usable CLI probes, 3 desktop launcher metadata probes, 18 read-only source-inventory probes including the five firmware repositories, 5 package/import probes including Blender MCP source-import plus the MeshLab `pymeshlab` bridge, 5 Python import repair probes for CadQuery/Open3D/build123d/numpy-stl/PyMesh, 3 read-only Moonraker/Klipper fleet probes, and 10 local/private HTTP health probes for FDM Monster, Fluidd, Mainsail, OctoFarm, OctoPrint, Manyfold, Open Filament Database, Kiri:Moto/GridSpace, ComfyUI, and the ComfyUI TRELLIS wrapper. The read-only runner smoke route reruns only already-registered package/import/local API proof and appends evidence; the executable-path smoke route reads only installed launcher file metadata/hash for Printrun, BambuStudio, and Cura; the CLI install/config preflight reads only Slic3r/SuperSlicer source, adapter schema, profile/config, and candidate executable metadata; the npm package metadata preflight reads only Azure Speech SDK JS package.json, script names, lockfile/manifests, and local node/npm executable presence. These routes cannot launch, install, update, slice, write outputs, or touch printers. All firmware rows are source-reference-only: Marlin, Prusa Firmware, RepRapFirmware, Repetier Firmware, and Smoothieware prove local source inventory only and expose no compile, flash, upload, or printer action. All 10 `HERMES3D_SOURCE_*_URL` keys are now created in `G:/private/.env` with non-secret local/private defaults, but those HTTP rows stay setup-required until the actual local services answer their non-mutating health/version probes. Loader launch-kind overrides reduce the vague `unknown` bucket to 0/60. The CLI-surface audit proves 24 local CLI/service hints still need verifier/runner work before Hermes Agents can execute them. |
| Agents rail/chat | UI_DONE_RUNTIME_PARTIAL | Browser mic, voice-note upload, file attachments, quick context prompts, Azure voice playback for agent replies, real runtime/SSE when configured, a bounded Hermes Agent Playwright proof runner, the OS operator action catalog surface, provider live-smoke proof buttons, and the Agent Code Workbench planning/review loop exist. The workbench now exposes reviewed patch apply, gate, branch, stage, commit, push, and PR controls backed by code-operator routes, plus a runtime-freshness guard that proves the live backend branch/commit/source path and required Agent Workbench routes so stale 404s cannot look like random agent failure. OpenCode is now built from local source and detected as `1.4.3-hermes3d`; OpenHands CLI is installed and detected as `OpenHands CLI 1.16.0`; Docker sandbox readiness proves daemon version, configured image presence, denied paths, and `none` network mode; both CLI preflights pass with MCP evidence. This does not mean Hermes Agents can fully co-develop Hermes3D yet: the backend now accepts the user's `G:/private/.env` aliases (`MINIMAX_*` and `DEEPSEEK_*`) and shows redacted source provenance in Settings/Agents, but provider chat-completions smoke still returns redacted HTTP 401, so provider-backed execution remains blocked until the rejected private provider values are corrected and both provider smokes pass. |
| Artifacts | DONE | Agent attachments and proof files are inspectable through live artifacts API. |
| Settings | IN_PROGRESS | Hermes Agent/Desktop update failsafes exist; printer onboarding form probes live Moonraker before save; backend launchers load `G:/private/.env` server-side only; Environment now shows a live runtime readiness ledger plus the Source App Setup Queue; next gap is app-wide update execution and daily idle automation runner setup. |
| Plugins | IN_PROGRESS | Plugin state is live-backed; source app update-readiness summary and runtime setup queue counts are visible; next gap is unified release watch and all-app update planning. |
| Jobs | DONE | Live job list/detail exists; proof-gated pipeline renders backend transition state; cancel, repair proposal, repair apply/escalation, retry, and rollback routes append proof/job events and are UI-wired. |
| Autopilot | IN_PROGRESS | Guardrails and readiness routes exist; next gap is idle safe-work queue plus evidence-gated execution. |
| Learning | IN_PROGRESS | Idle mode selection persists, daily queue API/UI records reviewable candidates, runtime truth now reports Hermes Agent runtime and idle runner ready. Research reports are execution-ready; documentation, workflow, app update, and printer maintenance stay blocked while S1 policy and queued job blockers are active. |
| Voice | IN_PROGRESS | Voice catalog/preview, chat mic, voice-note artifacts, Azure fast STT transcription, and per-agent Azure reply playback are backend-wired with proof; next gap is richer transcript review/history and Observe snapshot-to-agent voice workflows. |
| Design | IN_PROGRESS | P0 executor MVP is live for the real parametric desk-organizer template: `/api/design/intake` writes an STL, proof envelope, job steps, artifacts, truth-gate row, and proof event. Remaining Design gap is broader OpenSCAD/CadQuery/Blender/prompt-to-CAD coverage. |
| 3D Generation | IN_PROGRESS | P0 local generator MVP is live for the real calibration-cube template: `/api/generation/run` writes an STL, preview SVG, proof envelope, job steps, artifacts, truth-gate row, and proof event. Remaining Gen3D gap is broader ComfyUI/TRELLIS.2/Hunyuan3D/provider-backed generation coverage. |
| Approvals | DONE | Pending/approved/rejected approval actions are live-backed. |
| Roadmap | IN_PROGRESS | This file plus /api/roadmap/tab-completion track the current tab ledger. |

## UX/UI Completion Position

Overall status: about 78% complete toward the user's strict e2e GUI finish target.

The roadmap is accurate enough to drive the next work, but it is not considered complete until every item in the finish queue below is either DONE with proof or explicitly blocked by a real missing dependency. The current app shell, Simple GUI routing, dashboard density, Observe cameras, agent rail/chat, artifacts, approvals, source registry proof, Source OS runtime-state verifier/setup queue, Design executor MVP, 3D Generation executor MVP, Jobs repair/rollback transitions, and many live backend adapters are in place. The remaining work is mostly execution depth: broader generation providers, all-app update/rollback orchestration, idle automation execution, safe source-app setup runners, and final tab-by-tab polish.

Definition of roadmap completion:
- Every primary tab has a live backend data path, a disabled/blocked reason, or a real operator action.
- Simple mode and Main mode render the same real tab capabilities without silently switching modes.
- Every source app shows installed/source state, runtime readiness, update readiness, backup target, rollback target, and gate result.
- Every printer action is policy-gated, proof-recorded, and respects S1 locked/read-only status.
- Every Hermes Agent action either reaches a configured runtime/tool path or returns a precise blocked reason.
- Hermes Agent QA actions run through fixed proof scopes (`observe`, `smoke`, `full`) and store Playwright artifacts/proof events, rather than relying on agents self-reporting that the UI works.
- Settings Environment shows a runtime readiness ledger for the missing-runtime question, with exact env keys/proof endpoints and no secret values. Current local state is 7 ready, 2 partial, 0 blocked after loading Hermes Agent runtime, idle learning runner, and proof signing from `G:/private/.env`.
- Router hash synchronization keeps the URL and active mounted tab aligned, including Simple embedded live-tab mode, so buttons cannot appear unresponsive because another tab stayed mounted behind a changed hash.
- GUI launch now selects open local ports for the UI, GUI API, and Desktop compatibility API, writes `03_implementation/var/runtime-ports.json`, and passes the selected API port into Vite so Hermes3D still loads when the default ports are occupied.
- Printer fleet polling uses bounded parallel Moonraker probes; slow printers surface as `degraded` telemetry instead of falsely blocking the UI, while physical action routes still run strict live gates.
- Final Playwright, TypeScript, no-fake scan, route probes, and targeted printer/camera checks are recorded in proof.

## Full E2E Finish Queue

P0 correction from 2026-05-08:

- The active project priority is Hermes Agent co-developer runtime, not more manual runner-gap slices.
- Source OS runner work remains queued, but Hermes Agents are not considered working until they can help close those gaps through the same proof-gated coding loop Codex uses.
- The folder index from PR #86 is now required agent boot context at `03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/`. Before an agent coding task starts, MiniMax and DeepSeek must load the relevant handoff index files, name the files used in the task record, and prove the chosen files match the folder ownership context.
- Current live smoke proof for this workbench slice: folder-index and MCP lock readiness pass, `G:/private/.env` aliases are loaded and shown only as redacted sources, but MiniMax and DeepSeek chat execution are both blocked by redacted HTTP 401 from their configured private provider values. The route now returns redacted blocked reasons and evidence instead of crashing or claiming a usable provider.
- The complete truth/proof contract lives in `03_implementation/docs/handoffs/HERMES_AGENT_E2E_TRUTH_PROOF_PLAN_2026-05-08.md`.

Next working order:

1. DONE in the current workbench slice: build the Hermes Agent Code Workbench in Agents UI so the user can submit a real coding task with title, objective, files, target branch, provider team, and required roles.
2. PARTIAL in the current workbench slice: add backend orchestration for one E2E coding job through folder-index context -> programming/provider readiness -> file locks -> pre-snapshots -> MiniMax coding pass -> DeepSeek review pass -> evidence/release. Reviewed patch apply -> gates -> branch/stage/commit/push/PR controls are now visible in Agents and call real code-operator routes, but the first closed automatic E2E task is still blocked until MiniMax and DeepSeek live smoke pass.
3. DONE in the current workbench slice: add OpenHands/OpenCode CLI runner detection and read-only preflight as optional worker backends using the same MiniMax/DeepSeek provider pool. OpenCode and OpenHands executables are detected, Docker sandbox image inspection passes, and both preflights append MCP evidence. Keep write-capable run blocked until MiniMax/DeepSeek smoke, task-scoped container execution, output capture, review handoff, gates, and proof capture are configured.
4. BLOCKED on provider auth: add the first real smoke task that Hermes Agents complete end-to-end against a low-risk Hermes3D file, then record proof ids and PR URL.
5. Only after that passes, resume Source OS 24 runner gaps using Hermes Agents as co-workers rather than Codex closing rows alone.

| Priority | Work package | Status | Acceptance before DONE |
| --- | --- | --- | --- |
| P0 | Design executor MVP | DONE | Live proof job `2a5d92b42897401490962dfa0c13e4fe` generated `desk_organizer_150df888cd.stl`, `desk_organizer_150df888cd.proof.json`, and passed `design.parametric_mesh`. Unsupported prompts fail closed with supported-template guidance. |
| P0 | 3D Generation executor and preview proof | DONE | Live proof job `56954aa084b94a71a3bea4cb38f72f55` generated `calibration_cube_c8f48130af.stl`, `calibration_cube_c8f48130af.preview.svg`, `calibration_cube_c8f48130af.proof.json`, inserted proof event `bff1c6b5608e4384ad2e9c3fe4e5e5b5`, and passed truth status `pass`. Unsupported arbitrary prompts fail closed with provider setup guidance. |
| P0 | Jobs repair/rollback transitions | DONE | Live proof job `a936044cad8e4b07b378bd53c0ed1187` created REPAIR_APPROVAL `c998960a23e74b7ea1da4aca6390b5b9`, appended proposal proof `12f27d2e5eae4e0d95caaea28421b5c0`, apply/escalation proof `2421f6f2f80a4abd99b888e5d2eb9d82`, retry proof `cd752dcbed3c4add913c9d2901ed07ab`, and rollback proof `41583d82acb34f4db5df313c9e4b4e10`. UI controls call real routes and show blocked reasons. |
| P0 | Source OS + Plugins update execution | PARTIAL | Source OS Verify All, Setup Queue, selected-app Verify, selected-app Setup Plan, Backup, Check Update, no-op/current Update, Rollback routing, and proof events are wired. Runtime proof: Verify All `521e8565cfaf4115b3cd66c4fef66cc6` / backend route proof `e07a6629533c4a4c9333ba657120cecc`, Setup Queue proof `96885b17bdaf47b590b57da4d4515ca1`, PrusaSlicer setup-plan proof `5bce091c12c44656a4f3f1209fc6522d`, Azure Speech SDK setup-plan proof `9a7bd64d01644e8fb81359a196288179`, PrusaSlicer CLI `84e425b7fe514d42896ad16083eed561`, FLSUN Slicer CLI `eb18f6c1b98b4f52b8f955aee4b2503c`, source-only Azure Speech SDK `ae75bb3c53d6418ab7c603c7d7747e90`. Current runner-contract proof: `/api/modules/runtime/runner-contracts` returns 60 contracts, 7 agent-executable rows, 8 read-only runner smoke rows, 3 executable-path runner smoke rows, 5 Python import repair preflight rows, 2 CLI install/config preflight rows, 1 npm package metadata preflight row, 24 runner gaps/repair blockers, 36 runtime-ready rows, 7 source-ready runner-not-registered rows, 15 runtime-repair rows, and exact verifier-family gates; `SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json`, `SOURCE_APP_60_COMPLETION_AUDIT.json`, and `SOURCE_APP_RUNTIME_ACTION_PLAN.md` are regenerated from that matrix. The Python/CAD verifier-family slice promotes MeshLab to package/import-ready via the local `pymeshlab` import and registers honest repair probes for CadQuery, Open3D, build123d, numpy-stl, and PyMesh/pymeshfix. The read-only runner smoke slice adds `/api/modules/{module_id}/runtime/read-only-runner` for `blender_mcp_candidates`, `model_context_protocol`, `firmware_klipper`, `manifold`, `meshlab`, `trimesh`, `klipper`, and `moonraker`; it reruns only registered import/package/Moonraker proof and appends evidence, with no setup/install/update/launch/output/printer action. The executable-path runner smoke slice adds `/api/modules/{module_id}/runtime/executable-path-runner` for `printrun`, `bambustudio`, and `cura`; it reads only installed executable metadata/hash and appends evidence, with no app launch, setup/install/update/output/printer action. The slicer truth/config slice corrects Strec3D from a false CLI gap to verified source-reference-only inventory and adds `/api/modules/{module_id}/runtime/cli-install-config-runner` for `slic3r` and `superslicer`; it reads only source checkout, adapter schema, profile/config, and candidate executable metadata, while both rows remain blocked for real slicing until local CLIs pass `/runtime/verify`. The firmware inventory slice registers read-only source inventory for Marlin, Prusa Firmware, RepRapFirmware, Repetier Firmware, and Smoothieware; those rows are not executable and expose no compile/flash/upload actions. The service/web health slices register GET-only local/private URL verifiers for FDM Monster, Fluidd, Mainsail, OctoFarm, OctoPrint, Manyfold, Open Filament Database, Kiri:Moto/GridSpace, ComfyUI, and the ComfyUI TRELLIS wrapper. All 10 expected URL keys now exist in `G:/private/.env`; live proof probes attempted all 10 and correctly kept them setup-required because the corresponding services were not running. The service setup/start slice adds `/api/modules/{module_id}/runtime/start-runner` for those 10 rows as a preflight/proof contract: it checks local/private URL binding, checkout presence, command family, and port state, but still does not launch a process until a sandbox/process-supervisor gate is enabled. The npm package slice adds `/api/modules/{module_id}/runtime/npm-package-runner` for `azure_speech_sdk_js`; it reads package metadata/script names/lockfiles/manifests and node/npm path presence only, keeps `runtime_ready=false` and `agent_executable=false`, and cannot run npm install/scripts, start processes, write outputs, update source, or touch printers. Latest proof IDs: FDM Monster `23d8ef38a2074efd80868dfd2d1eaec9`, Fluidd `2d7b854c567a4163803ce7e5ab8e14f2`, Mainsail `02c0e8b6bb72485093d7b61def2b092a`, OctoFarm `a33df8ed7a944f78a23e0631ebd1efb2`, OctoPrint `00ebac59b3234831be708f8bae32befc`, Manyfold `0c7509883a8a41e4adf280da0aff0a87`, Open Filament Database `fdf19109e8084a5aa0cf89bea93f6fb5`, Kiri:Moto/GridSpace `9ae5b627fda044b3ae4822deb067f92b`, ComfyUI `ea093820a76741c981ebc6236d066bba`, ComfyUI TRELLIS wrapper `d279a094cae74c2e91953d2eddb35ecd`. Update proof on `blender_mcp_candidates`: backup `20260505T225446Z_blender_mcp_candidates_7636d13bded8`, backup proof `fa26b7f476d24de4b74a46f06b182ae5`, check proof `c89d2ea4965d4d9182c53e8b71e086b9`, update proof `970908d222734767a55401644878fa4a`. Remaining: sandboxed process supervisor for safe starts, all-app release watch, and richer post-update app-specific smoke gates for the 60-app registry. |
| P0 | Hermes Agent full OS operator coverage | IN_PROGRESS | `/api/agents/action-catalog` now exposes cataloged OS/code actions with public ready/partial/blocked state, proof requirements, approval/rollback flags, payload requirements, and no leaked internal handler names. Current action surface includes Source OS runner-contract matrix/single-row read actions, Source OS read-only runner smoke for package/import/local API proof rows, Source OS executable-path runner smoke for installed launcher metadata rows, Source OS Python import repair preflights, Source OS Slic3r/SuperSlicer CLI install/config preflights, Source OS Azure Speech SDK JS npm package metadata preflight, provider live-smoke proof, MCP-locked patch/restore/reviewed-apply, proof-gated git readiness/branch/stage/commit/push/PR, provider-team readiness/assignment/review-request contracts, bounded MiniMax coding-plan and DeepSeek review-pass artifacts, plus the new `code.e2e.*` workbench readiness/run contracts. Earlier safe sweep returned 25/25 accepted/completed proofs, protected missing-payload probes failed closed 5/5, and non-physical artifact actions passed 3/3: generation proof `783d06b27087489a8914956a5df559dd`, design proof `1ad2e99d3f9541d58b4a38a0e1ff5b16`, T1 #1 camera evidence proof `4a6143a9ef6a47c993530539d31a0dd1`, Azure voice preview proof `e4bbebf265e34035b3e3f47ecb3c4238` / TTS proof `324cbb9c902643a388ef773d83613c61`, Azure catalog proof `cb64df49be2f4036b1945d88ce2cd861`, and Roadmap truth proof `19f7ecf90f8a4a1ba303bf7fd0ec3142`. Focused Playwright passed 10/10 and screenshot proof is `03_implementation/proof/screenshots/agents-operator-catalog-expanded-2026-05-06.png`. Current workbench slice adds the user-visible Agent Code Workbench, live MiniMax/DeepSeek smoke buttons, reviewed patch -> gate -> branch/stage/commit/push/PR controls, and a backend planning/review loop that loads the PR #86 folder index, locks files, snapshots, runs MiniMax builder and DeepSeek reviewer artifacts, appends evidence, and releases locks without mutating source. P0 blocker: Hermes3D now reads the configured private provider aliases from `G:/private/.env` and exposes only redacted source names, but provider chat smoke is still rejected with HTTP 401; correct those provider values, rerun provider smoke, then complete the final low-risk agent-authored PR smoke task. Source OS runner gaps, update-all orchestration, and idle work remain secondary until the agents can help complete them. |
| P0 | Hermes Agent programming ecosystem | IN_PROGRESS | Source inputs are required, not optional: `https://github.com/NousResearch/hermes-agent.git` and `https://github.com/AtomicBot-ai/atomic-hermes.git`, with local source at `G:/Github/hermes-agent-fresh` and `G:/Github/atomic-hermes`. First safe code-operator slice is live and verified: programming readiness, Hermes MCP lock readiness, write readiness, repo status/tree/search, bounded file read, snapshot/diff/restore, proof-backed patch proposal, MCP-locked patch apply, exact-worktree MCP gate list/run APIs, exact-worktree MCP claim/lock/heartbeat/evidence/release APIs, proof-gated git branch/stage/commit/push/PR APIs, provider-team readiness/assignment/review-request APIs, and bounded provider-backed coding/review execution artifacts are exposed through `/api/code-operator/*` and mirrored into `/api/agents/action-catalog` with proof-required contracts. Route smoke proves `GET /api/code-operator/gates` returns 11 MCP gates and `POST /api/code-operator/gates/run` runs `git-diff-check` through `hermes_run_gate` as PASS while invalid owners fail closed; evidence `ev_4a3482659b8b91d3`. MCP coordination route smoke claimed task `h3d-agent-lock-route-smoke`, locked/hearted/released `03_implementation/ROADMAP.md`, recorded evidence, and rejected `../G/private/.env`; evidence `ev_77276b2ded845997`. Patch-apply route smoke created proposal `642990660dde4b688f14c35589eaf408`, applied it only under active same-owner MCP lock with pre/post snapshots, recorded chained MCP evidence, and passed `git-diff-check`; evidence `ev_2cd18d787167bc33`. PR #73 hardening proof is `ev_dfe36e14a23d418c`. Git shipping lane is implemented as the next stacked Codex slice: it creates only `codex/` or `hermes-agent/` branches from clean worktrees, stages only changed source files that have same-owner snapshots and active MCP file locks, commits with proof IDs, pushes to origin without force, and opens PRs through authenticated `gh`. The provider-team lane exposes Team A MiniMax builders and Team B DeepSeek reviewers as real readiness/assignment/review boundaries and now has execution routes that call configured OpenAI-compatible provider endpoints to produce proof artifacts only: MiniMax returns a coding plan/proposed-change artifact, DeepSeek returns a review verdict/findings artifact. These routes still do not mutate source; real edits remain behind patch proposal/apply, MCP locks, snapshots, gates, and git PR lanes. Remaining before autonomous source mutation is fully complete: converting accepted provider plans into reviewed patch proposals and rollback-gated repair workflow. Acceptance: both Hermes agent teams can take real Hermes3D tasks, claim/lock/heartbeat/gate/evidence/release through Hermes MCP locks, edit code through source-backed tools, run real tests/gates, produce proof artifacts, create branches/PRs, and restore any agent-touched file. |
| P0 | Claude 20-agent completion contract kit | IN_PROGRESS | The first 20-lane contract exists at `03_implementation/docs/handoffs/CLAUDE_20_AGENT_COMPLETION_CONTRACT.md`; the follow-up six-agent polish/audit contract exists at `03_implementation/docs/handoffs/CLAUDE_6_AGENT_POLISH_AUDIT_2026-05-06.md`. Acceptance: every Claude lane has exact files, locks, task id, branch/worktree rule, pass/fail gates, proof output, no-fake rule, S1 lock rule, GitHub push/PR rule, and "fix until pass" instruction. Claude agents may complete Source OS runners, tab polish, tests, docs/proof, visual checks, and missing runtime integrations, but must not touch files owned by the current Codex code-operator lane. |
| P0 | 60 source-app runtime completion | IN_PROGRESS | Keep the visible Source OS target at the proven 60 source-backed rows. Acceptance: `SOURCE_REGISTRY_TRUTH_AUDIT.json`, `/api/modules`, `/api/modules/runtime/verifiers`, `/api/modules/runtime/setup-queue`, `/api/modules/runtime/cli-surface`, `SOURCE_APP_60_COMPLETION_AUDIT.json`, `SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json`, `SOURCE_APP_CLI_SURFACE_AUDIT.json`, `SOURCE_APP_RUNTIME_ACTION_PLAN.md`, and Playwright Source OS/Plugins/Settings/Roadmap proof all agree; each row is either runtime-ready through a registered verifier or source-ready with an exact runner gap, every available CLI is exposed as an agent-usable verifier/runner before desktop fallback, and no row remains in an unclassified launch-kind bucket. |
| P1 | Voice Azure STT pipeline | DONE | Backend `/api/voice/stt` reads Azure Speech secrets only from runtime/private env, returns transcript or exact blocker, appends proof, and chat mic inserts transcript while preserving the audio artifact. Live Azure TTS-to-STT proof event: `5d9b8a25a1ac454f85ea46e5a59866f4`. |
| P1 | Hermes Agent Playwright proof runner | DONE | `/api/agents/{persona}/playwright-run` exposes fixed observe/smoke/full scopes, stores an `agent_playwright_run` artifact, appends proof events, and Agents UI can trigger the runner without arbitrary shell input. |
| P1 | Settings app update center | PENDING | One-click check/update/rollback surface covers Hermes Agent/Desktop and source apps with failsafes and user approval policy. |
| P1 | Printer onboarding/profile wizard polish | PENDING | New printers can be added with Moonraker probe, camera URL, profile refs, safety policy, and proof without editing TOML/source. |
| P1 | Idle automation workbench execution | PARTIAL | Agents can create research/build/update candidates while idle, Run fails closed with proof until trusted runtime prerequisites exist, then reports/gates are recorded before user review/merge. |
| P1 | Observe advanced view presets | DONE | Camera selection layouts for 1/2/3/all feeds, rotations 0/90/180/270, zoom/focus/color controls, undock, persisted presets, and Refresh reconnect proof work across the live Observe tab. |
| P1 | Rust acceleration worker lane | PARTIAL | First Rust slice adds `hermes3d-accel`, a read-only CLI for SHA-256 proof hashing, bounded G-code metadata parsing, and binary STL triangle/bounds metadata. Python wrappers keep safe fallback behavior when the Rust binary is missing, and proof hashing/G-code metadata paths opportunistically use Rust only when built/configured. Acceptance proof: `cargo test --manifest-path 03_implementation/rust/hermes3d_accel/Cargo.toml` passed 3/3; `cargo build --manifest-path 03_implementation/rust/hermes3d_accel/Cargo.toml` produced the local debug binary; `python -m pytest 04_testing\\pytest\\unit\\test_rust_accel.py -q` passed 4/4; Ruff and py_compile passed. Remaining Rust candidates stay scoped to where profiling pays: 3MF parsing, safety-bounds acceleration after parity tests, large proof/tree hashing expansion, camera-frame transforms, and sandbox/process-supervisor primitives. |
| P2 | Final density/responsive pass | IN_PROGRESS | Main navigation, Source OS project list, Settings sections, Voice agents, Plugins API panel, and Simple mode left rail now use persisted user-resizable panes with keyboard/Home/End control and double-click reset. Remaining: finish tab-by-tab density/polish after each feature surface is complete; dashboard stays non-scroll at operator viewport sizes. |
| P2 | Final docs/proof sync | PENDING | README/roadmap/proof docs match live tab count, printer policy, source app count, and current proof event IDs. |

## Primary Work Packages

### 1. Source OS + Plugins: App Update Center

Goal: every source-backed app shows installed version, upstream latest release/commit, health, backup target, update button, rollback target, and proof gates.

Current status:
- `/api/modules/update/readiness` exposes non-mutating source checkout readiness.
- Source OS and Plugins render compact update-readiness summaries.
- Deep Check is explicit and read-only.
- `/api/modules/runtime/verifiers`, `/api/modules/{module_id}/runtime/verify`, and `/api/modules/runtime/verify-all` expose source/runtime verifiers so installed source checkouts no longer collapse into an `unknown` badge. Known safe local tools currently verify PrusaSlicer, FLSUN Slicer, OrcaSlicer, OpenSCAD, Blender, and CuraEngine as real agent-usable CLI probes; Bambu Studio, UltiMaker Cura, and Printrun are launcher metadata only until a safe CLI/API smoke is proven; 13 read-only reference/catalog rows are verified by source-inventory probes; `trimesh`, `manifold`, `model_context_protocol`, `blender_mcp_candidates`, and `meshlab` are verified by backend package/import/source-import probes; `moonraker`, `klipper`, and `firmware_klipper` are verified through read-only printer API probes; `fdm_monster`, `fluidd`, `mainsail`, `octofarm`, `octoprint`, `manyfold`, `open_filament_database`, `kirimoto_gridspace`, `comfyui`, and `comfyui_trellis_wrapper` now have GET-only local/private health/version verifiers that remain `setup_required` until configured URLs produce real proof; source-only runnable modules report `source_ready` plus concrete setup steps.
- `/api/modules/runtime/setup-queue` and `/api/modules/{module_id}/runtime/setup-plan` give Hermes Agents a proof-backed queue of setup work without executing unregistered installers or pretending a source checkout is already a runnable app.
- `/api/modules/runtime/gaps` groups the remaining 24 runner gaps/repair blockers by launch kind and section, with the next safe verifier family needed for each group.
- `/api/modules/runtime/runner-contracts` is the canonical 60-row Hermes Agent execution matrix. It exposes `agent_executable`, `runner_status`, `required_verifier_family`, `safe_actions`, `acceptance_gate`, and `blocked_reason` for every Source OS app; Hermes Agents may execute only rows where `agent_executable=true`.
- `/api/modules/runtime/agent-cli-readiness` gives Hermes Agents a live 60-row execution-tier matrix: verified agent CLI, launcher metadata only, package/import ready, service/API ready, source-reference ready, CLI install/config preflight available, npm package metadata preflight available, or runner gap.
- `/api/modules/runtime/cli-surface` exposes `SOURCE_APP_CLI_SURFACE_AUDIT.json`: 7 enabled agent CLIs, 24 local CLI/service signals that still need verifiers, 3 launcher-only rows, and 10 rows with no local CLI signal.
- `/api/modules/runtime/setup-queue` is now also available as a read-only GET status for Plugins, Settings Environment, and Roadmap so the 24 runner/repair gaps are visible without creating proof spam; POST records a proof-backed plan.
- Source OS selected-app actions now call `/update/backup`, `/update/check`, `/update/apply`, and `/rollback` with backup metadata and proof events.
- Live no-op/current update proof exists for `blender_mcp_candidates`; all-app orchestration remains pending.

Implementation notes:
- Use GitHub latest-release API for public release-backed repos and local `git fetch --dry-run`/remote metadata for source checkouts.
- Use cached backend polling and proof events, not frontend loops.
- Add one-click "Check all apps" and "Update selected/all" with backup before update, post-update smoke check, and rollback if gates fail.
- Keep source-app update state visible in Source OS and summarized in Plugins/Settings.
- Track the corrected 60-app target as the active Source OS workstream. Current proof is 60 source-backed modules; the remaining work is runtime verifier/setup-runner coverage, not count expansion.
- Use isolated staging worktrees for update tests. Do not mutate live source checkouts before gates pass.
- Rollback must restore recorded backup data, not only checkout a branch/tag that may have moved.

Acceptance:
- No update action runs without backup metadata. Current Source OS Update button stays disabled until the readiness record reports a recorded backup.
- Failed/skipped gates stop or rollback.
- Every app row shows either latest release, latest commit, or a blocked reason.
- Every app row shows either runtime ready, source ready, install ready, setup needed, or blocked.
- Every app row with an available CLI must expose that CLI through a bounded verifier/runner path usable by Hermes Agents; if no CLI is installed or safe, the row must say `runner_not_registered` or launcher-metadata only.
- Verify All records a batch proof summary and never fetches, pulls, builds, or installs.
- Setup Queue records a batch proof summary and marks each source-only app as `runner_not_registered` until a safe app-specific setup runner and verifier exist.
- Plugins, Settings Environment, and Roadmap show the same setup queue counts as Source OS so missing runners are not hidden behind app tiles.
- Do not advertise any app row as runnable until a registered verifier, smoke gate, and proof artifact confirm the runtime.
- Hermes Agents can request updates while user is away, but user-facing risky actions remain gated by policy.
- Dirty checkouts fail the update gate until committed, backed up, or explicitly handled.

#### 60 Source App Completion Plan

The operator target is 60 useful source-backed apps. Current local truth is 60 proved modules, 36 verifier-backed ready rows, 7 agent-usable CLI probes, 24 CLI/service signals needing verifiers, 7 source-ready rows without safe runners, 15 registered verifier repair rows, 10 setup-required local/private HTTP rows, 18 source-reference-only rows, and 2 blocked rows. The completion path is:

1. Registry proof: keep the visible count at 60 and rerun `audit_source_registry_truth.py` after any source path or launch-kind change. Missing rows are blocked, not hidden or inflated.
2. Runtime verifier registry: 53 registered probe definitions are exposed by `/api/modules/runtime/verifiers`; the current matrix produces 36 verifier-backed ready rows. The next step is converting the remaining family-specific repair/gap rows into dry-run worker, service-health, CLI help/version, or reference-parser runners.
3. CLI-first agent runner lane: for every app that offers a CLI, add a bounded `--version`, `--help`, dry-run, import, or API smoke verifier first, then expose a Hermes Agent runner. Desktop launch metadata is allowed only as a fallback proof tier and must not be labeled as agent CLI-ready.
4. Runner registration: for each app family, add a safe verifier first. Example lanes: slicer CLI, CAD/modeler CLI, web app health endpoint, Python worker import/version check, firmware/toolchain version check, GPU worker smoke check, and reference-only docs/source modules.
5. App smoke gates: after a verifier passes, add a small non-destructive smoke gate: version/help output, local health endpoint, import check, or dry-run command. Printer-writing apps remain guarded by printer policy and approvals.
6. Update/rollback lane: every app row must expose backup, check update, update, rollback, proof, and failure rollback state before it can be included in one-click update-all.
7. UI proof lane: Source OS, Plugins, Settings, and Roadmap must show the same counts for proven apps, runtime-ready apps, runner gaps, install-ready apps, and blocked apps.
8. Agent lane: Hermes Agents can consume `/api/modules/runtime/gaps`, `/api/modules/runtime/runner-contracts`, plan the setup queue, and prepare PRs/config changes, but source installs/builds/updates execute only through registered runners and gates.

Definition of done for the 60-app target: no visible row is a shell. Each row has real source, real local state, a real blocked reason or runtime verifier, and a recorded proof path.

Current CLI readiness proof: `03_implementation/proof/SOURCE_APP_CLI_AGENT_READINESS_AUDIT.json`, `/api/modules/runtime/agent-cli-readiness`, and `/api/modules/runtime/runner-contracts` classify all 60 rows. As of this pass, 7 apps are verified agent CLI and agent-executable (`hermes_agent`, `blender`, `openscad`, `curaengine`, `flsun_slicer`, `orcaslicer`, `prusaslicer`), 3 are launcher metadata only with executable-path smoke available (`printrun`, `bambustudio`, `cura`), 5 are package/import ready (`model_context_protocol`, `blender_mcp_candidates`, `manifold`, `meshlab`, `trimesh`), 3 are service/API ready, 18 are read-only source/reference ready, 2 have CLI install/config preflight available (`slic3r`, `superslicer`), 1 has npm package metadata preflight available (`azure_speech_sdk_js`), and 24 remain runner gaps or repair blockers needing a real CLI/API/import/service smoke before Hermes Agents can execute them. Strec3D and the firmware rows (`marlin`, `prusa_firmware`, `reprapfirmware`, `repetier_firmware`, `smoothieware`) are verified source-reference-only from local source inventory; they are not agent-executable and no local safe compile/flash/upload path is claimed. The Python/CAD repair queue is explicit: `cadquery`, `open3d`, `build123d`, `numpy_stl`, and `pymesh` have registered import verifiers but the backend runtime cannot import them yet. The legacy slicer CLI config queue is explicit: `slic3r` and `superslicer` can read local source, adapter schema, profile/config, and candidate executable metadata only, and remain blocked for real slicing until local CLIs pass `/runtime/verify`. The npm package metadata queue is explicit: `azure_speech_sdk_js` can read package.json, script names, lockfile/manifests, and node/npm path presence only, and remains blocked for real runtime use until a sandboxed npm runner and node package verifier pass. The service/web queue is explicit too: `fdm_monster`, `fluidd`, `mainsail`, `octofarm`, `octoprint`, `manyfold`, `open_filament_database`, `kirimoto_gridspace`, `comfyui`, and `comfyui_trellis_wrapper` have registered local/private HTTP health verifiers, but remain setup-required unless their configured `HERMES3D_SOURCE_*_URL` endpoints respond to non-mutating GET probes. Separate CLI-surface proof lives at `03_implementation/proof/SOURCE_APP_CLI_SURFACE_AUDIT.json`; it records 24 local CLI/service hints that are candidates only until a safe verifier and proof gate exist.

Generated no-forget action plan: `03_implementation/proof/SOURCE_APP_RUNTIME_ACTION_PLAN.md` lists every open runner gap, launcher-only row, and CLI/service signal that still needs a verifier. This file must be regenerated with `python 03_implementation\scripts\write_source_runtime_action_plan.py` after any Source OS runtime or verifier change.

### 2. Printers + Settings: Fleet Onboarding

Goal: add and validate new Moonraker/Klipper printers through Hermes Agents without hand-editing config.

Current status:
- The live operator fleet is fixed to T1 #1, T1 #2, S1, and V400.
- T1 #1, T1 #2, and V400 are write-enabled through guarded paths.
- S1 remains read-only/action-locked.
- Settings can save camera URLs for configured printer IDs.
- `/api/printers/onboard` adds persistent Moonraker printers after live `/server/info` and `/printer/objects/query` probes.
- Settings exposes a compact Add Moonraker Printer form that reports the exact failed probe when onboarding is blocked.
- New onboarded printers appear in the Printers tab after the fixed T1/S1/V400 operator fleet.
- Onboarded printers default to read-only unless guarded writes are explicitly requested and the printer is idle.

Implementation notes:
- Probe `/server/info`, `/printer/objects/query`, webcam config, and safe printer status before accepting a printer.
- Add printer profile, camera URL, source wiki/profile refs, and safety lock policy in one wizard.
- Preserve the S1 read-only/locked default until user changes it.
- Add persistent onboarded-printer storage instead of relying only on static TOML/config merges.
- Do not let onboarding overwrite S1 into a write-enabled printer.

Acceptance:
- New printer creation records IP, adapter, camera endpoint, safety status, and proof event.
- Any unavailable Moonraker endpoint gives the exact failed probe.
- Existing four local printers stay correct.
- Newly onboarded non-S1 printers appear in Printers and Settings without source-code or TOML edits.
- All S1 aliases and `192.168.0.12` keep HTTP 423 behavior for test/move/upload/start.

### 3. Jobs + Autopilot: Proof-Gated Job Pipeline

Goal: jobs become an operator-grade workflow surface: model, slice, bounds, approval, upload, print, observe, complete, repair.

Current status:
- Jobs, Autopilot, and Approvals use live APIs.
- Print-start has strong backend gates for job id, approval, truth gates, bounds, plate clearance, S1 lock, and Moonraker idle state.
- Printers Upload + Start now requires an approved job ID in the UI and sends `job_id` to the backend upload/start route.
- The Jobs UI renders a proof-gated pipeline from live job detail data, including current blocker, required gate, and backend transition state.
- Server-side cancel, repair proposal, repair apply/escalation, retry, and rollback routes append `job_events` plus `proof_events`; rollback requires a recorded checkpoint artifact.
- Apply repair uses the existing read-mostly `RepairAgent` and records escalation honestly when no executable repair handler is available; it does not pretend to mutate files or printers.

Implementation notes:
- Show active job stages, current blocker, required gate, attached files, printer target, and rollback/cancel options.
- Use Moonraker upload/job queue only after approval and truth gates.
- Include automatic repair suggestions for slicer/config/tooling failures, not silent retry loops.
- Centralize print-start gates so orchestration code and printer API cannot diverge.
- Add server-side proof events for every job transition, accepted or blocked.

Acceptance:
- Starting a print without job approval still fails closed.
- Every implemented job transition appends proof.
- Agents can propose repair actions with explicit approve/deny controls.
- `uploadGcodeLive` and any workflow path must pass `job_id` for `start=true`.
- Repair proposals rejected by the user do not mutate the print artifact selected for printing.

### 4. Learning + Agents: Idle Workbench

Goal: when Hermes3D is idle, agents research safe improvements, app updates, source app opportunities, printer maintenance, and daily tasks for user review.

Current status:
- Learning config/report shell exists.
- Agents chat/attachments/actions/update controls exist.
- Autonomous session routes exist.
- `/api/learning/idle-workbench` now exposes persistent idle workbench candidates, live blockers, a daily prompt, proof event IDs, and server-side merge/build/install/update blocking.
- `/api/learning/idle-workbench/candidates/{id}/run` now gives the UI a real execution boundary: it blocks with proof when idle learning or Hermes Agent runtime prerequisites are missing, and when ready it may only create a report artifact for review. It cannot install, merge, upload, move, print, or silently mutate source/printers.
- Learning renders the idle workbench queue with candidate creation, review request, keep/remove decisions, and disabled merge until approval plus gates exist.
- Agents renders the same idle workbench queue summary so the agent surface and Learning surface agree.
- `/api/learning/idle-workbench` now also exposes automation readiness for research, documentation, workflow, app update, and printer maintenance. The Learning UI shows queue-only vs execution-ready status and names live blockers instead of implying risky agents are active.
- `/api/agents/{persona}/playwright-run` gives trusted Hermes Agents a real QA tool boundary for Playwright observe/smoke/full checks. The runner stores redacted output artifacts and proof events; it is not a free-form command executor.
- Current live state is partially ready: `HERMES3D_LEARNING_RUNNER_ENABLED` and `HERMES3D_AGENT_RUNTIME_URL` are configured through `G:/private/.env`, research reports are ready, and documentation/workflow/app-update/printer-maintenance remain blocked by S1 policy plus the queued `Pilot Calibration Cube` job.
- GUI API launchers now load `G:/private/.env` into backend API processes only. The current private env provides Azure/provider keys, proof signing, Hermes Agent runtime, and idle runner flags without exposing secrets to the Vite frontend.

Implementation notes:
- Add daily "what should we improve today?" prompt.
- Add idle queue: research candidate, build branch, run gates, summarize proof, ask user keep/remove/merge.
- Use lightweight APIs first; avoid heavy downloads or builds while printers are active.
- Add persistent queue/candidate state with branch/ref, gate statuses, proof event IDs, and blocked reasons.
- Reuse Approvals for keep/remove/merge or install/merge decisions.

Acceptance:
- Idle work never moves printers.
- Idle work never merges or installs without proof and policy approval.
- User gets a short daily queue with actionable choices.
- With active printers/jobs, build/download/install candidate actions are blocked server-side.
- Learning and Agents show the same queue state from the live API.
- Until live blockers clear and the specific work kind has gates/approval, idle work types stay queue-only and do not mutate code, apps, or printers.
- Candidate Run returns a report artifact plus proof event when runtime execution is available, or a visible blocked reason plus proof event when prerequisites are missing.

### 4A. Hermes Agent Codebase Operator

Goal: Hermes Agents can help code Hermes3D OS itself with full user/admin access, but only through a professional safety layer: snapshots, approvals, proof, gates, rollback, and explicit scopes. This closes the user's definition of "work": agents can use any offered tab/button/feature and can also improve the codebase when the operator allows it.

Daily-use runtime stack:
- Normal user actions use the Hermes action catalog, live backend routes, explicit blocked reasons, and proof gates.
- Coding actions require exact-worktree `hermes3d-locks` MCP coordination before edits: claim task, lock files, heartbeat, append evidence, release files, release task.
- Edit safety requires Atomic-style before/after file snapshots, diff-any-version, one-click restore, and rollback proof before and after restore.
- Execution safety defaults to a container sandbox for fast coding tasks, lint, unit tests, Playwright, package installs, and source verifier scripts.
- Risky agent work moves to a VM or microVM sandbox: unknown repos, internet-enabled installs, destructive command classes, printer/network automation, or any task that could mutate live hardware state.
- Merge safety requires tests, no-fake scan, visual proof when UI changes, security scan when files/routes/tools change, review-agent signoff, proof bundle, and then PR.

Readiness target:
- Read-only help, roadmap inspection, proof review, Source OS status, and safe UI actions are mostly ready.
- Agents coding Hermes3D OS is not daily-autonomous until sandboxed command execution, apply-patch rollback, and PR review gates are fully green from the Hermes Agent UI, not only from Codex.
- Hermes Agents must be sandboxed proof-gated operators, not chat agents with raw file access.

Atomic Hermes research findings to extract:
- File time-travel is the essential trust layer: record before/after snapshots for every file an agent touches, list versions by file, diff snapshot vs current, and restore with a fresh pre-restore snapshot.
- Code actions need a bounded terminal, not a free shell. Dangerous commands, sensitive paths, force pushes, destructive git, and env/config writes must route to an approval queue.
- Local and external providers should be interchangeable behind an OpenAI-compatible runtime contract; Hermes3D already has the local/private runtime URL path, so the next step is surfacing model/provider readiness and failover in Agents/Settings.
- Computer-use/browser testing should stay as an explicit proof runner. Hermes3D already exposes fixed Playwright scopes; expand them into tab-specific QA actions instead of giving agents arbitrary browser control first.
- Agent skills, memory, recurring jobs, and profile isolation map directly to Hermes3D idle learning, app updates, printer maintenance, and source-app setup queues.

Implementation plan:
1. Add a backend `code_history` service under `src/hermes3d/services/` that stores snapshots in `03_implementation/.hermes_history/` or `03_implementation/var/code-history/`, not in app source folders by default. Each record stores workspace root, relative path, sha256, size, timestamp, action id, agent id, and proof event id.
2. Add API routes for code history: list touched files, list snapshots for a file, read snapshot metadata, diff current vs snapshot, restore snapshot, and export a proof bundle. Restore must snapshot current content first.
3. Add a code action policy: allowed roots, denied globs (`.env`, secrets, `.git`, node_modules, build outputs, printer config unless explicitly scoped), max file size, text/binary handling, and required approvals for high-risk paths.
4. Add safe read-only code tools to `/api/agents/action-catalog`: repo status, roadmap gaps, grep/search, file read, dependency/runtime status, test list, and tab-to-file ownership map.
5. Add safe write tools after history exists: propose patch, apply patch to allowed files, format allowed files, run targeted test, run no-fake scan, run Playwright scope, append proof. No write action is accepted without pre-snapshot proof.
6. Add command runner lanes with fixed allowlists: `npm run lint`, `npm run typecheck`, selected Playwright specs, `python -m py_compile`, no-fake scanner, source-runtime verifier scripts, and read-only git status/diff/log. No arbitrary command text in the first implementation.
7. DONE: Add git lanes after tests pass: create branch with `codex/` or `hermes-agent/` prefix, stage only files from the agent's snapshot ledger plus active same-owner MCP file locks, commit with proof IDs, push, and open PR. Force push, reset hard, clean, and cross-worktree edits remain blocked.
8. Add UI surfaces: Agents tab "Code Operator" panel, Roadmap "Agent coding readiness" panel, Proof file-history browser, and left-rail chat quick actions ("inspect current tab", "fix this tab", "run proof", "restore file").
9. Add idle automation integration: when user is away, agents may create candidates and branches, but merge/install/update stays approval-gated. All while-away work must summarize changed files, snapshots, tests, proof IDs, and rollback options.
10. Add acceptance proof: route probes for every code API, unit tests for path traversal/denied globs/restore snapshots, Playwright proof that a file history row can be viewed/restored, no-fake scan, and Hermes lock/evidence chain proof.

Definition of done:
- Hermes Agents can read repo context, plan work, patch files, run fixed gates, and prepare PRs from Hermes3D OS without Codex acting as the hidden executor.
- Hermes Agents use `hermes3d-locks` MCP before any write: `hermes_claim_task` -> `hermes_lock_files` -> heartbeat during work -> `hermes_run_gate` for allowlisted gates -> `hermes_append_evidence` -> `hermes_release_files` -> `hermes_release_task`.
- `MCP_LOCK_WORKSPACE` must match the actual worktree being edited. A mismatched lock workspace is a hard blocker because it gives false coordination proof.
- Every agent-touched file has at least one pre-change snapshot and one post-change proof event.
- The user can diff and restore any agent-touched file from the UI.
- The code operator refuses secrets, S1 unsafe printer actions, destructive git, arbitrary shell, and paths outside the allowed Hermes3D workspace.
- Failed tests/gates stop the coding lane and expose restore/repair choices.

#### Required Source Inputs And First Working Slice

Active source inputs:
- `G:/Github/hermes-agent-fresh` from `https://github.com/NousResearch/hermes-agent.git`: primary runtime, tools, skills, MCP/delegation/terminal/code loop.
- `G:/Github/atomic-hermes` from `https://github.com/AtomicBot-ai/atomic-hermes.git`: source patterns for file history, approval UX, bridge, local runtime, and file diff/restore UI.
- `https://github.com/1ilkhamov/opencode-hermes-multiagent`: role/pipeline reference for finder, architect, coder, reviewer, tester, security, documentation, and infrastructure agent chains. Use the pattern behind Hermes3D locks/proof; do not replace the Hermes3D runtime or bypass snapshots/gates.
- OpenHands and OpenCode CLI usage is allowed for Hermes Agents when needed, but only as registered code-operator CLI runners with detection/version proof, sandbox execution by default, task-scoped env/cwd/files, MCP locks before writes, snapshots before invocation, redacted output artifacts, DeepSeek review, fixed gates, and rollback evidence. No raw unmanaged OpenHands/OpenCode command strings from chat. Current truth: source checkouts and private env key names exist, but execution stays blocked until real executable paths and a sandbox image pass readiness.

Minimum ecosystem for agents to program Hermes3D without bloat:
1. Import/launch true Hermes Agent runtime with `HERMES_HOME`, `TERMINAL_CWD`, and `HERMES_WRITE_SAFE_ROOT` scoped to Hermes3D worktrees.
2. Enable only the needed programming toolsets first: file read/write, patch, terminal, code execution, todo, memory, skills, MCP, delegate.
3. Configure two coding provider lanes from backend/private env: MiniMax and DeepSeek. They should be usable simultaneously by separate agent teams and swappable per task.
4. DONE: Add the source-backed programming readiness API: `/api/code-operator/programming-readiness`.
5. DONE: Add Hermes MCP lock readiness API: `/api/code-operator/mcp-locks/readiness`, including exact-worktree `MCP_LOCK_WORKSPACE` matching.
6. DONE: Add snapshot/diff/restore APIs before write tools: `/api/code-operator/history/*`.
7. IN_PROGRESS: Add bounded repo tools: tree, grep, file view, roadmap gaps, tab ownership map, test list.
8. IN_PROGRESS: Add patch/apply tools only after snapshots pass. Patch proposal is live and proof-backed; patch apply remains gated.
9. IN_PROGRESS: Add fixed command runner gates: lint, typecheck, no-fake scan, source verifier scripts, selected Playwright scopes, Python compile/pytest. MCP allowlisted gate list/run is live; additional Hermes3D-specific gates still need registration.
10. IN_PROGRESS: Add exact-worktree Hermes MCP coordination APIs for claim, file locks, heartbeat, evidence, release files, and release task.
11. DONE: Add branch/commit/PR lane after gates pass, staging only files from the snapshot ledger and active same-owner MCP locks.
12. Add task assignment flow so a MiniMax-backed Hermes team and a DeepSeek-backed Hermes team can receive real Hermes3D issues, coordinate through proof, ask each other for review, and fix failures until pass.
13. Add OpenCode-style role chains as Hermes3D skills without raw tool bypass: finder before edits, builder for the patch, reviewer/tester after every code change, and security reviewer for secrets/auth/MCP/process/printer/network changes.
14. IN_PROGRESS: Add OpenHands/OpenCode CLI runner adapters: `/api/code-operator/cli-runners`, `/api/code-operator/sandbox/readiness`, `/api/code-operator/cli-runners/preflight`, and gated `/api/code-operator/cli-runners/run`. The routes now prove source/executable/sandbox state and intentionally fail closed until runnable CLIs, sandbox readiness, MCP locks, snapshots, allowlisted task type, redacted output proof, DeepSeek review, and gate handoff are configured.

First backend slice now tracks this directly:
- `src/hermes3d/services/code_history.py`
- `src/hermes3d/api/routes/code_operator.py`
- `GET /api/code-operator/programming-readiness`
- `GET /api/code-operator/mcp-locks/readiness`
- `GET /api/code-operator/write/readiness`
- `GET /api/code-operator/repo/status`
- `GET /api/code-operator/repo/tree`
- `POST /api/code-operator/repo/search`
- `POST /api/code-operator/files/read`
- `POST /api/code-operator/patch/proposals`
- `POST /api/code-operator/patch/apply`
- `GET /api/code-operator/gates`
- `POST /api/code-operator/gates/run`
- `GET /api/code-operator/git/readiness`
- `POST /api/code-operator/git/branch`
- `POST /api/code-operator/git/stage-owned`
- `POST /api/code-operator/git/commit-owned`
- `POST /api/code-operator/git/push`
- `POST /api/code-operator/git/pr`
- `GET /api/code-operator/mcp-locks/state`
- `POST /api/code-operator/mcp-locks/claim-task`
- `POST /api/code-operator/mcp-locks/lock-files`
- `POST /api/code-operator/mcp-locks/heartbeat`
- `POST /api/code-operator/mcp-locks/evidence`
- `POST /api/code-operator/mcp-locks/release-files`
- `POST /api/code-operator/mcp-locks/release-task`
- `POST /api/code-operator/history/snapshots`
- `POST /api/code-operator/history/list`
- `GET /api/code-operator/history/diff/{snapshot_id}`
- `POST /api/code-operator/history/restore`
- agent action catalog entries for programming readiness, MCP lock readiness/state/claim/lock/heartbeat/evidence/release, write readiness, repo status/tree/search, bounded file read, patch proposal/apply, MCP gate list/run, and code snapshots.

The Claude 20-agent completion contract is `03_implementation/docs/handoffs/CLAUDE_20_AGENT_COMPLETION_CONTRACT.md`; its implementation and audit PRs have landed through PR `#82`.
The current provider/review execution lane is Codex PR `#85`; the active follow-up is the Source OS runner-contract/runner-family lane. PR `#87` added the canonical execution matrix, PR `#88` added the Python/CAD verifier-family slice, PR `#89` corrected slicer truth by making Strec3D source-reference-only while leaving missing SuperSlicer/Slic3r CLIs blocked, PR `#90` registered local/private health probes for FDM Monster, Fluidd, Mainsail, OctoFarm, and OctoPrint, PR `#91` registered local/private health probes for Manyfold, Open Filament Database, Kiri:Moto/GridSpace, ComfyUI, and the ComfyUI TRELLIS wrapper, PR `#93` added preflight-only start-runner contracts for those 10 service/web rows, PR `#94` made the full unit gate reliable, PR `#97` registered read-only source inventory for Marlin, Prusa Firmware, RepRapFirmware, Repetier Firmware, and Smoothieware without exposing compile, flash, upload, or printer actions, PR `#98` registered executable-path metadata runners for Printrun, BambuStudio, and Cura without launching them, PR `#99` added source/dependency metadata preflights for CadQuery, Open3D, build123d, numpy-stl, and PyMesh without installing packages, creating environments, starting workers, writing output, or touching printers, PR `#100` added source/schema/profile/candidate-path preflights for Slic3r and SuperSlicer without installing, launching, slicing, writing output, or touching printers, and the current npm package slice adds package metadata/script/lockfile preflight for Azure Speech SDK JS without running npm, installing dependencies, starting processes, writing output, updating source, or touching printers.

### 5. Voice + Observe: Operator Assist

Goal: make voice/camera useful during prints, not just a settings page.

Current status:
- Voice has Azure TTS catalog/preview via backend.
- Agent chat can speak assistant replies with the selected agent's Azure voice assignment via backend-only TTS and proof events.
- Agent chat has browser mic dictation, voice-note attachments, and backend Azure STT transcription insertion.
- Observe has live camera cards for all four configured printers, snapshot/capture APIs, persisted view controls, S1 defaults, refresh/reconnect proof, and plate state.
- `/api/voice/stt` uses Azure fast transcription via backend-only runtime secrets, appends proof events without transcript text leakage, and returns a transcript or exact blocked reason. Live proof: TTS preview audio transcribed back as `Hermes 3D speech-proof.` with proof `5d9b8a25a1ac454f85ea46e5a59866f4`.

Implementation notes:
- Extend transcript review/history so operators can inspect voice-note transcript proof from Voice, Agents, and Artifacts without opening raw audio.
- Let the chat mic attach commands, voice notes, and printer observations to agents.
- Use Observe snapshots/feed metadata for plate-clear checks, anomaly notes, and print-complete reminders.
- Add "send snapshot to agent" flow from Observe: capture evidence, attach artifact id, printer id, plate state, and card link to chat context.
- Treat browser dictation as convenience only; Azure STT is the real backend transcription path.

Acceptance:
- No speech key appears in frontend bundles or logs.
- Voice transcription returns a real transcript or an honest blocked reason.
- Camera/plate alerts link to the exact printer card and proof event.
- S1 camera assist remains read-only and never unlocks printer actions.
- V400 camera stays blocked until a real camera URL is configured.

## Source Research Notes

- Moonraker exposes `/server/info`, printer object queries, file upload, webcam config, and update manager endpoints; Hermes3D should keep printer and update work server-side and show live status in the UI.
- Moonraker webcam config supports stream URL, snapshot URL, flips, rotation values of 0/90/180/270, and aspect ratio, matching the Observe controls requested by the user.
- GitHub's latest-release endpoint can be used without auth for public repos and includes release assets/digests where available, matching Hermes3D's app update checks.
- PrusaSlicer has a real CLI through `prusa-slicer-console.exe` on Windows and loads/overrides profiles from 3MF/AMF/command arguments.
- OpenSCAD supports CLI exports via `-o` and command parameters, useful for Design/3D Generation workers.
- OrcaSlicer is open source, release-backed, and includes printer/material/process/calibration docs; Hermes3D should treat its CLI as detected/local-source capability and block if the local executable cannot prove a slice.

## References

- Moonraker Web API: https://moonraker.readthedocs.io/en/stable/web_api/
- Moonraker update manager: https://moonraker.readthedocs.io/en/latest/external_api/update_manager/
- Moonraker webcam config: https://moonraker.readthedocs.io/en/latest/configuration/#webcam
- GitHub latest release REST API: https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#get-the-latest-release
- PrusaSlicer CLI wiki: https://github.com/prusa3d/PrusaSlicer/wiki/Command-Line-Interface
- OpenSCAD CLI manual: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_OpenSCAD_in_a_command_line_environment
- OrcaSlicer repo/wiki: https://github.com/OrcaSlicer/OrcaSlicer
