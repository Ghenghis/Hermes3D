# Adapter Registry — Phase 0 Foundation

> **Status:** Phase 0 specification only. Zero `.py` source under `03_implementation/src/hermes3d/adapters/` is intentional. This README publishes the contracts, schemas, and matrices that the Phase 1 `AdapterBuilder` agent will implement against.
>
> **Anchored kit:** `hermes3d_gui_contract_kit_v4.1/` (HOW to build), commit `570de91`.

This document reconciles the v4.1 kit's adapter specs into a single canonical reference for implementers. It does not redesign anything — it synthesizes what is already specified across multiple kit docs and closes the normalisation gaps identified by the Phase 0 Adapter Registry audit (`var/phase0-agents/agent-4-adapter-registry-auditor.md`, audit summary in `00_overview/PHASE0_BASELINE_REPORT.md`).

## 1. Adapter taxonomy

11 locked adapter targets across 3 categories. Each row points at the authoritative kit spec(s).

| Key | Display name | Category | Dangerous | Safety gate | Dock modes | Kit specs |
|---|---|---|---|---|---|---|
| `flsun_slicer` | FLSUN Slicer | slicer | yes (write commands) | required | `external` (+ `docked` only when UI panel ships) | `03_implementation/adapters/SLICER_ADAPTERS.md`, `01_requirements/TOOL_INTEGRATION_REQUIREMENTS.md` |
| `prusa_slicer` | PrusaSlicer | slicer | yes | required | `external` | `03_implementation/adapters/SLICER_ADAPTERS.md` |
| `orca_slicer` | OrcaSlicer | slicer | yes | required | `external` | `03_implementation/adapters/SLICER_ADAPTERS.md` |
| `cura` | Cura (provisioning only) | slicer | yes | required | `external` | `03_implementation/adapters/SLICER_ADAPTERS.md` |
| `printrun` | Printrun (USB) | printer | **highest** | required | `external` (+ `docked` only when UI panel ships) | `03_implementation/adapters/PRINTER_ADAPTERS.md` §Printrun |
| `moonraker` | Moonraker | printer (HTTP API) | yes (write only) | required for write | `headless` | `03_implementation/adapters/PRINTER_ADAPTERS.md` §Moonraker |
| `octoprint` | OctoPrint | printer (REST + UI) | yes (write only) | required for write | `docked`, `undocked`, `external` | `03_implementation/adapters/PRINTER_ADAPTERS.md` §OctoPrint |
| `mainsail` | Mainsail (Moonraker UI) | printer-ui | no (writes go through Moonraker adapter) | n/a | `docked`, `undocked`, `external` | `03_implementation/adapters/PRINTER_ADAPTERS.md` §Fluidd/Mainsail; `01_requirements/DOCK_UNDOCK_REQUIREMENTS.md` |
| `fluidd` | Fluidd (Moonraker UI) | printer-ui | no | n/a | `docked`, `undocked`, `external` | `03_implementation/adapters/PRINTER_ADAPTERS.md` §Fluidd/Mainsail |
| `blender` | Blender | 3d (external) | yes (Python execution) | required | `external` (status/screenshots/logs in Hermes3D, never docked viewport) | `03_implementation/adapters/BLENDER_MCP_PROVIDER_MANAGER.md`; `01_requirements/DOCK_UNDOCK_REQUIREMENTS.md` |
| `blender_mcp` | Blender MCP (provider manager) | 3d-mcp | yes | required | n/a (provider) | `03_implementation/adapters/BLENDER_MCP_PROVIDER_MANAGER.md` |

**Coverage:** 10/10 user-locked tools + Cura provisioning slot. Registry YAML coverage details in `01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md`.

## 2. Canonical adapter surface (merged)

The kit publishes two non-identical adapter surfaces:
- `hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/ADAPTER_INTERFACE.md` — `detect / capabilities / validate / launch(mode) / status / dry_run / execute`
- `hermes3d_gui_contract_kit_v4.1/02_architecture/ADAPTER_BOUNDARY_ARCHITECTURE.md` — `detect / version / capabilities / healthcheck / open_docked / open_undocked / open_external`

Phase 1 implements the **union** below. This is a normalisation, not a redesign — every method here exists in at least one kit doc, and the disagreements (`validate` vs `healthcheck`, `launch(mode)` vs three explicit `open_*`) are resolved by keeping both: `validate()` for one-shot config check, `healthcheck()` for steady-state liveness, and explicit `open_*()` methods so dock state is type-checkable.

```python
class ToolAdapter(Protocol):
    # Identity (constants)
    key: str                    # e.g. "moonraker"
    display_name: str           # e.g. "Moonraker"
    category: str               # "slicer" | "printer" | "printer-ui" | "3d" | "3d-mcp"
    dangerous: bool             # writes G-code / runs Python / sends print commands

    # Lifecycle
    def version(self) -> Optional[str]: ...
    def detect(self) -> DetectResult: ...
    def capabilities(self) -> set[CapabilityFlag]: ...
    def validate(self) -> ValidateResult: ...        # one-shot config check
    def healthcheck(self) -> HealthResult: ...       # steady-state liveness
    def status(self) -> AdapterState: ...            # see §3

    # Dock / undock / external launch (only meaningful for UI-bearing adapters)
    def open_docked(self) -> LaunchResult: ...
    def open_undocked(self) -> LaunchResult: ...
    def open_external(self) -> LaunchResult: ...
    def detach_ui(self) -> None: ...                 # close panel without killing backend

    # Action plane
    def dry_run(self, action: Action) -> DryRunResult: ...   # returns dry_run_token
    def execute(self, action: Action, confirmation: Confirmation) -> ExecuteResult: ...
```

**Authority:** the kit specs remain the source of intent. This document is the implementation reconciliation. Any future change to method shapes lands as an ADR plus a kit spec update — never silently in code.

## 3. Lifecycle state machine

```
uninstalled → detected → configured → ready → connecting → connected → degraded → error
                                                    ↓             ↑           ↓
                                                  ready ←─────────┴───────────┘
```

States:
- `uninstalled` — `detect()` returned no binary / no service
- `detected` — found, but `validate()` not yet run or failed
- `configured` — `validate()` passed; required config present
- `ready` — capable of accepting `dry_run()` / `open_*()`
- `connecting` — async transition to `connected` (e.g. tunnel handshake, USB open)
- `connected` — `healthcheck()` returned OK
- `degraded` — `healthcheck()` returned warnings (e.g. high latency, partial features)
- `error` — fatal; requires user action to recover

`status()` MUST return one of these. UI badges and CI smoke gates key off this enum.

## 4. Dock / undock / fullscreen contract

Three modes (per `01_requirements/DOCK_UNDOCK_REQUIREMENTS.md` and `01_requirements/DOCK_UNDOCK_ACCEPTANCE.md`):

| Mode | Meaning | Implementation notes |
|---|---|---|
| `docked` | Tool's UI rendered inside a Hermes3D panel (typically iframe for web UIs, native viewport stub for Blender — but Blender stays external per kit) | iframe-allowed required; fall back to "open externally" link if `X-Frame-Options` / `frame-ancestors` blocks. |
| `undocked` | Tool's UI in a separate Hermes3D-managed window, still under Hermes3D process tree | Closing the undocked window MUST NOT kill the backend adapter — `detach_ui()` decouples. |
| `external` | Tool launched as its own OS process, fully outside Hermes3D | Hermes3D continues to talk to it via the adapter's transport (HTTP / USB / MCP / file watch). |

**Iframe-blocking fallback chain** (web UIs only — Fluidd, Mainsail, OctoPrint):
1. Try iframe embed.
2. On `X-Frame-Options: DENY` / `SAMEORIGIN` / `frame-ancestors` mismatch, surface "Open externally" CTA.
3. External launch uses the system browser, not an embedded webview.

A shared `WebPanelAdapter` mixin (Phase 1 deliverable) implements this fallback once for all three web-UI targets.

## 5. Capability flags

Fixed enum. `capabilities()` returns a subset of:

| Flag | Meaning |
|---|---|
| `cli` | Tool exposes a documented CLI with stable flags |
| `gui` | Tool has a native GUI |
| `headless_smoke` | Supports a non-interactive smoke run (e.g. Blender `--background --python`) |
| `usb` | Communicates over USB serial |
| `websocket` | Supports a WebSocket subscribe channel |
| `rest_api` | Has an HTTP REST API |
| `mcp` | Speaks Model Context Protocol |
| `dock_iframe` | Can be embedded in an iframe (X-Frame-Options compatible) |
| `streaming_logs` | Emits a structured log stream (vs. polling) |
| `dry_run_supported` | `dry_run()` returns a real preview, not a stub |
| `e_stop` | Has an emergency-stop or equivalent abort |
| `read_only` | Adapter is currently in read-only mode (write commands rejected) |

Phase 1's registry validator (`hermes3d_gui_contract_kit_v4.1/scripts/validate_registry.py` successor) will gate per-`type` capability requirements (e.g. `slicer` must declare `cli` and `external`-launch, `printer-ui` must declare `dock_iframe`).

## 6. Result envelope

Extends the kit envelope (`hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/ADAPTER_INTERFACE.md`) with structured error + dry-run binding:

```python
@dataclass(frozen=True)
class AdapterResult:
    ok: bool
    adapter: str            # adapter key
    mode: str               # "detect" | "validate" | "dry_run" | "execute" | "open_docked" | ...
    artifacts: list[ArtifactRef]   # paths under repo, or staging dir
    logs: list[LogEntry]    # structured (see below), not freeform strings

    # Proof metadata (kit-canonical)
    proof: ProofRef         # {timestamp_utc, branch, commit}

    # Extension fields (Phase 0 normalisation)
    error_code: Optional[str]            # SPDX-like enum, e.g. "ADAPTER.MOONRAKER.AUTH_REQUIRED"
    severity: Optional[Severity]         # info | warn | error | fatal
    recoverable: bool                    # can the user retry?
    user_action_required: Optional[str]  # human-readable next step

    # Dry-run binding (only on ExecuteResult)
    dry_run_token: Optional[str]         # required for execute() of any dangerous action
```

```python
@dataclass(frozen=True)
class LogEntry:
    ts_utc: str
    severity: Severity      # info | warn | error
    source: str             # adapter key + sub-channel, e.g. "moonraker.websocket"
    code: Optional[str]     # adapter-defined
    msg: str
    redactions: list[str]   # field paths that were redacted (e.g. ["headers.authorization"])
```

**Redaction policy:** API keys, tokens, IP addresses, printer serial numbers, and user PII MUST be redacted before being written into `logs[]`. Adapters are responsible for redaction at their own boundary; the proof bundle MUST NOT contain raw secrets (`hermes3d_gui_contract_kit_v4.1/05_truth_proof/SECURITY_AND_SAFETY_POLICY.md`).

## 7. Confirmation envelope

Required for any `execute()` of an adapter where `dangerous == True`:

```python
@dataclass(frozen=True)
class Confirmation:
    user: str                # session user id
    ts_utc: str              # ISO 8601 UTC
    printer_id: Optional[str]   # required if action targets a specific printer
    reason_text: str         # operator-supplied (≥ 1 char, ≤ 280 chars)
    dry_run_token: str       # MUST equal the dry_run_token from a prior dry_run() of THIS action's payload hash
    signed_token: str        # HMAC over (user, ts_utc, printer_id, action_payload_hash, policy_version) using HERMES3D_PROOF_KEY
    policy_version: str      # safety policy ref (e.g. "v4.1")
```

`execute()` MUST reject if any of: `dry_run_token` doesn't match the most recent dry-run for the same action payload hash; `signed_token` HMAC check fails; `policy_version` is older than the currently loaded policy; user is not authorized for this printer.

## 8. Per-adapter config schemas

JSON Schema files land under `03_implementation/adapter_registry/schemas/` in Phase 1 (filenames listed here so the path is reserved):

- `moonraker.schema.json` — `host`, `port`, `api_key` (optional), `wss_path`, `tls_verify`, `timeout_ms`
- `octoprint.schema.json` — `base_url`, `api_key` (required), `verify_tls`, `timeout_ms`
- `printrun.schema.json` — `serial_port`, `baud`, `auto_detect`, `gcode_denylist_ref`
- `prusa_slicer.schema.json` — `exe_path`, `profile_dir`, `cli_flags_supported`
- `orca_slicer.schema.json` — `exe_path`, `profile_dir`, `cli_flags_supported`
- `flsun_slicer.schema.json` — `archive_path` (user-provided zip), `extracted_dir`, `cli_supported` (bool)
- `cura.schema.json` — `exe_path`, `cura_engine_path`, `profile_dir`
- `blender.schema.json` — `exe_path`, `headless_capable`
- `blender_mcp.schema.json` — `provider_id`, `endpoint`, `version_pin`, `checksum`, `safety_executor`

Schemas are not authored in Phase 0. Phase 1 writes them.

## 9. Smoke-gate matrix

Mirrors `hermes3d_gui_contract_kit_v4.1/04_testing/integration/ADAPTER_SMOKE_GATES.md` with explicit per-phase columns. ✓ = required gate, — = not applicable.

| Adapter | P1: detect (read-only) | P3: read-only query | P6: gated write |
|---|---|---|---|
| flsun_slicer | ✓ binary path / extracted-zip layout | ✓ profile list, version capture | ✓ dry-run slice with sample STL |
| prusa_slicer | ✓ CLI present | ✓ `--info`, profile list | ✓ dry-run slice → staging |
| orca_slicer | ✓ CLI present | ✓ profile list | ✓ dry-run slice → staging |
| cura | ✓ binary present (CuraEngine for CLI) | ✓ profile list | — (provisioning only) |
| printrun | ✓ port enumeration (no open) | ✓ open + identify, read-only | ✓ G-code denylist scan + manual command (test mode + confirmation) |
| moonraker | ✓ `/server/info` + `/printer/info` | ✓ `/printer/objects/query` | ✓ allowlisted write (e.g. `pause`) |
| octoprint | ✓ version + status | ✓ `/api/printer` read | ✓ allowlisted write |
| mainsail | ✓ URL load + iframe probe | ✓ web-panel adapter health | — (writes via Moonraker) |
| fluidd | ✓ URL load + iframe probe | ✓ web-panel adapter health | — (writes via Moonraker) |
| blender | ✓ binary present | ✓ headless `--background --python` smoke; scene info; viewport screenshot | ✓ safe-executor Python; 3MF export |
| blender_mcp | ✓ provider detected | ✓ tools list, scene info, screenshot | ✓ harmless Python via safe executor |

## 10. Phase mapping

| Phase | Scope | Adapter outputs |
|---|---|---|
| **0** (this branch) | Foundation specs | This README, taxonomy, surface, schemas list, smoke-gate matrix. **Zero source code.** |
| **1** | Registry + adapter shell | Abstract `ToolAdapter` Python protocol; per-target skeletons with `detect()`/`version()`/`capabilities()` returning real values, all other methods raising `NotImplementedYet`; JSON schemas; detect-only smoke tests; CI Layer for adapter shell. |
| **3** | Read-only adapters | `validate()`, `healthcheck()`, `status()`, `dry_run()` for each adapter; `open_docked/undocked/external` for UI-bearing adapters; `WebPanelAdapter` shared mixin. |
| **6** | Safe write controls | `execute()` with confirmation envelope + dry-run-token binding; G-code denylist for Printrun; printer write allowlist for Moonraker/OctoPrint; Blender safe-executor. |

Phases 2, 4, 5 are UI-Final / release-gate / merge — not adapter-bearing.

## 11. Reuse-vs-rewrite — pre-Phase-0 modules

The repo contains client modules that pre-date the v4.1 kit and DO NOT yet conform to the `ToolAdapter` contract. Phase 1 must decide for each:

| Module | Decision | Rationale |
|---|---|---|
| `03_implementation/src/hermes3d/core/printers/moonraker_client.py` | **Wrap** in a `MoonrakerAdapter` | Inner client logic is good; needs adapter envelope + status mapping |
| `03_implementation/src/hermes3d/core/printers/printer_profiles.py` | **Keep as utility** | Cross-adapter helper; not adapter-shaped |
| `03_implementation/src/hermes3d/core/slicer/slicer_runner.py` | **Wrap** per slicer | Currently dispatches to multiple slicers in one module; split into per-adapter wrappers |
| `03_implementation/src/hermes3d/core/slicer/{gcode_analyzer,postproc_generator,profile_generator}.py` | **Keep as utility** | Pre-slice / post-slice helpers; not tool-specific I/O |
| `03_implementation/src/hermes3d/core/integrations/octoprint_client.py` | **Wrap** in an `OctoPrintAdapter` | Same as Moonraker |
| `03_implementation/src/hermes3d/core/integrations/farm_discovery.py` | **Keep as utility** | Multi-printer enumeration; cross-adapter |
| `03_implementation/src/hermes3d/core/integrations/obico_client.py` | **Defer** | Not on the locked-list; revisit in v5.4+ |
| `03_implementation/src/hermes3d/core/integrations/remote_control.py` | **Reassess** in Phase 6 | Currently bypasses the dangerous-action gate; will need refactor or removal |
| `03_implementation/src/hermes3d/core/orchestration/langgraph_adapter.py` | **Keep as-is** | Internal LangGraph runtime adapter; unrelated to external-tool adapters despite the name |

## 12. Cross-links

- Adapter contracts: [`ADAPTER_INTERFACE.md`](../../hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/ADAPTER_INTERFACE.md), [`ADAPTER_BOUNDARY_ARCHITECTURE.md`](../../hermes3d_gui_contract_kit_v4.1/02_architecture/ADAPTER_BOUNDARY_ARCHITECTURE.md)
- Per-category specs: [`SLICER_ADAPTERS.md`](../../hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/SLICER_ADAPTERS.md), [`PRINTER_ADAPTERS.md`](../../hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/PRINTER_ADAPTERS.md), [`BLENDER_MCP_PROVIDER_MANAGER.md`](../../hermes3d_gui_contract_kit_v4.1/03_implementation/adapters/BLENDER_MCP_PROVIDER_MANAGER.md)
- Dock/undock state: [`DOCK_UNDOCK_REQUIREMENTS.md`](../../hermes3d_gui_contract_kit_v4.1/01_requirements/DOCK_UNDOCK_REQUIREMENTS.md), [`DOCK_UNDOCK_ACCEPTANCE.md`](../../hermes3d_gui_contract_kit_v4.1/01_requirements/DOCK_UNDOCK_ACCEPTANCE.md)
- Smoke gates: [`ADAPTER_SMOKE_GATES.md`](../../hermes3d_gui_contract_kit_v4.1/04_testing/integration/ADAPTER_SMOKE_GATES.md)
- Tool integration: [`TOOL_INTEGRATION_REQUIREMENTS.md`](../../hermes3d_gui_contract_kit_v4.1/01_requirements/TOOL_INTEGRATION_REQUIREMENTS.md)
- Tab specs (consumers): [`TAB_SPECS.md`](../../hermes3d_gui_contract_kit_v4.1/01_requirements/TAB_SPECS.md) tabs 5/6/7/9/10
- Agent manifests: [`AGENT_MANIFESTS.md`](../../hermes3d_gui_contract_kit_v4.1/agents/AGENT_MANIFESTS.md) (Architect, AdapterBuilder, BlenderMCPAgent, SlicerAgent, PrinterControlAgent, SafetyAuditor)
- Tool registry audit: [`../../01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md`](../../01_requirements/EXTERNAL_TOOL_REGISTRY_AUDIT.md)
- Phase 0 baseline: [`../../00_overview/PHASE0_BASELINE_REPORT.md`](../../00_overview/PHASE0_BASELINE_REPORT.md)

## 13. Phase 1 deliverables

In order:
1. Abstract `ToolAdapter` Python protocol (typed, in `03_implementation/src/hermes3d/adapters/__init__.py`) implementing the merged surface from §2.
2. Registry loader that enumerates the 11 targets from `hermes3d_gui_contract_kit_v4.1/config/external_repos_registry.yaml` and builds an in-memory `AdapterRegistry`.
3. Per-target `*Adapter` skeletons with real `detect()` + `version()` + `capabilities()`; all other methods raise `NotImplementedYet` with a clear migration message pointing to the Phase 3 / Phase 6 deliverables.
4. JSON config schemas under `03_implementation/adapter_registry/schemas/*.schema.json` per §8.
5. Detect-only smoke tests under `04_testing/pytest/integration/adapters/` proving each adapter's `detect()` runs on Windows + Ubuntu CI without side effects.
6. CI workflow addition (a new "Layer Adapter" job) that runs the smoke tests on push to `develop` and `release/*`.
7. ADR-007 "Worker Authentication Scheme" (per security baseline — required before any tunnel/worker code lands).
8. ADR-008 "Adapter Lifecycle States + Confirmation Envelope" — codifies §3 and §7 as immutable.

## 14. Phase 0 read-only promise

This document publishes specifications. **It does not ship any `.py` source under `03_implementation/src/hermes3d/adapters/` and does not modify any kit doc.** Verification:

```bash
# Must return zero matches:
grep -rn "class .*Adapter" 03_implementation/src/hermes3d/ | grep -v "TypeAdapter\|langgraph_adapter"

# Must list zero files (directory may exist but is empty save this README + schemas/):
ls 03_implementation/src/hermes3d/adapters/ 2>/dev/null

# Kit untouched (must return zero modifications):
git diff develop...feat/phase-0-foundation-baseline -- hermes3d_gui_contract_kit_v4.1/
```

If any of those gates fail, Phase 0 is not actually clean — investigate and fix before proceeding to Phase 1.

---

**Phase 1 readiness for the adapter axis: GO.** Coordinator-side normalisation (this README) is in place; the kit's direction, target list, smoke-gate set, dock/undock modes, and dangerous-action policy are sound and locked.
