# W21 Codex Pass 3 - E2E User Journey Audit

Date: 2026-05-12
Auditor: Codex with 6 capped sub-agents
Repo: `G:\Github\Hermes3D`
Scope: end-to-end user journeys from UI intent to backend action to artifact/proof/UI refresh.
Printer hardware: not touched.

## Method

Pass 3 is journey-based. It asks: if a real user clicks through the product, where does the chain break?

Each journey is classified as:

- `WORKING_REAL`
- `WORKING_NARROW`
- `HONEST_BLOCKED`
- `BROKEN_BACKEND`
- `BROKEN_UI`
- `NOT_WIRED`
- `STALE_UI`
- `PROOF_MISSING`

## Journey 1 - Dashboard Cold Start

Expected:

User opens the app, sees live status, navigates to action areas, and status panels reflect current backend state.

Observed:

The shell boots and route registration is real. Dashboard-style panels exist. But not all dashboard controls route to the intended surface. The "Action Window" concept exists structurally, but routing/mounting is inconsistent.

Breakpoints:

| Step | Result |
|---|---|
| App shell loads | works |
| Sidebar primary tabs | works |
| Utility tabs discoverability | weak |
| Action Window entry | route/mount mismatch |
| Realtime panel refresh | incomplete |

Classification:

`WORKING_NARROW` plus `STALE_UI`

Fix:

Mount Action Window where the Dashboard says it goes, and add polling to stale dashboard panels.

## Journey 2 - Hermes Agents Complete a Queued W21 Task

Expected:

Task appears in queue, persona claims it, executes it, writes the requested handoff/result, then marks done or blocked.

Observed:

Queue status shows 8 claimed tasks and 0 done/blocked. Personas remain idle. No evidence that a claimed task is executed. The claim path exists; the work path does not.

Breakpoints:

| Step | Result |
|---|---|
| Queue task exists | works |
| Queue task claimed | works |
| Persona executes task | missing |
| Handoff markdown produced | missing |
| Task marked done/blocked | missing |
| UI proves completion | missing |

Classification:

`NOT_WIRED`

Fix:

W21 MVP-3: claimed task runner. It must either produce the requested artifact/handoff or set a clear blocked state with reason.

## Journey 3 - MiniMax/DeepSeek Assist a Hermes Agent

Expected:

Agent task invokes MiniMax/DeepSeek for builder/reviewer work, result is attached to the task, and UI shows evidence.

Observed:

Env keys now load and provider health reports MiniMax/DeepSeek keys present. Provider assist endpoint exists. But the queue runner does not call the provider assist path. Calls are manual, not agent-driven.

Breakpoints:

| Step | Result |
|---|---|
| Keys load from `G:\private\.env` | works |
| Provider health reports keys | works |
| Smoke/assist endpoint exists | works |
| Queue task invokes provider | missing |
| Provider result attached to task | missing |

Classification:

`WORKING_MANUAL_NOT_AGENT_E2E`

Fix:

Connect MVP-3 task execution to provider assist and persist provider evidence per task.

## Journey 4 - Hermes Logo Image to 3D Model

Expected:

User uploads or attaches the Hermes logo image, background is removed, a 3D provider creates a mesh, mesh appears in artifacts/files, then can be sliced.

Observed:

This journey is not working. UI can show or attach a reference concept, but the selected image is not carried through as a real provider input. `rembg` is missing. Gen3D providers are not live. Backend generation uses local template mesh generation, not image-to-3D.

Breakpoints:

| Step | Result |
|---|---|
| User has logo image | yes |
| UI passes image/artifact id to backend | incomplete |
| Background removal | missing `rembg` |
| Provider service ready | no |
| Hunyuan/TripoSR/TRELLIS execution | no |
| STL/mesh artifact created from logo | no |

Classification:

`NOT_WIRED`

Fix:

Install background removal, start one provider service, pass `reference_artifact_id` through UI/backend, and create a proofed mesh artifact.

## Journey 5 - 3D Generation Provider Card to Model

Expected:

User selects a provider card/template and gets output from that provider.

Observed:

Provider cards are visible, but live providers are `not_installed`. `/api/generation/run` creates local template output rather than dispatching to ComfyUI/Hunyuan/TripoSR/TRELLIS.

Breakpoints:

| Step | Result |
|---|---|
| Provider card visible | works |
| Provider readiness truthful | works, all not ready |
| Provider service invoked | missing |
| Provider weights loaded | missing |
| Provider output artifact | missing |

Classification:

`HONEST_BLOCKED` plus `NOT_WIRED`

Fix:

Minimum viable path: ComfyUI plus Hunyuan wrapper or TripoSR, recognized by `/api/gen3d/providers`, then real provider dispatch from `/api/generation/run`.

## Journey 6 - Design Prompt to STL

Expected:

User describes a custom part and gets a real STL.

Observed:

Works for desk-organizer-type input. Does not work for arbitrary custom modeling or image/logo designs. Stashed work adds calibration cube and simple box, but it is not on develop.

Breakpoints:

| Step | Result |
|---|---|
| Desk organizer prompt | works |
| STL output | works |
| Proof output | works for supported template |
| Arbitrary prompt | blocked/rejected |
| Logo/custom art | not implemented |

Classification:

`WORKING_NARROW`

Fix:

Land more templates, make supported-template limits explicit, and route image/logo modeling to Gen3D.

## Journey 7 - Design STL to Slicer to G-code

Expected:

Model created in Design can be sent to slicer and creates G-code visible in files/artifacts.

Observed:

Backend slicing is real. PrusaSlicer/OrcaSlicer subprocess path works. The weak point is UI handoff and persistence: if the model lives only in React session state, refresh/navigation can lose the action path even though the file exists on disk.

Breakpoints:

| Step | Result |
|---|---|
| Real STL exists | works |
| Slice route executes | works |
| G-code exists | works |
| G-code proof exists | works |
| UI lineage persists after refresh | weak |

Classification:

`WORKING_REAL_BACKEND` plus `STALE_UI`

Fix:

Persist design job/model lineage and add direct "slice this model" from Files/Artifacts cards.

## Journey 8 - Files and Artifacts Find Outputs

Expected:

Files and Artifacts tabs show the same real outputs with current proof status and lineage.

Observed:

The runtime DB has real rows and files exist on disk. Files scanner is real. But the Files UI still contains fallback assumptions and some lineage labels are wrong.

Breakpoints:

| Step | Result |
|---|---|
| Disk artifacts exist | works |
| Runtime DB artifacts exist | works |
| `/api/files` scanner | works |
| `/api/artifacts` DB route | works |
| UI stale/fallback copy | issue |
| Correct stage/job lineage | issue |

Classification:

`WORKING_REAL_DATA` plus `STALE_UI` and `PROOF_LINEAGE_WEAK`

Fix:

Make Files trust `/api/files`, fix reconcile labels/job links, and show consistent artifact lineage.

## Journey 9 - 60-App Proof Run

Expected:

User can run proofs for proof-capable apps, see pass/fail, and trust day-to-day install status.

Observed:

Registry is real, but most apps are unproven. Only one app is proven success; two failed; most never ran proof commands.

Breakpoints:

| Step | Result |
|---|---|
| 60 app rows visible | works |
| Truthful status concept | works |
| Proof command exists for 19 | works |
| Proofs actually run | mostly missing |
| Day-to-day usable status | not proven |

Classification:

`PROOF_MISSING`

Fix:

Batch-run the 18 proof-capable apps that are not already success/failure, persist status, then fix the failed apps.

## Journey 10 - Source OS App Detail Actions

Expected:

User opens Source OS module detail, views proof/logs/settings/bridge state, and can take safe actions.

Observed:

Registry/list surfaces exist. Several detail actions are disabled because matching backend endpoints do not exist yet.

Breakpoints:

| Step | Result |
|---|---|
| Registry visible | works |
| Detail opens | partial |
| Proof/log/settings actions | disabled/missing backend |
| Bridge action | disabled/missing backend |

Classification:

`BROKEN_UI_OR_HONEST_DISABLED`

Fix:

Either implement the detail endpoints or remove/rename disabled controls so the UI does not imply missing functionality is ready.

## Journey 11 - Plugins Activate/Deactivate

Expected:

User activates/deactivates a plugin and UI reflects state.

Observed:

Backend plugin DB update paths are real. The remaining risk is UI realtime refresh and proof that all plugin buttons reflect the state after refresh.

Breakpoints:

| Step | Result |
|---|---|
| Activate/deactivate backend | works |
| DB update | works |
| UI immediate reflection | partial |
| UI after refresh/poll | needs proof |

Classification:

`WORKING_BACKEND_STALE_RISK_UI`

Fix:

Add polling/refresh confirmation and a Playwright proof that state survives refresh.

## Journey 12 - Autopilot Plan, Freeze, and Thaw

Expected:

User can see readiness, write a plan/report, and use freeze/thaw controls where promised.

Observed:

Autopilot readiness/plan/report surfaces exist. Freeze/thaw controls reference backend paths that are not shipped.

Breakpoints:

| Step | Result |
|---|---|
| Readiness | works/exists |
| Write plan/report | exists |
| Freeze/thaw UI | visible |
| Freeze/thaw backend | missing |

Classification:

`BROKEN_BACKEND`

Fix:

Implement freeze/thaw endpoints or make the UI honest-disabled with reason.

## Journey 13 - Jobs and Dry-Run Print Flow

Expected:

Jobs tab reflects queued/running/completed jobs, and generated/sliced files create job rows.

Observed:

Jobs schema and routes exist. Slicer creates job-like records in runtime DB. But UI polling is partial, and many artifact rows have weak or null job lineage.

Breakpoints:

| Step | Result |
|---|---|
| Jobs routes | exist |
| Slice jobs | real |
| Job lineage across generated assets | weak |
| Polling | partial |

Classification:

`WORKING_PARTIAL`

Fix:

Normalize job creation for design/generation/slice and add consistent polling.

## Journey 14 - Voice, Learning, and Observe

Expected:

Voice and learning actions respond, observe surfaces reflect cameras/printer state where available.

Observed:

Routes exist and several honest-blocked semantics are present. Direct test coverage is thin. Observe/camera/printer probes were not called in this audit because they can touch hardware or live services.

Breakpoints:

| Step | Result |
|---|---|
| Routes registered | yes |
| Honest blocked states | yes |
| Safe no-hardware proof | incomplete |
| Direct tests | missing/thin |

Classification:

`HONEST_BLOCKED_UNDERTESTED`

Fix:

Add no-hardware TestClient smoke tests and mocked adapter tests.

## Journey 15 - Realtime UI After Backend Change

Expected:

After installing, proving, generating, slicing, or agent-claiming, the UI changes without manual reload.

Observed:

Only some tabs poll. Files, Artifacts, Agents, Gen3D, Plugins, Dashboard, and parts of Jobs can remain stale.

Breakpoints:

| Step | Result |
|---|---|
| Backend state changes | often works |
| UI notices automatically | inconsistent |
| UI stays correct after refresh cycle | not proven |

Classification:

`STALE_UI`

Fix:

Add lag-protected polling with two-stable-read confirmation:

1. Backend evidence changes.
2. UI reflects it.
3. UI remains correct after one poll interval or manual refresh.

## Pass 3 Verdict

The product breaks in the same few places across many journeys:

1. Agent claim is not execution.
2. Gen3D providers are visible but not usable.
3. Image/logo-to-3D is not wired.
4. Design is real but narrow.
5. Slicer is real, but model-to-slicer UX lineage is weak.
6. Files/artifacts data is real, but UI and lineage semantics lag behind.
7. App registry is real, but proof status is mostly unproven.
8. Realtime refresh is incomplete across most tabs.

This is not a mystery failure. It is a completion backlog.
