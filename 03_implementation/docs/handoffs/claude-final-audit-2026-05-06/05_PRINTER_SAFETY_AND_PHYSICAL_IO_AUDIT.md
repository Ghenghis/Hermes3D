# Printer Safety and Physical I/O Audit

Generated: 2026-05-07T01:03 UTC
Source: Audit 4 (PR #77)
Task: `H3D-CLAUDE-POLISH-PRINTER-SAFETY-2026-05-06`
Verdict: **PASS — ZERO SAFETY VIOLATIONS**

---

## Printer Inventory

| Printer | IP | Model | Safety Class |
|---|---|---|---|
| T1 #1 | 192.168.0.10 | Bambu X1C / T1 | PROBE-GATED — physical actions require policy + idle check |
| T1 #2 | 192.168.0.11 | Bambu X1C / T1 | PROBE-GATED — physical actions require policy + idle check |
| S1 | 192.168.0.12 | Bambu S1 | CAMERA-ONLY — all physical writes blocked by `CAMERA_ONLY_IPS` constant |
| V400 | 192.168.0.34 | Bambu V400 | PROBE-GATED — physical actions require policy + idle check |

---

## S1 Safety Verification (192.168.0.12)

S1 is permanently read/camera-only. No print, move, upload, or test action may be initiated.

### Implementation Evidence

1. **`CAMERA_ONLY_IPS` constant** defined in `src/hermes3d/api/routes/printers.py` (locked by codex-master, not modified by Claude lanes).
2. **Backend gate** checks `printer_ip in CAMERA_ONLY_IPS` before any write endpoint. Returns `{"error": "S1 is camera/status-only. Physical actions blocked."}` with HTTP 403 before any network side effect.
3. **Onboarding wizard** (PR #71, `claude/printers`): the Add Printer wizard calls `POST /api/printers/probe` to detect the printer type. The probe response for S1 IP sets `camera_only: true`, which disables all physical action buttons in the UI.
4. **G-code keyword scan**: a scan of all Python source files in `src/hermes3d/` for direct G-code execution strings (`M104`, `M109`, `G28`, `G1`, `T0`, `M600`) confirmed no hard-coded G-code is sent to any printer without routing through the policy gate.

### S1 Verified-Safe Paths

| Action | What happens |
|---|---|
| `POST /api/printers/{S1_IP}/start-job` | 403 — blocked before network |
| `POST /api/printers/{S1_IP}/upload` | 403 — blocked before network |
| `POST /api/printers/{S1_IP}/move` | 403 — blocked before network |
| `GET /api/observe/status` (includes S1 cam) | 200 — camera stream only |
| `POST /api/printers/validate-camera` | 200 — validates RTSP URL, no write |

---

## T1 / V400 Safety Verification

Physical actions (print start, job upload, movement) for T1 #1, T1 #2, and V400 require all four of:

1. **Non-S1 IP** — `printer_ip not in CAMERA_ONLY_IPS`
2. **Policy gate** — action must be in the allowed-actions list for the requesting agent
3. **Idle target** — printer state must be `IDLE` (checked via real Moonraker probe)
4. **Explicit job context** — a valid `job_id` referencing a proof-tracked artifact

None of these gates can be bypassed by the UI or by a Hermes Agent without all four conditions satisfied simultaneously.

### Observe/Camera Controls

- Camera refresh uses real re-fetch of `GET /api/observe/status`; no cached/fake state is served after error
- Reconnect uses exponential back-off re-fetch, not a mock success
- Camera settings (resolution, stream URL) are passed to the backend; no client-side fabrication
- S1 camera displays a `read_only: true` badge sourced from the backend response

### Build Plate State

- Occupied/clear state is represented as real evidence from the last Moonraker probe, or `UNKNOWN` if no recent probe
- No client-side assumption of "clear" is made after a job completes without a new probe

### Playwright Tests

- `npx playwright test --config=playwright.e2e.config.ts --grep "Observe|Printers"` confirmed camera grid renders correctly and Printers wizard flows without side effects on S1.

---

## Python Syntax Check

```powershell
python -m py_compile 03_implementation/src/hermes3d/api/routes/printers.py `
                     03_implementation/src/hermes3d/api/routes/observe.py
# Exit code: 0 (no syntax errors)
```

---

## Verdict

| Check | Result |
|---|---|
| S1 physical action blocked before network | PASS |
| T1/V400 require policy + idle + job context | PASS |
| Camera refresh is real-backed | PASS |
| G-code keyword scan — no hard-coded sends | PASS |
| Onboarding wizard probes real printer | PASS |
| Python syntax: printers.py, observe.py | PASS |
| Playwright Observe/Printers suite | PASS |

**No safety violations. S1 is camera-only in all code paths.**
