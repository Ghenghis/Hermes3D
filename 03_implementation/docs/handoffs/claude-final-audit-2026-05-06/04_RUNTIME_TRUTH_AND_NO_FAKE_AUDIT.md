# Runtime Truth and No-Fake Audit

Generated: 2026-05-07T01:03 UTC
Sources: Audit 2 (PR #79), Audit 3 (PR #74)

---

## Audit 2 — No-Fake UI (PASS)

Task: `H3D-CLAUDE-POLISH-NOFAKE-UI-2026-05-06`
Auditor: claude-polish-nofake-02 (findings), claude-orchestrator (report commit)
PR: #79 `claude/polish-nofake-audit`
Verdict: **PASS — ZERO BLOCKERS**

### No-Fake Scanner

Command: `python 03_implementation/scripts/scan_active_ui_no_fake.py`

| Worktree | Production files scanned | Violations |
|---|---|---|
| h3d-claude-voice | checked | 0 |
| h3d-claude-observe | checked | 0 |
| h3d-claude-printers | checked | 0 |
| h3d-claude-design | checked | 0 |
| h3d-claude-gen3d | checked | 0 |
| h3d-claude-jobs | checked | 0 |
| h3d-claude-learning-autopilot | checked | 0 |
| h3d-claude-source-ui | checked | 0 |
| h3d-claude-settings-plugins | checked | 0 |
| h3d-claude-artifacts-proof | checked | 0 |
| h3d-claude-app-shell | checked | 0 |

**Total: 0 violations across 11 UI worktrees**

Note: `scan_active_ui_no_fake.py` is currently locked by codex-master. Codex should re-run after unlocking and merging.

### Fake Pattern Grep (14 patterns)

Patterns checked: `mock`, `fake`, `placeholder`, `TODO`, `FIXME`, `hardcoded`, `demo`, `simulated`, `lorem`, `coming soon`, `not implemented`, `Math.random()`, `setTimeout.*success`, `resolve.*true.*setTimeout`

All hits were **BENIGN**:
- `placeholder=` HTML input attributes (correct use — not fake data)
- Anti-slop assertion comments in `Design.tsx`, `AutopilotConsole.tsx`, `AboutSubtab.tsx`, `UpdateCenterSubtab.tsx` — these explicitly document what was **removed**

**Zero actual fake/mock/hardcoded data patterns found.**

### Button Wiring Verification (33 critical buttons)

Every visible button is one of:
- **WIRED** — calls a real backend route that returns real data
- **BLOCKED-HONEST** — action is policy-blocked with an honest reason visible to the user
- **SAFE** — no frontend secret; proxied by backend

| Tab | Button/Action | Backend Endpoint | Status |
|---|---|---|---|
| Voice | Play/pause/stop | GET /api/voice/recordings/{id} | WIRED |
| Voice | Transcript list | GET /api/voice/transcripts | WIRED |
| Voice | Proof review | GET /api/voice/proof-events | WIRED |
| Voice | No frontend secret | TTS proxied by backend | SAFE |
| Observe | Camera grid | GET /api/observe/status | WIRED |
| Observe | Refresh all | re-fetch /api/observe/status | WIRED |
| Observe | Reconnect on error | exponential backoff re-fetch | WIRED |
| Observe | S1 read-only badge | read_only: true from backend | WIRED |
| Printers | Add Printer wizard | POST /api/printers/probe | WIRED |
| Printers | Camera URL validate | POST /api/printers/validate-camera | WIRED |
| Printers | S1 IP block | CAMERA_ONLY_IPS before network | BLOCKED-HONEST |
| Jobs | Retry | POST /api/jobs/{id}/retry (policy-gated) | WIRED |
| Jobs | Repair | POST /api/jobs/{id}/repair (policy-gated) | WIRED |
| Jobs | Rollback | POST /api/jobs/{id}/rollback (policy-gated) | WIRED |
| Design | Template list | GET /api/design/templates | WIRED |
| Design | Provider health | GET /api/design/providers | WIRED |
| Design | Generate (unavailable) | shows "Provider not available" | BLOCKED-HONEST |
| Gen3D | Provider panel | GET /api/gen3d/providers | WIRED |
| Gen3D | Template gallery | GET /api/gen3d/templates | WIRED |
| Gen3D | Generate (no provider) | honest blocked message + proof event | BLOCKED-HONEST |
| Learning | Run scan | POST /api/learning/run | WIRED |
| Learning | Queue/Review/Keep | real backend endpoints | WIRED |
| Autopilot | Next Gate | POST /api/autopilot/next-gate | WIRED |
| Autopilot | Status display | GET /api/autopilot/readiness (30s poll) | WIRED |
| Source UI | CLI readiness | GET /api/sources/readiness | WIRED |
| Source UI | Proof artifacts | /api/artifacts links | WIRED |
| Settings | Update center | GET /api/settings/update-center | WIRED |
| Settings | Provider health | GET /api/settings/provider-health | WIRED |
| Settings | Rollback | POST /api/settings/update-center/rollback/{component} | WIRED |
| Plugins | Plugin health | backend plugin list | WIRED |
| Artifacts | Proof list | GET /api/artifacts/list | WIRED |
| Artifacts | View proof file | GET /api/artifacts/proof/{filename} | WIRED |
| App Shell | Simple/Main mode | real mode state (no stale mock) | WIRED |

**All 33 critical buttons: WIRED, BLOCKED-HONEST, or SAFE. Zero fake buttons.**

### TypeScript Lint (lane-owned errors)

| Lane | Lane-owned errors | Pre-existing regression |
|---|---|---|
| voice | 0 | pre-existing TS7026 (not introduced) |
| observe | 0 | pre-existing TS7026 (not introduced) |
| printers | 0 | pre-existing TS7026 (not introduced) |
| design | 0 | pre-existing TS7026 (not introduced) |
| gen3d | 0 | pre-existing TS7026 (not introduced) |
| jobs | 0 | pre-existing TS7026 (not introduced) |
| learning-autopilot | 0 | not present on this branch |
| source-ui | 0 | pre-existing (noted in PR body) |
| settings-plugins | 0 | pre-existing (noted in PR body) |

Lane-owned TypeScript errors: **0**

Pre-existing TS7026/TS7006 regression in ~57 `src/*.tsx` files pre-dates this contract. Fix: PR #80 restores `ui-ci.yml` CI trigger on `feat/**` branches. The runner installs `node_modules` via `npm ci` so lint passes.

### Simple/Main Mode

- Simple mode does not revert to Main unexpectedly.
- Mode switching does not expose stale mock state.
- Confirmed via App Shell audit (PR #54).

---

## Audit 3 — Runtime Truth and Source OS Completeness (PASS)

Task: `H3D-CLAUDE-POLISH-SOURCE-RUNTIME-2026-05-06`
PR: #74 `claude/polish-runtime-audit`
Verdict: **PASS**

### Source OS Registry

- All 60 registered app rows present in the module registry.
- `UNKNOWN` badges are justified by genuinely missing local runtimes (ComfyUI, TRELLIS, Hunyuan3D not installed on machine), not missing implementation.
- Runtime probes used real local process/binary detection — no invented status.

### CLI Surfacing

Apps with verified CLI/service access:
- **Slicers**: PrusaSlicer, Bambu Studio, Cura — CLI verifier probes `--version`
- **Modelers**: Blender (`blender --version`), OpenSCAD (`openscad --version`), FreeCAD (`freecad --version`), CadQuery, trimesh (Python import)
- **Firmware**: PlatformIO (`pio --version`), avrdude, esptool
- **Print farm**: Moonraker HTTP probe, Klipper systemd check, OctoPrint `/api/version`
- **3D Generation**: ComfyUI launch probe, TRELLIS/Hunyuan3D/TripoSR import probes

### Update/Backup/Rollback

- Update center readiness check: `GET /api/settings/update-center`
- Rollback requires explicit `POST /api/settings/update-center/rollback/{component}` with policy gate
- No destructive action executes without user-visible approval step

### Runtime Gaps

Known gaps (documented in ROADMAP, not implementation bugs):
- ComfyUI not installed locally → `UNKNOWN` badge (correct)
- TRELLIS/Hunyuan3D/TripoSR not installed → `UNKNOWN` badges (correct)
- Flash/firmware upload for S1 blocked by policy (S1 is camera-only)

All gaps have concrete next actions in ROADMAP.
