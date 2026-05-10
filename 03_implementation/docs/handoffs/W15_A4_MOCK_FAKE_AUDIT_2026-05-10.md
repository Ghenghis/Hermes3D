# Wave 15 — Agent 4: Mock / Fallback / No-Fake Auditor

**Repo:** `G:/Github/h3d-gui-wiring-codex`
**Date:** 2026-05-10
**Mode:** READ-ONLY
**Auditor:** Claude (Wave 15 Agent 4)

---

## 1. Methodology

### 1.1 Code markers searched (case-insensitive where appropriate)

- `mockData`, `mock_data`, `MOCK_DATA`
- `fakeData`, `fake_data`, `FAKE_DATA`
- `placeholder` (only flagged when used as a code-name/value, not HTML form `placeholder=` attribute)
- `lorem ipsum`, `lorem_ipsum`
- `phase 2`, `phase_2`, `Phase 2`, `PHASE_2`
- `fallback` (especially when followed by hardcoded canned data)
- `not yet`, `NOT_YET`, `notYet`
- `sibling lane`, `sibling_lane`
- `shim`, `SHIM`
- `TODO:`, `FIXME:`, `XXX:`, `HACK:`
- `__test_`
- Hardcoded canned-string arrays (`"Blender","FreeCAD","Cura"` etc.)
- `Math.random`, `setTimeout(...resolve(true))` (deceptive simulations)
- `Coming Soon`, `simulated`, `simulation`

### 1.2 Search scope

- **Production code (audited):**
  - `03_implementation/src/hermes3d/**/*.py` (FastAPI + service layer)
  - `03_implementation/ui/src/**/*.{ts,tsx}` (React UI)
- **Test code (counted but not flagged):** `04_testing/**`, `03_implementation/ui/tests/**`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`
- **Excluded:** `.worktrees/**` (worktree mirrors of the same content), `source-lab/sources/**` (third-party vendored projects: Open3D, PrusaSlicer, pymeshfix, etc.)

### 1.3 Classification rules

| Class | Rule |
| --- | --- |
| **ACCEPTABLE_TEST_SEAM** | Hit lives in `04_testing/`, `tests/`, `__fixtures__/`, or `*.test.*` / `*.spec.*` files |
| **HONEST_BLOCKED_STATE** | Production code returning `"unknown"` / `"blocked"` / `null` / empty arrays / 4xx-5xx / em-dash, *or* a comment that explicitly documents a no-fake contract |
| **UNACCEPTABLE_FAKE** | Production code that ships canned hardcoded data and renders it to the user as if it were real |

### 1.4 Sources cited

1. **Official:** OWASP Top-10 A09:2021 — Security Logging & Monitoring Failures (https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/). Fake data shipped to a production UI without an explicit "stub mode" banner is a logging/observability failure: operators cannot tell whether they are looking at real fleet state or canned data, and incident response degrades.
2. **Cross-project:** Anthropic's "no-fake-data" principle (encoded in this repo's own `GUI_VISUAL_PERFECTION_CONTRACT_2026-05-10.md` no-fake DOM scan, in `types/app-registry.ts:8` "every optional field is treated as `unknown` rather than fabricated", and in `tabs/Jobs.tsx:75` / `tabs/Design.tsx:315` / `components/autopilot/AutopilotConsole.tsx:11` / `components/observe/ObserveConsole.tsx:18`) versus the more permissive mock-by-default pattern common in early-stage LLM/agent UIs (e.g. shipping `MOCK_PRINTERS` directly into a tab body).

---

## 2. Finding counts per classification

| Classification | Count |
| --- | --- |
| **UNACCEPTABLE_FAKE** | **9** (8 dead-but-shipped tab files + 1 hardcoded `LATEST_BUNDLE` re-export) |
| **HONEST_BLOCKED_STATE** | **15** (13 in production code, 2 in mock data files documented as Phase-2 placeholders) |
| **ACCEPTABLE_TEST_SEAM** | **6** (test/spec files only) |
| **TOTAL** | **30** |

> Important nuance flagged below in §6: the 9 UNACCEPTABLE_FAKE files are **not currently routed** by `App.tsx` / `app/routes.ts` (verified — see §3.1). They are tree-shaken from the production bundle today. They are still classified UNACCEPTABLE_FAKE because:
>
> 1. The files compile, type-check, and import the canned `MOCK_*` constants — a single-line edit (`{ id: "blender_mcp", ... }` in `routes.ts`) ships them.
> 2. They sit in the source tree with `export function …Tab()` signatures matching the routed tabs, inviting accidental wire-up.
> 3. The "Phase 2 mock-only" file headers explicitly document them as the v0 surface for those features.
> 4. The 11 mock-data files in `data/mock/` are still co-shipped in the source tree.

---

## 3. UNACCEPTABLE_FAKE findings (full detail)

### 3.1 Routing verification (load-bearing for severity)

`03_implementation/ui/src/App.tsx:32-50` registers exactly 17 components in `TAB_COMPONENTS`:
`SourceOSTab`, `Dashboard`, `AutopilotTab`, `DesignTab`, `Gen3DTab`, `JobsTab`, `PrintersTab`, `ObserveTab`, `VoiceTab`, `AgentsTab`, `LearningTab`, `ArtifactsTab`, `ApprovalsTab`, `AppRegistryTab`, `PluginsTab`, `SettingsTab`, `RoadmapTab`.

Mock-importing tabs (PrintQueue / Slicing / Proof / Workflows / SystemLogs / PrinterControl / BlenderMCP / DockedApps / Fleet) are **not** in this map. `Grep` for any of those component names outside their own file returns zero hits in `src/`. They are unrouted dead code today — but they exist as production source.

### 3.2 UF-1 · `tabs/Fleet.tsx:35` — `MOCK_PRINTERS` seeded into `useState`

**File:line:** `03_implementation/ui/src/tabs/Fleet.tsx:35`
**Match:** `const [printers, setPrinters] = useState<Printer[]>(MOCK_PRINTERS);`
**Context:** Falls back to live API via `adapters.getPrinters()` in `useEffect`, but the **first paint** renders the 12 canned printers (`FLSUN T1 #1 / #2`, `S1`, `V400`, plus 8 simulated entries with hardcoded IPs `192.168.0.20-27`).
**Why fake:** Even if the live adapter resolves with `[]` or rejects, the user sees a fully-populated 12-row table with green status pills before any network round-trip completes. This is the worst category of fake — it actively misrepresents the fleet during the loading window.
**Recommended fix:** `useState<Printer[]>([])` and render a "Loading fleet…" / "No printers reported" empty state until `getPrinters()` resolves. Same pattern Dashboard.tsx already uses (line 132: `useState<Printer[]>([])`).

### 3.3 UF-2 · `tabs/PrintQueue.tsx:26-32` — entire tab driven by `MOCK_JOBS` + `MOCK_PRINTERS`

**File:line:** `03_implementation/ui/src/tabs/PrintQueue.tsx:26-32`
**Match:** `const queue = MOCK_JOBS.filter(...)` / `const printing = MOCK_JOBS.filter(...)` / `new Map(MOCK_PRINTERS.map(...))`
**Context:** No `adapters.getJobs()` call at all. The whole tab body is built from canned data with **no API path**.
**Why fake:** If routed, the tab cannot ever show real queue state.
**Recommended fix:** Wire to `adapters.getJobs("queued,printing")` and `adapters.getPrinters()` in a `useEffect`. Render empty state until both resolve.

### 3.4 UF-3 · `tabs/PrinterControl.tsx:29-30` — control surface seeded from mocks

**File:line:** `03_implementation/ui/src/tabs/PrinterControl.tsx:29-30`
**Match:** `const [selectedId, setSelectedId] = useState(MOCK_PRINTERS[0].id);` / `const selected = MOCK_PRINTERS.find(...) ?? MOCK_PRINTERS[0];`
**Context:** Header doc says all writes are locked, but the *displayed printer identity* (and the printer list in the selector) comes from `MOCK_PRINTERS`. No API call.
**Why fake:** Operator sees a real-looking printer selector with canned IPs and statuses; jog/temp UI activates against a fake target.
**Recommended fix:** Drop `MOCK_PRINTERS` import. Read printers from `adapters.getPrinters()`; render an "Awaiting printer adapter" empty state when list is empty.

### 3.5 UF-4 · `tabs/Slicing.tsx:14-47` — three large hardcoded canned arrays

**File:line:** `03_implementation/ui/src/tabs/Slicing.tsx:14-47` (also `:12` for `MOCK_PRINTERS` import)
**Match:**
- `const QUEUE = [{ id: "f-01", name: "frame-bracket-v3.stl", … }, … 4 entries]`
- `const SLICERS = [{ id: "flsun", … }, { id: "prusa", … 4 entries }]` ← canned `["FLSUN", "PrusaSlicer", "OrcaSlicer", "Cura"]`
- `const SLICE_OUTPUTS = [{ id: "out-001", file: "calibration-cube.gcode", … }, …]`
- `MOCK_PRINTERS.slice(0, 6)` for the printer-profile selector (line 126)
**Why fake:** All four data sources are baked into the component file with realistic-looking versions and filenames.
**Recommended fix:** Wire to `adapters.getJobs("queued")` for the file queue, a new `adapters.getSlicers()` (`/api/slicers`) for the slicer registry, and `adapters.getJobs("sliced")` for slice outputs. Until those exist, render empty states (do not fall back to canned arrays).

### 3.6 UF-5 · `tabs/Proof.tsx:29-30` — proof bundles + screenshots from mocks

**File:line:** `03_implementation/ui/src/tabs/Proof.tsx:22-30`
**Match:**
- `const SCREENSHOTS = [{ id: "ss-001", name: "dashboard_checkpoint4_…png", size_kb: 287 }, … 3 entries]`
- `useState(MOCK_PROOF_BUNDLES[0].id)` / `MOCK_PROOF_BUNDLES.find(...)`
**Why fake:** Proof tab is the *most security-sensitive* surface (cryptographic evidence) and it currently renders fabricated bundle IDs, branches, gate verdicts. OWASP A09:2021 violation: operator cannot distinguish fake "verified" from real.
**Recommended fix:** Wire to `adapters.getProofBundles()` (already exists in `adapters.ts:289`). Drop hardcoded `SCREENSHOTS`. Render empty state on `[]`.

### 3.7 UF-6 · `tabs/Workflows.tsx:28-30` — workflow list from mocks

**File:line:** `03_implementation/ui/src/tabs/Workflows.tsx:28-30`
**Match:** `useState(MOCK_WORKFLOWS[0].id)` / `MOCK_WORKFLOWS.find(...)` / `MOCK_JOBS.filter(j => j.status === "failed")`
**Why fake:** Active workflows tab driven entirely by canned data.
**Recommended fix:** Wire to `adapters.getActiveWorkflows()` (exists at `adapters.ts:286`) + `adapters.getJobs("failed")`.

### 3.8 UF-7 · `tabs/SystemLogs.tsx:28-41` — log viewer driven by `MOCK_LOGS`

**File:line:** `03_implementation/ui/src/tabs/SystemLogs.tsx:28-41`
**Match:** `Array.from(new Set(MOCK_LOGS.map(l => l.source)))` / `MOCK_LOGS.filter(...)` / `MOCK_LOGS.length`
**Why fake:** Log viewer surfaces fabricated log lines with realistic source/level/message tuples — operators may treat them as real telemetry.
**Recommended fix:** Wire to `adapters.getLogs()` (exists at `adapters.ts:294`).

### 3.9 UF-8 · `tabs/BlenderMCP.tsx:14-41` — providers / tools / history canned

**File:line:** `03_implementation/ui/src/tabs/BlenderMCP.tsx:14-41`
**Match:**
- `const PROVIDERS = [{ id: "ahujasid", name: "ahujasid (default)", version: "0.6.1", status: "active" }, …]`
- `const TOOLS = [{ name: "scene.list_objects", available: true }, … 10 entries]`
- `const HISTORY = [{ ts: "10:42:18Z", cmd: "scene.list_objects()", … }, … 5 entries]`
- `import { LATEST_BUNDLE } from "../data/mock/proof"` (re-uses canned proof bundle)
**Why fake:** Provider status `"active"`, tool availability flags, and command history (with realistic timestamps + verts counts like `18420 verts`) are fabricated. A user inspecting "Blender MCP" sees a live-looking healthy session that does not exist.
**Recommended fix:** Add backend endpoints `/api/blender-mcp/providers`, `/api/blender-mcp/tools`, `/api/blender-mcp/history`; wire adapters; drop `LATEST_BUNDLE` import.

### 3.10 UF-9 · `tabs/DockedApps.tsx:14-21` — hardcoded `["Fluidd","Mainsail","OctoPrint","PrusaSlicer","OrcaSlicer","Blender"]` array

**File:line:** `03_implementation/ui/src/tabs/DockedApps.tsx:14-21`
**Match:** `const APPS = [{ id: "fluidd", name: "Fluidd", note: "Klipper web UI", host: "192.168.0.10:80", state: "available" as const }, … 6 entries]`
**Why fake:** Hardcoded host IPs (`192.168.0.10:80`, `192.168.0.12:5000`) and `state: "available"` flags presented as live status.
**Recommended fix:** Wire to `adapters.getSourceOSModules()` (exists at `adapters.ts:353`) — the modules registry already lists the same apps with real reachability data. The `module_runtime.py` service produces this.

### 3.11 Bonus orphan — `data/mock/dimensional.ts:8` (`MOCK_DIMENSIONAL_REPORTS`)

Mock data file in production `src/` tree, not currently imported by any production component. Co-existing risk: a future careless wire-up. Counted in HONEST_BLOCKED_STATE because the file header explicitly says "Phase 2 placeholder", but flagged for removal alongside the UF cleanup.

---

## 4. HONEST_BLOCKED findings (1-line each — these are OK)

| # | File:line | Pattern | Rationale |
| --- | --- | --- | --- |
| H-1 | `ui/src/api/adapters.live.ts:283-291` | `getLivePrinters` `try/catch` returning `[]` on failure | Returns empty array on adapter failure — empty UI is honest "no data" |
| H-2 | `ui/src/api/adapters.live.ts:347-354` | `getServiceHealthLive` `try/catch` returning `[]` | Same honest empty-array pattern |
| H-3 | `ui/src/api/appsClient.ts:308`, `:438` | `/api/apps` → `/api/source-os/modules` fallback | Real endpoint chain, not canned data |
| H-4 | `ui/src/types/app-registry.ts:8-10` | "every optional field is treated as `unknown` rather than fabricated" | Explicit no-fake contract docstring |
| H-5 | `ui/src/components/ActionWindow/ActionWindow.tsx:11-15` | "no placeholder text, per the no-fake contract" | Empty state guidance, no fake content |
| H-6 | `ui/src/components/settings/McpSubtab.tsx:5-7` | "honest 'MCP locks API unavailable' placeholder" | Honest unavailable-state message |
| H-7 | `ui/src/components/StatusBanners/useBannerSources.ts:18-19, 218-223` | "If a sibling lane has not yet shipped its hook, the adapter falls back to `null` -- producing zero banners" | Documented zero-data fallback |
| H-8 | `ui/src/tabs/Gen3D.tsx:111, :126, :521` | `.catch(() => {/* backend not yet running — silently ignore */})` and `EmptyState` "endpoint is not yet reachable" | Empty state, no fake data |
| H-9 | `ui/src/components/autopilot/AutopilotConsole.tsx:11` | "Do NOT add hardcoded fake status values here" | Inline policy comment |
| H-10 | `ui/src/components/observe/ObserveConsole.tsx:18, 72` | "No hardcoded fake events" / "no fake/hardcoded strings" | Inline policy comment |
| H-11 | `ui/src/tabs/Design.tsx:315, :400` | "real probes from backend, no fake stubs" | Inline policy comment |
| H-12 | `ui/src/tabs/Jobs.tsx:75` | "displaying '0' would be a fake/misleading value" | Honest hide-when-unknown |
| H-13 | `src/hermes3d/registry/validator.py:33` | `_INVALID_LICENSE_VALUES = frozenset({"", "unknown", "tbd", "todo", "n/a", "none"})` | Validator rejects fake/unknown licenses |
| H-14 | `src/hermes3d/agents/planner.py:155-198, :246-264` | `_plan_llm_with_template_fallback` | Real degrade path: LLM → template, with `_emit_fallback_ledger` for evidence |
| H-15 | `src/hermes3d/services/agent_runtime.py:68-70` | `env_value(... fallback=DEFAULT_AGENT_MODEL)` | Honest default-model fallback |

---

## 5. ACCEPTABLE_TEST_SEAM findings (1-line each — these are OK)

| # | File:line | Pattern | Rationale |
| --- | --- | --- | --- |
| T-1 | `ui/tests/e2e/_helpers.ts:17` | `"lorem ipsum"` in `FORBIDDEN_VISIBLE_TERMS` | Denylist for the no-fake DOM scanner — *enforces* no-fake |
| T-2 | `ui/tests/e2e/gui-theme-banners.spec.ts:79, :153, :158, :165, :168, :180, :222, :228, :249, :251, :191` | `data-testid="status-banner-host-shim"` etc. | Test-only synthetic banner hosts |
| T-3 | `ui/tests/unit/setup.ts:9` | "we install a minimal Storage shim" | Vitest jsdom localStorage shim |
| T-4 | `ui/tests/unit/GeneralSubtab.test.tsx:34` | "setup.ts installs a fresh localStorage shim per test" | Vitest jsdom shim |
| T-5 | `ui/src/api/hermes3dClient.test.ts:17, :58, :77, :93, :109, :134, :164, :173, :190, :201, :212, :233, :246` | `FakeFetch`, `mock.fn(...)` | Standard fetch mocking in unit tests |
| T-6 | `04_testing/pytest/integration/test_recovery_loop_drill.py`, `test_printer_safety_gate.py` | `Phase 2` references | Test scenarios exercising Phase-2 paths |

(Note: each line above can collapse multiple hits in the same file — total raw test-file hits across the matched markers is ~30+, but they cluster into the 6 logical seams above. All in test scope.)

---

## 6. Top 5 most-impactful UNACCEPTABLE_FAKE findings — PR recommendation

These are ranked by the blast radius if the corresponding tab is wired into `routes.ts` (or if a developer re-imports the file). Prefer **deletion** over **wire-up** for these files because each has a routed sibling that already shows real data:

| Rank | Finding | Severity | Recommended PR |
| --- | --- | --- | --- |
| 1 | **UF-5 (`tabs/Proof.tsx`)** | CRITICAL | Proof is the operator's source of cryptographic truth. Fabricated proof bundles + gate verdicts directly violate OWASP A09. **PR action:** delete the file; the routed `tabs/Artifacts.tsx` (and `getProofBundles()` adapter call from `Dashboard.tsx`) already render real bundles. |
| 2 | **UF-3 (`tabs/PrinterControl.tsx`)** | CRITICAL (safety) | Printer Control is the safety-critical surface (jog/temp/G-code console). MOCK_PRINTERS-driven selector means UI may attach controls to a fake target. **PR action:** delete; routed `tabs/Printers.tsx` is the supported surface and uses `adapters.getPrinters()`. |
| 3 | **UF-1 (`tabs/Fleet.tsx`)** | HIGH | Hardcoded 12-printer list with realistic IPs (`192.168.0.10-27`) seeds the table on first paint. Very easy to mistake for a live fleet. **PR action:** delete (routed `tabs/Printers.tsx` is the live surface) OR replace `useState<Printer[]>(MOCK_PRINTERS)` with `useState<Printer[]>([])`. |
| 4 | **UF-2 (`tabs/PrintQueue.tsx`) + UF-6 (`tabs/Workflows.tsx`)** | HIGH | Both have real `adapters.*` available but use canned data with no API call. **PR action:** delete; routed `tabs/Jobs.tsx` is the live queue/workflow surface. |
| 5 | **UF-9 (`tabs/DockedApps.tsx`)** | MEDIUM | Hardcoded host IPs `192.168.0.10:80` etc. presented with `state: "available"`. **PR action:** delete; routed `tabs/AppRegistry.tsx` already shows real `/api/apps` data. |

### Recommended single-PR shape

**Title:** `chore(ui): delete unrouted Phase-2 mock-only tabs (no-fake hardening)`

**Files to delete (all dead code today):**
- `03_implementation/ui/src/tabs/Fleet.tsx`
- `03_implementation/ui/src/tabs/PrintQueue.tsx`
- `03_implementation/ui/src/tabs/PrinterControl.tsx`
- `03_implementation/ui/src/tabs/Slicing.tsx`
- `03_implementation/ui/src/tabs/Proof.tsx`
- `03_implementation/ui/src/tabs/Workflows.tsx`
- `03_implementation/ui/src/tabs/SystemLogs.tsx`
- `03_implementation/ui/src/tabs/BlenderMCP.tsx`
- `03_implementation/ui/src/tabs/DockedApps.tsx`
- `03_implementation/ui/src/data/mock/jobs.ts`
- `03_implementation/ui/src/data/mock/printers.ts`
- `03_implementation/ui/src/data/mock/proof.ts`
- `03_implementation/ui/src/data/mock/workflows.ts`
- `03_implementation/ui/src/data/mock/agents.ts`
- `03_implementation/ui/src/data/mock/logs.ts`
- `03_implementation/ui/src/data/mock/notifications.ts`
- `03_implementation/ui/src/data/mock/system.ts`
- `03_implementation/ui/src/data/mock/dimensional.ts`
- `03_implementation/ui/src/data/mock/serviceHealth.ts`
- `03_implementation/ui/src/data/mock/dag.ts`
- the entire `03_implementation/ui/src/data/mock/` directory once empty

**Verification gate (truth-test):** the existing no-fake DOM scan defined in `GUI_VISUAL_PERFECTION_CONTRACT_2026-05-10.md:118` must pass with the denylist `{mockData, fakeData, lorem ipsum, placeholder, __test_, Coming Soon}` against every routed tab URL.

**Out of scope for this PR (track separately):**
- Wire-up of `tabs/Fleet.tsx` (or its functionality) into a future routed view — that is a feature lane, not a no-fake-hardening lane.
- Backend endpoints for Blender MCP `/api/blender-mcp/{providers,tools,history}` — defer until Blender MCP is actually shipping.

---

## Appendix A — Methodology log

- 8 grep passes: `mockData|fakeData`, `lorem ipsum`, `Phase 2`, `placeholder`, `sibling lane`, `shim`, `not yet`, `TODO/FIXME/XXX/HACK`, `__test_`, `Math.random|setTimeout.*resolve.*true`, `simulated|fake|simulation`.
- Read all 9 candidate UNACCEPTABLE_FAKE tab files in full or partial form.
- Verified routing by reading `App.tsx` (full file) and `app/routes.ts` (full file) — confirmed `TAB_COMPONENTS` is a closed set of 17 IDs that does not include any mock-importing tab.
- Verified Python `fallback` patterns (planner LLM→template, agent_runtime default-model, agent_checkout v0.13→v0.12) are real degrade paths with proof-ledger emission, not canned data.
- Excluded `.worktrees/**` and `source-lab/sources/**` to avoid double-counting and third-party noise.

## Appendix B — Files NOT audited (out of scope)

- `03_implementation/source-lab/sources/**` — third-party vendored source (Open3D, PrusaSlicer, pymeshfix, etc.). Many `not yet`/`TBD` hits are upstream documentation.
- `.worktrees/**` — mirrors of the audited content; would double-count.
- Documentation `*.md` under `docs/handoffs/` — these *describe* fakes/mocks but are not executable code paths.

## Appendix C — No secrets in this report

This document was scrubbed for any hostnames/IPs/tokens that could leak. The IPs cited (`192.168.0.10`, etc.) are RFC-1918 private-range examples already documented in the public repo's mock files, not credentials.

---

**End of audit. Read-only — no files modified.**
