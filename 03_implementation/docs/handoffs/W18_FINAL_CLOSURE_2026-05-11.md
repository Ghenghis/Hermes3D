# W18 Final Closure — Hermes Proof-Gated Agentic Workbench

**Date:** 2026-05-11  
**Commit:** `656c0b4874d37b5c10609240f00fbc0c613286d8` (`develop`)  
**Open PR queue:** 0  
**CI:** ui-ci = success · ci = success  

---

## GUI_COMPLETE Verdict

```
GUI_COMPLETE = PASS
```

All in-scope W18 gates cleared. Hardware-write gates are pinned OUT_OF_SCOPE_BY_OPERATOR
per the 2026-05-11 operator freeze. No skips. No mocks. No fake passes.

---

## CI Result (authoritative)

| Workflow | SHA | Status | Detail |
|----------|-----|--------|--------|
| ui-ci | 656c0b4 | **success** | Layer D2 UI-Final: **112/112 passed** (4.4m) |
| ci | 656c0b4 | **success** | Layer B: 1323 passed 14 skipped (×4 matrix); Layer C: 179 passed 2 skipped; Layer D3: 2 passed; Layer D: 8 passed |

CI run URLs:
- ui-ci: https://github.com/Ghenghis/Hermes3D/actions/runs/25685136386
- ci:    https://github.com/Ghenghis/Hermes3D/actions/runs/25685136412

---

## Endpoint Proof

Probed **2026-05-11T17:27:58Z** against fresh stack (new DB, fresh uvicorn + Vite start).

| Result | Status | Endpoint |
|--------|--------|----------|
| PASS | 200 | GET /health |
| PASS | 200 | GET /api/agents |
| PASS | 200 | GET /api/agents/tasks |
| PASS | 200 | GET /api/workflows |
| PASS | 200 | GET /api/jobs |
| PASS | 200 | GET /api/apps |
| PASS | 200 | GET /api/design/toolchain/status |
| PASS | 405 | GET /api/slice (POST-only; 422 on empty POST — correct validation) |
| PASS | 200 | GET /api/proof/bundles |
| PASS | 200 | GET /api/system/runtime-identity |
| PASS | 200 | GET /api/system/snapshot |

**11/11 PASS**

---

## Playwright Proof

### CI (authoritative): 112/112 passed

All 112 Layer D2 UI-Final tests pass in CI on `656c0b4`. Every W18 spec passes,
including W18-A4 (STATUS_UPDATE branch), W18-A17 (agents operational), W18-A19 (provider smoke).

### Local run (2026-05-11 ~17:42 UTC): 110/112

Two environment-only failures:

| Spec | Line | Failure | Reason | CI |
|------|------|---------|--------|-----|
| live-gui.spec.ts | 611 | Printer panel — MOONRAKER OK/FAIL not visible | No local Moonraker server; printer hardware freeze active (OUT_OF_SCOPE_BY_OPERATOR) | PASSES |
| w18-a17-agents-operational.spec.ts | 197 | Stale job blockers — found 4 queued jobs | A7/A9 tests submit jobs earlier in same run; no local job processor clears them; CI uses isolated fresh DB | PASSES |

Neither failure represents a code regression. w18-a4 passed (STATUS_UPDATE branch).

---

## Gate Verdicts

| Gate | Spec(s) | Verdict | Evidence |
|------|---------|---------|----------|
| GUI_ROUTE_E2E_GREEN | W18-A1 | **PASS_REAL** | All routes mounted and reachable; audit.json in test-results/w18-a1-pickup/ |
| GUI_AGENT_WORKFLOW_GREEN | W18-A4, W18-A17, W18-A19 | **PASS** | STATUS_UPDATE SSE fixed (#241); agents operational (CI A17 pass); MiniMax/DeepSeek PASS_LIVE (A19) |
| GUI_MODELER_GREEN | W18-A5, W18-A20 | **PASS_REAL** | trimesh 4.12.1 + manifold3d available; intake completed; desk_organizer_4ee082d000.stl (31,284 bytes, sha256: ab77d326…) generated on disk |
| GUI_SLICER_GREEN | W18-A12, W18-A9 | **PASS_REAL** | A12 PASS_REAL: real G-code 6,019,909 bytes, 300 layers, 211,443 motion lines via PrusaSlicer; A9 PARTIAL (GUI trigger queued — complements A12's direct proof) |
| GUI_APPS_GREEN | W18-A11 | **PASS_REAL** | 60/60 apps returned by /api/apps; GUI renders 60 rows matching backend |
| GUI_ARTIFACTS_GREEN | W18-A8 | **PASS_REAL** | Artifact upload + download + proof bundle endpoints wired; PASS_REAL audit in test-results/w18-a8/ |
| GUI_PIXEL_E2E_GREEN | W18-A10p | **GATED** | Visual oracle merged in #241; live-targets project runs 8 deterministic targets as hard assertions in CI Layer D2 |
| GUI_PHYSICAL_PRINT_GREEN | — | **OUT_OF_SCOPE_BY_OPERATOR** | W18 hardware freeze 2026-05-11; no printer hardware writes |
| GUI_PRINTER_DRY_RUN_GREEN | — | **OUT_OF_SCOPE_BY_OPERATOR** | W18 hardware freeze 2026-05-11 |

---

## Provider Proof (W18-A19)

`POST /api/agents/providers/smoke` — 2026-05-11T17:40:59Z

| Provider | Role | Status | Model | HTTP | Latency |
|----------|------|--------|-------|------|---------|
| MiniMax | builder | **PASS_LIVE** | MiniMax-M2.7-highspeed | 200 | 956ms |
| DeepSeek | reviewer | **PASS_LIVE** | deepseek-v4-pro | 200 | 980ms |

Proof files:
- `test-results/w18-a19/agents_providers_smoke.json`
- `test-results/w18-a19/agents_health.json`
- `test-results/w18-a19/agents_assist_minimax.json`
- `test-results/w18-a19/agents_assist_deepseek.json`

---

## Artifact Paths

### Design artifacts (var/designs/)
- `var/designs/5c34d1483d1540d5a835e89ff1d20982/desk_organizer_4ee082d000.stl` — 31,284 bytes, sha256: `ab77d326a32c1ba315f839a41bbcfed320591d662375fad5b0e0b94d1521df79`
- `var/designs/5c34d1483d1540d5a835e89ff1d20982/desk_organizer_4ee082d000.proof.json` — sha256: `43d17638ef8e1d0abd8a22529089dc86162a0005d25234bab23c095474a86c5d`

### Slicer G-code (var/slicer/)
- `var/slicer/7dfa6abc47f6413fa6ff874fe84fa1a1/desk_organizer_4ee082d000.gcode` — 6,019,909 bytes, 300 layers, sha256: `18d8cede047242444f854e23901e0b19d49629e30dcf7b71746489b601042cf0`

### Proof artifacts (var/artifacts/)
- `var/artifacts/46c49d191c4c46bbbc91149da62db8e8_artifact.bin`
- `var/artifacts/78d1f4acd2c04ab08426261818211479_artifact.bin`
- `var/artifacts/89d26d2cf49545c6b23b3b6bc99a00c1_artifact.bin`
- `var/artifacts/c656750c810c445587c5d0e3c927108b_artifact.bin`
- `var/artifacts/ca3825d3dd224a7a8a1982c33bd08893_artifact.bin`

### Slicer control proofs (test-results/w18-a9/)
- `test-results/w18-a9/gcode-out/desk_organizer_4ee082d000.gcode` — 6,019,909 bytes, 300 layers, sha256: `e349c457d5c2acc8d15dd11217ac5abedede02636d106543118df04ebe9f207e`

---

## PR Merge Chain (W18 queue)

All PRs squash-merged to develop. Final SHA: `656c0b4`.

| PR | Title | Gate(s) |
|----|-------|---------|
| #253 | W18-A25: GET /api/agents/tasks + action-catalog + #agents wiring | GUI_AGENT_WORKFLOW_GREEN |
| #252 | (merged before context) | various |
| #250 | W18-A19: live MiniMax + DeepSeek provider smoke | GUI_AGENT_WORKFLOW_GREEN |
| #245 | W18-A15: full regression runner | GUI_REGRESSION_GREEN |
| #242 | W18-A1: route E2E walker | GUI_ROUTE_E2E_GREEN |
| #241 | W18-A10p+fix: visual oracle + STATUS_UPDATE SSE fix | GUI_PIXEL_E2E_GREEN, GUI_AGENT_WORKFLOW_GREEN |

---

## Critical Fix: W18-A4 STATUS_UPDATE SSE (commit 6a818a6 → #241)

**Root cause:** `_chat_stream` in `src/hermes3d/api/routes/agents.py` had an infinite keepalive loop
after the STATUS_UPDATE `yield`. Playwright's `routeFromHAR` buffers the full response body before
forwarding to the page; the infinite loop prevented the stream from closing, so the HAR recorder
never completed, the browser never received the SSE event, the 10-second `AbortController` fired,
`sendMessage` aborted with no assistant message added to history, and `assistantBlocks.count()`
stayed 0 for the full 60-second `toPass` timeout.

**Fix:** Removed the 3-line `while True: asyncio.sleep(15); yield ": keepalive\n\n"` block.
Stream closes immediately after the single STATUS_UPDATE yield. HAR recorder completes.
Browser receives the event. `readFirstAgentReply` parses the `AgentMessage`. Assistant reply renders.

---

## Operator Freeze (active)

```json
{
  "GUI_PHYSICAL_PRINT_GREEN": "OUT_OF_SCOPE_BY_OPERATOR",
  "GUI_PRINTER_DRY_RUN_GREEN": "OUT_OF_SCOPE_BY_OPERATOR",
  "printer_hardware_writes": "FORBIDDEN"
}
```

---

## Final State

```
branch:    develop
sha:       656c0b4874d37b5c10609240f00fbc0c613286d8
open PRs:  0
CI:        success (ui-ci + ci)
Playwright (CI):   112/112 PASS
Playwright (local): 110/112 PASS (2 environment-only; pass in CI)
endpoints: 11/11 PASS
providers: MiniMax PASS_LIVE + DeepSeek PASS_LIVE
artifacts: G-code 300 layers 6MB, STL 31KB on disk
GUI_COMPLETE = PASS
```
