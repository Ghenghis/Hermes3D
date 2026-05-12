# W21 Codex Completion Backlog

Date: 2026-05-12
Auditor: Codex with 6 capped sub-agents
Purpose: turn the structural, behavioral, and journey audits into finishable work.

## Current Honest Completion Estimate

The user's 55-65 percent E2E estimate is reasonable.

| Layer | Honest state |
|---|---|
| GUI shell | mostly real |
| Backend route registration | real and large |
| Slicer | working real |
| Files/artifacts data | real but lineage/UI needs cleanup |
| Design | real for one template |
| Agents | claims tasks, does not execute |
| Gen3D | provider pipeline not usable |
| Image-to-3D/logo workflow | not wired |
| Realtime UI | incomplete |
| App registry | real registry, mostly unproven |
| Test coverage | broad but uneven; many routes lack direct tests |

## P0 - Must Fix Before Claiming Product E2E

### 1. Hermes Agent MVP-3: execution, not just claim

Problem:

Queue status can show claimed tasks, but no task deliverable is produced and no task becomes done/blocked.

Required outcome:

- Persona reads claimed task.
- Persona performs one bounded work type, initially audit/handoff generation.
- Persona writes the requested `handoff_path` or task artifact.
- Task transitions to `done` or `blocked` with reason.
- UI shows claimed, active, done, blocked counts.

Proof required:

- Unit test for claim-to-done.
- Integration test with temp orchestrator queue.
- UI proof that a task changes from claimed to done or blocked.

### 2. Gen3D minimum viable provider path

Problem:

Provider cards exist, but all major providers are not usable from Hermes.

Minimum useful target:

- Pick one working local path first.
- Recommended first path: ComfyUI plus Hunyuan3D wrapper because weights appear partially present.
- Secondary fallback: TripoSR if install is smaller and VRAM can be freed.

Required work:

- Free GPU VRAM or run a CPU-safe path where possible.
- Install missing deps, especially `rembg`.
- Start provider service.
- Make `/api/gen3d/providers` show one provider ready.
- Make `/api/generation/run` dispatch to that provider when selected.
- Persist STL/mesh/proof in DB and Files/Artifacts.

Proof required:

- Provider readiness 200 and ready.
- One model generated from provider path, not local cube.
- Artifact visible in Files and Artifacts.
- Playwright proof with lag budget.

### 3. Hermes logo image-to-3D pipeline

Problem:

The user specifically needs the Hermes logo modeled without the white background included. The current app does not carry image bytes through to a background-removal/provider pipeline.

Required work:

- Add image upload/reference artifact persistence.
- Send `reference_artifact_id` from Gen3D UI to backend.
- Install and call background removal for non-transparent images.
- Feed processed image to the chosen provider.
- Write output mesh/proof/artifact.

Proof required:

- Input PNG accepted.
- Background removed or alpha mask generated.
- Mesh artifact produced.
- White background not represented as geometry.
- UI shows the produced artifact.

### 4. Runtime artifact reconciliation and lineage

Problem:

Runtime DB exists under `var\hermes3d.db` and contains real artifacts, but lineage and reconcile semantics need correction.

Required work:

- Stop checking/reporting the wrong `data\hermes3d.db` path.
- Add unique file path protection or reliable idempotence.
- Link artifacts to jobs when possible.
- Correct stage/gate labels for slicer files.
- Reconcile the one scanner-relevant G-code missing from DB.

Proof required:

- Reconcile test with mixed design/generation/slicer files.
- DB rows match expected paths.
- UI shows correct type/stage/job lineage.

### 5. Realtime UI refresh for stale tabs

Problem:

Backend state changes do not consistently update the UI.

Tabs needing polling or event subscription:

- Dashboard
- Files
- Artifacts
- Agents
- Gen3D
- Plugins
- Jobs, partially

Required work:

- Use existing fetch functions.
- Add 10-15 second polling or event stream where appropriate.
- Avoid blind retries.
- Use lag-protected proof: backend changed, UI changed, UI remains correct after one poll.

Proof required:

- One Playwright test for each stale class or a shared polling harness test.

## P1 - High-Value Completion Work

### 6. Land W21 design templates

Problem:

Develop supports one real design template.

Required work:

- Restore the stashed/branch work for `calibration_cube` and `simple_box`.
- Ensure every template writes STL and proof.
- Make template selection explicit in UI.

Proof required:

- Unit tests for all templates.
- Integration tests via `/api/design/intake`.
- Playwright proof that UI creates all templates.

### 7. 60-app proof run

Problem:

Only one app has proven success. Most apps are registered but not day-to-day proven.

Required work:

- Run proof commands for the 18 proof-capable apps not already successful.
- Persist `last_proof_status`, timestamp, and logs.
- Fix or honestly mark failures.

Proof required:

- App registry counts before/after.
- App row UI shows updated proof status.
- Proof artifacts exist.

### 8. Fix visible no-op/disabled controls

Problem controls:

- Source OS detail proof/log/settings/bridge actions
- Dashboard Action Window route/mount
- Freeze/Thaw controls
- Generic panel overflow menu
- Files fallback language
- Apps route double-wire

Required work:

- Implement backend routes or remove/disable controls with honest reason.
- Do not leave clickable controls that do nothing.

Proof required:

- Playwright clicks every safe visible action.
- Each action yields backend call, state change, honest disabled reason, or clear blocked envelope.

### 9. Code-operator readiness latency

Problem:

Several readiness endpoints respond only after about 17.5-18.2 seconds.

Required work:

- Cache slow checks.
- Parallelize readiness probes.
- Make UI show progress and not look frozen.

Proof required:

- Endpoint latency budget test.
- UI test with lag budget, no instant assertion.

### 10. Connectors and skills registries

Problem:

`/api/connectors` and `/api/skills` return honest not-implemented envelopes.

Required work:

- Implement registry source.
- Show installed/unavailable/blocked statuses.
- Wire Hermes Agent skills so agents can use project-specific capabilities.

Proof required:

- Registry rows appear.
- Skill metadata visible.
- Agent task can reference a skill or marks missing skill blocked.

## P2 - Coverage, Hygiene, and Scale

### 11. Add direct route smoke tests

Problem:

16 route modules lack direct endpoint-literal evidence; 188 of 280 operations lack direct endpoint evidence.

Required work:

- Add no-hardware TestClient smoke tests.
- Mock adapters for hardware/camera/printer routes.
- Keep printer writes out of tests.

### 12. Reduce or justify skipped tests

Problem:

34 skipped tests across 17 files.

Required work:

- Unskip where possible.
- For permanent skips, add reason and issue/backlog link.

### 13. Source-lab/app install reality

Problem:

Registry and source-lab claims exceed proven installed/useful state.

Required work:

- Decide which source-lab repos must be fully cloned.
- Run app proofs.
- Stop marking source as day-to-day usable until proof exists.

### 14. Optional provider key expansion

Problem:

MiniMax/DeepSeek are smoke-verifiable. Other keys exist or are optional but not smoked.

Required work:

- Add smoke endpoints only for providers actually used.
- Do not add fake provider cards.

## Suggested Claude Prompt

Continue W21 with no GUI_COMPLETE claim.

Use at most 6 agents. Do not run another 20-agent sweep.

Read these Codex audit files first:

- `03_implementation/docs/handoffs/W21_CODEX_PASS1_STRUCTURAL_AUDIT_2026-05-12.md`
- `03_implementation/docs/handoffs/W21_CODEX_PASS2_BEHAVIORAL_AUDIT_2026-05-12.md`
- `03_implementation/docs/handoffs/W21_CODEX_PASS3_E2E_JOURNEY_AUDIT_2026-05-12.md`
- `03_implementation/docs/handoffs/W21_CODEX_COMPLETION_BACKLOG_2026-05-12.md`

Immediate order:

1. Implement Hermes Agent MVP-3 so claimed tasks produce a handoff or become blocked with a reason.
2. Fix artifact reconcile/lineage using the runtime DB at `03_implementation/var/hermes3d.db`.
3. Add realtime polling to stale tabs.
4. Restore and land W21 design templates with proofs.
5. Start Gen3D minimum viable provider setup only after confirming VRAM and install constraints.

Rules:

- No printer hardware actions.
- No fake pass.
- No route-only green.
- Use lag-protected waits.
- Every fixed feature needs backend proof, UI proof, and artifact/proof evidence where applicable.

## Final Backlog Verdict

Hermes3D is not one final bugfix from complete. It is a real foundation with several unfinished product loops.

The shortest path to feeling complete is not more route audits. It is:

1. Make agents actually finish tasks.
2. Make one Gen3D provider produce a real model from an image.
3. Make files/artifacts/job lineage trustworthy.
4. Make UI state update in realtime.
5. Run app proofs and stop calling unproven apps usable.

That is the day-to-day completion path.
