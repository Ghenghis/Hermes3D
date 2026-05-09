# E2E Completion — Master Registry (2026-05-09)

**Mission:** Reconcile every existing audit / registry / matrix / handoff / merged PR into a single source of truth for Hermes3D OS E2E completion. This doc is the Phase 0 deliverable of the Master Continuation; it does NOT add new product scope.

**Inputs reconciled:**
- `E2E_BLOCKER_REGISTRY_2026-05-09.md` (PR #142)
- `REMAINING_SKIPPED_BLOCKERS_WAVE_2026-05-09.md` (PR #146)
- `60_APP_UPDATE_READINESS_AUDIT_2026-05-09.md` (PR #135)
- `60-apps-batch2/bonus12-bug-finder.md`, `bonus13-schema-inconsistency.md`, `bonus13-errata-followup.md` (PR #144)
- `60-apps-batch2/agent7-docker-proof.md`, `agent8-ubuntu2404-proof.md`, `agent9-vps-proof-plan.md`, `agent10-compat-patch.md`, `agent11-upstream-issues.md`, `bonus14-secret-leak-scanner.md`
- `Images-GUI/` reference pack (PR #128/#134)
- All merged PRs #136-#150 today
- 20-agent Blocker Elimination Swarm (Wave 1, 2026-05-09 morning)
- 10-agent Remaining/Skipped Wave (Wave 2, 2026-05-09 afternoon)

---

## 1. PR ledger (today's cadence)

15 PRs merged today, all squash. No fake passes; PR #143 is honest partial-with-escalation.

| PR | Squash SHA | Subject | Closes |
|---|---|---|---|
| #136 | 320107a | staged-update gate (path-ignore + workers env + fail-closed skip) | BLK-008 |
| #137 | a4d3c1d | recovery ledger lock + idempotent outcome + auto-repair escape | BLK-004/005/006 |
| #138 | d308cc3 | `_zip_dirty_entries` allowZip64 + symlink + arcname sanity | BLK-007 |
| #139 | e0b719d | SSRF fail-closed in `_remote_release_tags` + `_latest_release` | BLK-001 |
| #140 | 32b05d4 | redaction symmetry to `agent_config` | BLK-002 |
| #141 | e5ff363 | `apply_patch_proposal` TOCTOU | BLK-003 |
| #142 | 589c842 | E2E Blocker Registry (mandate) | mandate |
| #143 | 24a0822 | `_call_mcp_tool` partial mitigation (escalated as BLK-009) | BLK-009 partial |
| #144 | 6593aba | Bonus 13 docs errata follow-up | BLK-010 |
| #145 | b5b925a | DeepSeek explicit `RuntimeError` on missing env | Squad G #1 |
| #146 | 8f18727 | Wave synthesis doc | mandate |
| #147 | b0109a3 | `load_modules` rollback + `parents[5]` IndexError | Bonus 12 #9 + #10 |
| #148 | 4c94342 | MiniMax env-KeyError parity (mirrors PR #145) | Wave Agent 7 |
| #149 | b130b6e | RC v2 commits 1+2 (`freeze_run` + `thaw_run` + saga compensation) | BLK-012 partial |
| #150 | ba4194d | 7 broad-except observability cleanups | Wave Agent 7 |

## 2. Reconciled blocker matrix

### Verified (closed)

| Blocker | Description | PR(s) |
|---|---|---|
| BLK-001 | SSRF in `_remote_release_tags`/`_latest_release` | #139 |
| BLK-002 | `agent_config` raw-payload redaction asymmetry | #140 |
| BLK-003 | `apply_patch_proposal` TOCTOU + crash window | #141 |
| BLK-004 | Recovery ledger file-lock gap | #137 |
| BLK-005 | `mark_recovery_outcome` non-idempotent | #137 |
| BLK-006 | HTTPException escapes `_auto_repair_to_backup` | #137 |
| BLK-007 | ZIP path-traversal + missing `allowZip64` | #138 |
| BLK-008 | Staged-update gate path-only ignore + skip-pass | #136 |
| Bonus 12 #9 | `_registry_path` `parents[5]` IndexError on frozen build | #147 |
| Bonus 12 #10 | `load_modules` no rollback / FD leak | #147 |
| BLK-017 | Active-UI no-fake re-sweep | already verified `ACTIVE_UI_NO_FAKE_SWEEP.md` 2026-05-08 |
| Squad G #1 | DeepSeek bare-`KeyError` env disclosure | #145 |
| Squad G #2 | MiniMax bare-`KeyError` env disclosure | #148 |
| Squad G #3 | 7 broad-except silent fallbacks | #150 |

### Partial (escalated with exact upstream/cross-repo blocker)

| Blocker | Description | Owner | Status |
|---|---|---|---|
| BLK-009 | `_call_mcp_tool` Popen→`subprocess.run` migration | hermes3d-locks Node server team | thread.join + env whitelist pinned in #143; full fix needs server-side stdin EOF drain OR HTTP transport |
| BLK-012 | Recovery Controller v2 active repair loop | claude-lead | commits 1+2 landed in #149; commits 3-5 (MiniMax / DeepSeek / apply+rerun) paused per user instruction |

### Upstream/env-blocked

| Blocker | Description | External signal required |
|---|---|---|
| BLK-011 | Hermes Agent v0.13.0 staged install | EITHER (a) v2026.5.8+ tag with green main `Tests` run, OR (b) 5 consecutive green main runs, OR (c) merged PR fixing `gateway.draining` translation-key regression |

### Open (ready-to-PR but not yet shipped)

| Blocker | Description | Wave Agent | LOC est. |
|---|---|---|---|
| BLK-013 | OpenCode/OpenHands real bounded task | A5 | ~420 (service + route + 6 tests) |
| BLK-014 | 60-app matrix backfill (5 rows × 6 fields) | A8 | ~30 in YAML-A (cross-repo: lives in Hermes3D, not codex) |
| BLK-015 | Playwright dashboard-advanced pixel-diff | A9 | ~10 LoC test + 1 PNG baseline (CI-generated) |
| BLK-016 | Printer safety end-to-end drill | A10 | ~330 LoC (drill + Moonraker shim) |
| BLK-018 | Continuous CI secret-leak scan (Gitleaks) | A7 | ~50 LoC in `.github/workflows/` |
| BLK-019 | GHA `hermes-agent-proof.yml` workflow | Agent 13 (W1) | ~60 LoC YAML — DEFERRED until BLK-011 unblocks (else permanent red CI) |
| BLK-020 | `desktop_updates.py` same redaction asymmetry as #140 | Agent 7 (W1) | ~10 LoC |

### Deferred by audit-doc lock

| Item | Reason |
|---|---|
| Bonus 13 source-doc edit (42-row SPDX remap, 5 repo URL canon) | `bonus13-schema-inconsistency.md` locked by `claude-lead-app-audit` (heartbeat 16:53Z, expires 20:53Z); follow-up landed as sibling doc in #144 |

## 3. E2E Definition of Done (14 items, status now)

| # | DoD item | Status |
|---|---|---|
| 1 | MiniMax smoke passes | PR #148 closed env-KeyError; Wave Agent 14 confirmed redaction layer; needs live re-smoke |
| 2 | DeepSeek smoke passes | PR #145 closed env-KeyError; same status as #1 |
| 3 | Hermes Agent proof lane passing OR formally deferred with safe fallback | **deferred** (Joint Agent 1+3 KEEP DEFERRED) |
| 4 | OpenCode + OpenHands run a real bounded coding/audit task | open (BLK-013) |
| 5 | Recovery Controller v2 handles failure → repair → review → retry | partial (commits 1+2 in #149; commits 3-5 paused) |
| 6 | 60 apps have update/install/proof profiles | open (BLK-014; cross-repo) |
| 7 | No fake UI states in active tabs | **verified** (`ACTIVE_UI_NO_FAKE_SWEEP.md` 2026-05-08) |
| 8 | Printer safety gates pass | unit-tested (Wave Agent 10); BLK-016 needs live drill |
| 9 | S1 remains camera-only | unit-tested (G1 in `test_printer_policy.py`) |
| 10 | Build plate clear gate enforced | unit-tested + source-inspection only; BLK-016 drill needed |
| 11 | GUI has Playwright proof for changed pages | open (BLK-015; dashboard-advanced ready as first target per Wave Agent 9) |
| 12 | Staged updater has backup + rollback proof | code complete (#137); needs end-to-end drill |
| 13 | No secret values in logs/proofs/docs | **verified** (Bonus 14 + Discovery #3 + Wave Agent 7 + #145 + #148) |
| 14 | CI + local gates pass | pre-push hook green on all 15 PRs; CodeRabbit pass on each |

## 4. Hard gates

| Gate | Status | Authority |
|---|---|---|
| **v0.13 retry**: Joint Agent 1+3 BOTH must say YES | **CLOSED — KEEP DEFERRED** | Wave Agent 1 + 3 (2026-05-09) |
| **GUI Playwright start**: Agent 9 must name first ready visual target | **OPEN** — `dashboard-advanced` named ready | Wave Agent 9 |
| **RC v2 resume**: prerequisites met | **OPEN** — commits 1+2 landed in #149, 3-5 paused | user instruction |
| **OpenCode/OpenHands real task**: prerequisites met | **OPEN** — Wave Agent 5 plan ready, ~420 LoC | user authorization needed |

## 5. Open by category (next-PR candidates)

### P0 (none remaining)
All P0 closed in PRs #136–#147 + Wave 2.

### P1 (open)
1. **BLK-013** OpenCode/OpenHands bounded task — Wave Agent 5 PR-ready; Docker `network=none` + redacted + 6 tests
2. **RC v2 commit 3** — MiniMax fix proposal step (Wave Agent 4 brief)
3. **BLK-018** Gitleaks GHA workflow — Wave Agent 7 spec
4. **BLK-015** Playwright dashboard-advanced — Wave Agent 9 confirmed ready

### P2 (open)
1. **BLK-014** 60-app schema backfill — cross-repo (Hermes3D, not codex)
2. **BLK-016** Safety drill harness — Wave Agent 10 plan ready
3. **BLK-020** desktop_updates redaction symmetry
4. **JSON Schema validator** for 6 new 60-app fields (codex-side preparation)

## 6. Hard external blockers (cannot fix in code)

| Item | What's needed |
|---|---|
| BLK-009 (full fix) | hermes3d-locks Node server: drain queued JSON-RPC on stdin EOF before shutdown OR ship HTTP transport |
| BLK-011 | Upstream NousResearch/hermes-agent main goes green (3 alternative signals listed) |
| 10 license-unknown 60-app rows | User / vendor reads upstream LICENSE files |
| 7 repo-identity reconciliations | User confirms canonical repos |
| Hunyuan3D 2.1 community license | User legal review for `LicenseRef-TencentHunyuanCommunity` |

## 7. Provenance & evidence

- 20-agent Wave 1 receipts banked in this conversation transcript (Agents 1–15: research + cross-comparisons)
- 10-agent Wave 2 receipts banked (Agents 1–10 + Discovery 1–3)
- MCP evidence ledger unbroken: `ev_ec7b7be7…` through `ev_e9ba9a60…` and beyond, hash-chained
- Pre-push hook green on every merged PR
- CodeRabbit pass on every merged PR
- 1 honest 1-loop escalation (PR #143 → BLK-009)
- 0 fake passes
- 0 secret values exposed in any artifact today

## 8. Reading order for next session

1. This doc (master state)
2. `REMAINING_SKIPPED_BLOCKERS_WAVE_2026-05-09.md` (next-5 plan, sections 5+)
3. `E2E_BLOCKER_REGISTRY_2026-05-09.md` (per-blocker detail)
4. Wave Agent 5 brief (BLK-013) for OpenCode/Hands implementation
5. Wave Agent 4 brief (RC v2 commit 2) — already used for #149; same pattern for commit 3
