# Hermes Agent v0.13.0 — Lane C+ (Py3.11 Docker) Formal Defer (2026-05-09)

> **Status:** **SUPERSEDED 2026-05-10 by PR #160** — v0.13 is production default. This stub doc exists to close a broken local-relative link from `60_APP_UPDATE_READINESS_AUDIT_2026-05-09.md:L3`. The full formal-defer record lives in the orchestrator repo (a different repo from this GUI-wiring repo).

## What this stub is

This doc was referenced by `60_APP_UPDATE_READINESS_AUDIT_2026-05-09.md:L3` but never landed in this repo because the formal-defer record was authored in the **orchestrator repo** (a separate repo). The W5-8 audit (2026-05-09) flagged the broken local link as a P1 finding. The W5-8b doc-fix PR closes that link by:

1. updating `60_APP_UPDATE_READINESS_AUDIT_2026-05-09.md` to point at the orchestrator-repo URL, AND
2. creating this stub for any reader who lands here from a cached link.

## Where to find the canonical record

- Orchestrator repo: <https://github.com/Ghenghis/hermes3d-mcp-lock-orchestrator>
- Canonical formal-defer doc: <https://github.com/Ghenghis/hermes3d-mcp-lock-orchestrator/blob/main/docs/orchestrator/cplus_py311_formal_defer_2026-05-09.md>
- Closing commit on orchestrator main: `046eaef` (`docs(C-plus-py311+docker): formal defer of v0.13.0 update lane`)

## Why the formal defer was lifted

PR #160 in this repo (merged 2026-05-10T00:19:20Z, squash `3158a4e152350eefd8805015420ed5007629fb04`) promoted Hermes Agent v0.13 to the production default. The post-promotion source-of-truth constants now read:

| Constant | Value (post-promotion) | Source |
|---|---|---|
| `DEFAULT_AGENT_CHECKOUT` | `Path("G:/Github/hermes-agent-v013-canary")` | `services/agent_checkout.py:L31` |
| `V012_FALLBACK_CHECKOUT` | `Path("G:/Github/hermes-agent-fresh")` | `services/agent_checkout.py:L27` |
| Current upstream tag | `v2026.5.7` | canary checkout HEAD |
| Fallback upstream tag | `v2026.4.30` | `hermes-agent-fresh` HEAD |

To revert to v0.12 at runtime (no restart needed), set `HERMES_AGENT_CHECKOUT=G:/Github/hermes-agent-fresh`. The resolver reads this env var per-call.

## Pre-promotion lane summary (preserved)

The pre-promotion blockers tracked in lanes A / B / C+:

- **Lane A (Win `pwd` import):** addressed by upstream tag bump path; no longer relevant after promotion.
- **Lane B (50 stale tests upstream removed in `66320de52`):** the 50 tests were removed upstream after the prior tag was cut; canary lane validated the post-removal main.
- **Lane C+ (Cplus Docker, Py3.11): 20 residuals** — 10 systemd-DBus / 4 audio / 4 process / 2 transient. The `_auto_repair_to_backup` pathway was proven 4× across lanes A / B / C+ during the canary phase (PR #155 / PR #157).

## Next steps

- The cold-start race documented as **BLK-021** in `E2E_BLOCKER_REGISTRY_2026-05-09.md` is the only post-promotion residual flagged so far.
- A future fresh-formal-defer would only be opened if a v0.13.x patch tag re-introduces a regression that cannot be auto-repaired; in that case, a new dated doc supersedes this stub.

## Provenance

- Audit finding: `V013_PROMOTION_DOC_AUDIT_2026-05-09.md` §2.5 (P1 — broken local link)
- Closing PR: this PR (W5-8b doc-fix consolidated)
- Source-of-truth check: `services/agent_checkout.py` constants verified line-by-line.
