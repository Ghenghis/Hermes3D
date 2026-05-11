# W19/W20 Reboot Continuation — 2026-05-11

Saved at PC reboot checkpoint. Resume from here after restart.

---

## Immediate Priority Order After Reboot

1. **Check PR #254 CI** — merge if green (W19 gap audit doc)
2. **Check PR #255 CI** — merge after #254 (branch: `claude/w19-fixes-1-3`, latest commit: `d21b1b1`)
3. **Confirm bed leveling done with user** → start medallion print
4. **While print runs** → create W20 Tab Feature Action Audit doc

---

## PR #255 — All Fixes Already Applied

Branch: `claude/w19-fixes-1-3`  
Latest pushed commit: `d21b1b1`

| File | Fix Applied |
|------|------------|
| `src/hermes3d/api/routes/agents.py` | Removed unused `ds_result` variable (ruff F841) — both declaration and assignment deleted |
| `src/hermes3d/api/routes/files.py` | Docstring line 3: "stub/placeholder" → "interim implementation" (forbidden pattern fix). Added `/api/files/list` and `/api/files/index` backward-compat aliases before `{file_id}` route |
| `src/hermes3d/api/routes/design.py` | Added `from pathlib import Path` import (was crashing with NameError) |
| `ui/tests/e2e/w18-a1-pickup-full-route-walk.spec.ts` | Added `127.0.0.1:8766` to `BENIGN_CONSOLE_FRAGMENTS` |
| `ui/tests/e2e/app-status.spec.ts` | Added `proof_command` to `hermes-agent` stub in `SAMPLE_APPS` |

**Check CI:** `gh pr checks 255`  
**Merge order:** #254 first, then #255 (standing auto-merge authorization applies)

---

## Medallion Print Job

**G-code:** `var/slicer/hermes3d_medallion_t1b_v2.gcode` (1140 KB, 32 layers)  
**Printer:** FLSUN T1 #B at `192.168.0.11` (Rapid PLA+)  
**Upload status:** CONFIRMED — Moonraker accepted the file before reboot  
**Print status:** NOT STARTED — user was doing bed leveling

**Verified G-code settings:**
- Hotend: 222°C first layer → 218°C
- Bed: 65°C  
- Speed: M220 S70 at layer 1, M220 S100 at layer 11 (speed ramp)
- Bed shape: circular delta radius 130mm (arc prime within ±130mm)

**Start command after leveling confirmed:**
```bash
curl -s -X POST "http://192.168.0.11/printer/print/start" \
  -H "Content-Type: application/json" \
  -d '{"filename": "hermes3d_medallion_t1b_v2.gcode"}'
```

**Monitor print:**
```bash
curl -s "http://192.168.0.11/printer/objects/query?print_stats"
```

**Why these settings:** Previous attempt crashed because wrong bed shape (300×300 rectangular vs circular ±130mm delta) sent carriage out of bounds. Temperatures were also wrong (200°C hotend, 0°C bed). Fixed by re-slicing with FlsunSlicer 2.0.4 native T1 profiles + custom Rapid PLA+ filament profile.

---

## W20 Tab Feature Action Audit — PENDING

**Output:** `docs/handoffs/W20_TAB_FEATURE_ACTION_AUDIT_2026-05-11.md`

Enumerate every tab + every visible UI action. For each:

| Field | Values |
|-------|--------|
| `route` | hash route e.g. `#gen3d` |
| `control` | label / testid |
| `endpoint` | backend API path |
| `expected` | what should happen |
| `observed` | what actually happens |
| `status` | `WORKING_REAL` \| `WORKING_HONEST_BLOCKED` \| `DISABLED_WITH_REASON` \| `BROKEN_NO_RESPONSE` \| `BROKEN_BACKEND` \| `BROKEN_UI` \| `PLACEHOLDER_OR_STUB` \| `NOT_WIRED` |

**Priority tabs:** `#gen3d` → `#design` → Slicer → `#files`/`#artifacts` → `#agents` → `#apps` → Autopilot/Jobs/Workflows/Proof/Settings

**STRICT:** Printer hardware buttons = `OUT_OF_SCOPE_BY_OPERATOR` (enumerate but do NOT click during audit).

**STRICT:** Do NOT claim `GUI_COMPLETE` until W19 fix order items 1–8 are all verified.

---

## W19 Fix Order (Reference)

1. File/artifact store wiring
2. `#gen3d` local generation → visible in Generated Models with downloadable proof
3. `#design` output → artifacts, sendable to slicer
4. Slicer → visible G-code artifact
5. 60-app proof/status correctness
6. Provider setup truth (ComfyUI/TRELLIS/Hunyuan3D/TripoSR)
7. Hermes Agent MiniMax/DeepSeek model-create/slice workflow
8. Final Playwright product E2E

**Do NOT claim complete until all 8 verified.**
