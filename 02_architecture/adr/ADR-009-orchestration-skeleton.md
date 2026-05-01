# ADR-009: Orchestration Skeleton — Supervisor, Capability Tokens, Ledger, Local Bridge, Refusal Rules

## Status
Accepted (Phase 3.1, 2026-05-01).

## Context
Phase 2 ([`PHASE2_COMPLETION_REPORT.md`](../../00_overview/PHASE2_COMPLETION_REPORT.md)) shipped the UI-Final React shell with a frozen `AdapterAPI` interface at [`03_implementation/ui/src/api/adapters.ts`](../../03_implementation/ui/src/api/adapters.ts). Every dangerous action renders a `LockedAction` pill; the UI cannot reach across the adapter boundary.

Phase 3 ([`PHASE3_PLAN.md`](../../00_overview/PHASE3_PLAN.md)) introduces the first real adapter — a Moonraker GET-only client behind an orchestration layer — without weakening any Phase-2 safety boundary. ADR-008 already locks the **adapter** surface (16-member Protocol, dry-run/execute gate, capability vocabulary). This ADR locks the **orchestration** surface that sits between the UI and those adapters.

Without this ADR, four ambiguities would re-emerge per implementer:
1. Who owns scheduling of agent tool calls?
2. What stops an agent from calling a tool it shouldn't?
3. Where do tool invocations get logged so the proof bundle can include them?
4. How does the UI reach the orchestrator without becoming a launch surface itself?

## Decision

### 1. Supervisor — single point of dispatch
A **single in-process supervisor** is the only component that:
- holds a registry of registered agents and their declared toolsets,
- issues capability tokens (§2),
- holds per-resource mutexes (per-printer, per-Blender-process, per-slicer-binary),
- walks the task DAG topologically and dispatches ready nodes,
- writes every dispatch + result to the ledger (§3),
- honors a single global `Cancel` channel.

Agents do not call tools directly. Agents receive a typed `PollRequest` (or, in later phases, a typed `Action`) plus a `CapabilityToken` from the supervisor. Tools accept calls only when the presented token is valid for the requested operation. An agent without a token cannot dispatch — see §5.

Phase 3.1 ships **one** supervisor implementation, **one** agent (`PrinterExecutor`), and **one** tool (Moonraker read-only). No Planner, no Repair, no Releaser yet — those land in Phase 3.2+.

### 2. Capability-token model
A `CapabilityToken` is an immutable, supervisor-signed record:

| Field | Type | Purpose |
|---|---|---|
| `token_id` | uuid4 | unique handle for ledger correlation |
| `agent_id` | str | the agent the supervisor issued it to |
| `tools` | frozenset[str] | tool method-names this token unlocks |
| `scopes` | frozenset[str] | data-scope qualifiers (e.g. `printer:t1-1`) |
| `issued_at_utc` | ISO 8601 | issuance timestamp |
| `expires_at_utc` | ISO 8601 | hard expiry; default 30 s in Phase 3.1 |
| `phase` | int | minimum adapter `phase` this token may invoke (clamped at the supervisor's current phase) |
| `signature` | hex bytes | HMAC over the above fields with `HERMES3D_PROOF_KEY` |

Rules:
- A token is **single-use per tool call**. The tool consumes it before executing; replays are rejected.
- A token's `phase` is **never** higher than the supervisor's current operational phase. Phase 3.1 supervisors clamp to `phase=3`.
- Tokens are not network-reachable; they live in process memory and the ledger, never in the UI.
- The UI never sees, requests, or carries a token. The bridge (§4) speaks only in already-collected snapshots.

### 3. Ledger — append-only event log
A SQLite database at `var/orchestration/ledger.sqlite`, schema:

```sql
CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc        TEXT    NOT NULL,    -- ISO 8601
    run_id        TEXT    NOT NULL,    -- supervisor run identifier
    agent_id      TEXT    NOT NULL,    -- which agent acted
    tool          TEXT    NOT NULL,    -- which tool method
    inputs_sha    TEXT    NOT NULL,    -- sha256 of the canonical-JSON input
    outputs_sha   TEXT,                -- sha256 of the canonical-JSON output (NULL on Err)
    verdict       TEXT    NOT NULL,    -- "pass" | "fail" | "skip"
    message       TEXT,                -- short human-readable summary
    token_id      TEXT    NOT NULL     -- the capability token consumed
);
CREATE INDEX IF NOT EXISTS events_run_idx ON events(run_id);
```

Invariants:
- **Append-only.** No `UPDATE`, no `DELETE`. The Phase 0/1 forbidden-pattern scanner is extended to fail any commit that contains `UPDATE events` or `DELETE FROM events`.
- Every dispatch writes one row at issuance (`verdict=pending` placeholder is forbidden — the row is written on completion, not on dispatch start).
- Every row carries the token id used; orphan rows (no matching token) are rejected by the supervisor on rollup.
- Rollup helper produces a content-addressed sha that the proof bundle references; the bundle's manifest must claim the exact ledger sha or honesty-diff fails.

### 4. Bridge — local-only HTTP boundary
The UI-to-orchestrator channel is a FastAPI app bound to **127.0.0.1** only.

| Constraint | Rule |
|---|---|
| Bind address | `127.0.0.1` exclusively. The bridge MUST refuse `0.0.0.0` (asserted in integration test). |
| Port | Resolved from `HERMES3D_BRIDGE_PORT` (default 9787); written to `var/orchestration/bridge.port` for the UI to discover. |
| CORS | Disabled for non-loopback origins. The default policy refuses every request whose `Origin` resolves outside `127.0.0.1` / `localhost` / `[::1]`. |
| Routes (Phase 3.1) | `GET /api/printers` only. Returns the supervisor's most recent `Printer[]` snapshot. No body, no query params. |
| Authentication | None in Phase 3.1; loopback binding is the boundary. Phase 4 introduces a process-local shared secret for write actions. |
| Rate limit | Server-side soft cap of 10 req/s per route; excess returns 429. |
| TLS | Not used on loopback in Phase 3.1. |
| Logs | Every request is logged to the ledger as a `bridge.read` event with the consuming token id; the bridge itself holds a zero-scope token issued at startup. |

The bridge is the **only** surface the UI reaches. The UI cannot import from `hermes3d.orchestration` directly; all data flows through `GET /api/printers` for now and matching read-only routes in later phases.

### 5. Refusal rules — no token, no tool
Five hard refusals are enforced in code and asserted in tests:

| # | Trigger | Outcome |
|---|---|---|
| R1 | A tool method is called without a presented `CapabilityToken`. | `Err::Forbidden("no_token")`. The tool returns immediately and writes `verdict=fail` to the ledger. |
| R2 | The presented token is not in the supervisor's issued-and-not-yet-consumed set. | `Err::Forbidden("token_unknown")`. |
| R3 | The presented token's `tools` set does not contain the called method. | `Err::Forbidden("tool_not_authorized")`. |
| R4 | The token has expired (`now > expires_at_utc`). | `Err::Forbidden("token_expired")`. |
| R5 | The presented token's `phase` is below the adapter's declared phase, or the adapter manifest declares `phase>=4` while the supervisor's phase is `<4`. | `Err::Forbidden("phase_violation")`. The adapter is also refused at registration time. |

`register_adapter()` runs at supervisor boot; the manifest schema lives at `03_implementation/src/hermes3d/adapters/_capabilities.py`. A manifest with any write-class capability flag (e.g. `print_start`, `gcode_send`, `move_axis`) AND a `phase` that exceeds the supervisor's current phase is rejected before `__init__` returns.

In addition:
- The supervisor refuses to dispatch to an agent whose declared toolset is not a subset of the adapter manifests it has seen.
- The supervisor never issues a token whose `tools` set extends beyond the agent's declared toolset.
- The Phase 0 forbidden-pattern scanner is extended to reject any source line that calls a tool method without first naming a `CapabilityToken` parameter (heuristic, advisory; integration test is authoritative).

These five rules are the Phase-3 analogue of Phase-2's `LockedAction`: the UI's pill says "no, this is not yet wired"; the supervisor's token model says "no, this caller is not authorized."

### 6. What this ADR does NOT cover
- The Planner agent's task-DAG schema (Phase 3.2 ADR).
- Repair agent semantics (Phase 3.2+ ADR).
- Write-action capability tokens (Phase 4 ADR; will extend `tools` to include action-class methods and require an additional `Confirmation` per ADR-008 §5).
- Multi-supervisor / distributed orchestration (out of scope; Phase 3 is single-process).
- Inter-agent messaging beyond supervisor-mediated dispatch (out of scope).

## Rationale
- Centralizing dispatch in one supervisor makes capability checks unforgeable: there is no "back door" to a tool because the tool only accepts supervisor-signed tokens.
- An append-only ledger turns "did this agent call this tool?" from a code-audit question into a sha-rollup query — and lets the proof bundle reference it without re-scanning logs.
- Loopback binding eliminates the entire class of remote-attack surfaces for the bridge; if the user is not on the host, the bridge is unreachable.
- The five refusal rules give Codex (and human reviewers) a tight checklist: a PR that adds a tool call without naming a token, or an adapter manifest that elevates phase, fails review at the static gate.
- Keeping the surface to **one** route (`GET /api/printers`) for Phase 3.1 forces every later route to come with its own checkpoint and its own ADR amendment.

## Consequences
- Phase 3.2+ Planner / Repair work MUST issue tokens through the supervisor — no direct tool calls.
- Phase 4 write actions MUST extend the token model with action-class methods and the ADR-008 `Confirmation` envelope; no shortcuts.
- The forbidden-pattern scanner gains two new patterns (no `UPDATE events`/`DELETE FROM events`, advisory token-naming check); Phase-2-merged code is unaffected because the orchestration package does not yet exist.
- The UI's `AdapterAPI` contract is unchanged; only the implementation behind `getPrinters()` changes when CP3.1-D wires the live resolver.
- Adding any new bridge route requires (a) a new ADR amendment, (b) a new fixture, and (c) a new Layer D2 live-mode test.

## Cross-links
- [`00_overview/PHASE3_PLAN.md`](../../00_overview/PHASE3_PLAN.md) §"Phase 3.1" (this ADR's execution plan)
- [`02_architecture/adr/ADR-008-adapter-lifecycle-and-dock-undock.md`](ADR-008-adapter-lifecycle-and-dock-undock.md) (adapter surface; this ADR sits above it)
- [`03_implementation/ui/src/api/adapters.ts`](../../03_implementation/ui/src/api/adapters.ts) (the UI swap point; unchanged in CP3.1-A)
- [`hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md`](../../hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md) (the safety baseline this ADR strengthens)
- [`00_overview/PHASE2_COMPLETION_REPORT.md`](../../00_overview/PHASE2_COMPLETION_REPORT.md) §"Safety audit" (the boundary Phase 3.1 must preserve)
