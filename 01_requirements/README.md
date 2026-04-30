# Hermes3D-OS Lite — README

> Agentic 3D-print farm OS for a 12-printer mixed-kinematics fleet.
> Local-first, Docker-friendly, contract-driven.

This kit is the **v5 Contract Kit** edition of Hermes3D-OS Lite. It is
not a finished commercial product — it is a fully wired, tested,
honest scaffold that one engineer can run on a workstation and grow
incrementally into a daily driver.

## What this gives you, immediately

- A fleet model of 12 verified printer profiles (6 delta + 4 cartesian
  + 2 CoreXY) with bed shapes, kinematics, and material capability
  metadata.
- A dispatcher that picks the right printer for a job by 8 strategies
  (auto, fastest, quality, largest_bed, smallest_fit, least_busy,
  delta_prefer, cartesian_prefer).
- Eight truth gates that refuse to dispatch a print whose mesh,
  material, or printer state isn't safe.
- An HMAC-SHA256 proof-envelope system that produces signed records of
  every dispatch, slicer run, and acceptance test outcome.
- A Gradio control panel on `http://127.0.0.1:7860` and a FastAPI REST
  surface on `http://127.0.0.1:8765`.
- A long-term skill memory store with five skill kinds, scope
  matching, reinforcement, and import/export bundles.
- A multi-LLM provider abstraction (Ollama, LM Studio, vLLM,
  llama.cpp, OpenRouter) with graceful fallback when none is reachable.
- A 12-node print workflow graph with atomic JSON checkpointing.
- Telegram and Discord remote-control bridges (opt-in, off by default).
- 264 passing tests + 48/48 acceptance variants × printers, all
  producing verifiable proof envelopes.

## Install (Windows 11, primary)

```powershell
git clone <this-repo> hermes3d-os-lite
cd hermes3d-os-lite
pwsh 06_release/installer\install.ps1
```

The installer is interactive. It asks about each optional component
(Gradio UI, REST API, Ollama provider, remote-control bridges, FAISS
vector memory). Pick what you want. Required dependencies install
automatically.

After it finishes, run the doctor to confirm the environment is sane:

```powershell
pwsh scripts\scaffolding\doctor.ps1
```

## Install (Linux / WSL)

```bash
git clone <this-repo> hermes3d-os-lite
cd hermes3d-os-lite
bash 06_release/installer/install.sh
bash scripts/scaffolding/doctor.sh
```

## Run

```powershell
# Windows: one click
run.bat

# Or via PowerShell
pwsh scripts\scaffolding\run-dev.ps1
```

```bash
# Linux / WSL
bash scripts/scaffolding/run-dev.sh
```

The Gradio UI starts at `http://127.0.0.1:7860`, the REST API at
`http://127.0.0.1:8765`, and the supervisor daemon runs in the
background. Logs go to `logs/`.

## Test

```powershell
pwsh scripts\scaffolding\test.ps1                # Layer A + B (fast)
pwsh scripts\scaffolding\test.ps1 -Integration   # + Layer C
pwsh scripts\scaffolding\test.ps1 -E2E           # + Layer D
```

```bash
bash scripts/scaffolding/test.sh
bash scripts/scaffolding/test.sh --integration
bash scripts/scaffolding/test.sh --e2e
```

The acceptance runner — 4 desk-organiser variants × 12 printers — is
included in Layer B and produces signed proof envelopes under
`var/acceptance-results/`.

## Documentation

| Audience | File |
|----------|------|
| First-time user | this file + `02_architecture/TROUBLESHOOTING.md` |
| Operator | `01_requirements/PRINTER_FLEET_GUIDE.md`, `01_requirements/AGENTIC_AUTOMATION.md` |
| Contributor / AI programmer | `01_requirements/AI_PROGRAMMER_GUIDE.md`, `00_overview/contract/MASTER_CONTRACT.md` |
| Architecture | `02_architecture/ARCHITECTURE.md`, `02_architecture/diagrams/*` |
| Brain layer | `01_requirements/BRAIN_LAYER_GUIDE.md` |
| Security | `02_architecture/SECURITY.md` |
| Changes | `02_architecture/CHANGELOG.md` |
| Honest feature inventory | `00_overview/contract/FEATURES.md`, `00_overview/contract/HONESTY_LEDGER.md` |

## Repository layout

```
00_overview/contract/                  the contract: MASTER, DOD, GATES, FEATURES, ROADMAP, ...
02_architecture/              diagrams, JSON schemas
03_implementation/               the actual code
   src/hermes3d/              Python package
   tests/                     264 tests
   config/                    printers.toml + Klipper configs + skill packs
   scripts/                   doctor, test, run-dev, lint, format, build, release
   .github/workflows/ci.yml   CI matrix (Linux + Windows × 3.11 + 3.12)
05_truth_proof/              conformance runner + protocol docs
04_testing/acceptance/  acceptance runner + design briefs
06_release/installer/                 install scripts + manifest + post-install verifier
01_requirements/                      everything in this Documentation table
env/.env.example              template env vars
run.bat                       Windows one-click launcher
pyproject.toml                package metadata
```

## What's NOT here yet (honest)

- No mobile app. Telegram / Discord remote control is the mobile story.
- No vendor cloud. Everything runs on your machine.
- No Blender MCP runtime. The scaffolding is in place
  (`core.modeling.blender_mcp_server`) but it will refuse with a clear
  message until you install Blender 4.2 and bpy.
- No LangGraph runtime adapter — only a source exporter. Run the
  workflow with the built-in linear executor, or wire LangGraph
  yourself per `01_requirements/AI_PROGRAMMER_GUIDE.md`.

The honesty ledger (`00_overview/contract/HONESTY_LEDGER.md`) is the canonical
list of "runnable / scaffold / spec" for every module.

## Credits

This is Dave Lavalley's farm. The kit was assembled with AI assistance
under a strict no-stubs / real-tests / zero-warnings engineering
contract (see `00_overview/contract/MASTER_CONTRACT.md`). Anything you find
here that doesn't work is a contract violation — please file an
issue, or, better, fix it.

## License

See `LICENSE` (to be populated by the user before public distribution).
