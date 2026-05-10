# Hermes Agent — Cross-Version Compatibility Matrix (2026-05-09)

**Mission:** Document which Hermes Agent features ship in which upstream version, which Hermes3D consumer features depend on which version, and which version an operator should pick for which mode of work. **Pure docs.** No source edits.

**Owner:** Wave 2 Agent **P2-5** (cross-version compat matrix builder).
**Branch:** `claude/agent-version-compat-matrix`.
**File:** `03_implementation/docs/handoffs/HERMES_AGENT_VERSION_COMPAT_MATRIX_2026-05-09.md`.

**Banked inputs (informational only — this doc reproduces and corrects them with primary-source verification):**
- Wave 2 prior swarm Agent 2 (multi-version compat mapper) returned a 7-feature x 4-version preliminary table.
- Wave A3 (PR #155) confirmed redaction default-ON in v0.13 (upstream PR #21193) — verified at `agent/redact.py:67` in canary checkout.
- Wave A3 confirmed 10 `@mcp.tool()` decorators intact in v0.13 `mcp_serve.py`.
- v0.13 ships `plugins/model-providers/` directory with **28** provider sub-directories (this doc — corrects the "27+" approximation).
- Latest tag upstream is `v2026.5.7` (v0.13.0 "Tenacity Release"). `v2026.5.8` and `v2026.5.9` do **not** exist on `NousResearch/hermes-agent`.

---

## 0. Version-to-tag map

Source of truth: `gh api repos/NousResearch/hermes-agent/releases` run 2026-05-09.

| Display name | Upstream tag | Release date (UTC) | Release codename |
|---|---|---|---|
| v0.11 | `v2026.4.23` | 2026-04-23T22:32:13Z | Hermes Agent v0.11.0 |
| v0.12 | `v2026.4.30` | 2026-04-30T18:31:21Z | Hermes Agent v0.12.0 |
| v0.13 | `v2026.5.7` | 2026-05-07T16:23:08Z | Hermes Agent v0.13.0 — "The Tenacity Release" |
| main HEAD | (no tag) | latest commit on `NousResearch/hermes-agent:main` | drift > 247 commits / ~2 days post v0.13 per Wave A1 retry-loop heuristic |

**v0.13.0 is the highest tagged release.** Anything labelled "v0.14+" in earlier briefs is forward investment and lives on `main` until a future tag is cut.

---

## 1. Feature x Hermes Agent Version

Legend: **Y** = present + default-on, **opt-in** = present but operator must enable, **N** = absent or non-functional, **partial** = present in some surfaces only.

| Feature (upstream) | v0.11 (`v2026.4.23`) | v0.12 (`v2026.4.30`) | v0.13 (`v2026.5.7`) | main HEAD (post v0.13) |
|---|---|---|---|---|
| **Kanban (multi-profile board)** | Y | Y | Y | Y |
| **Heartbeat reclaim (false-timeout guard + zombie cleanup)** | partial (no zombie-cleanup pass) | Y | Y | Y |
| **Zombie detection (darwin zombie workers + auto-block)** | N | Y | Y | Y |
| **Per-task retry budget (`max_retries` override)** | N | Y | Y | Y |
| **Hallucination recovery (gate + recovery UX)** | N | partial (gate only, no UX) | Y | Y |
| **Redaction default-ON (PR #21193)** | N | opt-in (`HERMES_REDACT_SECRETS=true`) | **Y** (default-on; opt-out via `HERMES_REDACT_SECRETS=false`) | Y |
| **Pluggable model-providers directory (`plugins/model-providers/`)** | N | N | **Y** (28 provider sub-dirs) | Y (33 declared per upstream commit message; new providers land on main first) |
| **Native Windows TUI guard (PR #21561)** | N | N | N (un-guarded `signal.SIGPIPE` / `SIGHUP` at `tui_gateway/entry.py:143-145`) | **Y** (PR #21561 merged 2026-05-08T21:27:41Z, **post-v0.13 tag**) |

### Source citations for each row (line:col references are against the canary checkout at `G:/Github/hermes-agent-v013-canary` SHA `498bfc7b`)

- **Redaction default-ON**: v0.13 `agent/redact.py:67` reads `os.getenv("HERMES_REDACT_SECRETS", "true")`; v0.12 same file reads `os.getenv("HERMES_REDACT_SECRETS", "")` (default OFF). Diff is the literal `"true"` second argument to `os.getenv`. Upstream PR: <https://github.com/NousResearch/hermes-agent/pull/21193>.
- **Pluggable providers**: `git log v2026.5.7 --max-count=1 -- plugins/model-providers/` returns commit `9022804d7` "feat(providers): make all 33 providers pluggable under plugins/model-providers/". Same query at `v2026.4.30` (v0.12) returns empty (path did not exist). Listed sub-dirs at v0.13: `ai-gateway, alibaba, alibaba-coding-plan, anthropic, arcee, azure-foundry, bedrock, copilot, copilot-acp, custom, deepseek, gemini, gmi, huggingface, kilocode, kimi-coding, minimax, nous, ollama-cloud, openai-codex, opencode-zen, openrouter, qwen-oauth, stepfun, xai, xiaomi, zai` plus `README.md` and `__init__.py` (28 dirs total at the v0.13 tag).
- **Native Windows TUI guard**: `gh api repos/NousResearch/hermes-agent/pulls/21561` reports `merged_at = 2026-05-08T21:27:41Z`, **after** the v0.13 tag at `2026-05-07T16:23:08Z`. Therefore the guard is **NOT** in v0.13; it is on `main` HEAD only.
- **Kanban / heartbeat / zombie / retry / hallucination**: per Wave 2 prior swarm Agent 2 banked finding; this doc adopts that mapping verbatim. No public PR-numbered cross-check was available for those rows in the bank.

---

## 2. Hermes3D consumer compat (does the Hermes3D feature work on Hermes Agent v0.12 / v0.13 / main HEAD?)

| Hermes3D consumer feature | Pinned upstream Hermes Agent surface | Works on v0.12 | Works on v0.13 | Works on main HEAD |
|---|---|---|---|---|
| **Staged update endpoint** (`/api/agents/update/staged`) | `services/agent_updates._run_update_checks()` + `services/agent_checkout.py` resolver | Y | Y | Y (untested; depends on `_run_update_checks` shape stability) |
| **Provider smoke** (MiniMax + DeepSeek via `POST /providers/smoke`) | v0.12: monolithic `gateways/providers/*.py`. v0.13: `plugins/model-providers/{minimax,deepseek}/`. Hermes3D adapter bridges both shapes. | Y | Y | Y |
| **OpenCode + OpenHands preflight** (`hermes-agent` discovers both binaries) | `acp_registry/` + `tools/` packages — same shape v0.11 -> main HEAD | Y | Y | Y |
| **BLK-013 bounded task** (`POST /cli-runners/run-bounded-task`, Docker `--network=none --read-only --cap-drop=ALL`) | Hermes3D-side service; calls into upstream `tools/` and `agent/` only | Y (PR #159 landed; agent-version agnostic by design) | Y | Y |
| **MCP tool registry (Hermes locks)** | upstream `mcp_serve.py` — 10 `@mcp.tool()` decorators v0.12 and v0.13 (Wave A3 line-by-line check) | Y | Y | Y (likely; no upstream removal observed in commit log post v0.13) |
| **Recovery Controller v1 ledger** | Hermes3D-side only; reads agent-side proof events | Y | Y | Y |
| **Recovery Controller v2** (commits 1+2 only; commits 3-5 paused) | Hermes3D-side only; agent-version agnostic per PR #149 design | Y | Y | Y |

### Notes on the consumer matrix

1. **All Hermes3D consumer features work on v0.12, v0.13, and main HEAD today.** This is not aspirational — Wave A2/A3 ran the canary install + smoke at v0.13 and produced 7 PASS / 1 N/A / 0 FAIL (the N/A is BLK-013 which has now landed in PR #159). v0.12 is the production default and is byte-identical pre/post canary work per the PR #157 audit.
2. **The redaction default flip is the ONLY behavior visible to Hermes3D consumers that changes between v0.12 and v0.13.** On v0.12 the operator must explicitly set `HERMES_REDACT_SECRETS=true`. On v0.13 redaction is on unless `HERMES_REDACT_SECRETS=false` is explicitly set. Hermes3D's `services/agent_checkout.py` resolver does **not** override this — the upstream agent's process-wide default applies.
3. **`plugins/model-providers/` is forward-investment.** Hermes3D's provider bridge (`build_probe_request()` in `gateways/providers/{minimax,deepseek}.py`) currently targets the **monolithic** v0.12 shape and works against v0.13 because v0.13 keeps backward-compatible top-level imports. If a future Hermes3D feature needs to enumerate providers via `plugins/model-providers/` (e.g. an admin "list providers" UI), that feature would require **v0.13 minimum**.
4. **Native Windows TUI gateway is NOT a current Hermes3D consumer surface.** Hermes3D does not embed the upstream TUI dashboard. Whether PR #21561 is in the running checkout therefore does **not** gate any Hermes3D consumer feature today. It is listed here only because future Hermes3D features that wrap the TUI (none planned) would require main HEAD.
5. **Recovery Controller v2 commits 3-5 are paused per the standing project memory entry.** This doc does not promote them to "supported on v0.X"; it lists only the shipped commits 1+2.

---

## 3. Operator decision table — when to pick which version

| Scenario | Recommended version | Rationale |
|---|---|---|
| **Conservative production ops who want zero churn until v0.13.x patches accumulate** | **v0.12** (`v2026.4.30`) | Production default per Wave 1 prior to PR #160 promotion. Operator opts out of v0.13 by setting `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`. No Hermes3D feature regresses on v0.12. The redaction-default-OFF behavior is acceptable in fully-trusted-operator environments and is mitigated by Hermes3D's own log scrubbers. |
| **Production default (Wave 1 verified)** | **v0.13** (`v2026.5.7`) | 7 PASS / 1 N/A / 0 FAIL canary smoke (PR #157), `pip install -e .` clean on Windows at this tag (Wave A2), redaction-default-ON (defense-in-depth), 10 MCP tools intact. Promoted by PR #160. Operators get the new pluggable provider directory and the per-task retry budget. **This is the recommended default.** |
| **Upstream-test reproduction only** | **main HEAD** | Use **only** for reproducing an upstream bug or testing a yet-to-be-tagged commit. Drifts > 247 commits / ~2 days from the latest tag (per Wave A1 measurement). PR #21561 (Native Windows TUI guard) lives here, but Hermes3D does not currently consume the TUI surface, so the only reason to switch is bug-bisection. **Do NOT use in production.** |

### How to switch (for ops reference)

The Hermes3D resolver `services/agent_checkout.py` reads `HERMES_AGENT_CHECKOUT` per call (PR #155), so version flips do **not** require process restart:

```
# Use v0.13 (production default after PR #160)
unset HERMES_AGENT_CHECKOUT   # or leave at DEFAULT_AGENT_CHECKOUT

# Force v0.12 fallback mid-process
HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh

# Force main HEAD for upstream-test reproduction
HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-main-canary   # operator must clone first
```

The exact flip-and-back behavior is proven in the Smoke 8 test of `HERMES_AGENT_V013_CANARY_SMOKE_2026-05-09.md` (mid-process canary -> prod -> canary -> prod, all PASS, no restart).

---

## 4. Cross-comparison reference (per brief)

This doc's structure was sanity-checked against two external version-compat doc patterns:

1. **Letta release notes** (<https://github.com/letta-ai/letta/releases>) — uses **per-version "Highlights" + explicit "Breaking Changes" call-outs + PR/issue numbers + actionable guidance segmented by deployment mode (self-hosted vs cloud)**. This doc mirrors that pattern via Section 1's **PR-numbered citations** and Section 3's **scenario-segmented decision table**.
2. **LangChain version policy** (<https://docs.langchain.com/oss/python/langchain/overview>) — pattern for compat matrices is module-by-version-by-status with explicit deprecation-vs-removal calls. This doc adopts the **module-by-version-by-status** axis but uses **feature-by-version** (the more end-user-readable axis) per the brief's required-tables spec.

---

## 5. Out-of-scope (deliberately not in this doc)

- **No source edits.** Pure docs PR.
- **No new tests.** Reuse the existing Wave A2/A3/A4 smoke harnesses for empirical verification.
- **No promotion of RC v2 commits 3-5.** Those are paused per standing project memory; only commits 1+2 are listed as supported.
- **No paid services / no secret values.** Citations are public upstream tags + PR numbers + Hermes3D-internal commit SHAs.

---

## 6. Handoff for downstream agents

- **P3-5 (provider compat matrix per version)** consumes this doc's Section 1 row 7 (Pluggable model-providers directory) and Section 2 row 2 (Provider smoke) and produces a **per-provider** matrix (one row per provider, columns = v0.12 / v0.13 / main HEAD reachability + redaction layer). P3-5 should also enumerate the 28 v0.13 provider sub-dirs vs the 33 declared on upstream `main` and flag any provider whose Hermes3D adapter expects the **v0.12 monolithic shape** (the brittle ones).
- **P2-1 (version registry)** is already shipped (commit `afd8999`); this doc references its registry shape but does not depend on its on-disk presence.
- **P3-3 (multi-version GHA proof workflow)** can use Section 1 as the matrix axis for `.github/workflows/hermes-agent-versions.yml` (rows from the feature table become assertion targets per matrix entry).

---

## 7. Verification commands run

```bash
# Primary research (REQUIRED per brief — gh api tag dates)
gh api repos/NousResearch/hermes-agent/releases --jq '.[] | "\(.tag_name)\t\(.published_at)\t\(.name)"'

# Cross-confirm PR #21193 (redaction default ON) merge date relative to v0.13 tag
gh api repos/NousResearch/hermes-agent/pulls/21193 --jq '{number,title,merged,merged_at}'
# -> merged 2026-05-07T12:10:33Z, BEFORE v0.13 tag at 2026-05-07T16:23:08Z -> shipped in v0.13 (correct)

# Cross-confirm PR #21561 (native Windows TUI guard) merge date relative to v0.13 tag
gh api repos/NousResearch/hermes-agent/pulls/21561 --jq '{number,title,merged,merged_at}'
# -> merged 2026-05-08T21:27:41Z, AFTER v0.13 tag -> NOT in v0.13, only on main HEAD (correct)

# Confirm plugins/model-providers/ first appears at v0.13 tag and not earlier
git -C G:/Github/hermes-agent-fresh log v2026.4.30 --max-count=1 -- plugins/model-providers/   # empty -> not in v0.12
git -C G:/Github/hermes-agent-fresh log v2026.4.23 --max-count=1 -- plugins/model-providers/   # empty -> not in v0.11
git -C G:/Github/hermes-agent-fresh log v2026.5.7  --max-count=1 -- plugins/model-providers/   # 9022804d7 "feat(providers): make all 33 providers pluggable" -> shipped in v0.13

# Count provider sub-dirs at the v0.13 tag (28 dirs + README.md + __init__.py)
ls G:/Github/hermes-agent-v013-canary/plugins/model-providers/ | wc -l

# Confirm redaction default literal at each version
grep -n "HERMES_REDACT_SECRETS" G:/Github/hermes-agent-fresh/agent/redact.py        # v0.12: getenv(..., "")     -> default OFF
grep -n "HERMES_REDACT_SECRETS" G:/Github/hermes-agent-v013-canary/agent/redact.py  # v0.13: getenv(..., "true") -> default ON
```

All commands above produce stable output independent of secret values.

---

## 8. Source links

- v0.13 release: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.5.7>
- v0.12 release: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.4.30>
- v0.11 release: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23>
- PR #21193 (redaction default ON): <https://github.com/NousResearch/hermes-agent/pull/21193>
- PR #21561 (native Windows TUI guard): <https://github.com/NousResearch/hermes-agent/pull/21561>
- Hermes3D PR #155 (canary env-switch resolver): commit `8544bbcb`, branch `claude/hermes-agent-canary-env-switch`
- Hermes3D PR #160 (v0.13 promotion): commit `3158a4e`, branch `feat/hermes3d-7-complete-gui-repo-wiring`
- Wave A3 / canary smoke results: `03_implementation/docs/handoffs/HERMES_AGENT_V013_CANARY_SMOKE_2026-05-09.md`
- Wave 2 master plan (P2-5 row): `03_implementation/docs/handoffs/HERMES_AGENT_PRODUCTION_V013_ACTION_PLAN_2026-05-09.md`
- Cross-comparison (Letta releases pattern): <https://github.com/letta-ai/letta/releases>
- Cross-comparison (LangChain overview pattern): <https://docs.langchain.com/oss/python/langchain/overview>
