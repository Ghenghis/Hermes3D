# HANDOFF_TO_CODEX — Service Health (Task 4c)

> **Status:** READY for Codex pickup.
>
> **Sequence position:** Task 4c in overnight queue (after Task 4b).
>
> **Owner:** `codex-impl-08`.
>
> **Estimated time:** 2-3 hours.
>
> **Audit history:** parent brief assumed `SettingsTab.tsx` exists — IT DOES NOT (audit confirmed `ui/src/components/` has only badges/cards/charts/dock/layout/pipeline/tables, no SettingsTab). Parent also assumed `port-monitor` is a Python library — it's a C++/Qt6 desktop GUI. This split commits up-front to in-house port probing (stdlib socket) and a NEW top-level `/health` route (NOT a Settings subtab).

---

## 1. Mission

Make Hermes3D's service topology VISIBLE in the React UI. Operators need to see at a glance whether: HermesProof MCP is reachable, LM Studio is up, Ollama is up, Blender MCP is up, ComfyUI is up, Moonraker is reachable per printer, FastAPI server is up, Gradio launcher is up, VPS tunnel is up.

Three pieces:

1. **`port_probe.py`** (NEW) — stdlib `socket.connect_ex` probe across a known service list. NO `port-monitor` library dependency (it's a desktop GUI, not callable).
2. **FastAPI endpoint** `/api/health/services` — returns probe results as JSON.
3. **React `/health` route** (NEW) — top-level route in the React UI sidebar. Cards per service with status pills.

NO LLM provider work. NO Mnemosyne. Those are 4a and 4b.

---

## 2. Claim

```text
hermes_pick_task
  owner=codex-impl-08
  prefer_task_id=CP-HERMES3D-SERVICE-HEALTH
```

Or fallback: `taskId=CP-HERMES3D-SERVICE-HEALTH`, `title=Service Health UI + in-house port probe`, `reason=Operators need topology visibility. Split 3/3 of LOCAL-INTELLIGENCE which failed audit.`

---

## 3. Branch

`feat/cp-hermes3d-service-health` from `develop`.

---

## 4. Lock these files (audit-verified)

```text
hermes_lock_files
  owner=codex-impl-08
  taskId=CP-HERMES3D-SERVICE-HEALTH
  ttlMinutes=180
  files=[
    "03_implementation/src/hermes3d/core/integrations/port_probe.py",
    "03_implementation/src/hermes3d/api/server.py",
    "03_implementation/src/hermes3d/api/routes/health.py",
    "03_implementation/ui/src/app/routes.tsx",
    "03_implementation/ui/src/app/AppShell.tsx",
    "03_implementation/ui/src/components/health/ServiceHealthPage.tsx",
    "03_implementation/ui/src/components/health/ServiceCard.tsx",
    "03_implementation/ui/src/components/health/StatusPill.tsx",
    "04_testing/pytest/integration/test_port_probe.py",
    "04_testing/pytest/integration/test_health_route.py",
    "04_testing/playwright/health_page.spec.ts"
  ]
```

**Confirmed existing on develop:**
- `03_implementation/src/hermes3d/api/server.py` (NOTE the `src/hermes3d/` subpath — the parent brief got this wrong)
- `03_implementation/ui/src/app/routes.tsx`
- `03_implementation/ui/src/app/AppShell.tsx`
- `03_implementation/ui/src/components/` (no `health/` subdir yet — NEW)
- `04_testing/playwright/` (existing test directory)

**Confirmed NEW:** `port_probe.py`, `routes/health.py`, all 3 React `health/*.tsx` files, the 3 test files.

**If `api/routes/` directory doesn't exist** on develop (FastAPI app may have routes inline in `server.py`), update the lock list: drop `routes/health.py` and add the new endpoint inline in `server.py` instead. Verify before locking.

---

## 5. Implementation contract

### 5.1 `port_probe.py` — in-house stdlib probe

```python
"""Service-health port probe. NO external library — stdlib socket only.

`port-monitor` (rakaarwaky/port-monitor) is a C++/Qt6 desktop GUI, not a
Python library. We probe ports ourselves with `socket.connect_ex` for
fast TCP-reachability checks plus optional HTTP probes for richer status.
"""
from __future__ import annotations

import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional


class Status(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNREACHABLE = "unreachable"
    AUTH_REQUIRED = "auth-required"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    host: str
    port: int
    category: str       # "mcp" | "llm" | "modeling" | "printer" | "api" | "tunnel"
    enabled: bool = True
    http_health_path: Optional[str] = None  # e.g. "/v1/models" for LM Studio


@dataclass
class ProbeResult:
    spec: ServiceSpec
    status: Status
    detail: str
    latency_ms: float
    probed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


KNOWN_SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec("HermesProof MCP", "127.0.0.1", 0, "mcp", enabled=False),  # stdio, special-cased
    ServiceSpec("LM Studio",       "127.0.0.1", 1234,  "llm", http_health_path="/v1/models"),
    ServiceSpec("Ollama",          "127.0.0.1", 11434, "llm", http_health_path="/api/tags"),
    ServiceSpec("Hipfire (AMD)",   "127.0.0.1", 11435, "llm", enabled=False),  # only if HERMES3D_AMD_NODE=1
    ServiceSpec("Blender MCP",     "127.0.0.1", 9876,  "modeling"),
    ServiceSpec("ComfyUI",         "127.0.0.1", 8188,  "modeling"),
    ServiceSpec("FastAPI server",  "127.0.0.1", 8000,  "api"),
    ServiceSpec("Gradio launcher", "127.0.0.1", 7860,  "api"),
)


def probe_one(spec: ServiceSpec, timeout_s: float = 0.5) -> ProbeResult:
    if not spec.enabled:
        return ProbeResult(spec, Status.DISABLED, "service disabled by config", 0.0)
    if spec.port == 0:
        return ProbeResult(spec, Status.UNKNOWN, "stdio service; probe via MCP handshake separately", 0.0)
    start = datetime.now(timezone.utc)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout_s)
            rc = s.connect_ex((spec.host, spec.port))
            elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            if rc == 0:
                return ProbeResult(spec, Status.ONLINE, f"TCP {spec.host}:{spec.port} accepted", elapsed_ms)
            return ProbeResult(spec, Status.OFFLINE, f"TCP {spec.host}:{spec.port} refused (errno={rc})", elapsed_ms)
    except socket.gaierror as exc:
        return ProbeResult(spec, Status.UNREACHABLE, f"DNS/host error: {exc}", 0.0)
    except OSError as exc:
        return ProbeResult(spec, Status.UNREACHABLE, f"socket error: {exc}", 0.0)


def probe_all(extra: tuple[ServiceSpec, ...] = ()) -> list[ProbeResult]:
    """Probe KNOWN_SERVICES plus any extra (e.g., per-printer Moonraker entries
    loaded from printers.user.toml).
    """
    return [probe_one(s) for s in (*KNOWN_SERVICES, *extra)]
```

Per-printer Moonraker entries: read `03_implementation/config/printers.toml` (stock template) and the gitignored `printers.user.toml` if present. For each printer, build a `ServiceSpec("Moonraker — {printer_id}", host=printer.ip, port=7125, ...)`. Don't fail if `printers.user.toml` doesn't exist — fall back to stock-template hosts.

### 5.2 `/api/health/services` endpoint

In `api/server.py` (or `api/routes/health.py` if the FastAPI app uses APIRouter modules):

```python
from hermes3d.core.integrations.port_probe import probe_all

@router.get("/api/health/services")
def health_services():
    results = probe_all()
    return {"results": [
        {
            "name": r.spec.name,
            "category": r.spec.category,
            "status": r.status.value,
            "detail": r.detail,
            "latency_ms": round(r.latency_ms, 1),
            "probed_at": r.probed_at,
        }
        for r in results
    ]}
```

Same auth as the rest of the API (session token via `Depends(get_session)` or whatever the existing pattern is — read existing route examples in `server.py` first).

### 5.3 React `/health` route — NEW top-level route

The audit confirmed there's NO Settings tab in the React UI. So this is NOT a subtab — it's a new top-level route in the existing sidebar.

**`ui/src/app/routes.tsx`** — add a new route `{ path: "/health", element: <ServiceHealthPage /> }`.

**`ui/src/app/AppShell.tsx`** — add a sidebar nav entry for `/health` with an icon (use `Heart` or `Activity` from lucide-react). Place it between the existing Logs and any future Settings items, or at the end if Settings doesn't exist.

**`ui/src/components/health/ServiceHealthPage.tsx`** (NEW):
- Calls `GET /api/health/services` on mount
- Auto-refreshes every 30s (configurable; expose a "Pause auto-refresh" toggle)
- Renders a grid of `ServiceCard`s grouped by category (MCP / LLM / Modeling / Printer / API / Tunnel)
- "Re-probe now" button calls the API immediately

**`ui/src/components/health/ServiceCard.tsx`** (NEW):
- Service name + category badge
- Status pill (online green / offline red / unreachable amber / auth-required purple / disabled gray)
- Last-probed timestamp (relative, "12s ago")
- Latency in ms

**`ui/src/components/health/StatusPill.tsx`** (NEW):
- Reusable pill component with status → color mapping
- Used by ServiceCard, may be used by other tabs later

### 5.4 Tests

- `test_port_probe.py` — probe a localhost port that's open (use `socketserver` fixture); probe a closed port; timeout handling; per-result schema correctness
- `test_health_route.py` — mock `probe_all`, verify endpoint shape; auth required; latency reported
- `health_page.spec.ts` (Playwright) — page loads at `/health`, cards render, "Re-probe now" button triggers a request

---

## 6. Tests + gates

```text
hermes_run_gate gateId=git-status      cwd=.
hermes_run_gate gateId=git-diff-check  cwd=.
```

Local:
- `pip install -e ".[all]"` (no new deps — uses stdlib socket)
- `pytest -q` — 670+ existing + 2 new pytest tests pass
- `npm --prefix 03_implementation/ui run build` — UI builds clean
- `npm --prefix 03_implementation/ui test` (if Vitest configured) — passes
- `npx playwright test 04_testing/playwright/health_page.spec.ts` — passes (via `scripts/run-e2e.sh` if needed)

CI: Layer A/B/C/D/D3/F/M/T/W must all pass. Layer D3 should not regress (Codex fixed it cleanly — keep that pattern).

---

## 7. PR + close-out

```bash
git push -u origin feat/cp-hermes3d-service-health
gh pr create --base develop \
  --title "feat(ui): Service Health page + in-house port probe (Task 4c)" \
  --body "[Hermes evidence chain: PASS; Task: CP-HERMES3D-SERVICE-HEALTH; Gate run via hermes_run_gate]"
```

Close-out per standard pattern.

---

## 8. Hard rules

- DO NOT add `port-monitor` (rakaarwaky/port-monitor) as a dependency — it's a C++/Qt6 desktop GUI, not a library. Use stdlib `socket` only.
- DO NOT auto-discover printer IPs from network scan — read from existing `printers.toml` + gitignored `printers.user.toml`.
- DO NOT make the health endpoint unauthenticated — same auth as the rest of the API.
- DO NOT touch the LLM provider chain (that's Task 4a) or Mnemosyne (that's Task 4b).
- DO NOT touch any file outside the §4 lock list.
- DO NOT introduce a Settings tab if you discover a half-written one — that's its own checkpoint, not this brief's scope.

## 9. Failure protocol

If the FastAPI app's structure is `routes/` (separate route modules) — fine, follow that pattern. If it's a single-file `server.py` — fine, add the endpoint inline. Don't refactor existing route organization just for this PR.

If Playwright is broken on the develop branch (e.g., the launcher's tab names changed again), update the smoke test to match reality and fix it as part of this PR — same pattern Codex used for the Layer D3 flake fix during B4. That's a known-acceptable cross-cutting fix.
