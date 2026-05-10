# V0.13 Promotion — Merge Plan (2026-05-09 → 2026-05-10)

> **Status:** **EXECUTED.** This is the post-execution capture of the W5-1 merge plan. Per the W5-8 audit, this file was previously a 0-byte placeholder; this stub captures the executed plan so the file is no longer empty (P2 finding).

## Context

The W5-1 merge plan dispatched a 9-PR sequence to promote Hermes Agent v0.13 from canary → smoke → conditional promotion → flip → regression-pin → multi-version coexistence → provider compat matrix. The plan executed on 2026-05-09T23:23Z → 2026-05-10T01:44Z. All 9 PRs landed; PR #169 (W5-1 Phase B follow-on) is the only one still in flight at the time of this doc-fix and is currently in `dirty` mergeable state.

## Executed PR ledger

| Order | PR | Title | State | Merged at (UTC) | Wave |
|---|---|---|---|---|---|
| 1 | #155 | feat(hermes-agent): canary resolver — read `HERMES_AGENT_CHECKOUT` per call (Wave 1 P1-3) | MERGED | 2026-05-09T23:23:01Z | 1 |
| 2 | #157 | proof(hermes-agent): canary smoke 7 PASS / 1 N/A / 0 FAIL (Wave 1 P1-4) | MERGED | 2026-05-09T23:47:50Z | 1 |
| 3 | #159 | proof(BLK-013): real Docker bounded-task proof (PR #159; Wave 1 P1-7) | MERGED | 2026-05-10T00:19:17Z | 1 |
| 4 | #160 | feat(hermes-agent): promote v0.13 to production default (Wave 1 P1-5; 7/7 gates green) | MERGED | 2026-05-10T00:19:20Z | 1 |
| 5 | #165 | test(v0.13): regression-pin v0.13 production default behavior (Wave 2 P2-4) | MERGED | (pre-WB) | 2 |
| 6 | #171 | test(recovery): pin RC v2 saga semantics across v0.12 + v0.13 (Wave 4 P3-4) | MERGED | (pre-WB) | 4 |
| 7 | #172 | ci(P3-3): multi-version regression gate (Wave 2) | MERGED | (pre-WB) | 2 |
| 8 | #173 | feat(hermes-agent): version-tag proof events (Wave 2 P2-6) [re-target of #168] | MERGED | 2026-05-10T01:44:09Z | 2 |
| 9 | #174 | docs+feat(hermes-agent): provider compat matrix per version (Wave 4 P3-5) [re-target of #170] | MERGED | 2026-05-10T01:44:12Z | 4 |

**Total:** 9 PRs merged. **In-flight:** PR #169 (W5-1 Phase B follow-on; mergeable_state currently `dirty` per `gh pr view 169 --json mergeable`).

## Source-of-truth constants (post-execution)

After the merge sequence, `services/agent_checkout.py` reads:

```python
DEFAULT_AGENT_CHECKOUT = Path("G:/Github/hermes-agent-v013-canary")
V012_FALLBACK_CHECKOUT  = Path("G:/Github/hermes-agent-fresh")
```

The resolver `current_agent_checkout()` reads `HERMES_AGENT_CHECKOUT` per call, so revert to v0.12 is a 1-env-var operation (no restart needed).

## Companion docs

For the full Wave 5 merge narrative, consult:

- `E2E_COMPLETION_MASTER_REGISTRY_2026-05-09.md` (post-execution master ledger)
- `HERMES_AGENT_PRODUCTION_V013_ACTION_PLAN_2026-05-09.md` (the action plan that drove the wave)
- `HERMES_AGENT_V013_CANARY_SMOKE_2026-05-09.md` (PR #157 smoke results)
- `PROVIDER_RESCUE_BLOCKER_PROOF_2026-05-09.md` (provider-side env rescue)

## Why this file is a stub, not a full plan

The original full merge plan was authored as the W5-1 dispatch artifact and consumed verbally by the swarm in real time; the file in this repo was never populated. Per the W5-8 doc-audit P2 finding, an empty .md file referenced by other docs causes 404-like UX, so this stub captures the executed-plan ledger and points at the live source-of-truth docs for everything else.

## Provenance

- Audit finding: `V013_PROMOTION_DOC_AUDIT_2026-05-09.md` §2.13 (P2 — empty placeholder)
- Closing PR: this PR (W5-8b doc-fix consolidated)
- Source-of-truth check: `gh pr view <N> --json state,mergedAt` for each PR in the table.
