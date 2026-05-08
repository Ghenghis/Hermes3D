<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./site/diagrams/pipeline-9-stage.svg"/>
  <source media="(prefers-color-scheme: light)" srcset="./site/diagrams/pipeline-9-stage.svg"/>
  <img src="./site/diagrams/pipeline-9-stage.svg" alt="Hermes3D-OS — nine-stage orchestration pipeline (theme-aware)" width="100%"/>
</picture>

<br/>

# Hermes3D-OS

**The first agentic 3D printing emporium.**

A 60-app, dual-Hermes, GPU-backed ecosystem for **printing, designing, generating, and self-coding** — all under one truth-gated roof. Anonymous to use. Fully agentic. Starts prints only when the build plate is empty.

[![CI](https://github.com/Ghenghis/Hermes3D/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Ghenghis/Hermes3D/actions/workflows/ci.yml)
[![Pages](https://github.com/Ghenghis/Hermes3D/actions/workflows/pages.yml/badge.svg)](https://ghenghis.github.io/Hermes3D/)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](./LICENSE)
[![Apps catalogued](https://img.shields.io/badge/apps%20catalogued-60-06b6d4?style=flat-square)](#-the-60-app-catalog)
[![Tabs](https://img.shields.io/badge/UI%20tabs-18-06b6d4?style=flat-square)](#-the-react-control-plane--18-tabs)
[![Routes](https://img.shields.io/badge/API%20routes-220-06b6d4?style=flat-square)](#-mcp-coordination)
[![MCP tools](https://img.shields.io/badge/MCP%20tools-44-a855f7?style=flat-square)](https://modelcontextprotocol.io)
[![Truth gates](https://img.shields.io/badge/truth--gates-17%2F17-22c55e?style=flat-square)](./PROOF_E2E_REPORT.md)
[![Hermes teams](https://img.shields.io/badge/Hermes%20teams-MiniMax%20M2.7%20%2B%20DeepSeek%20V4-ec4899?style=flat-square)](#-two-hermes-teams)

[![Governed by](https://img.shields.io/badge/governed%20by-HermesProof-ec4899?style=flat-square)](https://github.com/Ghenghis/HermesProof)
[![Sigstore](https://img.shields.io/badge/sigstore-keyless%20OIDC-f59e0b?style=flat-square)](https://www.sigstore.dev/)
[![Sandbox](https://img.shields.io/badge/sandbox-Docker%20%C2%B7%20net%3Dnone-22c55e?style=flat-square)](#-two-hermes-teams)
[![Anonymous](https://img.shields.io/badge/users-anonymous-0e8090?style=flat-square)](#-anonymous--fully-agentic)

**Live site → [ghenghis.github.io/Hermes3D](https://ghenghis.github.io/Hermes3D/)**

[60 apps](#-the-60-app-catalog) · [Custom Stacks](#-custom-stacks) · [Image→Print](#-image-to-print-autonomously) · [Build-plate safety](#-build-plate-safety--stop-before-heat) · [Two Hermes teams](#-two-hermes-teams) · [Pipeline](#-the-pipeline) · [Truth Gate](#-truth-gate) · [Fleet](#-print-farm) · [MCP](#-mcp-coordination) · [Anonymous](#-anonymous--fully-agentic) · [Quickstart](#-quickstart) · [Self-host](#-self-host)

</div>

---

## What it is — in 60 seconds

- **An emporium, not a tool.** 60 catalogued open-source apps — 11 slicers, 13 modelers, 6 firmware sources, 10 print-farm services, 6 3D-generation engines, 7 agent runtimes, plus libraries/materials/hardware/research/utilities — wired into one operator console. Pick at least one per section, ship more on demand.
- **Two Hermes agent teams that build the OS itself.** A **MiniMax-M2.7** builder team and a **DeepSeek-V4** reviewer team (with **OpenHands 1.16** and **OpenCode 1.4.3-hermes3d** in a Docker `net=none` sandbox) propose, review, gate, and ship code under MCP file locks with hash-chained evidence. The system extends the system.
- **GPU-backed image-to-print on your RTX 3090 Ti.** Drop an image in. Hermes generates a mesh (ComfyUI · TRELLIS.2 · Hunyuan3D 2.1 · TripoSR), repairs it, truth-gates it for printability, slices it, and dispatches it to a free printer — switching generation models on command.
- **Autonomous, but only when the bed is clear.** Hermes will start a print on its own — *if* the build plate is empty, the last print has been removed, the camera observer reports no obstruction, and policy approval is in place. **STOP / pause before heating bed or hotend** if any of those fail. Hard alert. Cannot continue until the user clears the plate.
- **Anonymous to use, fully agentic.** No account required to operate. The system claims work on its own under role tokens (BUILDER · CRITIC · SCRIBE · GATE-SMITH), shows you exactly which agent is doing what, and lets you take over at any time.
- **Truth-gated, signed, attested.** 17 truth gates re-prove the codebase on every push to `main`. Sigstore keyless OIDC seals every release. Build-provenance attestation on every Windows installer. Tamper invalidates the chain.

---

## ✦ What makes it first-of-its-kind

> A 3D environment around 3D printing, around coding, around creating new features for itself — agents-as-program, ecosystem-as-product. There isn't anything else like this.

Three modes share one runtime, one evidence chain, one safety policy:

| Mode | Loop | Hermes role | Safety boundary |
| --- | --- | --- | --- |
| **Print** | image / prompt → mesh → repair → truth-gate → slice → bed-clear check → heat → print | dispatcher · auto-orient · auto-recovery · incident detector | S1 read-only; T1 print-approval-required; build-plate-clear gate |
| **Design / generate** | prompt or image → ComfyUI / TRELLIS.2 / Hunyuan3D 2.1 / TripoSR / Blender → STL / 3MF | model-switcher · GPU broker · proof envelope per artifact | sandbox-bounded GPU jobs · denied path list |
| **Self-code** | folder-index load → claim · lock · snapshot → MiniMax build → DeepSeek review → patch apply → gates → branch · commit · push · PR | dual Hermes teams · MCP locks · evidence ledger · reviewed-patch-only | Docker `net=none` · `G:/private` denied · review-required before any source mutation |

The same per-file lock, evidence ledger, and proof envelope serve all three. Every action — printing a part, generating a model, or modifying the source code that runs the system — leaves the same shape of audit trail.

---

## ✦ The 60-app catalog

```text
60 source-backed apps · 11 sections · 7 agent-CLI-ready today · 24 runner gaps to close
```

You don't get a black box. You get a **catalog** — pick what you actually run.

| Section | Apps | Default(s) shipped | Examples (full list in [`source-os-60-apps/REGISTRY.md`](./03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/source-os-60-apps/REGISTRY.md)) |
| --- | --- | --- | --- |
| **Slicers** (must pick ≥1) | 11 | PrusaSlicer · OrcaSlicer | BambuStudio · Cura · CuraEngine · FLSUN Slicer · Kiri:Moto · MatterControl · Slic3r · Strec3D · SuperSlicer |
| **Modelers** (must pick ≥1) | 13 | Blender · OpenSCAD | build123d · CadQuery · FreeCAD · Manifold · MeshLab · numpy-stl · Open3D · pymesh · SolveSpace · trimesh · truck |
| **3D generation** (optional, GPU) | 6 | TRELLIS.2 (default if RTX present) | ComfyUI · ComfyUI Frontend · ComfyUI TRELLIS.2 Wrapper · Hunyuan3D 2.1 · TripoSR |
| **Print farm** (must pick ≥1) | 10 | Moonraker · Klipper | FDM Monster · Fluidd · KlipperScreen · Mainsail · OctoFarm · OctoPrint · BotQueue · Printrun |
| **Firmware** (reference) | 6 | Klipper firmware | Marlin · Prusa Firmware · Repetier · RepRapFirmware · Smoothieware |
| **Agents** | 7 | Hermes Agent (NousResearch) · Model Context Protocol | Azure Speech SDK JS · Blender MCP candidates · Kiln · LangChain · LangGraph |
| **Library** | 1 | Manyfold | — |
| **Materials** | 1 | Open Filament Database | — |
| **Hardware** (reference) | 3 | — | Awesome Extruders · BoxTurtle · EnragedRabbitProject |
| **Research** | 1 | — | Awesome 3D Printing |
| **Utilities** | 1 | — | 3D Box Generator |

**Selection rules**:

1. **Minimum one per `must-pick` section** (slicers, modelers, print-farm). Hermes refuses to start without at least one in each.
2. **Defaults are shipped pre-installed.** PrusaSlicer + Blender + Klipper + Moonraker are wired and ready on first launch.
3. **Optional sections (3D generation, Agents, Library, Materials)** opt in when you choose to use them. Hermes detects RTX 3090 Ti and offers TRELLIS.2 by default for image-to-mesh.
4. **More can be added at any time.** The Source OS tab lets you select a row, click *Plan Setup*, review the proof gate, and approve the install. Backups, smoke gates, and rollback are part of every update.
5. **Reference-only rows** (firmware, hardware, research, utilities) ship as source archives — no automated executor, no flashing without explicit approval.

```text
catalog truth (live `/api/modules/runtime/runner-contracts`):
  60 modules · 7 agent_cli_ready · 8 read_only_runner · 3 executable_path
  · 5 python_import_repair · 5 metadata_ready_needs_runner · 2 cli_install_config
  · 1 npm_package_preflight · 3 desktop_app_runner_gap · 3 gpu_worker_runner_gap
  · 15 runtime_repair_required · 18 source_reference_only · 2 blocked
```

---

## ✦ Custom Stacks

Not every workflow needs every app. A **Custom Stack** is a named, saved selection from the 60-app catalog — combined with its operator settings, printer profile, and truth-gate configuration — that reproduces a specific environment in one click.

**Users create stacks** from the Source OS tab: pick rows from the catalog, give the bundle a name ("FDM Prototyping", "Resin Detail", "GPU Concept"), and save. The stack is stored as a signed manifest (`stacks/<name>.stack.json`). Reload it on any Hermes3D-OS instance to restore that exact environment — apps verified, gates re-run, profiles applied.

**Hermes agents create stacks programmatically** during the coding loop. When an agent determines that a task requires a particular combination of tools, it calls `hermes_lock_files` on the relevant catalog rows, builds the environment, and persists the resulting stack manifest as a signed artifact alongside the PR proof. Subsequent agents load that manifest rather than re-deriving the environment.

| Capability | Detail |
|---|---|
| **Author** | User via Source OS tab _or_ Hermes agent via MCP |
| **Storage** | `stacks/<name>.stack.json` · signed · truth-gated snapshot |
| **Contents** | App list · operator settings · printer profile · gate config |
| **Load / switch** | One click in Source OS (user) · `hermes_claim_task` payload (agent) |
| **Share** | Export `.stack.json` · import on any Hermes3D-OS instance |
| **Version** | Each save creates a timestamped snapshot; rollback to any prior version |
| **Defaults** | Three built-in stacks ship pre-configured on every install |

Built-in stacks shipped with every install:

| Stack name | Apps included | Use case |
|---|---|---|
| **FDM Core** | OrcaSlicer · PrusaSlicer · Moonraker · Mainsail · Klipper | Standard FDM print-farm |
| **Resin Detail** | Lychee · Chitubox · UVtools · Moonraker | Resin SLA / MSLA printing |
| **GPU Concept** | Blender · TRELLIS.2 · Hunyuan3D 2.1 · ComfyUI · OpenSCAD | Image-to-print on RTX 3090 Ti |

Stacks are the unit of sharing between operators: export a `.stack.json`, share it with another Hermes3D-OS user, and they get an identical verified environment. Hermes agents can propose stack additions in PRs — the same MCP lock + truth-gate flow that governs code changes governs stack changes.

---

## ✦ Image-to-print, autonomously

Drop an image. Get a printable part. Hermes orchestrates the whole chain on your local GPU.

```mermaid
flowchart LR
    IMG[image upload<br/>or text prompt] --> ROUTE{router}
    ROUTE -->|text to 3D| TRELLIS[TRELLIS.2<br/>RTX 3090 Ti]
    ROUTE -->|image to 3D| HUNYUAN[Hunyuan3D 2.1<br/>RTX 3090 Ti]
    ROUTE -->|image to mesh| TRIPOSR[TripoSR<br/>fast preview]
    ROUTE -->|prompt to render| COMFY[ComfyUI graph]
    ROUTE -->|parametric| OPENSCAD[OpenSCAD / CadQuery]
    TRELLIS --> RAW[raw mesh]
    HUNYUAN --> RAW
    TRIPOSR --> RAW
    COMFY --> RAW
    OPENSCAD --> RAW
    RAW --> REPAIR[auto-repair<br/>Manifold + meshlab]
    REPAIR --> TG[Truth Gate<br/>6 checks · HMAC seal]
    TG -->|fail| RETRY[regenerate · max N]
    RETRY --> ROUTE
    TG -->|pass| SLICE[slicer<br/>Prusa / Orca / Cura]
    SLICE --> SAFETY{build plate<br/>clear?}
    SAFETY -->|no| STOP[STOP · alert user]
    SAFETY -->|yes| HEAT[heat bed + hotend]
    HEAT --> PRINT[dispatch + lock printer]
    PRINT --> EVIDENCE[signed proof envelope]
```

**Switch generation models on command.** Hermes Agents respond to:

> "Switch to TripoSR for the next preview" · "Use Hunyuan3D for the production render" · "Run TRELLIS.2 on this image at high quality" · "Re-render with the OpenSCAD parametric template instead"

The model registry exposes runtime status, GPU readiness, model-cache presence, and dependency health for each engine. Every switch lands a proof event so the run history shows which engine produced which mesh.

**RTX 3090 Ti is a first-class scheduling resource.** The GPU broker prioritises one job at a time, queues the rest, and yields the card back to the OS when idle. ComfyUI, TRELLIS.2, Hunyuan3D, and TripoSR share the same broker; no thrashing.

---

## ✦ Build-plate safety — STOP before heat

> *Hermes will start a print on its own — only when it knows the bed is clear.*

The autonomous-print policy enforces a hard chain of checks before any heater ever turns on. **Any single failure halts the entire chain and alerts the user.** No override without explicit user action.

```mermaid
sequenceDiagram
    participant Agent as Hermes Agent
    participant Camera as Camera Observer
    participant Policy as Safety Policy
    participant Printer
    participant User

    Agent->>Policy: request: start print on T1
    Policy->>Camera: probe build plate (live frame)
    alt last print not removed
        Camera-->>Policy: obstruction detected
        Policy-->>Agent: BLOCKED — plate not clear
        Agent->>User: STOP — Build plate not cleared
        Note over User,Printer: Heaters DO NOT turn on
    else plate clear, last print removed
        Camera-->>Policy: clear · no foreign object
        Policy->>Printer: heat bed (gated)
        Printer-->>Policy: bed reached target
        Policy->>Printer: heat hotend (gated)
        Printer-->>Policy: hotend reached target
        Policy->>Printer: prime + start gcode
        Printer-->>Agent: printing
    end
```

The exact rules currently enforced:

| Gate | Trigger | Action when violated |
| --- | --- | --- |
| **Build-plate clear** | Camera observer sees previous part, brim, or foreign object on the bed | **HARD STOP.** Heaters stay off. User alert: *"Build plate not cleared — remove the previous print and any debris before continuing."* |
| **Last-print removed** | Job history shows `print_state=complete` but no `bed_cleared=true` ack | **HARD STOP.** Hermes refuses to start a new print until the user clicks *Bed Cleared* or the camera confirms a clean surface |
| **No active alert** | Any open alert from `incident_detector` (filament out, thermal runaway, layer shift) | **HARD STOP.** The originating alert must be acknowledged and resolved first |
| **Printer policy** | Printer profile is read-only (S1 by user policy) | **HARD STOP.** No autonomous prints on read-only printers — user runs them manually |
| **Truth-gate pass** | Mesh failed any of the 6 printability checks | **HARD STOP.** Repair loop must succeed before the slicer is invoked |
| **Approval policy** | T1 / V400 require explicit *Print Approved* before each job (configurable) | **PAUSE.** Hermes posts the approval request to the Approvals tab; print waits |

When the gate fires, the user sees one of the hard alerts:

> **STOP — Build plate not cleared.** *Remove the previous print and any tools, brims, or debris from the build surface, then click "Bed Cleared" to continue. Heaters will not turn on while this alert is active.*

> **STOP — Cannot heat: cleared-plate proof missing.** *Hermes never heats the bed or hotend without a fresh cleared-plate confirmation. Resolve the open camera alert first.*

> **STOP — Open incident on Printer T1#1.** *Filament-runout alert (`ev_…`) is unresolved. Acknowledge and resolve before queuing a new print.*

S1 is **read-only by default** in user policy — no autonomous action of any kind. T1#1 / T1#2 / V400 follow the cleared-plate chain above. Every safety decision lands a proof event so the run history shows which gate passed and which fired.

---

## ✦ Two Hermes teams

> Builders propose. Reviewers ship. Locks coordinate. Sandboxes contain. Evidence proves.

Hermes3D-OS extends itself. Two distinct Hermes Agent teams, two distinct API keys (private env, never on disk in this repo), one bounded coding loop:

| Team | Provider | Model | Role | Default scope |
| --- | --- | --- | --- | --- |
| **Team A — Builders** | MiniMax | **MiniMax-M2.7** (high-speed) | Reads folder index, drafts patch proposals, runs scaffolding, suggests refactors | Folder-index-bounded, lock-required |
| **Team B — Reviewers** | DeepSeek | **DeepSeek-V4** | Reviews patches, validates safety/security risks, checks proof IDs and gate results | Read-only on source until review is approved |

Each team is wired to **OpenHands CLI 1.16.0** and **OpenCode 1.4.3-hermes3d** as terminal/file/browser tools, executing inside a **Docker sandbox** (`ghcr.io/openhands/openhands:latest`, 393 MB) with `network=none` and a denied-path list (`.git`, `03_implementation/proof`, `03_implementation/var`, `G:/private`, `node_modules`).

```mermaid
flowchart TD
    USER[user · agents tab · workbench task] --> CLAIM[hermes_claim_task]
    CLAIM --> LOCK[hermes_lock_files<br/>same-owner enforcement]
    LOCK --> SNAP[code-history snapshot]
    SNAP --> MM[Team A · MiniMax-M2.7<br/>builder pass]
    MM --> PROP[patch proposal artifact]
    PROP --> DS[Team B · DeepSeek-V4<br/>reviewer pass]
    DS --> JUDGE{review<br/>accepts?}
    JUDGE -->|no| REPAIR[repair plan · NO source mutation]
    REPAIR --> MM
    JUDGE -->|yes| APPLY[patch/apply-reviewed<br/>same-owner lock check]
    APPLY --> GATES[run gates: git-diff-check<br/>· tests · lint · scan_active_ui_no_fake]
    GATES -->|fail| ROLL[history/restore · rollback proof]
    ROLL --> CLAIM
    GATES -->|pass| POST[post-edit snapshot]
    POST --> BR[git/branch · commit · push]
    BR --> PR[gh pr create]
    PR --> EV[append final evidence<br/>release lock · release task]
```

**The whole loop is observable.** Every step appends to a hash-chained evidence ledger. The Agents tab shows you which step is running right now, which team is acting, and exactly which file is locked. You can stop, hand off, or take over at any boundary.

> Status today: live `/api/code-operator/e2e/readiness` reports both providers configured but currently `auth_failed` (HTTP 401 from the configured private keys). Routes, locks, sandbox, snapshots, gates, and PR lane are all wired and ready. Replace the keys in `G:/private/.env`, restart the API, and the loop runs end-to-end.

---

## ✦ Anonymous & fully agentic

You don't sign in to operate Hermes3D-OS. You run it. The system claims work on its own under named role tokens — and shows you, in real time, what it's doing.

| Concept | What it is |
| --- | --- |
| **Anonymous role tokens** | Built-in `BUILDER`, `CRITIC`, `SCRIBE`, `GATE-SMITH` claims via `hermes_anonymous_claim` / `_release` / `_state`. No auth required. Each role is rate-limited and lock-bounded. |
| **Agent-aware UI** | The Agents tab streams a live picture: which task is active, which file is locked, which provider is mid-pass, which evidence ID was just appended. |
| **Operator interrupt** | Anywhere in the chain, you can Pause, Stop, or hand off to another role. State flushes; locks release; the next claim picks up from the last evidence snapshot. |
| **No data exfiltration** | Provider secrets stay in `G:/private/.env`; never logged, never echoed in proof artifacts, never shipped to the frontend bundle. The sandbox denies the path entirely. |
| **Idle work, never destructive** | When there's no active job, agents may research safe improvements, draft setup plans, and write candidate reports. They never merge, install, flash firmware, or move printers without explicit approval. |
| **S1-policy lock** | The user's FLSUN S1 is read-only by user policy. No agent — anonymous or named — issues motion, heat, or print commands to it. Period. |

```text
$ curl -s http://127.0.0.1:8765/api/anonymous/state | jq
{
  "claims": [
    {"role": "BUILDER",   "task": "h3d-meshlab-cli-verifier",  "owner": "anon-7f3a", "ttl_s": 3540},
    {"role": "CRITIC",    "task": "review-pr-104",             "owner": "anon-d1e2", "ttl_s": 5012},
    {"role": "SCRIBE",    "task": "evidence-chain-replay",     "owner": "anon-c884", "ttl_s": 1801}
  ]
}
```

---

## ✦ The pipeline

Every print walks the same orchestrator state machine. Nine stages, one source of truth, structured evidence at every transition.

<div align="center">
<img src="./site/diagrams/pipeline-9-stage.svg" alt="Animated 9-stage Hermes3D pipeline showing INIT, VISION, GENERATE, REPAIR, TRUTH GATE, SLICE, PRINT, REPORT, DONE with a flowing data pulse" width="100%"/>
</div>

```mermaid
flowchart LR
    INIT[01 INIT<br/>intent] --> VISION[02 VISION<br/>analyze]
    VISION --> GENERATE[03 GENERATE<br/>mesh build]
    GENERATE --> REPAIR[04 REPAIR<br/>auto-fix]
    REPAIR --> TRUTH{05 TRUTH GATE<br/>6 checks}
    TRUTH -->|pass| SLICE[06 SLICE<br/>profile + gcode]
    TRUTH -->|fail| GENERATE
    SLICE --> PRINT[07 PRINT<br/>dispatched]
    PRINT --> REPORT[08 REPORT<br/>evidence]
    REPORT --> DONE[09 DONE<br/>signed proof]
```

```text
01 INIT          intent captured (text prompt, image upload, STL upload, MCP tool call)
02 VISION        analyze: mesh stats, dimensions, complexity score, image-to-mesh routing
03 GENERATE      mesh build (parametric · LLM-augmented · GPU-backed image-to-3D · direct upload)
04 REPAIR        auto-fix: holes, flipped normals, non-manifold edges
05 TRUTH GATE    six independent printability verifications · HMAC envelope
06 SLICE         skill-aware profile generation + gcode emission
07 PRINT         dispatched to selected printer with atomic lock + cleared-plate gate
08 REPORT        evidence appended: filament, duration, quality scores
09 DONE          job closed, lock released, proof signed
```

Stage 05 may loop back to GENERATE up to N times when the truth gate fails — the iteration count is part of the evidence so silent regressions cannot hide.

---

## ✦ Truth Gate

Drop an STL into the launcher. Hermes runs six concurrent printability checks and HMAC-signs the verdict.

<div align="center">
<img src="./site/diagrams/truth-gate-verification.svg" alt="Animated truth-gate verification flow with six checks flipping from amber to green and a signed proof envelope" width="100%"/>
</div>

| Check | What it proves |
| --- | --- |
| `manifold_closure` | Watertight surface — no floating triangles, no flipped normals, no slicer-filled holes |
| `wall_thickness` | Minimum thickness vs. configured nozzle diameter — caught before first-layer commit |
| `overhang_ratio` | Slope above 45° — surfaceable by the auto-orient agent into a printable orientation |
| `bridge_spans` | Unsupported spans > 25 mm flagged as cooling/sag risks |
| `support_estimate` | Predicted cm³ of support material — factored into cost + feasibility |
| `first_layer_area` | Bed adhesion is a top failure mode — Hermes computes it and gates on it |

The HMAC envelope binds the verdict + check matrix + source mesh hash + run timestamp to a per-instance key. Tampering invalidates the seal.

<details>
<summary><strong>See the 17 truth gates that re-prove the system on every push</strong></summary>

<br/>

Hermes3D doesn't ask you to trust it. **17 truth gates** re-attest the system on every push to `main`, sign `PROOF/latest.json` with Sigstore (keyless OIDC), publish a build-provenance attestation, and commit the refreshed proof bundle back to the repo automatically.

```text
source.integrity_manifest          SHA-256 manifest of every source file
deps.parity                        package.json declared deps match installed
tests.unit                         pytest -q (670+ tests, all green)
server.stdio_handshake             Real `node src/server.mjs` returns 44 tools
doctor.hermes3d                    Cross-platform prereq check (json_schema_version: 1)
e2e.multi_agent_flow               14-step real stdio probe (claim -> lock -> block -> handoff -> gate -> release)
workspace.integrity                No probe leaks; no unexpected tracked changes
clients.config_presence            Claude Desktop / Code / Codex / Windsurf / Cursor / Kilo Code wired
clients.claude_code_live           `claude mcp list` reports OK Connected
server.tool_description_hygiene    Free of OWASP MCP tool-poisoning markers
evidence.hash_chain_valid          Mid-chain tamper detected at right index
docs.master_prompt_deliverables    All 10 master-prompt design docs present
events.directory_present           `events/{outbox,handled,failed}` exist
trigger.doctor_passes              Trigger bridge validates outbox + schema
tasks.directory_present            `tasks/{pending,claimed,blocked,done}` exist
queue.doctor_passes                Queue lifecycle validated end-to-end
wizard.dry_run_passes              Universal setup wizard plans without writing
```

Every push to `main` re-proves the chain. The latest run lives at [`PROOF_E2E_REPORT.md`](./PROOF_E2E_REPORT.md).

</details>

---

## ✦ Print farm

Fleet-wide orchestration with per-file locks and atomic handoffs. Multiple agents, multiple printers, no clobber.

<div align="center">
<img src="./site/diagrams/print-farm-orchestration.svg" alt="Animated print-farm orchestration showing the dispatcher selecting a printer, the LOCK badge appearing, and three other printers running independent jobs in parallel" width="100%"/>
</div>

| Layer | What's in it |
| --- | --- |
| **15 adapters** | Cura · PrusaSlicer · OrcaSlicer · FLSun Slicer · Moonraker (RW + RO) · OctoPrint · Fluidd · Mainsail · Printrun · Blender · Blender-MCP |
| **17 internal agents** | Orchestrator · parallel planner · dispatcher · mesh analyzer · mesh repair · auto-orient · auto-recovery · job queue · calibration · incident detector · quality scorer · materials · scheduler · preflight · equivalence · multi-agent critic |
| **4 integrations** | Obico AI failure detection · OctoPrint REST · farm auto-discovery (Moonraker / Mainsail / Fluidd / OctoPrint) · remote control plane |
| **3 printer policies** | T1#1 + T1#2 (autonomous, cleared-plate-gated) · V400 (autonomous, approval-required) · S1 (read-only by user policy) |

> The 17 internal agents are the **deterministic Hermes3D pipeline workers** — different from the two **Hermes Agent teams** (MiniMax + DeepSeek) that build the OS itself. The pipeline workers are stateless, no API key required, and run inside the local FastAPI process. The Hermes Agent teams are LLM-backed, dual-provider, sandbox-isolated, and only act on explicit task claims.

---

## ✦ MCP coordination

Six AI clients. Forty-four MCP tools. One governed surface. HermesProof's lock layer ensures concurrent agents don't step on each other's work.

<div align="center">
<img src="./site/diagrams/mcp-coordination.svg" alt="Animated MCP coordination diagram with Claude, Codex, Cursor, Windsurf, VS Code Copilot, and Kilo Code calling tools through the HermesProof governance band" width="100%"/>
</div>

```text
DISPATCH         hermes_dispatch_recommend         hermes_pick_task
LOCKS            hermes_lock_files                 hermes_release_files
                 hermes_recover_stale_locks        hermes_list_locks
TASKS            hermes_claim_task                 hermes_release_task
                 hermes_record_task                hermes_list_pending_tasks
                 hermes_recover_stale_tasks
A2A              hermes_a2a_create_task            hermes_a2a_get_task
                 hermes_a2a_list_tasks             hermes_a2a_update_task
HANDOFFS         hermes_create_blocked_handoff     hermes_request_handoff
                 hermes_approve_handoff
EVIDENCE         hermes_append_evidence            hermes_verify_evidence
                 hermes_emit_event                 hermes_list_events
                 hermes_mark_event_handled
GATES            hermes_run_gate                   hermes_list_gates
DOCTOR           hermes_doctor                     hermes_get_state
                 hermes_read_policy                hermes_record_outcome
ANONYMOUS        hermes_anonymous_claim            hermes_anonymous_release
                 hermes_anonymous_state
USERS            hermes_user_check_authorization   hermes_user_grant_session
                 hermes_user_revoke_session
AGENT            hermes_agent_health               hermes_agent_request_user_session
                 hermes_agent_resolve_blocked      hermes_agent_revoke_session
                 hermes_list_agents                hermes_heartbeat
QUEUE            hermes_enqueue_task
```

Each tool ships with MCP `2025-11-25` annotations (`readOnlyHint` · `destructiveHint` · `idempotentHint` · `openWorldHint`) so clients render approval prompts that match the actual blast radius — read-only listing tools auto-allow; destructive ones always confirm.

The backend FastAPI process exposes **220 HTTP routes** including the 10 required Agent Workbench routes (`/api/code-operator/e2e/readiness`, `/api/code-operator/e2e/jobs`, `/api/code-operator/providers/smoke`, `/api/code-operator/patch/apply-reviewed`, `/api/code-operator/gates/run`, `/api/code-operator/git/pr`, `/api/code-operator/cli-runners`, `/api/code-operator/cli-runners/preflight`, `/api/code-operator/cli-runners/run`, `/api/code-operator/sandbox/readiness`).

---

## ✦ The React control plane · 18 tabs

```text
DASHBOARD     SIMPLE GUI    OBSERVE       PRINTERS      SOURCE OS    AGENTS
ARTIFACTS     SETTINGS      PLUGINS       JOBS          AUTOPILOT    LEARNING
VOICE         DESIGN        3D GEN        APPROVALS     ROADMAP      AGENTS RAIL
```

| Tab | What it does |
| --- | --- |
| **Dashboard** / **Simple GUI** | Fleet KPIs, active prints, runtime freshness, headline state — dense and resizable, with a Simple compact mode |
| **Observe** | Live camera feeds (V400 · S1 · T1) with rotation, undock, plate-clearance gate |
| **Printers** | T1#1 / T1#2 / S1 / V400 onboarding wizard (probe Moonraker → camera URL → safety → save) |
| **Source OS** | The 60-app catalog. Verify, Setup Plan, per-row Backup / Check / Update / Rollback |
| **Agents** | Two-Hermes-team workbench: claim task, lock files, run providers, review patch, ship PR |
| **Artifacts** | Every proof envelope, every signed mesh, every transcript — grid + list, agent-attached |
| **Settings** / **Plugins** | Provider keys, printer profiles, environment ledger, app update center |
| **Jobs** | Full pipeline state · cancel · repair propose / apply · retry · rollback — every transition emits proof |
| **Autopilot** | Idle work guardrails: S1 lock, print approval, truth gate, advance-to-next-gate |
| **Learning** | Idle research candidates, daily review queue, Run/Keep/Remove decisions |
| **Voice** | Azure STT/TTS, transcript history, agent reply voice playback, proof events |
| **Design** | Parametric design intake, OpenSCAD/CadQuery/Blender provider lanes |
| **3D Generation** | Image-to-mesh and prompt-to-mesh — TRELLIS.2 / Hunyuan3D / TripoSR / ComfyUI |
| **Approvals** | Pending / approved / rejected — every risky action lands here first |
| **Roadmap** | Live tab-completion ledger, next packages, current proof event head |
| **Agents Rail** | Persistent left-rail chat across all tabs, with mic, file upload, voice replies |

`scan_active_ui_no_fake.py` confirms **81 active production files, zero fake/mock markers**.

---

## ✦ Quickstart

Three commands and you're at `localhost:7860` with the Truth Gate · Organizer · Pipeline tabs working. **No API keys required for the base launcher.**

```bash
git clone https://github.com/Ghenghis/Hermes3D
cd Hermes3D
pip install -e ".[ui]"
python -m hermes3d.app.launcher
# -> http://127.0.0.1:7860
```

Verify everything:

```bash
python scripts/scaffolding/doctor.py --json   # cross-platform prereq probe
pytest -q                                      # 670+ tests, full suite
hermes3d truth-gate ./mymesh.stl               # CLI smoke
```

Wire it into every MCP client (Claude Desktop · Claude Code · Codex · Cursor · Windsurf · VS Code Copilot · Kilo Code) with one interactive command:

```bash
npm run wizard --prefix ../HermesProof
```

To enable the dual-Hermes coding loop, add MiniMax-M2.7 and DeepSeek-V4 keys to `G:/private/.env` (Windows) or `~/.config/hermes3d/private.env` (Linux/macOS):

```text
HERMES3D_MINIMAX_API_KEY=sk-...           # never committed
HERMES3D_MINIMAX_BASE_URL=https://api.minimax.io
HERMES3D_MINIMAX_MODEL=MiniMax-M2.7
HERMES3D_DEEPSEEK_API_KEY=sk-...
HERMES3D_DEEPSEEK_BASE_URL=https://api.deepseek.com
HERMES3D_DEEPSEEK_MODEL=deepseek-v4-pro
HERMES3D_OPENCODE_BIN=/path/to/opencode
HERMES3D_OPENHANDS_BIN=/path/to/openhands
HERMES3D_AGENT_SANDBOX_IMAGE=ghcr.io/openhands/openhands:latest
HERMES3D_AGENT_SANDBOX_NETWORK=none
```

Then restart and click **Smoke MiniMax** + **Smoke DeepSeek** in the Agents tab. Both must pass before the dual-team loop runs.

---

## ✦ Customization

<table>
<tr>
<td width="33%" align="center">

**Printer profiles**

[`03_implementation/config/printers.toml`](./03_implementation/config/printers.toml)

Stock template with 12 example profiles. Override with `printers.user.toml` (gitignored — stays local). S1 read-only by policy; T1 / V400 cleared-plate-gated.

</td>
<td width="33%" align="center">

**Skill packs**

[`03_implementation/config/skill_packs/`](./03_implementation/config/skill_packs/)

JSON-defined "what works on this printer × material × quality" hints. Three stock packs ship; auto-derived overrides are learned from print history.

</td>
<td width="33%" align="center">

**LLM + provider policy**

[`03_implementation/config/llm_policy.yaml`](./03_implementation/config/llm_policy.yaml)

Provider allowlist · cost caps · timeouts. API keys via env (`HERMES3D_*_API_KEY`), never on disk in this repo. Sandbox denies the private-env path.

</td>
</tr>
</table>

---

## ✦ Composes with

Hermes3D-OS is the orchestration + truth-gate + fleet + dual-Hermes-team layer. It coexists with peer servers in your MCP graph:

| Concern | Server | Status |
| --- | --- | --- |
| Per-file locks · handoffs · evidence | [**HermesProof**](https://github.com/Ghenghis/HermesProof) | governance layer (sister project) |
| 3D model generation (text → mesh, image → mesh) | ComfyUI · TRELLIS.2 · Hunyuan3D 2.1 · TripoSR · Blender MCP | external — wired via Source OS catalog |
| LLM inference (cloud) | MiniMax M2.7 · DeepSeek V4 · OpenAI · Anthropic · OpenRouter | private env only · Bearer at request time |
| LLM inference (local) | Ollama · LM Studio · vLLM | external — `llm_policy.yaml` allowlist |
| Code-loop sandbox | OpenHands CLI 1.16.0 · OpenCode 1.4.3-hermes3d · Docker | bounded, `network=none`, denied paths enforced |
| Read / write filesystem | [`@modelcontextprotocol/server-filesystem`](https://github.com/modelcontextprotocol/servers) | external — coexists |

---

## ✦ Self-host

Run Hermes3D's web UI on a Hostinger VPS while keeping inference on your local machine. No port forwarding, no public LLM endpoint, ~$8/month total.

```text
INTERNET → hermes.userdomain.com (A record)
  ↓
HOSTINGER KVM 2 (Ubuntu 24.04, ~$7/mo)
  · Caddy 2.8 :443 (auto-SSL via Let's Encrypt)
  · Gradio :7860 + FastAPI :8000
  · Postgres 16 + Redis 7
  · tailscaled (peer)
  · restic -> Backblaze B2 (nightly, ~$1/mo)
  ↓ Tailscale (WireGuard, no public ports)
GAMING PC (Windows 11, RTX 3090 Ti)
  · Ollama 0.5 :11434 (GPU, native /api/chat for streaming + tool calls)
  · ComfyUI · TRELLIS.2 · Hunyuan3D · TripoSR (GPU broker)
  · OpenHands + OpenCode sandbox (Docker)
  · tailscaled (peer)
  · Syncthing -> NAS (.env, printer configs)
  ↓ LAN
PRINTER FLEET (Klipper · Moonraker · OctoPrint)
```

The full deploy bundle (Caddy config + Docker Compose + Tailscale ACL + Restic systemd timer) lands at [`06_release/deploy/vps/`](./06_release/deploy/vps/) — see [`06_release/deploy/README.md`](./06_release/deploy/README.md) once it ships.

---

## ✦ Releases

Signed Windows binaries on every tag (PyInstaller + Velopack auto-update + Sigstore keyless OIDC), source bundle with Sigstore-signed proof envelope, and GitHub native build-provenance attestation.

```bash
# Verify the Sigstore signature on a release artifact
cosign verify-blob \
  --certificate-identity-regexp 'https://github.com/Ghenghis/Hermes3D' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --bundle hermes3d-os.json.cosign.bundle hermes3d-os.json

# Verify the GitHub build-provenance attestation
gh attestation verify Hermes3D-Setup.exe --repo Ghenghis/Hermes3D

# Or just `winget install` (Phase 2)
winget install Hermes3D
```

Latest release: <https://github.com/Ghenghis/Hermes3D/releases>

---

## ✦ Documentation

- **Architecture** — [`02_architecture/`](./02_architecture/) (ADRs · diagrams · contracts)
- **Phase reports** — [`00_overview/`](./00_overview/) (Phase 1 → 5.1, evidence-backed)
- **Release notes** — [`00_overview/V5_3_0_RELEASE_NOTES.md`](./00_overview/V5_3_0_RELEASE_NOTES.md) (v5.3.0 RC — draft for review)
- **Honesty ledger** — [`00_overview/contract/HONESTY_LEDGER.md`](./00_overview/contract/HONESTY_LEDGER.md) (every claim, with status)
- **Roadmap** — [`03_implementation/ROADMAP.md`](./03_implementation/ROADMAP.md)
- **Live proof** — [`PROOF_E2E_REPORT.md`](./PROOF_E2E_REPORT.md) (refreshed by CI on every push)
- **60-app registry** — [`source-os-60-apps/REGISTRY.md`](./03_implementation/docs/handoffs/hermes3d-os-folder-index-2026-05-07/source-os-60-apps/REGISTRY.md)
- **Hermes Agent E2E truth/proof plan** — [`HERMES_AGENT_E2E_TRUTH_PROOF_PLAN_2026-05-08.md`](./03_implementation/docs/handoffs/HERMES_AGENT_E2E_TRUTH_PROOF_PLAN_2026-05-08.md)
- **Claude E2E intelligence bundle** — [`claude-e2e-intelligence-2026-05-08/`](./03_implementation/docs/handoffs/claude-e2e-intelligence-2026-05-08/) (PR 106)

---

## ✦ Contributing

Direct pushes to `main` are blocked at three layers — local pre-push hook, `branch-guard` CI workflow, and branch-protection rules. Open a feature branch and PR into `develop`. Full contributor guide at [`CONTRIBUTING.md`](./CONTRIBUTING.md).

<details>
<summary><strong>Branch model + 10-layer CI gate map (dev-internal)</strong></summary>

<br/>

```text
main         <- production. Protected. Only release/* and hotfix/* may merge.
develop      <- integration. All feature branches merge here first.
feat/<area>/<desc>   <- features. PR -> develop.
release/v<x.y.z>     <- release prep. PR -> main + develop.
hotfix/<id>          <- production fixes. PR -> main + develop.
```

CI layers (all must pass on every PR to develop):

- **Layer A** — static gates (ruff format · ruff check · mypy · forbidden-pattern scan)
- **Layer B** — smoke + acceptance (4 cells: ubuntu/windows × py3.11/3.12)
- **Layer C** — integration (real adapter I/O, Linux only)
- **Layer D** — UI E2E (Playwright + Gradio launcher)
- **Layer D3** — Gradio launcher smoke (advisory until stability data confirms)
- **Layer E** — release dry-run (gated on `release/*` branches)
- **Layer F** — honesty gates (regenerate manifest + claim audit + scan_active_ui_no_fake)
- **Layer M** — matrix coverage (silent-regression catch)
- **Layer T** — unified truth gate (consolidated proof bundle)
- **Layer W** — wizard E2E (recorded wizard run)

</details>

<details>
<summary><strong>Phase status + repository layout (dev-internal)</strong></summary>

<br/>

**Current track:** v5.3.0 RC (Contract Kit hardening complete) — see [`00_overview/V5_3_0_RELEASE_NOTES.md`](./00_overview/V5_3_0_RELEASE_NOTES.md). Phase 5.1 kit hardening is closed: [`00_overview/PHASE5_1_COMPLETION_REPORT.md`](./00_overview/PHASE5_1_COMPLETION_REPORT.md).

**Repository layout:**

```text
00_overview/        Phase plans, contracts, roadmap, honesty ledger
01_research/        Research artifacts feeding architecture decisions
02_architecture/    ADRs · diagrams · contracts · API surface
03_implementation/  Source: hermes3d/ package, config/, ui/, source-lab/
04_testing/         pytest suites · Playwright E2E · matrix fixtures
05_proof/           PROOF/latest.json · proof verifier · gates
06_release/         PyInstaller spec · Velopack · Hostinger VPS bundle
handoffs/           Open architect -> implementer briefs
site/               Marketing landing page (GH Pages, ./site/)
```

**Open handoffs:** see [`handoffs/`](./handoffs/) — architect -> implementer briefs.

</details>

---

## ✦ License

MIT — see [`LICENSE`](./LICENSE).

---

<div align="center">

**Built honestly. Proved continuously. Coordinated by [HermesProof](https://github.com/Ghenghis/HermesProof).**
**60 apps. Two Hermes teams. One truth-gated emporium.**

</div>
