# CHANGELOG — Hermes3D-OS Lite

All notable changes to this kit are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [5.0.0] — 2026-04-29

The **v5 Contract Kit** edition. First public, contract-driven
release.

### Added

- 12 verified printer profiles (6 delta + 4 cartesian + 2 CoreXY)
  with bed shapes, kinematics, and material capability metadata —
  `core.printers.printer_profiles`.
- 8-strategy dispatcher (auto, fastest, quality, largest_bed,
  smallest_fit, least_busy, delta_prefer, cartesian_prefer) with bed
  fit and material eligibility checks — `core.agents.dispatcher`.
- 8 truth gates: schema, geometry, bed, material, skill, spool,
  health, workflow — `core.validation.truth_gate`.
- HMAC-SHA256 signed proof envelopes with batch verification —
  `core.proof.proof_envelope`, `05_truth_proof/conformance_runner.py`.
- 12-node print workflow with atomic JSON checkpointing —
  `core.orchestration.print_workflow`.
- Skill memory store with 6 skill kinds, scope matching,
  reinforce/weaken — `core.memory.skill_store`.
- Skill-pack import/export bundles (SHA-256 verified) —
  `core.memory.skill_pack`.
- Vector memory backend (TF-IDF + optional FAISS) —
  `core.memory.vector_memory`.
- Multi-LLM provider abstraction (Ollama, LM Studio, vLLM, llama.cpp,
  OpenRouter) with reachability fallbacks — `core.llm.providers`.
- Multi-agent loop (Critic + Optimiser + Executor) with synthetic
  fallback when no LLM is reachable — `core.agents.multi_agent`.
- Failure predictor blending PrintHistory + SkillStore signals —
  `core.intelligence.failure_predictor`.
- Quality scorer with 5 explainable dimensions —
  `core.agents.quality_scorer`.
- Tool registry + 11 built-in tools wired to real backends —
  `core.agents.tool_registry`, `core.agents.tool_registrations`.
- Incident detector covering 9 incident types —
  `core.agents.incident_detector`.
- Supervisor daemon with event listeners and auto-skill creation —
  `core.supervisor.daemon`.
- Print farm dashboard, spool tracker, cost estimator, print history,
  backup orchestrator — `core.farm.*`.
- OctoPrint client, Obico client, farm auto-discovery, Telegram +
  Discord remote control bridge — `core.integrations.*`.
- FastAPI REST server (10 endpoints) — `api.server`.
- Hand-rolled MCP stdio server (16 tools) — `api.mcp_server`.
- `hermes3d` CLI with subcommands (fleet, validate, dispatch, slice,
  queue, spool, proof) — `cli.__main__`.
- Gradio launcher with multi-tab control panel — `app.launcher`.
- Notifier (Discord/Slack/Generic) with env-only secrets —
  `core.notifications.notifier`.
- Mesh repair, mesh analysis, auto-orient, auto-recovery, parallel
  planner, equivalence checker, preflight checklist, calibration
  macro lookup — `core.agents.*`.
- LangGraph source export adapter (linear runtime executor is the
  default) — `core.orchestration.langgraph_adapter`.

### Tooling

- One-button scripts: `doctor`, `test`, `run-dev`, `lint`, `format`,
  `build`, `release`, `proof-collect` — both PowerShell and Bash.
- Forbidden-pattern scan (TODO/FIXME/STUB/PLACEHOLDER/
  NotImplementedError + bare `except: pass`) —
  `scripts/forbidden_pattern_scan.py`.
- Honesty-ledger drift detector — `scripts/honesty_diff.py`.
- README claim audit — `scripts/readme_claim_audit.py`.
- Installer with manifest-driven optional component selection —
  `06_release/installer/install.{ps1,sh}`, `verify_install.py`.
- Windows one-click launcher — `run.bat`.
- GitHub Actions CI matrix (Linux + Windows × Python 3.11 + 3.12)
  with 6 jobs across 5 layers — `.github/workflows/ci.yml`.

### Tests

- 264 tests across `tests/unit/`, `tests/conformance/`,
  `tests/integration/` — all green.
- Acceptance runner: 4 desk-organiser variants × 12 printers, 48 cells
  produce signed proof envelopes — runs in <10 seconds —
  `04_testing/acceptance/run_acceptance.py`.

### Documentation

- Master contract (`00_overview/contract/MASTER_CONTRACT.md`) plus four
  derived contract docs: `DEFINITION_OF_DONE`, `GATES`,
  `TRUTH_AND_PROOF_SYSTEM`, `ROADMAP`, `FEATURES`,
  `HONESTY_LEDGER`, `KIT_MANIFEST.json`.
- Architecture, security, troubleshooting, agentic automation, brain
  layer, AI programmer, and printer fleet guides — `07-DOCS/*`.

### Known limitations

- Blender MCP server is **spec-only** — install bpy 4.2 + pymeshlab
  to activate; otherwise calls raise `NotImplementedError` with a
  clear remediation message.
- LangGraph runtime adapter is **spec-only** — only the source
  exporter is functional. Linear executor is the default and is fully
  tested.
- The Gradio dashboard's deeper tabs (skill memory browser, incident
  log, remote-control test, LLM provider switcher) are present in
  `app.launcher` but marked scaffold in the honesty ledger pending
  v5.3 polish.

---

## Format reference

Future entries should use these section headings:

- **Added** — new features
- **Changed** — changes in existing functionality
- **Deprecated** — features marked for removal
- **Removed** — features removed in this release
- **Fixed** — bug fixes
- **Security** — security-related changes

Every entry must reference a file path or module name, and must be
backed by a passing test. Documentation-only changes go under
`Documentation`.
