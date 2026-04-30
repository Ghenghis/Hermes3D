# GATES.md — Layered Anti-Laziness System

> The Hermes3D-OS Lite contract is enforced by **six layers** of automated
> gates. A change passes only if every applicable gate is green. This
> document defines each gate, names the tooling, and explains the
> deliberate redundancy between layers.

The layers are ordered from **fastest** (cheap to run, fail early) to
**most expensive** (long-running, real-world). CI runs them in this order
and short-circuits on the first failure to keep feedback tight.

---

## Layer A — Static gates (sub-second to ~30s)

**Purpose:** catch the failure modes that don't even need code to run.

| Gate | Tool | Command | Failure mode caught |
|------|------|---------|---------------------|
| Formatter | ruff format | `ruff format --check src/ tests/` | inconsistent whitespace, quote style, blank-line policy |
| Linter | ruff check | `ruff check src/ tests/` | unused imports, F-strings without interpolation, mutable defaults, etc. |
| Type checker | mypy | `mypy --strict src/hermes3d` | structural type errors, missing return types, `Any` leaks |
| Forbidden-pattern scan | `scripts/forbidden_pattern_scan` | regex over `src/` and `scripts/` | TODO/FIXME/STUB/PLACEHOLDER/`raise NotImplementedError` outside ABCs, empty `except:` |
| Schema validators | jsonschema CLI | over every `.schema.json` in `01-ARCHITECTURE/contracts/` | malformed contract schemas |
| YAML/TOML validators | `python -c "import tomllib; ..."` and `pyyaml` | over `pyproject.toml` and `.github/workflows/*.yml` | unparseable config |

**Wall-clock target:** entire layer under 30 seconds on the test
machine.

**Bypass policy:** none for runtime code. Test fixtures may carry
intentional anomalies (e.g., a malformed STL) — those live under
`tests/fixtures/` and are excluded from the forbidden-pattern scan.

---

## Layer B — Runtime gates (30s – 3 min)

**Purpose:** prove the system actually starts, talks to itself, and
handles a happy-path workflow before exotic integrations get tested.

| Gate | Command | Pass condition |
|------|---------|----------------|
| Smoke import | `python -c "import hermes3d.app.launcher"` | no ImportError, no warning, returns within 5s |
| CLI smoke | `hermes3d --help` and `hermes3d fleet --json` | exit code 0, valid JSON on stdout |
| API smoke | start `hermes3d-api` in background, GET `/healthz`, GET `/v1/fleet` | both return 200; healthz body matches schema |
| MCP smoke | spawn `hermes3d-mcp`, send `initialize` and `tools/list` over stdio | response includes ≥ 16 tools |
| Acceptance runner | `python 04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py` | 48/48 variants × printers green, all proof envelopes verify |
| Workflow graph | `python -m hermes3d.tools.workflow_smoke` | builds the 12-node print workflow, runs in DryRun mode, every node returns PASS or SKIP |

**Wall-clock target:** entire layer under 3 minutes on the RTX 3090 Ti
test rig.

---

## Layer C — Integration gates (3 – 10 min)

**Purpose:** prove the system works with its real persistence layers and
optional dependencies.

| Gate | Dependency | Command |
|------|-----------|---------|
| Queue + history persistence | filesystem (real `./var/`) | `pytest -m persistence` |
| Slicer integration | PrusaSlicer or OrcaSlicer on `$PATH` | `pytest -m slicer` |
| Moonraker contract | none (probe is mocked but uses real HTTP wire format) | `pytest -m moonraker_contract` |
| LLM provider contract | Ollama or LM Studio reachable, or skipped | `pytest -m llm_provider` |
| Vector memory | optional faiss-cpu + sentence-transformers | `pytest -m vector_memory` |

Tests marked with these `pytest` markers are excluded from the default
suite (Layer A/B) and run only here. CI exposes them as separate jobs so
that a missing optional dependency doesn't fail the main pipeline.

---

## Layer D — UI / E2E gates (5 – 15 min)

**Purpose:** prove the Gradio UI is actually wired to the backend, not
just visually present.

| Gate | Tool | What's verified |
|------|------|-----------------|
| Gradio launcher | direct subprocess + `requests` against the launcher's HTTP port | every tab loads, every primary button responds with non-empty server-side state change |
| Tab × backend | `tests/e2e/test_ui_wiring.py` | for each tab, click the primary action and assert that a corresponding entry appears in `./var/queue.json`, `./var/skills.json`, log file, or notification queue |
| Capture on failure | screenshot/video/HTML dump | written to `./logs/e2e/<test_id>/` |

**Note:** these tests are platform-aware. They run headless in CI on
ubuntu-latest, and headed locally on Windows 11 when invoked via
`scripts/test.ps1 -E2E`.

---

## Layer E — Release gates (10 – 25 min)

**Purpose:** prove the packaged artifact actually runs.

| Gate | Command |
|------|---------|
| Build wheel | `python -m build --wheel` produces a `.whl` whose `RECORD` file matches the staged tree |
| Build distribution zip | `scripts/release.ps1 -Stage build` produces a versioned zip + SHA256 |
| Clean-room install | spin up a fresh Python venv, `pip install dist/*.whl`, run `hermes3d --help` and the smoke tests above |
| Acceptance against installed package | run `04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py` against the installed module, not the source tree |
| Proof envelope | `python -m hermes3d.tools.release_proof --verify dist/<artifact>.zip` confirms the build's HMAC chain |

---

## Layer F — Honesty gates (manual + automated)

**Purpose:** prevent drift between what the system *does* and what the
documentation *claims* it does.

| Gate | Mechanism | Authoritative file |
|------|-----------|--------------------|
| Honesty ledger reconciliation | `scripts/honesty_diff.py` compares the runnable-vs-spec annotations against actual test coverage | `00-CONTRACT/HONESTY_LEDGER.md` |
| README claim audit | `scripts/readme_claim_audit.py` extracts every "X works" claim from the README and looks for a corresponding passing test | `README.md`, `07-DOCS/README.md` |
| CHANGELOG completeness | every PR that touches a `runnable` module must add a CHANGELOG entry — enforced by a CI check | `CHANGELOG.md` |
| Tier annotation freshness | every file in `src/hermes3d/` carries a `Status:` header (`runnable | scaffold | spec`); CI fails if a `spec` file gains code without being upgraded to `runnable` | every module top-of-file comment |

---

## Layered redundancy is intentional

Each layer can, in theory, catch failure modes the layers above missed:

- Layer A may pass while Layer B fails (e.g., import succeeds but a
  module has a runtime side effect that hangs the launcher).
- Layer B may pass while Layer C fails (e.g., the queue serialiser
  works on toy data but corrupts on a 50-job queue).
- Layer C may pass while Layer D fails (e.g., a backend handler works
  but the Gradio binding sends `None` instead of `""`).
- Layer D may pass while Layer E fails (e.g., a path is hard-coded to
  the source-tree layout and breaks when installed as a wheel).
- Layer E may pass while Layer F catches a stale README.

A change passes when **every applicable layer** is green. "Applicable"
is the only judgment the author exercises — the documentation change
that adds a CHANGELOG entry doesn't need Layer D, and a new printer
profile doesn't need Layer E. Everything else is mechanical.

---

## Local invocation

| What you want | Command |
|---------------|---------|
| Layer A only (fast) | `pwsh scripts/lint.ps1` |
| Layer A + B (default) | `pwsh scripts/test.ps1` |
| Layer A + B + C | `pwsh scripts/test.ps1 -Integration` |
| Layer A + B + C + D | `pwsh scripts/test.ps1 -E2E` |
| Layer E (release dry-run) | `pwsh scripts/release.ps1 -DryRun` |
| Layer F (manual audit) | `python scripts/honesty_diff.py` |

WSL/Linux equivalents use `bash scripts/test.sh [--integration|--e2e]`.

---

## Summary

| Layer | Cost | Catches | Owner |
|-------|------|---------|-------|
| A | seconds | typos, lint, types, forbidden patterns | author + ruff/mypy |
| B | minutes | imports, boot, smoke flows, acceptance | author + pytest |
| C | minutes | persistence, slicer, Moonraker, LLM, vectors | CI integration job |
| D | minutes | UI ↔ backend wiring | CI E2E job, manual smoke |
| E | tens of minutes | release artifact reality | CI release job |
| F | manual + scripted | docs ↔ code drift | reviewer + audit scripts |

If a layer is silent, it isn't passing — it's missing. Missing layers
are tracked in the honesty ledger until they are added. The contract
forbids declaring a system "production-ready" while any applicable
layer is silent.
