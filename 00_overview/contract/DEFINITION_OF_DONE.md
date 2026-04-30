# DEFINITION OF DONE — Hermes3D-OS Lite v5

> **Source of truth:** This document derives from `MASTER_CONTRACT.md` §37
> and the user's standing engineering contract (no stubs, real tests, zero
> warnings, turn-key repos). It enumerates the exit criteria a change must
> satisfy before it can be considered "done" — i.e., before it can be
> merged, packaged, released, or claimed as working in any documentation.

---

## 0. Scope

A "change" is any of the following:

- A new feature or module
- A bug fix or behavioural change to an existing module
- A refactor that touches public APIs or persistence layouts
- A new printer profile, slicer profile, skill pack, or built-in tool
- An update to scripts, CI, installer, or runtime configuration
- A documentation update that asserts new or revised behaviour

Pure typo fixes, comment-only edits, and dead-link repairs are exempt from
the build/test gates but still require honest CHANGELOG accounting.

---

## 1. Build & run

A change is **NOT done** unless all of these are true:

1. **Clean clone builds.** A fresh clone of the repository onto a clean
   Windows 11 + Python 3.11 environment can produce a runnable artifact
   with one of:
   - `pwsh scripts/run-dev.ps1`
   - `bash scripts/run-dev.sh`
   - `pip install -e .` followed by `hermes3d --help` and `hermes3d-api`.
2. **CI builds match local.** The GitHub Actions workflow runs the same
   commands as the local scripts and reaches the same outcome. CI is
   never "skipped" or "marked optional" without an entry in
   `00-CONTRACT/HONESTY_LEDGER.md`.
3. **Smoke boot proves life.** The launcher (`hermes3d-api` for the REST
   server, `python -m hermes3d.app.launcher` for the Gradio UI) starts,
   responds to a healthcheck, and shuts down cleanly within 30 seconds on
   the test machine.

---

## 2. Quality gates (zero-warning default)

| Gate | Tool | Threshold | Override |
|------|------|-----------|----------|
| Format | `ruff format --check` | zero diff | none |
| Lint | `ruff check` | zero warnings | time-bounded allowlist in `pyproject.toml` with rule id, path, reason, and ISO 8601 expiry |
| Type | `mypy --strict src/hermes3d` | zero errors | per-file `# mypy: ignore-errors` requires a comment explaining why and a tracking issue |
| Static gate | `scripts/forbidden_pattern_scan` | zero hits in runtime code paths | none |

Forbidden patterns (in any file under `src/` or `scripts/`):

- `TODO`, `FIXME`, `STUB`, `PLACEHOLDER`, `NOT_IMPLEMENTED` (any case)
- Empty `except` blocks (`except: pass` and variants)
- `raise NotImplementedError` outside abstract base classes
- Top-level `print(` calls in non-CLI library code
- UI handlers that do nothing — including button `onClick`/`Command`
  bindings that resolve to no-op methods

---

## 3. Tests (real code paths first)

| Tier | Required for | Notes |
|------|--------------|-------|
| **Smoke** | Every change | Service boots, healthcheck passes, minimum API roundtrip succeeds |
| **Integration** | Anything that touches persistence, slicer, Moonraker, or LLM provider | Real filesystem fixtures, optional docker-compose for stateful deps |
| **Contract** | Anything that touches the REST or MCP API surface | Schema-validated, version-tagged |
| **E2E / UI** | Anything that touches the Gradio UI or launcher behaviour | Headless browser or scripted launcher invocation |
| **Unit** | Anything where unit-level isolation aids debugging | Lowest priority — never the *only* coverage |

**Mock policy:** Mocks are permitted **only** when:

- The dependency requires paid external API keys, **and**
- That dependency is not in the critical path for the feature, **or**
- The dependency is non-deterministic hardware (e.g., a USB camera, a
  printer's MCU) and the test is exercising upstream logic.

When mocks are used, at least one separate test must exercise the same
flow through the real implementation. Mock-only coverage of a public
behaviour is a contract violation.

**Flake policy:** A test that flakes is a bug. It is fixed at the root
cause, never quarantined or skipped silently. A `@pytest.mark.skip` is
permitted only with a tracking issue ID and an ISO 8601 expiry comment;
CI fails after that date.

---

## 4. Security baseline

A change is **NOT done** unless:

1. **No secrets in code.** Anything that looks like an API key, token,
   password, or signing secret is in `env/.env.example` only as a
   placeholder name. Real values live in `.env`, which is gitignored.
2. **Secret scan passes.** `gitleaks` or equivalent runs in CI with zero
   findings.
3. **Dependency scan passes.** `pip-audit` reports no unaddressed
   critical or high findings. Non-critical findings have a tracking
   issue or `requirements-pinned.lock` exemption with rationale.
4. **Risky surfaces documented.** If the change introduces or alters
   external-process execution, plugin loading, file download, user-
   uploaded mesh execution, or any operation that may write outside
   `./var/`, that surface is enumerated in `SECURITY.md`.
5. **Proof envelope unbroken.** Any change that touches truth-gate
   results, dispatch decisions, slicer outputs, or test-case acceptance
   maintains the HMAC-SHA256 proof-envelope chain. Acceptance proofs are
   verifiable by `python 03-PROOF-SYSTEM/conformance_runner.py
   --verify`.

---

## 5. Documentation

Updated **with the same PR**, never deferred:

- `README.md` — install, run, troubleshoot
- `ARCHITECTURE.md` — components, data flow, key decisions (Mermaid
  diagrams, no ASCII art)
- `CHANGELOG.md` — versioned, every user-visible change explained
- `SECURITY.md` — threat model, risky surfaces
- `07-DOCS/AGENTIC_AUTOMATION.md` — when agents/tools change
- `07-DOCS/PRINTER_FLEET_GUIDE.md` — when fleet/profiles change
- `07-DOCS/AI_PROGRAMMER_GUIDE.md` — when contracts or APIs change

Inline docstrings for every public function, class, and module — no
"will be filled in later" placeholders.

---

## 6. Release artifacts

A change earmarked for release is **NOT done** unless:

1. The release script (`scripts/release.ps1` / `.sh`) produces:
   - A versioned `dist/hermes3d_os_lite_v<MAJOR>.<MINOR>.<PATCH>.zip`
   - A SHA256 checksum file alongside it
   - A signed proof envelope describing the build (commit hash,
     environment fingerprint, test summary)
2. The artifact extracts and runs on a clean Windows 11 VM with no
   network access (after dependencies are pre-installed) — i.e., no
   surprise downloads at first launch.
3. The acceptance runner (`04-TEST-CASE-DESK-ORGANIZER/run_acceptance.py
   --strict`) succeeds against the artifact's own scaffolding without
   manual intervention.
4. `CHANGELOG.md` has a dated entry for the version, listing every
   user-visible change.

---

## 7. Honesty obligations

Every claim made in user-facing copy (README, ARCHITECTURE, CHANGELOG,
the launcher's "About" panel, the Gradio UI's tab descriptions) must be
backed by either:

- A passing test, or
- An explicit "spec / scaffold" annotation in `HONESTY_LEDGER.md`

If a feature is described as "available" but is not yet implemented, the
description is wrong — it must be removed from copy or qualified as
"experimental — not yet implemented" with a tracking issue ID.

The honesty ledger is updated in the same PR that introduces or
withdraws functionality. Drift between code and ledger is a contract
violation.

---

## 8. Sign-off checklist

The author of a change asserts, in the PR description:

- [ ] Builds from a clean clone via the documented steps
- [ ] All gate scripts (`format.ps1`, `lint.ps1`, `test.ps1`) pass
- [ ] No new forbidden patterns introduced
- [ ] CHANGELOG and relevant 07-DOCS entries updated
- [ ] HONESTY_LEDGER reconciled
- [ ] Smoke run from `run-dev.ps1` succeeds
- [ ] Acceptance runner is still 48/48 (or has been updated honestly)
- [ ] Security scans clean (or new findings explained)

This document is the contract. If a step here cannot be met, the change
is not done — it does not ship, it does not get described as working,
and it does not block other work pretending to be a foundation. Either
finish it or remove it.
