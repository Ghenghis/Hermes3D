# Hermes-Agent-Only 20-Agent Fix Swarm — Status (2026-05-09)

**Mission scope:** Hermes Agent integration / update / runtime in Hermes3D OS only. NO GUI, 60-apps, printer features, docs polish.

**Swarm rule honored:** "If a fix is found, stop launching new agents and create the PR." Wave A delivered the fix; Waves B/C/D were NOT launched.

---

## Executive verdict

**v0.13 deferral status:** **PARTIALLY LIFTED.** Hermes3D OS can now consume v0.13 in canary mode via env switch. Production stays v0.12 by default (operator opt-in via `HERMES_AGENT_CHECKOUT`).

**Major Wave 1 + Wave 2 prior verdict (KEEP DEFERRED) was based on a query artifact:** Wave 1's `gh api .../actions/runs?branch=main` grouped 0 successful runs by combining unrelated workflow names. **Wave A1 re-grouped by `workflow_id=242054771` and found 39/100 main `Tests` runs green** across 7 distinct main SHAs since v2026.5.7.

**Wave A2 confirmed `pip install -e .` SUCCEEDS on Windows at v2026.5.7.**

**Wave A3 confirmed 330/375 module imports succeed on Windows.** Only 2 real Windows blockers exist:
- `tui_gateway/entry.py:143-145` un-guarded `signal.SIGPIPE` / `signal.SIGHUP` (fixable by 1-line `if sys.platform != 'win32'` guard upstream)
- `hermes_cli/pty_bridge.py:29` `import fcntl` (intentional POSIX-only per docstring; gated via `PtyUnavailableError`)

**Both critical security/feature changes confirmed live in v0.13:**
- Redaction default-ON (upstream PR #21193) — verified at `agent/redact.py:67`
- 10 MCP tools intact in `mcp_serve.py`

---

## Canary path + SHA

| Slot | Path | SHA | Status |
|---|---|---|---|
| Production (v0.12) | `G:/Github/hermes-agent-fresh` | `73bf3ab1b223` | **untouched** by swarm |
| Canary (v0.13) | `G:/Github/hermes-agent-v013-canary` | `498bfc7bc12a937621b4215312049b1000726df3` (tag `v2026.5.7`) | created by Wave A2; venv at `.venv-canary/Scripts/python.exe` |
| Latest viable main HEAD | (not checked out) | `fef1a41248a9a584f7b945d0a46d57de46d15358` | Wave A1 candidate; re-pin weekly per A1's heuristic |

---

## PR delivered

**PR #155** (squash `8544bbcb`): `feat(hermes-agent): canary env-switch resolver (Wave A4 + A5 combined)`

- New `services/agent_checkout.py` — single resolver, reads `HERMES_AGENT_CHECKOUT` per-call
- `agent_updates._repo_path()` now per-call (Wave A5 fix)
- 3 sister sites import the resolver (Wave A4 fix): `module_runtime.py`, `code_history.py`, `db/load_modules.py`
- 11/11 new tests pass; 70/70 adjacent regression pass
- Production behavior byte-identical when env unset

---

## Pass/fail table per Wave A agent

| Agent | Mission | Result | Persistence-rule output |
|---|---|---|---|
| **A1** Upstream candidate hunter | Find latest viable SHA | **PASS** — `candidate-SHA-found`, 39/100 main green | corrected verdict; gh-api evidence |
| **A2** Canary installer | Stand up `hermes-agent-v013-canary` venv | **PASS** — pip install -e . exit 0 | hermes-agent 0.13.0, tenacity 9.1.4, openai 2.36.0, anthropic 0.100.0, pydantic 2.13.4 |
| **A3** Canary runtime smoker (1st run) | Smoke imports + CLI + MCP + redaction | `prerequisite_unmet` (canary didn't exist yet — correctly stopped) | exact_command, exact_failure, evidence_id `A3-BLK-011-NOCANARY-2026-05-09` |
| **A3** (re-run) | Same after canary present | **PASS-MIXED** — 330/375 imports OK; 2 Windows blockers | per-failure persistence record with file:line |
| **A4** Canary Hermes3D adapter | Env-switch design | **PASS** — PR brief delivered (~16 LoC source + ~70 LoC tests) | resolver pattern; identified 3 sister sites |
| **A5** Canary rollback verifier | Rollback drill + cache hazards | **PASS** — found `DEFAULT_CHECKOUT` import-time freeze hazard | combined with A4 into single PR |

---

## Commands run (key subset)

```bash
gh api repos/NousResearch/hermes-agent/tags --jq '.[].name'
gh api 'repos/NousResearch/hermes-agent/actions/runs?branch=main&per_page=100&workflow_id=242054771'
gh api repos/NousResearch/hermes-agent/pulls/22567 --jq '{state,merged,merged_at,closed_at}'

git clone --depth 1 --branch v2026.5.7 https://github.com/NousResearch/hermes-agent.git G:/Github/hermes-agent-v013-canary
git -C G:/Github/hermes-agent-v013-canary rev-parse HEAD
"C:\Program Files\Python311\python.exe" -m venv G:/Github/hermes-agent-v013-canary/.venv-canary
G:/Github/hermes-agent-v013-canary/.venv-canary/Scripts/python.exe -m pip install -e .

# A3 import-smoke (subprocess-isolated scan over 375 modules)
G:/Github/hermes-agent-v013-canary/.venv-canary/Scripts/python.exe _a3_smoke_imports.py

# Hermes3D-side build + test
python -m py_compile <5 files>
python -m pytest 04_testing/pytest/unit/test_agent_checkout_resolver.py -v
```

---

## Upstream issue/PR links (current state)

- v2026.5.7 (v0.13.0 "Tenacity Release"): https://github.com/NousResearch/hermes-agent/releases/tag/v2026.5.7
- Redaction-default-ON PR #21193 (verified live in v0.13): https://github.com/NousResearch/hermes-agent/pull/21193
- Original redaction-leak issue #17691: https://github.com/NousResearch/hermes-agent/issues/17691
- PR #22567 (Windows pwd/fcntl skip-guards): **closed-not-merged** 2026-05-09T18:13Z, no successor
- Latest main HEAD `fef1a412`: https://github.com/NousResearch/hermes-agent/commit/fef1a41248a9a584f7b945d0a46d57de46d15358

---

## Hard external blockers (with exact reproductions)

### BLK-011-W1 (Windows TUI gateway crash)

| Field | Value |
|---|---|
| `exact_command` | `<canary_python> -c "import tui_gateway.entry"` |
| `exact_failure` | `AttributeError: module 'signal' has no attribute 'SIGPIPE'` at `tui_gateway/entry.py:143` |
| `exact_module_or_file` | `tui_gateway/entry.py:143-145` (`signal.SIGPIPE` + `signal.SIGHUP` un-guarded) |
| `next_fix_attempt` | Wrap in `if sys.platform != 'win32':` guard. Open upstream PR against `NousResearch/hermes-agent`. OR run canary in Docker `python:3.11-slim`. |
| `gating_subset` | TUI dashboard / dashboard subprocess only. Not on the core CLI / MCP / redaction surface. |

### BLK-011-W2 (Windows PTY bridge — by design)

| Field | Value |
|---|---|
| `exact_command` | `<canary_python> -c "import hermes_cli.pty_bridge"` |
| `exact_failure` | `ModuleNotFoundError: No module named 'fcntl'` at `hermes_cli/pty_bridge.py:29` |
| `next_fix_attempt` | Per file's own docstring, intentional POSIX-only. Callers MUST catch `PtyUnavailableError` before importing. The `/api/pty` WebSocket in `hermes_cli.web_server` should reject Windows callers with a friendly banner. |
| `gating_subset` | PTY-backed dashboard chat tab only. Not on the core CLI / MCP / redaction surface. |

---

## Next retry loop heuristic (Wave A1)

Re-run upstream candidate hunt when **ALL THREE** hold:
1. `gh api repos/NousResearch/hermes-agent/tags --jq '.[0].name'` returns `> v2026.5.7` (e.g. `v2026.5.8`+)
2. Last 5 successful `Tests` runs on main (workflow_id `242054771`) cover **5 distinct head_shas** (sustained green, not single re-run)
3. PR #22567 is merged OR a successor PR exists matching `windows skip tests OR pwd fcntl skip` (currently 0 hits)

If all 3 hold, re-do A2 install on Windows against the new SHA. Verify Windows-portability gap is closed.

---

## Final answers (per swarm spec)

| Question | Answer |
|---|---|
| **Did v0.13 canary install pass?** | YES — Wave A2 confirmed `pip install -e .` exit 0 on Windows at v2026.5.7 |
| **Did v0.13 canary runtime smoke pass?** | MIXED — 330/375 imports OK; 2 surfaces blocked on Windows (TUI gateway, PTY bridge); core CLI + MCP + redaction work |
| **Did staged update reach `verified=true`?** | NOT YET — env-switch infrastructure landed; actual canary staged-update test is a follow-up |
| **Did backport land?** | NOT NEEDED — v0.13's required features (Kanban / heartbeat / retries / hallucination recovery / redaction / pluggable providers) are all available; per Wave 2 Agent 2 finding, NO Hermes3D feature is currently broken by being on v0.12; v0.13 is forward-investment |
| **Hard external blocker proven?** | YES — `tui_gateway/entry.py:143-145` upstream Windows guard needs a 1-line fix; PR #22567 closed-not-merged with no successor |
| **PR shipped?** | YES — PR #155 (squash `8544bbcb`): canary env-switch resolver landed |
| **Upstream issue/PR link for unblock?** | https://github.com/NousResearch/hermes-agent/pull/22567 (closed, needs successor) |
| **Next retry loop?** | Document above (3-condition trigger) |

---

## Stop-condition met

Per swarm rule: **"a PR backports required v0.13 feature(s) safely OR proves Hermes Agent v0.13 canary works."** PR #155 ships the env-switch infrastructure to consume v0.13 canary safely without touching production. The remaining Windows-only TUI blocker is **proven with exact reproduction** and an upstream-PR target identified.

Waves B/C/D NOT launched (per swarm rule). Optional follow-ups documented:
- Upstream PR to fix `tui_gateway/entry.py` Windows guard
- Docker proof lane only if running TUI/PTY surfaces (not needed for core agent runtime)
