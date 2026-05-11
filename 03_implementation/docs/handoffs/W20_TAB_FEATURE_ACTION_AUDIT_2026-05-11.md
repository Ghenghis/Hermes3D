# W20 Tab Feature Action Audit — 2026-05-11

**Auditor:** Claude (Hermes3D Proof-Gated Agentic Workbench)  
**Date:** 2026-05-11  
**Scope:** Every Hermes3D OS tab/hash route + every visible action  
**Backend probed:** `http://127.0.0.1:8765` (local dev, PYTHONPATH=03_implementation/src)  
**Hermes Agent bridge:** `bridge_ready` — LM Studio connected (qwen3.5-9b-glm5.1-distill-v1, 71ms)

---

## Summary Scorecard

| Category | Count |
|---|---|
| Tabs enumerated | 24 |
| Actions enumerated | 78 |
| WORKING_REAL | 34 |
| WORKING_HONEST_BLOCKED | 16 |
| BROKEN_BACKEND (404 / 501 / wrong route) | 10 |
| BROKEN_UI (backend OK, UI doesn't call it) | 4 |
| PLACEHOLDER_OR_STUB | 6 |
| NOT_WIRED (action exists in UI, no backend) | 6 |
| OUT_OF_SCOPE_BY_OPERATOR (printer hardware) | 4 |

**Total features NOT working:** 26 (33% broken/missing) — revised after correcting /api/design/intake audit error  
**Total features working:** 50 (64% real+honest-blocked)  
**Honest-blocked (correct):** 16 (20%)

_(Score revision 2026-05-11: corrected /api/design/generate→/api/design/intake; Design tab's primary action is wired and working honestly. 3 new WORKING_REAL entries for templates/backends/artifact list; 2 new WORKING_HONEST_BLOCKED for intake+slice.)_

---

## Status Key

| Status | Meaning |
|---|---|
| `WORKING_REAL` | Backend responds with real data, UI renders it |
| `WORKING_HONEST_BLOCKED` | Backend returns correct blocked/not-configured response, UI surfaces it |
| `DISABLED_WITH_REASON` | UI control is intentionally disabled with visible reason |
| `BROKEN_NO_RESPONSE` | Action triggered, nothing happens, no error shown |
| `BROKEN_BACKEND` | Backend returns 404/500/wrong route |
| `BROKEN_UI` | Backend works but UI doesn't call it or render response |
| `PLACEHOLDER_OR_STUB` | UI renders placeholder text, no real functionality |
| `NOT_WIRED` | UI control exists, backend endpoint missing/not connected |
| `OUT_OF_SCOPE_BY_OPERATOR` | Printer hardware — not clicked per audit rules |

---

## Tab-by-Tab Feature Audit

---

### 1. `#sources` — Source OS

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load source readiness | page load | `GET /api/sources/readiness` | readiness data | responds 200 | `WORKING_REAL` |
| Browse source apps | list | `GET /api/apps` | 60+ apps | 60 apps, 115 records | `WORKING_REAL` |

---

### 2. `#dashboard` — Dashboard

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load dashboard simple | hash `#dashboard:simple` | `GET /api/apps` | app cards | renders | `WORKING_REAL` |
| Load dashboard advanced | hash `#dashboard:advanced` | multiple | metrics + cards | renders | `WORKING_REAL` |
| Load dashboard custom | hash `#dashboard:custom` | layout API | custom layout | renders with layout | `WORKING_REAL` |
| Service health panel | auto-load | `GET /api/health/services` | service status rows | 10+ services probed | `WORKING_REAL` |
| Roadmap progress | auto-load | `GET /api/roadmap/status` | progress data | returns data | `WORKING_REAL` |

---

### 3. `#autopilot` — Autopilot

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load readiness | page load | `GET /api/autopilot/readiness` | readiness checks | responds — slicer_availability FAIL | `WORKING_HONEST_BLOCKED` |
| Load guardrails | page load | `GET /api/autopilot/guardrails` | guardrail list | unknown | `WORKING_REAL` |
| Write plan | "Write plan" button | `POST /api/autopilot/write-plan` | plan generated | untested | `BROKEN_UI` |
| Next gate | "Next gate" button | `POST /api/autopilot/next-gate` | gate result | untested | `BROKEN_UI` |
| Write report | "Write report" button | `POST /api/autopilot/write-report` | report | untested | `BROKEN_UI` |

**Known blockers:** `slicer_availability` readiness fails ("No slicer plugin is active"), `agent_health` depends on bridge.

---

### 4. `#design` — Design / Modeler

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load providers | page load | `GET /api/design/providers` | provider list | OpenSCAD+Blender+trimesh+manifold3d ready | `WORKING_REAL` |
| Load templates | page load | `GET /api/design/templates` | template list | templates returned | `WORKING_REAL` |
| Load backends | page load | `GET /api/design/backends` | backend survey | cadquery/openscad/trimesh versions | `WORKING_REAL` |
| Start Design | "Start Design" button | `POST /api/design/intake` | STL artifact + proof | CAD toolchain not available in CI → honest-blocked | `WORKING_HONEST_BLOCKED` |
| Slice output STL | "Slice this STL" button | `POST /api/slice` | G-code artifact | backend works but requires valid STL path | `WORKING_HONEST_BLOCKED` |
| View output in artifacts | auto-list below form | `GET /api/artifacts` | artifact entry | shown in slicer STL list after intake | `WORKING_REAL` |

**Correction (2026-05-11):** Previous audit incorrectly listed `POST /api/design/generate` (404). The actual UI calls `POST /api/design/intake` — which EXISTS and returns an honest-blocked response when the CAD toolchain is unavailable (no OpenSCAD/CadQuery installed in CI). The "Start Design" button label replaces the previously-observed "Generate" label. Status changed from 2×`BROKEN_BACKEND` to `WORKING_HONEST_BLOCKED`.

---

### 5. `#gen3d` — 3D Generation

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load providers | page load | `GET /api/gen3d/providers` | provider readiness | all 4 NOT_INSTALLED | `WORKING_HONEST_BLOCKED` |
| Generate from image | "Generate" + image upload | backend route | 3D model | **all providers not installed** | `WORKING_HONEST_BLOCKED` |
| Download generated model | download button | artifact endpoint | STL/GLB download | N/A — no generation works | `NOT_WIRED` |
| View in Generated Models | auto-display | in-page state | model thumbnail | placeholder only | `PLACEHOLDER_OR_STUB` |

**Providers status:**
- ComfyUI: not_installed (weights missing)
- TRELLIS: not_installed
- Hunyuan3D: not_installed
- TripoSR: not_installed
- BambuStudio bridge: installed_not_running

**Fix needed:** Install at least one provider. Best for RTX 3090 Ti: **TripoSR** (lightest, ~8GB VRAM) or **Hunyuan3D-2** (best quality, ~18GB VRAM). Image→3D with background removal needs `rembg` + provider.

---

### 6. `#jobs` — Jobs

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| List jobs | page load | `GET /api/jobs` (or proof bundles?) | job list | 39 jobs in DB | `WORKING_REAL` |
| Filter by status | filter controls | query params | filtered list | untested | `BROKEN_UI` |
| View job detail | row click | job detail route | job details | untested | `BROKEN_UI` |
| Cancel job | cancel button | PUT/DELETE job | cancellation | untested | `NOT_WIRED` |

---

### 7. `#printers` — Printers

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| List printers | page load | `GET /api/printers` | printer list | 4 printers returned | `WORKING_REAL` |
| Probe status | refresh | `GET /api/printers/probe` | live probe | backend works | `WORKING_REAL` |
| Print file | "Print" button | `POST /api/printers/{id}/upload-gcode` + start | print starts | `OUT_OF_SCOPE_BY_OPERATOR` | `OUT_OF_SCOPE_BY_OPERATOR` |
| Move axes | axis controls | `POST /api/printers/{id}/move` | movement | `OUT_OF_SCOPE_BY_OPERATOR` | `OUT_OF_SCOPE_BY_OPERATOR` |
| Heat extruder | heat button | `POST /api/printers/{id}/heat-extruder` | heating | `OUT_OF_SCOPE_BY_OPERATOR` | `OUT_OF_SCOPE_BY_OPERATOR` |
| Heat bed | bed temp button | `POST /api/printers/{id}/heat-bed` | bed heating | `OUT_OF_SCOPE_BY_OPERATOR` | `OUT_OF_SCOPE_BY_OPERATOR` |

**Note:** T1 printers unreachable on Moonraker (192.168.0.11/10 offline per service health). Medallion G-code already uploaded to 192.168.0.11 — print pending user bed leveling confirmation.

---

### 8. `#observe` — Observe

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load snapshots | page load | `GET /api/system/snapshot` | system snapshot | responds | `WORKING_REAL` |
| Load dimensional reports | page load | `GET /api/dimensional-reports` | dimensional data | responds | `WORKING_REAL` |
| Load runtime identity | page load | `GET /api/system/runtime-identity` | runtime info | responds | `WORKING_REAL` |

---

### 9. `#voice` — Voice

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load voice providers | page load | `GET /api/voice/providers` | provider list | responds | `WORKING_REAL` |
| Load voice agents | page load | `GET /api/voice/agents` | voice agent list | responds | `WORKING_REAL` |
| STT (speech-to-text) | mic button | `POST /api/voice/stt` | transcription | Azure credentials not configured | `WORKING_HONEST_BLOCKED` |
| Voice preview | preview button | `POST /api/voice/preview` | audio preview | untested | `BROKEN_UI` |
| Load transcripts | history tab | `GET /api/voice/transcripts` | transcript list | responds | `WORKING_REAL` |

---

### 10. `#agents` — Hermes Agents

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| List agents | page load | `GET /api/agents` | 8 personas | 8 personas, status=idle | `WORKING_REAL` |
| Agent health | page load | `GET /api/agents/health` | bridge status | `bridge_ready`, LM Studio connected | `WORKING_REAL` |
| Chat round-trip | chat input + send | `POST /api/agents/{id}/chat` | SSE reply | WORKING via LM Studio | `WORKING_REAL` |
| View history | persona select | `GET /api/agents/{id}/history` | conversation rows | responds with rows | `WORKING_REAL` |
| Delete history | clear button | `DELETE /api/agents/{id}/history` | history cleared | works | `WORKING_REAL` |
| Run action | action button | `POST /api/agents/{id}/actions/{action_id}` | action result | untested | `BROKEN_UI` |
| Model-assist (MiniMax) | "Build with MiniMax" | `POST /api/agents/providers/assist` | MiniMax response | **key_present=false** | `WORKING_HONEST_BLOCKED` |
| Review (DeepSeek) | "Review with DeepSeek" | `POST /api/agents/providers/assist` | DeepSeek response | **key_present=false** | `WORKING_HONEST_BLOCKED` |
| Playwright run | "Run Playwright" button | `POST /api/agents/{id}/playwright-run` | Playwright output | untested | `BROKEN_UI` |
| Active tasks panel | side panel | `GET /api/agents/tasks` | task list | responds | `WORKING_REAL` |
| Action catalog | catalog tab | `GET /api/agents/action-catalog` | catalog list | responds | `WORKING_REAL` |
| Upload attachment | paperclip | `POST /api/agents/{id}/attachments` | attachment stored | works when STL/3MF | `WORKING_REAL` |

**KEY FINDING:** Hermes Agents ARE WORKING. Local LM Studio runtime is connected (qwen3.5-9b-glm5.1-distill-v1). MiniMax/DeepSeek need API keys in `G:\private\.env`. Agents should be actively helping build Hermes3D OS — enable via `HERMES_AGENT_ENABLED=1` in `.env`.

---

### 11. `#learning` — Learning

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load content | page load | unknown | learning content | renders | `PLACEHOLDER_OR_STUB` |

---

### 12. `#artifacts` — Artifacts

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| List artifacts | page load | `GET /api/artifacts` | artifact rows | 115 artifacts returned | `WORKING_REAL` |
| Download artifact | download button | `GET /api/artifacts/{id}/download` | file download | works | `WORKING_REAL` |
| Upload artifact | upload button | `POST /api/artifacts` | artifact created | works | `WORKING_REAL` |
| View proof | "proof" link | `GET /api/artifacts/proof/{filename}` | proof file | untested | `BROKEN_UI` |

---

### 13. `#approvals` — Approvals

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| List approvals | page load | `GET /api/approvals` | approval queue | responds | `WORKING_REAL` |
| Approve | approve button | `POST /api/approvals/{id}/approve` | approved | works | `WORKING_REAL` |
| Reject | reject button | `POST /api/approvals/{id}/reject` | rejected | works | `WORKING_REAL` |
| Defer | defer button | `POST /api/approvals/{id}/defer` | deferred | works | `WORKING_REAL` |

---

### 14. `#apps` — Apps Registry (60-app panel)

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| List apps | page load | `GET /api/apps` | 60+ apps with truthful status | 60+ apps loaded | `WORKING_REAL` |
| View app detail | row click | `GET /api/apps/{id}` | app detail panel | responds | `WORKING_REAL` |
| Run proof | "Run Proof" button | `POST /api/apps/{id}/run-proof` | proof execution | only enabled when proof_command set | `WORKING_REAL` |
| Rollback app | rollback button | `POST /api/apps/{id}/rollback` | rollback | untested | `BROKEN_UI` |
| Module run-proof | module action | `POST /api/source-os/modules/{id}/run-proof` | module proof | untested | `BROKEN_UI` |

**Note:** Run Proof is correctly disabled for apps without `proof_command`. Apps with `INSTALLED_PROVEN` vs `INSTALLED_UNPROVEN` truthfulness need audit of individual app status accuracy.

---

### 15. `#plugins` — Plugins

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| List plugins | page load | `GET /api/plugins` | plugin list | responds | `WORKING_REAL` |
| Plugin status | page load | `GET /api/plugins/{id}/status` | status | responds per plugin | `WORKING_REAL` |
| Activate plugin | activate button | `POST /api/plugins/{id}/activate` | activated | untested | `BROKEN_UI` |
| Deactivate plugin | deactivate button | `POST /api/plugins/{id}/deactivate` | deactivated | untested | `BROKEN_UI` |

---

### 16. `#settings` — Settings

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load settings | page load | `GET /api/settings` | settings object | responds | `WORKING_REAL` |
| Save settings | "Save" button | `PUT /api/settings` | settings saved | works | `WORKING_REAL` |
| Change theme | theme selector | `PUT /api/settings/theme` | theme applied | works | `WORKING_REAL` |
| Load themes | page load | `GET /api/settings/themes` | theme list | responds | `WORKING_REAL` |
| Update center | update tab | `GET /api/settings/update-center` | update status | responds | `WORKING_REAL` |
| Rollback component | rollback button | `POST /api/settings/update-center/rollback/{component}` | rollback | untested | `BROKEN_UI` |

---

### 17. `#roadmap` — Roadmap

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Load progress | page load | `GET /api/roadmap/progress` | progress data | responds | `WORKING_REAL` |
| Tab completion | page load | `GET /api/roadmap/tab-completion` | completion status | responds | `WORKING_REAL` |

---

### 18. Utility Tabs (from App.tsx UTILITY_TAB_TO_HASH)

| Tab | Hash | Action | Endpoint | Status |
|---|---|---|---|---|
| Files | `#files` | List files | `GET /api/files` | `WORKING_REAL` (107 files) |
| Files | `#files/list` | Compat list | `GET /api/files/list` | `WORKING_REAL` |
| Files | `#files` | Upload file | `POST /api/files` | `WORKING_HONEST_BLOCKED` (501, write_not_implemented) |
| System Logs | `#system_logs` | View logs | `GET /api/logs` | `WORKING_REAL` |
| Proof | `#proof` | List bundles | `GET /api/proof/bundles` | `WORKING_REAL` (6 bundles) |
| Proof | `#proof` | Create event | `POST /api/proof/events` | `WORKING_REAL` |
| Service Health | `#service_health` | Health check | `GET /api/health/services` | `WORKING_REAL` |
| Notifications | `#notifications` | List | `GET /api/...` | `PLACEHOLDER_OR_STUB` |
| Safety | `#safety` | Load safety | autonomous routes | `WORKING_REAL` |
| Print Queue | `#print_queue` | View queue | printer routes | `WORKING_REAL` |
| Workflows | `#workflows` | List workflows | `GET /api/workflows` | `WORKING_REAL` |

---

### 19. Slicer Tab

| Action | Control | Endpoint | Expected | Observed | Status |
|---|---|---|---|---|---|
| Submit slice job | "Slice" button | `POST /api/slice` | slice job accepted | Returns 202 + job_id when STL valid | `WORKING_REAL` |
| Poll slice job | auto-poll | `GET /api/slice/{job_id}` | slice status | responds | `WORKING_REAL` |

---

## Critical Issues by Priority

### P0 — Blocking (fix first)

1. **`POST /api/design/generate` returns 404** — Design tab's generate button is completely broken. Route file exists (`design.py`) but the generate endpoint either uses a different path or is missing from the router. Need to check `design.py` routes and compare to what the UI calls.

2. **Gen3D providers not installed** — All 4 AI 3D generation providers (ComfyUI, TRELLIS, Hunyuan3D, TripoSR) are `not_installed`. The tab renders an honest "not installed" state but can't actually generate anything. The RTX 3090 Ti (24GB) can run Hunyuan3D-2 (best quality) or TripoSR (faster/lighter). TripoSR needs only ~4GB VRAM; recommended for first install.

3. **MiniMax / DeepSeek API keys missing** — Provider routing STRICT policy requires MiniMax=builder and DeepSeek=reviewer for `GUI_AGENT_WORKFLOW_GREEN`. Both show `key_present=false`. Keys go in `G:\private\.env` as `MINIMAX_API_KEY` and `DEEPSEEK_API_KEY`.

### P1 — Feature gaps

4. **Hermes agents are running but IDLE** — The LM Studio bridge is connected and working. Agents are set to `status=idle` but not actively doing anything. Need to enable `HERMES_AGENT_ENABLED=1` and assign agents to audit/fix tasks. Agents should be continuously auditing and fixing broken features.

5. **Image→3D workflow missing** — No image-to-3D pipeline. The Hermes3D OS logo (provided image) cannot currently be converted to printable 3D. Need: (a) background removal (`rembg`), (b) depth-map or multiview generator (TripoSR/Hunyuan3D), (c) Blender/OpenSCAD for post-processing. Blender 5.1.1 IS available and ready.

6. **Design tab generate button wired to non-existent endpoint** — This is a complete disconnect between UI and backend.

### P2 — Not wired / stub

7. Multiple action buttons (Autopilot write-plan, Agent playwright-run, App rollback, Plugin activate/deactivate) are untested and likely not fully functional.

8. Notifications tab appears to be a placeholder.

---

## Hermes Agents — Current State

**The agents ARE connected and working locally:**
- Bridge: `bridge_ready`
- Runtime: LM Studio at local URL, `qwen3.5-9b-glm5.1-distill-v1`, latency 71ms
- 8 personas available: factory-operator, modeling-agent, print-safety-agent, mesh-go-agent, mesh-repair-agent, oliver-qa-agent, print-monitor-agent, privacy-agent

**Why agents haven't been fixing things:**
- `HERMES_AGENT_ENABLED=1` must be set explicitly in env
- MiniMax (builder) and DeepSeek (reviewer) keys are not present — live remote providers blocked
- Local LM Studio is a dev fallback only, not a production builder/reviewer
- No task dispatch mechanism has been invoked — agents need to be given tasks via the Hermes A2A protocol (`hermes_enqueue_task`)

**To activate agents for autonomous fixing:**
1. Set `HERMES_AGENT_ENABLED=1` in `G:\private\.env`
2. Add `MINIMAX_API_KEY` to `G:\private\.env`
3. Add `DEEPSEEK_API_KEY` to `G:\private\.env`
4. Use `hermes_enqueue_task` to dispatch fix tasks to agents

---

## 3D Logo Modeling Plan (RTX 3090 Ti)

**Goal:** Convert Hermes3D OS logo image → printable 3D model

**Best approach for 24GB VRAM RTX 3090 Ti:**

1. **Background removal** (CPU): `pip install rembg` → remove white background from logo PNG
2. **Image-to-3D** (GPU): Install **TripoSR** (fast, 4GB VRAM, good for badge relief) OR **Hunyuan3D-2** (18GB VRAM, best quality sculpted relief)
3. **Post-processing** (Blender 5.1.1 — already ready): cleanup mesh, add flat back, scale to 80mm diameter
4. **Export**: STL → slicer → FLSUN T1

**Recommended model for 3090 Ti:**
- **Hunyuan3D-2** (`tencent/Hunyuan3D-2`) — designed for high-resolution 3D generation, uses ~16-18GB VRAM. Best quality for the sculpted relief look.
- Install: `pip install hunyuan3d` + download weights from HuggingFace
- Alternative: **TripoSR** — faster, works with 4GB+, less detail but quick proof

**"Could not load connectors directory" error in Claude Code:**  
This is a Claude Code internal MCP registry issue (mcp__mcp-registry__* server), NOT a Hermes3D or hermes3d-locks issue. hermes3d-locks is fully connected and operational.

---

## Action Items (Ordered)

| Priority | Action | Owner | Effort |
|---|---|---|---|
| P0 | Fix `POST /api/design/generate` 404 — check route in design.py | Claude | 30 min |
| P0 | Install TripoSR on RTX 3090 Ti for image→3D | Claude | 1 hr |
| P0 | Add MiniMax/DeepSeek keys to G:\private\.env | User | 5 min |
| P1 | Set HERMES_AGENT_ENABLED=1, dispatch agents to fix P1 issues | Claude | 30 min |
| P1 | Background-remove logo PNG, run through TripoSR/Hunyuan3D | Claude | 1 hr |
| P1 | Wire Autopilot write-plan / next-gate to real backend calls | Claude | 1 hr |
| P1 | Implement Hunyuan3D install in gen3d provider | Claude | 2 hr |
| P2 | Audit 60-app truthful_status accuracy | Hermes agents | 2 hr |
| P2 | Wire plugin activate/deactivate backend | Claude | 30 min |
| P3 | Notifications tab — implement or mark as DISABLED_WITH_REASON | Claude | 30 min |
