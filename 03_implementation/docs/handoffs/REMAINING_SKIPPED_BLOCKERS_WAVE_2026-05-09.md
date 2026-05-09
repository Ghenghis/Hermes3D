# Remaining/Skipped Blockers Wave — Synthesis (2026-05-09)

**Provenance:** 10-agent Remaining/Skipped Blocker Wave (Pipelines 1-3, agents 1-10), all returned with research receipts. This synthesis is the mandated artifact that gates code-PR resumption.

**Companion docs (already merged):**
- `E2E_BLOCKER_REGISTRY_2026-05-09.md` (PR #142)
- `60_APP_UPDATE_READINESS_AUDIT_2026-05-09.md` (PR #135)
- `60-apps-batch2/bonus12-bug-finder.md`, `bonus13-schema-inconsistency.md`, `bonus13-errata-followup.md` (PR #144)

**PRs landed today:** #136, #137, #138, #139, #140, #141, #142, #143, #144, #145.

---

## 1. What remains blocked

| ID | Type | Detail |
|---|---|---|
| BLK-009 | server-contract / cross-repo | `_call_mcp_tool` Popen → `subprocess.run` migration. Reverted because hermes3d-locks Node server treats stdin EOF as client disconnect; full fix needs server-side drain-before-shutdown OR HTTP transport. PR #143 partial mitigation (thread.join + env whitelist pin) landed. |
| BLK-011 | upstream-blocked | Hermes Agent v0.13.0. Last 100 upstream `Tests` runs on `main`: 0 succeeded. PR #22567 (Windows pwd/fcntl skip-guards) closed-not-merged 2026-05-09. **Real upstream red is product regressions** (`gateway/test_restart_drain.py` translation-key, telegram TTS routing async-mock, `test_async_httpx_del_neuter`), NOT Windows guards. |
| BLK-016 | proof-blocker (NOT code blocker) | Printer/fleet/safety: 4 hard gates PRESENT + UNIT-TESTED; only the live E2E drill is missing. ZERO `TODO|FIXME|xfail|skipif` in `core/safety/**`. Drill plan ready (~250 LoC harness + ~80 LoC Moonraker shim). |

## 2. What was skipped/deferred

| Item | Reason |
|---|---|
| Bonus 12 #9 (`load_modules.py:_registry_path` `parents[5]` IndexError) | Not addressed by PRs #136-#145 — frozen-build edge path |
| Bonus 12 #10 (`load_modules.py:load_modules` no rollback on partial load) | Not addressed by PRs #136-#145 — connection FD leak on KeyError mid-loop |
| MiniMax `_minimax_api_key` bare `KeyError` (parity with PR #145 DeepSeek fix) | Found by Wave Agent 7 |
| 10 broad-except cleanup sites | Discovery audit + Wave Agent 7: silent fallbacks; mechanical 1-line `logger.warning("...: %s", exc)` inserts |
| BLK-018 continuous CI secret-leak scan | Bonus 14 NO_LEAKS at 2026-05-09 was manual; needs Gitleaks Action v8 |
| RC v2 commits 2-5 | Paused per user; Wave Agent 4 brief shows commit-2 ready (~140 LOC, 7 tests) |
| BLK-013 OpenCode/OpenHands real bounded task | Squad C plan + Wave Agent 5 plan ready; ~220 LoC service + ~20 LoC route + ~180 LoC tests |
| BLK-014 60-app matrix backfill | Wave Agent 8 first 5 rows ready (`prusaslicer`, `orcaslicer`, `blender`, `trimesh`, `manifold`) |
| BLK-015 Playwright dashboard pixel-diff | Wave Agent 9: ONE screenshot ready today (`dashboard-advanced`); other 4 blocked on `data-load-state` attr |
| BLK-019 GHA hermes-agent-proof workflow | Lane 3 in 6-lane proof; would be permanently red until BLK-011 resolves — defer |
| BLK-020 desktop_updates.py same redaction asymmetry as PR #140 | low-severity follow-up |

## 3. What can be fixed now (PR-buildable today)

In ascending risk order:

| # | PR | Files | LOC | Tests |
|---|---|---|---|---|
| 1 | **Bonus 12 #10** load_modules rollback | `db/load_modules.py` | ~10 | 1 regression (inject `sqlite3.IntegrityError` on iter 2) |
| 2 | **Bonus 12 #9** load_modules `parents[5]` IndexError | `db/load_modules.py` | ~5 | 1 regression (monkeypatch short Path) |
| 3 | **MiniMax KeyError parity** | `gateways/providers/minimax.py` | ~10 | 2 (probe + completion) |
| 4 | **10 broad-except cleanups** | 10 files (1 line each) | ~10 | none required (zero behavior change; pin pre-push) |
| 5 | **60-app first 5-row backfill** | `external_repos_registry.yaml` | ~30 (5 rows × 6 fields) | 1 (loader still parses 60 rows + field counts ≥5) |
| 6 | **RC v2 commit 2** (`freeze_run` + `thaw_run`) | `recovery_controller.py` | ~140 | 7 |
| 7 | **BLK-013 bounded task** | `code_history.py` + `code_operator.py` + new test | ~420 | 6 |
| 8 | **BLK-016 safety drill harness** | `04_testing/e2e/safety_e2e_drill.py` + Moonraker shim | ~330 | drill = 1 spec; pre-existing unit tests still pass |
| 9 | **BLK-015 dashboard-advanced Playwright** | extend `dashboard.spec.ts` + first-run baseline | ~10 LoC test + 1 PNG baseline | 1 |
| 10 | **BLK-018 Gitleaks GHA** | `.github/workflows/gitleaks.yml` + `.gitleaks.toml` allowlist | ~50 | n/a (CI-only) |

## 4. What needs upstream / env / user action

| Item | Owner | Trigger |
|---|---|---|
| BLK-009 full fix | hermes3d-locks Node server team | Drain queued JSON-RPC on stdin EOF before shutdown OR ship HTTP transport |
| BLK-011 v0.13 retry | NousResearch/hermes-agent maintainers | Any of: (a) v2026.5.8+ tag with green main run, (b) 5 consecutive green main runs, (c) merged PR fixing `gateway.draining` translation-key regression |
| ~10 license-unknown 60-app rows | user / vendor | Read upstream `LICENSE` files for `flsun_slicer`, `strec3d`, `kiln`, `awesome_extruders`, `comfyui_trellis_wrapper`, `botqueue`, `box_stl_generator`, `open_filament_database` |
| 7 repo-identity reconciliations | user | Confirm canonical repos (Kiln→codeofaxel, BoxTurtle→ArmoredTurtle, ERCF→EtteGit, Awesome Extruders→SartorialGrunt0, Repetier Firmware, FLSUN Slicer, blender_mcp_candidates) |
| Hunyuan3D 2.1 community license | user | Legal review for `LicenseRef-TencentHunyuanCommunity` + commercial-use threshold |
| Marlin tested_versions pin | user | Confirm `2.1.2.5` stable from rolling `latest-2.1.x` tag |
| First-run Playwright baseline | reviewer | Generate in CI, eyeball baseline PNG before merge (Storybook/Chromatic guidance) |

## 5. Next 5 PRs in exact order

Ordered by **safety-first** then **highest unblocking value**:

1. **PR #146 — Bonus 12 #10 load_modules rollback (P0)**
   - Files: `db/load_modules.py`, new test
   - Why first: only remaining P0 from Bonus 12 batch; mechanical edit; unblocks frozen-build packaging
2. **PR #147 — Bonus 12 #9 load_modules `parents[5]` IndexError (P1)**
   - Files: `db/load_modules.py`, new test
   - Why second: paired with PR #146 (same file); same review surface
3. **PR #148 — MiniMax KeyError parity + 10 broad-except cleanups (P1, batch)**
   - Files: `minimax.py`, 10 broad-except sites, gateways tests
   - Why third: closes parity gap with PR #145 + tightens silent-fallback observability; zero behavior change
4. **PR #149 — RC v2 commit 2 (`freeze_run` + `thaw_run`) (P1)**
   - Files: `recovery_controller.py` (additive), 1 new test file
   - Why fourth: unblocks RC v2 commits 3-5; uses PR #137 + #141 hardening; confirm-by-default + autonomous gate untouched
5. **PR #150 — 60-app first 5-row backfill (P1, data-only)**
   - Files: `external_repos_registry.yaml` (5 rows × 6 fields)
   - Why fifth: data-only, additive (loader parser at L161-180 accepts unknown keys); first concrete progress on BLK-014

After these 5: PR #151 (BLK-013 bounded task), PR #152 (BLK-016 safety drill harness), PR #153 (BLK-015 dashboard Playwright), PR #154 (BLK-018 Gitleaks).

## 6. Whether Hermes Agent v0.13 can be retried now

**NO — KEEP DEFERRED.** Joint Agent 1 + Agent 3 verdict.

Required signals before retry (all 3 must hold):
- Lane 3 GHA workflow `hermes-agent-proof.yml` has shipped + has run green at least once on a real upstream tag
- Either v2026.5.8+ tag exists OR 5 consecutive green `main` runs OR merged PR fixing `gateway.draining` translation-key regression
- Then re-poll Agents 1+3 for fresh joint gate

**Until Lane 3 produces a single green run, the verdict remains KEEP DEFERRED.** Lane 1 (Windows host) cannot certify v0.13 by construction (10 systemd + 4 audio + 4 process-isolation tests deterministically fail on WSL2 kernel; not lifted by `--ignore=tests/integration --ignore=tests/e2e`).

**Critical insight from Agent 2:** NO Hermes3D feature is currently broken by being on v0.12. Hermes3D has parallel local implementations (`retry_controller.py`, `gateways/redaction.py`, `gateways/providers/{deepseek,minimax}.py`, pure-stdlib `agent_runtime.py`). The v0.13 lift is forward-investment, not blocker-clearance.

## 7. Whether RC v2 can resume now

**YES.** All preconditions met:
- RC v1 ledger correctness restored (PR #137: file lock + idempotent outcome)
- `apply_patch_proposal` hardening (PR #141: hash-before-replace + fsync + inflight DB record) — RC v2 commit 5's apply step inherits this
- Agent 2 confirmed RC v2 does NOT depend on v0.13 (uses Hermes3D-local primitives)
- Agent 4 brief: commit 2 is ~140 LOC additive, 7 tests, no edits to `code_history.py`, confirm-by-default + autonomous gate preserved

Recommended sequencing: **commit 2 → 3 → 4 → 5** as 4 sequential PRs (not bundled). Each commit ≤3 files per Squad B plan.

## 8. Whether OpenCode/OpenHands real task proof can start now

**YES, with sandbox hardening Wave Agent 5 specified.** All preconditions met:
- Docker 29.4.1 reachable (Agent 11 confirmed earlier)
- Both runners detected per A3 audit
- `_redacted_env_export` + `private_env()` boundary established (Agent 14 confirmed)
- Docker invocation: `--network=none --read-only --tmpfs /tmp:size=64m,noexec,nosuid --memory=512m --cpus=1 --pids-limit=128 --cap-drop=ALL --security-opt=no-new-privileges -v PROJECT_ROOT:/workspace:ro`
- `G:/private/`, `.git`, `node_modules`, `proof|var` NEVER mounted
- Stderr returned to client as **sha256 only**, never raw
- Stdout: `redact_text(stdout)[:200]` excerpt; full sha256 in evidence
- 6 tests cover: sandbox not ready, runner not detected, happy path, timeout+reap, network=none argv invariant, G:/private not mounted

Recommended scope: ship as **PR #151** (after the 5 above) since it's a >1-day code lane; depends on RC v2 commit 2 being uncontroversially merged first.

---

## Decision points (orchestrator gates)

| Gate | Status | Authority |
|---|---|---|
| v0.13 retry | **CLOSED** (Agent 1 + Agent 3 both NO) | Joint Agent 1+3 verdict |
| RC v2 resume | **OPEN** (Agent 2 + Agent 4 both YES) | User authorization to proceed with commit 2 |
| GUI Playwright start | **OPEN — single screenshot only** (Agent 9 says dashboard-advanced ready) | User authorization to ship dashboard.spec.ts extension |
| Code PR freeze | **LIFT after this synthesis lands** | User mandate |

## Provenance

All 10 wave agents produced 2+ research receipts (1 primary + 1 cross-comparison) per user mandate. Cross-comparisons spanned: OpenHands CI (`py-tests.yml`), Letta (`0.16.7`), CrewAI (`1.14.4`), Temporal saga pattern, OpenAI/Anthropic SDK auth redaction, Klipper G-Codes + RepRap M112 spec, Homebrew Cask `prusaslicer`, Storybook/Chromatic baseline workflow, Codecov 2021 post-mortem.

No fake passes. No broad skips. No secret values exposed. Two agents (1, 6) reported "no new evidence vs prior swarm" honestly and stopped per the 2-loop escalation rule.
