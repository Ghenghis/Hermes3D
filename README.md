<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./site/diagrams/pipeline-9-stage.svg"/>
  <source media="(prefers-color-scheme: light)" srcset="./site/diagrams/pipeline-9-stage.svg"/>
  <img src="./site/diagrams/pipeline-9-stage.svg" alt="Hermes3D-OS — nine-stage orchestration pipeline (theme-aware)" width="100%"/>
</picture>

<br/>

# Hermes3D-OS

**An operating system for your print farm.**

[![CI](https://github.com/Ghenghis/Hermes3D/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Ghenghis/Hermes3D/actions/workflows/ci.yml)
[![Pages](https://github.com/Ghenghis/Hermes3D/actions/workflows/pages.yml/badge.svg)](https://ghenghis.github.io/Hermes3D/)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-06b6d4?style=flat-square)](https://www.python.org)
[![MCP](https://img.shields.io/badge/MCP-2025--11--25-a855f7?style=flat-square)](https://modelcontextprotocol.io)
[![Truth gates](https://img.shields.io/badge/truth--gates-17%2F17-22c55e?style=flat-square)](./PROOF_E2E_REPORT.md)

[![Governed by](https://img.shields.io/badge/governed%20by-HermesProof-ec4899?style=flat-square)](https://github.com/Ghenghis/HermesProof)
[![Sigstore](https://img.shields.io/badge/sigstore-keyless%20OIDC-f59e0b?style=flat-square)](https://www.sigstore.dev/)
[![Made with](https://img.shields.io/badge/made%20with-Gradio%20%7C%20FastAPI%20%7C%20React-06b6d4?style=flat-square)](#)

**Live site → [ghenghis.github.io/Hermes3D](https://ghenghis.github.io/Hermes3D/)**

[Quickstart](#-quickstart) · [Pipeline](#-the-pipeline) · [Truth Gate](#-truth-gate) · [Fleet](#-print-farm) · [MCP](#-mcp-coordination) · [Releases](#-releases) · [Self-host](#-self-host) · [Contributing](#-contributing)

</div>

---

## What it does — in 30 seconds

- **Truth-gates every mesh** through six concurrent printability checks, then HMAC-signs the verdict so it can be audited later — even by someone who doesn't trust the printer that ran the job.
- **Dispatches across your fleet** with per-file locks, atomic handoffs, and 8 selection strategies — Claude, Codex, Cursor, Windsurf, VS Code Copilot and Kilo Code can call the same 16-tool MCP surface without clobbering each other.
- **Proves the system continuously.** 17 truth gates re-attest the codebase on every push to `main`, sign `PROOF/latest.json` with Sigstore (keyless OIDC), and commit the refreshed bundle back to the repo. **77 of 79 user-visible features are real today** — the other two are conspicuously disabled with explanations, never "Coming Soon" buttons.
- **Treats Hermes Agents as user-authorized operator/admin delegates.**
  Agents may use Hermes3D OS, the user's PC, local files/apps, web
  services, VPS/remote hosts, source repositories, GitHub branches,
  commits, pushes, and PRs when the user assigns that work. Missing
  data means ask or block; never invent printer state, slicer output,
  generated models, proof events, setup status, or remote-host state.
- **Keeps OpenCode/OpenHands honest.** Hermes3D detects their source
  checkouts, private executable-path keys, and sandbox readiness separately.
  Agent CLI runs stay blocked until a real executable, Docker sandbox image,
  MCP locks, snapshots, redacted output proof, review, and gates are present.

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
01 INIT          intent captured (text prompt, STL upload, MCP tool call)
02 VISION        analyze: mesh stats, dimensions, complexity score
03 GENERATE      mesh build (parametric / LLM-augmented / direct upload)
04 REPAIR        auto-fix: holes, flipped normals, non-manifold edges
05 TRUTH GATE    six independent printability verifications
06 SLICE         skill-aware profile generation + gcode emission
07 PRINT         dispatched to selected printer with atomic lock
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
server.stdio_handshake             Real `node src/server.mjs` returns 24 tools
doctor.hermes3d                    Cross-platform prereq check (json_schema_version: 1)
e2e.multi_agent_flow               14-step real stdio probe (claim → lock → block → handoff → gate → release)
workspace.integrity                No probe leaks; no unexpected tracked changes
clients.config_presence            Claude Desktop / Code / Codex / Windsurf wired
clients.claude_code_live           `claude mcp list` reports ✓ Connected
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
| **17 agents** | Orchestrator · parallel planner · dispatcher · mesh analyzer · mesh repair · auto-orient · auto-recovery · job queue · calibration · incident detector · quality scorer · materials · scheduler · preflight · equivalence · multi-agent critic |
| **4 integrations** | Obico AI failure detection · OctoPrint REST · farm auto-discovery (Moonraker / Mainsail / Fluidd / OctoPrint) · remote control plane |

---

## ✦ MCP coordination

Six AI clients. Sixteen tools. One governed surface. HermesProof's lock layer ensures that concurrent agents don't step on each other's work.

<div align="center">
<img src="./site/diagrams/mcp-coordination.svg" alt="Animated MCP coordination diagram with Claude, Codex, Cursor, Windsurf, VS Code Copilot, and Kilo Code calling 16 tools through the HermesProof governance band" width="100%"/>
</div>

```text
DISPATCH       hermes3d.dispatch        hermes3d.parallel_plan
QUEUE          queue_list               queue_enqueue           queue_cancel
FLEET          fleet_status             spool_list
VALIDATE       truth_gate               analyze_mesh            proof_verify
SLICE          generate_profile         list_materials
INTELLIGENCE   predict_failure          skill_lookup            skill_list
COST           estimate_cost
```

Each tool ships with MCP `2025-11-25` annotations (`readOnlyHint` · `destructiveHint` · `idempotentHint` · `openWorldHint`) so clients render approval prompts that match the actual blast radius — read-only listing tools auto-allow; destructive ones always confirm.

---

## ✦ Quickstart

Three commands and you're at `localhost:7860` with the Truth Gate · Organizer · Pipeline tabs working. **No API keys required for the base launcher.**

```bash
git clone https://github.com/Ghenghis/Hermes3D
cd Hermes3D
pip install -e ".[ui]"
python -m hermes3d.app.launcher
# → http://127.0.0.1:7860
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

---

## ✦ Customization

<table>
<tr>
<td width="33%" align="center">

**Printer profiles**

[`03_implementation/config/printers.toml`](./03_implementation/config/printers.toml)

Stock template with 12 example profiles. Override with `printers.user.toml` (gitignored — stays local).

</td>
<td width="33%" align="center">

**Skill packs**

[`03_implementation/config/skill_packs/`](./03_implementation/config/skill_packs/)

JSON-defined "what works on this printer × material × quality" hints. Three stock packs ship; auto-derived overrides are learned from print history.

</td>
<td width="33%" align="center">

**LLM policy**

[`03_implementation/config/llm_policy.yaml`](./03_implementation/config/llm_policy.yaml)

Provider allowlist · cost caps · timeouts. API keys via env (`HERMES3D_*_API_KEY`), never on disk in this repo.

</td>
</tr>
</table>

---

## ✦ Composes with

Hermes3D is intentionally narrow at its core — it's the orchestration + truth-gate + fleet layer. It coexists with peer servers in your MCP graph:

| Concern | Server | Status |
| --- | --- | --- |
| Per-file locks · handoffs · evidence | [**HermesProof**](https://github.com/Ghenghis/HermesProof) | governance layer (sister project) |
| 3D model generation (text → mesh) | ComfyUI · TRELLIS · Hunyuan3D | external — wired via Blender MCP |
| LLM inference | Ollama · vLLM · LM Studio · Anthropic · OpenAI | external — `llm_policy.yaml` allowlist |
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
  · restic → Backblaze B2 (nightly, ~$1/mo)
  ↓ Tailscale (WireGuard, no public ports)
GAMING PC (Windows 11)
  · Ollama 0.5 :11434 (GPU, native /api/chat for streaming + tool calls)
  · tailscaled (peer)
  · Syncthing → NAS (.env, printer configs)
  ↓ LAN
PRINTER FLEET (Klipper · Moonraker · OctoPrint)
```

The full deploy bundle (Caddy config + Docker Compose + Tailscale ACL + Restic systemd timer) lands at [`06_release/deploy/vps/`](./06_release/deploy/vps/) — see [`06_release/deploy/README.md`](./06_release/deploy/README.md) once it ships.

---

## ✦ Releases

Signed Windows binaries on every tag (PyInstaller + Velopack auto-update + Azure Artifact Signing), source bundle with Sigstore-signed proof envelope, and GitHub native build-provenance attestation.

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
- **Roadmap** — [`00_overview/contract/ROADMAP.md`](./00_overview/contract/ROADMAP.md)
- **Operator GUI roadmap** — [`03_implementation/ROADMAP.md`](./03_implementation/ROADMAP.md) (16 tabs · live ledger · printer policy)
- **20-agent completion contract** — [`03_implementation/docs/handoffs/CLAUDE_20_AGENT_COMPLETION_CONTRACT.md`](./03_implementation/docs/handoffs/CLAUDE_20_AGENT_COMPLETION_CONTRACT.md)
- **Live proof** — [`PROOF_E2E_REPORT.md`](./PROOF_E2E_REPORT.md) (refreshed by CI on every push)

---

## ✦ Contributing

Direct pushes to `main` are blocked at three layers — local pre-push hook, `branch-guard` CI workflow, and branch-protection rules. Open a feature branch and PR into `develop`. Full contributor guide at [`CONTRIBUTING.md`](./CONTRIBUTING.md).

<details>
<summary><strong>Branch model + 10-layer CI gate map (dev-internal)</strong></summary>

<br/>

```text
main         ← production. Protected. Only release/* and hotfix/* may merge.
develop      ← integration. All feature branches merge here first.
feat/<area>/<desc>   ← features. PR → develop.
release/v<x.y.z>     ← release prep. PR → main + develop.
hotfix/<id>          ← production fixes. PR → main + develop.
```

CI layers (all must pass on every PR to develop):

- **Layer A** — static gates (ruff format · ruff check · mypy · forbidden-pattern scan)
- **Layer B** — smoke + acceptance (4 cells: ubuntu/windows × py3.11/3.12)
- **Layer C** — integration (real adapter I/O, Linux only)
- **Layer D** — UI E2E (Playwright + Gradio launcher)
- **Layer D3** — Gradio launcher smoke (advisory until stability data confirms)
- **Layer E** — release dry-run (gated on `release/*` branches)
- **Layer F** — honesty gates (regenerate manifest + claim audit)
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
03_implementation/  Source: hermes3d/ package, config/, ui/
04_testing/         pytest suites · Playwright E2E · matrix fixtures
05_proof/           PROOF/latest.json · proof verifier · gates
06_release/         PyInstaller spec · Velopack · Hostinger VPS bundle
handoffs/           Open architect → implementer briefs
site/               Marketing landing page (GH Pages, ./site/)
```

**Open handoffs:** see [`handoffs/`](./handoffs/) — architect → implementer briefs.

</details>

---

## ✦ License

MIT — see [`LICENSE`](./LICENSE).

---

<div align="center">

**Built honestly. Proved continuously. Coordinated by [HermesProof](https://github.com/Ghenghis/HermesProof).**

</div>
