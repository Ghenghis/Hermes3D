# W21-A4 — Hermes Agents Activation & Provider-Routing Audit

**Task ID:** `W21-A4-HERMES-AGENTS-ACTIVATION-AUDIT-2026-05-11`
**Auditor:** Claude (filling W21-A4 directly because the agents this audit is supposed to wake up are themselves idle — chicken-and-egg)
**Date:** 2026-05-11
**Backend probed:** `http://127.0.0.1:8765` (PID 33228, uvicorn launched 15:46:04 PT)
**Orchestrator state:** `G:\Github\Hermes3D\.hermes3d_orchestrator\`
**Develop SHA:** `603ba65` (includes #255 fixes + #256 docs)

---

## Verdict

`HERMES_AGENTS_NOT_ACTIVATED`

**Why agents are idle:** there is **no code path** in the running backend that reads
`.hermes3d_orchestrator/tasks/pending/`, matches `target_owner_pattern` against the
8 Hermes personas, and claims/dispatches the task. The orchestrator MCP and the
backend Hermes runtime are two disconnected systems sharing the same disk but no
process logic.

Secondary blocker: `G:\private\.env` is never loaded into the backend's process
environment, so `MINIMAX_API_KEY` and `DEEPSEEK_API_KEY` show `key_present:false`
even though both values are present on disk. The agents cannot route work to
remote providers; only the LM Studio fallback responds.

LM Studio responding is **NOT** equivalent to MiniMax/DeepSeek being live —
calling it equivalent would violate the W18 strict provider-routing rule.

---

## Evidence

### 1. Queue contents (orchestrator side)

`.hermes3d_orchestrator/tasks/pending/` contains **7 W21 task files**:

```
W21-A1-FEATURE-ACTION-DEEP-AUDIT-2026-05-11.json        priority=100  owner=oliver-qa-agent|factory-operator
W21-A2-DESIGN-MODELER-E2E-AUDIT-2026-05-11.json         priority=95   owner=modeling-agent|mesh-go-agent
W21-A3-GEN3D-PROVIDER-3090TI-AUDIT-2026-05-11.json      priority=90   owner=modeling-agent|mesh-go-agent
W21-A4-HERMES-AGENTS-ACTIVATION-AUDIT-2026-05-11.json   priority=100  owner=factory-operator|privacy-agent|oliver-qa-agent
W21-A5-60-APP-PROOF-DEEP-AUDIT-2026-05-11.json          priority=85   owner=oliver-qa-agent|factory-operator
W21-A6-REALTIME-UX-STALE-STATE-AUDIT-2026-05-11.json    priority=88   owner=oliver-qa-agent|factory-operator
W21-A7-LAG-PROTECTED-E2E-HARNESS-2026-05-11.json        priority=92   owner=oliver-qa-agent|factory-operator
```

All 7 files have `claimed_by: null`, `heartbeat_utc: null`, `done_utc: null`.

### 2. Hermes personas (backend side)

`GET /api/agents/health` (probed at 23:18 UTC):

```json
{
  "healthy": true,
  "status": "bridge_ready",
  "agents": {
    "factory-operator": "idle",
    "modeling-agent": "idle",
    "print-safety-agent": "idle",
    "mesh-go-agent": "idle",
    "mesh-repair-agent": "idle",
    "oliver-qa-agent": "idle",
    "print-monitor-agent": "idle",
    "privacy-agent": "idle"
  },
  "providers": {
    "minimax":  { "key_present": false, "model": "MiniMax-M2",      "kind": "live_remote" },
    "deepseek": { "key_present": false, "model": "deepseek-v4-pro", "kind": "live_remote" },
    "lm_studio": { "key_present": false, "status": "green" },
    "ollama":   { "key_present": false, "status": "green" }
  }
}
```

All 8 personas are `idle`. They are **alive in the runtime** but have nothing to
do because no task ever reaches them.

### 3. Orchestrator agent registry side

`mcp__hermes3d-locks__hermes_list_agents` (probed via the MCP):

```
21 actors registered — NONE of them are the 8 Hermes personas.
The 21 entries are all w18-* and claude-* (past Claude/CI session actors).
factory-operator, modeling-agent, print-safety-agent, mesh-go-agent,
mesh-repair-agent, oliver-qa-agent, print-monitor-agent, privacy-agent
do not appear.
```

That is the **smoking gun**: the orchestrator has never seen the Hermes personas
even register themselves, so the queue's dispatch-rank logic could never route
to them even if it tried.

### 4. Code-search proof for the missing bridge

Greps that returned NO matches in `03_implementation/src/hermes3d/`:

| Pattern | Match count | Notes |
|---|---|---|
| `hermes_pick_task` | 0 | MCP claim verb — backend never calls it |
| `hermes_claim_task` | 1 (docstring only at `agents.py:3402`) | "Uses hermes_claim_task" comment, not a runtime call |
| `hermes_list_pending_tasks` | 0 | Backend never lists pending tasks |
| `tasks/pending` | 0 | Backend never reads the directory |
| `HERMES_AGENT_ENABLED` | 0 | Flag mentioned in W19/W20 plans is not wired |
| `load_dotenv` / `dotenv` / `private\.env` / `env_file` | 0 | No .env loading code anywhere |

`mcp_locks.py` reads `.hermes3d_orchestrator/locks/` for FILE LOCK state — but
not `tasks/`. The two pieces of state live in the same directory but are
served by different code paths and only the locks half is wired.

### 5. Backend launch command (PID 33228, PT 15:46:04)

```
C:\Python314\python.exe -m uvicorn hermes3d.api.app:app --host 127.0.0.1 --port 8765
```

No `--env-file`. No wrapper script. `hermes3d.api.app` does not import or call
any dotenv-style loader (proven by grep). So whatever was in `G:\private\.env`
at process start was never visible to this process.

`G:\private\.env` was confirmed to contain (operator confirmed values; redacted):

```
MINIMAX_API_KEY=sk-cp-…       (1 line, 88 chars — non-empty)
DEEPSEEK_API_KEY=sk-…          (1 line, 35 chars — non-empty)
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_MODEL=MiniMax-M2.7-highspeed
HERMES3D_MINIMAX_API_KEY=sk-cp-…   (Hermes3D-namespaced alias)
HERMES3D_DEEPSEEK_API_KEY=sk-…     (Hermes3D-namespaced alias)
```

---

## Classification

Per the W20 status taxonomy, the Hermes Agents tab and the backend bridge are:

| Surface | Status | Reason |
|---|---|---|
| `/api/agents/health` | `WORKING_HONEST_BLOCKED` | bridge_ready, personas alive, but no live provider key |
| `/api/agents/providers/health` | `BROKEN_BACKEND` (404) | endpoint not registered — UI gets 404 |
| `MiniMax` provider | `BROKEN_BACKEND` (key not loaded) | env file unread |
| `DeepSeek` provider | `BROKEN_BACKEND` (key not loaded) | env file unread |
| Hermes persona task-claim | `NOT_WIRED` | no poller exists |
| Orchestrator → persona dispatch | `NOT_WIRED` | personas never register with orchestrator |

---

## Fix Plan (small, incremental, lag-protected)

### MVP-1 — Env file loading (one PR)

Goal: `key_present:true` for MiniMax + DeepSeek after backend restart.

1. Add `python-dotenv` to the runtime dependency set (already a transitive dep
   in most stacks; if missing, add to `pyproject.toml` `[project.dependencies]`).
2. Create `hermes3d.config.env_loader` that:
   - Reads `HERMES3D_ENV_FILES` (semicolon-separated list, default
     `G:\private\.env;./.env`) at process start.
   - Loads each file's keys into `os.environ` with `override=False` (existing
     env always wins so CI / explicit env can override).
   - Logs which files were found, which keys were applied (names only, never
     values), and which files were missing.
3. Call `env_loader.load_at_startup()` at the very top of
   `hermes3d.api.app.create_app` and `create_gui_app` BEFORE any route imports
   that read env at import time.
4. Add integration test that:
   - Writes a temp `.env` containing `MINIMAX_API_KEY=test_sentinel`.
   - Points `HERMES3D_ENV_FILES` at it.
   - Spawns the FastAPI app via `TestClient`.
   - `GET /api/agents/health` → `providers.minimax.key_present == true`.

**Lag protection:** test waits on `TestClient` boot, then probes — no `sleep`
loops, no `time.sleep` between assertions.

### MVP-2 — Activation bridge (second PR, after MVP-1 lands)

Goal: at least one Hermes persona claims at least one W21 task.

1. Add `hermes3d.services.queue_bridge` that:
   - Polls `.hermes3d_orchestrator/tasks/pending/*.json` on a `asyncio` background
     task (5s interval).
   - For each task, matches `target_owner_pattern` regex against the live
     persona id set returned by the existing agent registry.
   - Calls into the MCP `hermes_claim_task` verb (or directly renames the file
     to `claimed/` with a `claimed_by` and `claimed_utc` patch — depends on
     whether the orchestrator file format is the contract or just a cache).
   - On claim, persists `actor_id = "<persona>-W21Axx"` so the orchestrator
     reputation system sees them.
2. Add `/api/agents/queue/status` route that returns the current
   `(pending, claimed_by_us, claimed_by_others, done)` counts so the UI's
   Agents tab can render a real-time bridge health card.
3. Add an `actor_register` startup that does the inverse:
   register every persona id as an orchestrator actor on first launch (so
   `hermes_list_agents` includes them).
4. Wire a "Run task" action per persona in the existing `#agents` tab that
   manually triggers a claim of the highest-priority matching task (so the
   operator can force-claim while the auto-poller is in soak).

**Lag protection (W21-A7 alignment):**
- Poller interval is 5s; do NOT assert on a sub-5s window in tests.
- E2E test arms `waitForResponse('**/api/agents/queue/status')` before the
  expected first poll cycle.
- Backend-evidence check (`tasks/claimed/W21-A?.json` exists on disk) AND
  UI evidence (queue status card reflects claim) must BOTH pass — two
  stable reads with a 1.5s gap.

### MVP-3 — Persona execution path (third PR, only after MVP-2)

Goal: a claimed task transitions to `done/` with a real handoff doc.

1. For each persona, add a minimal "execute" surface — a Python function that
   takes a claimed task and produces the deliverable named in `handoff_path`.
2. The MVP execute can be a STUB that writes a 1-line "claimed by X, work
   needed" handoff doc and marks the task `BLOCKED_HUMAN`. That is honest
   ('the persona acknowledged but cannot finish without external code'), and
   it gets the orchestrator unstuck so future PRs can implement real execute.

---

## Rules followed

- **No printer hardware actions.**
- **No fake pass.** The audit honestly reports the activation bridge is
  missing; it does not claim agents are working.
- **No route-only green.** Every claim in the verdict references a probe
  result, a code-search result, or a process listing.
- **No broad skips.** Each of the 7 sub-systems was probed individually.
- **LM Studio is NOT MiniMax.** The audit explicitly separates LM Studio
  (`status: green` but `key_present: false`) from MiniMax/DeepSeek
  (`key_present: false`).

---

## Recommended dispatch

After MVP-1 lands and the backend is restarted with the env loaded:

1. Re-probe `/api/agents/health` → expect `minimax.key_present:true`,
   `deepseek.key_present:true`.
2. Smoke MiniMax via `POST /api/agents/providers/smoke {"provider":"minimax"}`
   and DeepSeek via the same; expect `PASS_LIVE`.
3. Then MVP-2 ships, and the W21-A1/A2/A3/A5/A6/A7 tasks become claimable.

Only after MVP-2 ships and a persona claims at least one W21 task can this
audit be marked `done`. Until then, this handoff doc IS the in-flight work
product for W21-A4.
