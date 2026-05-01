# ADR-008: Adapter Lifecycle, Dock/Undock Model, Capability Vocabulary, Dry-Run/Execute Boundary, Error Model

## Status
Accepted (Phase 1, 2026-04-30).

## Context
Phase 0 (PR #11) found two non-identical adapter surfaces in the v4.1 kit:
- [`hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/ADAPTER_INTERFACE.md`](../../hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/ADAPTER_INTERFACE.md): 7 methods (`detect / capabilities / validate / launch(mode) / status / dry_run / execute`).
- [`hermes3d_gui_contract_kit_v4.1/02_architecture/ADAPTER_BOUNDARY_ARCHITECTURE.md`](../../hermes3d_gui_contract_kit_v4.1/02_architecture/ADAPTER_BOUNDARY_ARCHITECTURE.md): a different 7 methods (`detect / version / capabilities / healthcheck / open_docked / open_undocked / open_external`).

The Phase 0 coordinator README at [`03_implementation/adapter_registry/README.md`](../../03_implementation/adapter_registry/README.md) §2 reconciled them as a normalisation. This ADR locks that reconciliation as immutable for Phase 1+ work and adds the lifecycle, capability vocabulary, dry-run/execute binding, and error-model contracts that the kit specs leave loose.

## Decision

### 1. Adapter surface (canonical 16 members)
A `ToolAdapter` exposes:
- **Identity** (constants): `key: str`, `display_name: str`, `category: str`, `dangerous: bool`
- **Lifecycle**: `version() -> str | None`, `detect() -> DetectResult`, `capabilities() -> frozenset[CapabilityFlag]`, `validate() -> ValidateResult`, `healthcheck() -> HealthResult`, `status() -> AdapterState`
- **Dock surface** (UI-bearing only): `open_docked() -> LaunchResult`, `open_undocked() -> LaunchResult`, `open_external() -> LaunchResult`, `detach_ui() -> None`
- **Action plane**: `dry_run(action: Action) -> DryRunResult`, `execute(action: Action, confirmation: Confirmation) -> ExecuteResult`

`validate()` (one-shot config check) and `healthcheck()` (steady-state liveness) are kept distinct rather than merged into one method.

### 2. Lifecycle states
8 states, monotonic progression with two backward edges:
```
uninstalled → detected → configured → ready → connecting → connected
                                                    ↑
                                                degraded ↔ error
```
- `uninstalled` — `detect()` returned no binary / no service
- `detected` — present but `validate()` not yet run or failed
- `configured` — `validate()` passed; required config present
- `ready` — accepts `dry_run()` / `open_*()`
- `connecting` — async transition (tunnel handshake, USB open)
- `connected` — `healthcheck()` returned OK
- `degraded` — `healthcheck()` returned warnings (high latency, partial features)
- `error` — fatal; user action required

`status()` MUST return one of these.

### 3. Dock/undock/external — three modes
- `docked` — tool's UI inside a Hermes3D panel (iframe for web UIs; native external surface for Blender)
- `undocked` — tool's UI in a separate Hermes3D-managed window; closing the window MUST NOT kill the backend (`detach_ui()` decouples)
- `external` — tool launched as its own OS process; Hermes3D continues to talk to it via the adapter's transport

Iframe-blocking fallback for web UIs (per [`DOCK_UNDOCK_REQUIREMENTS.md`](../../hermes3d_gui_contract_kit_v4.1/01_requirements/DOCK_UNDOCK_REQUIREMENTS.md)): try iframe → on `X-Frame-Options` mismatch surface "Open externally" CTA → external launch via system browser.

### 4. Capability vocabulary
Closed enum (`CapabilityFlag`):
`cli`, `gui`, `headless_smoke`, `usb`, `websocket`, `rest_api`, `mcp`, `dock_iframe`, `streaming_logs`, `dry_run_supported`, `e_stop`, `read_only`.

UI conditional rendering and CI smoke gates key off this enum. New tokens require a new ADR.

### 5. Dry-run / execute boundary
`execute()` of any `dangerous` adapter MUST require a `Confirmation` whose `dry_run_token` matches the most recent `dry_run()` of the same `Action.payload` hash. The token is opaque (impl detail of the adapter) but must be:
- short-lived (per-session; recommended TTL ≤ 5 min)
- tied to the exact action payload hash (replay-protection)
- presented exactly once (consumed on `execute()`)

`Confirmation` also carries: `user`, `ts_utc` (ISO 8601), optional `printer_id`, `reason_text` (1-280 chars), `signed_token` (HMAC over `(user, ts_utc, printer_id, action_payload_hash, policy_version)` with `HERMES3D_PROOF_KEY`), and `policy_version`.

`execute()` MUST reject if any of: token mismatch, signed_token HMAC fails, `policy_version` older than the loaded policy, user not authorized for this `printer_id`.

### 6. Error model
Extended `AdapterResult` envelope:
- Always carries: `ok`, `adapter`, `mode`, `artifacts`, `logs`, `proof` (`{timestamp_utc, branch, commit}`)
- Phase 1 additions: `error_code` (stable string, e.g. `ADAPTER.MOONRAKER.AUTH_REQUIRED`), `severity` (`info`/`warn`/`error`/`fatal`), `recoverable` (bool), `user_action_required` (string | null), `dry_run_token` (set only on `ExecuteResult` after consumption)

`logs[]` entries are `LogEntry` records — never freeform strings — with `ts_utc`, `severity`, `source`, `code`, `msg`, `redactions`. Adapters are responsible for redacting API keys / tokens / IPs at their own boundary; raw secrets MUST NOT appear in proof bundles ([`SECURITY_AND_SAFETY_POLICY.md`](../../hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md)).

### 7. Phase mapping
- **Phase 1** (this PR): `detect()`, `version()`, `capabilities()` are real; everything else raises `NotImplementedYet`.
- **Phase 3**: `validate()`, `healthcheck()`, `status()`, `open_docked/undocked/external()`, `detach_ui()` ship — read-only adapters.
- **Phase 6**: `dry_run()` and `execute()` ship — write actions behind the dry-run-token + Confirmation gate.

## Rationale
- Two divergent kit specs would have been re-resolved differently by every implementer; locking one canonical surface removes that ambiguity.
- `validate()` vs `healthcheck()` are different *kinds* of check (one-shot vs liveness); merging them would make UI badges ambiguous.
- A typed `AdapterState` enum lets the UI render consistent badges per panel without each adapter inventing its own status vocabulary.
- A closed `CapabilityFlag` enum lets the registry validator + UI conditionally render controls without string-matching.
- The `dry_run_token` binding is the foundation of the user's "no live print commands before dry-run proof gates" rule; without it, dry-run is advisory only.
- The extended error envelope (with `error_code`, `severity`, `recoverable`, `user_action_required`) lets the proof bundle and the UI surface actionable failure information instead of a stack trace.

## Consequences
- Phase 3 adapter implementers MUST satisfy this Protocol.
- Phase 6 write-action implementers MUST require a valid `Confirmation` with matching `dry_run_token`.
- Future surface changes (additional methods, new lifecycle states, new capability tokens) require a new ADR and a kit-spec update — never a silent code change.
- The kit specs ([ADAPTER_INTERFACE.md](../../hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/ADAPTER_INTERFACE.md), [ADAPTER_BOUNDARY_ARCHITECTURE.md](../../hermes3d_gui_contract_kit_v4.1/02_architecture/ADAPTER_BOUNDARY_ARCHITECTURE.md)) remain canonical for the *intent* they describe. This ADR codifies the *implementation* of that intent.

## Cross-links
- [`03_implementation/adapter_registry/README.md`](../../03_implementation/adapter_registry/README.md) §2-§7 (the reconciliation this ADR locks)
- [`hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/ADAPTER_INTERFACE.md`](../../hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/ADAPTER_INTERFACE.md)
- [`hermes3d_gui_contract_kit_v4.1/02_architecture/ADAPTER_BOUNDARY_ARCHITECTURE.md`](../../hermes3d_gui_contract_kit_v4.1/02_architecture/ADAPTER_BOUNDARY_ARCHITECTURE.md)
- [`hermes3d_gui_contract_kit_v4.1/01_requirements/DOCK_UNDOCK_REQUIREMENTS.md`](../../hermes3d_gui_contract_kit_v4.1/01_requirements/DOCK_UNDOCK_REQUIREMENTS.md)
- [`hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md`](../../hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md)
