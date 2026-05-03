# Project Completion Roadmap — pre-written briefs queue

> **Purpose:** Forward-look at the next 8-15 checkpoints across both Hermes3D and HermesProof. The 4 overnight-priority briefs have full specs (linked below). The rest are one-paragraph stubs marked `[NEEDS-FULL-BRIEF]` — they can't be picked up until expanded.
>
> **For Codex's overnight loop:** ONLY pick tasks marked `READY` in the table below. Skip anything `[NEEDS-FULL-BRIEF]`.

---

## Status legend

- ✅ **MERGED** — landed on develop or main, closed
- 🟢 **READY** — full brief exists, Codex can claim and ship
- 🟡 **STUB** — paragraph-level description; needs architect expansion before claim
- 🔵 **DEFERRED** — explicitly post-v6 or post-v5.3 release; don't touch

---

## Hermes3D-OS

| ID | Title | Status | Brief |
|---|---|---|---|
| H3D-CP5.1-A | Phase 5.1 plan + ADR-013 | ✅ | merged |
| H3D-CP5.1-B | failure_predictor + backup scheduler | ✅ | merged |
| H3D-CP5.1-C | profile_generator + skill_store + doctor JSON | ✅ | merged |
| H3D-CP5.1-D | Gradio smoke + matrix coverage gate | ✅ | merged |
| H3D-CP5.1-E | Phase 5.1 completion report + proof bundle | ✅ | merged |
| H3D-WINREL-MVP | Windows release MVP (PyInstaller + Velopack) | ✅ | merged |
| H3D-VPS-DEPLOY | Hostinger VPS deploy bundle | ✅ | merged |
| H3D-LOCAL-BACKUP | Syncthing + Restic-B2 scripts | ✅ | merged |
| H3D-MARKETING-V1 | Marketing site v1 (4 SVGs + landing) | ✅ | merged |
| H3D-SOTA-MARKETING-V2 | Codex's design-led SOTA marketing upgrade | 🟢 | `HANDOFF_TO_CODEX_SOTA_MARKETING_V2.md` |
| H3D-BLENDER-AUDIT | Audit `rakaarwaky/blender-mcp-native` (research only ADR) | 🟢 | `HANDOFF_TO_CODEX_BLENDER_MCP_AUDIT.md` |
| CP-HERMESPROOF-0.6 | Secret + Quality + Test gate pack (HermesProof repo) | 🟢 | `HANDOFF_TO_CODEX_HERMESPROOF_0.6_GATE_PACK.md` |
| ~~H3D-LOCAL-INTELLIGENCE~~ | ~~mega-task superseded after audit FAIL~~ | 🚫 | SUPERSEDED — see splits below |
| H3D-LOCAL-LM-STUDIO | Task 4a — LM Studio default + Ollama fallback + Hipfire optional | 🟢 | `HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md` |
| H3D-MNEMOSYNE-RECALL | Task 4b — `mnemosyne-memory` recall layer (NOT canonical) | 🟢 | `HANDOFF_TO_CODEX_HERMES3D_MNEMOSYNE_RECALL.md` |
| H3D-SERVICE-HEALTH | Task 4c — in-house port probe + new top-level `/health` route | 🟢 | `HANDOFF_TO_CODEX_HERMES3D_SERVICE_HEALTH.md` |
| H3D-HERMES-AGENT-PORT-PATTERNS | Port 3 patterns from `NousResearch/hermes-agent` v0.12.0: registry, injection-defense scanner, delegate isolation | 🟡 | [NEEDS-FULL-BRIEF — research agent flagged: Hermes Agent is ACTIVE not stale; 130k stars, last push 2026-05-03; MIT licensed; ADOPT-SELECTIVELY verdict] |
| H3D-SETTINGS-TAB-FULL | Implement React Settings tab fully (provider config form, env-var management UI, validation) | 🟡 | [NEEDS-FULL-BRIEF — architect to write] |
| H3D-SCREENSHOT-CAPTURE | Playwright-driven 22-shot capture pass + commit to `site/screenshots/` | 🟡 | [NEEDS-FULL-BRIEF — depends on launcher running locally] |
| H3D-VHS-DEMO | Author + render `site/demos/quickstart.tape` to GIF + MP4 | 🟡 | [NEEDS-FULL-BRIEF — depends on CLI being demoable] |
| H3D-RELEASE-V5.3.0 | Cut release/v5.3.0 → main → tag → gh release create | 🔵 | DEFERRED — user must authorize release cut |
| H3D-WINREL-SIGN | Phase 5B — Azure Artifact Signing + winget manifest | 🟡 | [NEEDS-FULL-BRIEF — pending user signing up for Azure Artifact Signing $9.99/mo] |
| H3D-DOCS-CONSOLIDATION | Move dev-internal README content to CONTRIBUTING.md + tighten AGENTS.md | 🟡 | [NEEDS-FULL-BRIEF] |
| H3D-HIPFIRE-OPTIONAL | Wire `rakaarwaky/hipfire` AMD provider (gated on env var) | 🟡 | [NEEDS-FULL-BRIEF — only meaningful if user spins up an AMD inference node] |
| H3D-ANYTYPE-OPTIONAL | Anytype docs / knowledge graph integration | 🔵 | DEFERRED — post-v6 |

---

## HermesProof

| ID | Title | Status | Brief |
|---|---|---|---|
| HP-0.4 | Trigger bridge (4 event tools, hash-chained ledger) | ✅ | merged |
| HP-0.4.1 | Perf + robustness (streaming evidence, lazy events, webhook timeout) | ✅ | merged (PR #14) |
| HP-0.5.0 | Task queue (4 new tools, 14 → 17 truth gates) | ✅ | merged (PR #15) |
| HP-WIZARD | Universal setup wizard (6-client interactive CLI) | ✅ | merged (PR #16) |
| HP-SITE-V1 | Marketing site (HermesProof's own GH Pages) | ✅ | merged (PRs #12, #17) |
| HP-V0.5.0-RELEASE | GitHub release v0.5.0 published | ✅ | https://github.com/Ghenghis/HermesProof/releases/tag/v0.5.0 |
| HP-0.5.1-PERF | Gemini's 4 deferred items (init-once guard, O(1) heartbeat-by-id, parallel readTasks, per-task error handling in recoverStaleTasks) | 🟡 | [NEEDS-FULL-BRIEF — small, can be written quickly] |
| CP-HERMESPROOF-0.6 | Secret + Quality + Test gate pack (cross-listed; lives in HermesProof repo) | 🟢 | `HANDOFF_TO_CODEX_HERMESPROOF_0.6_GATE_PACK.md` |
| HP-0.7-MNEMOSYNE-RECALL | Use Mnemosyne for HermesProof's own conflict-pattern recall (optional, debatable) | 🔵 | DEFERRED — not strictly needed; HermesProof has its own evidence ledger |
| HP-DOCS-V05-AUDIT | Audit existing v0.5.0 release notes for accuracy after a few weeks of usage | 🟡 | [NEEDS-FULL-BRIEF — wait until users have hit any v0.5 quirks first] |

---

## Tonight's overnight queue (priority order)

Codex picks these in order:

1. **🟢 H3D-SOTA-MARKETING-V2** — `HANDOFF_TO_CODEX_SOTA_MARKETING_V2.md` (already on develop pre-overnight)
2. **🟢 H3D-BLENDER-AUDIT** — `HANDOFF_TO_CODEX_BLENDER_MCP_AUDIT.md`
3. **🟢 CP-HERMESPROOF-0.6** — `HANDOFF_TO_CODEX_HERMESPROOF_0.6_GATE_PACK.md` (in HermesProof repo)
4. **🟢 H3D-LOCAL-LM-STUDIO** (4a) — `HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md`
5. **🟢 H3D-MNEMOSYNE-RECALL** (4b) — `HANDOFF_TO_CODEX_HERMES3D_MNEMOSYNE_RECALL.md`
6. **🟢 H3D-SERVICE-HEALTH** (4c) — `HANDOFF_TO_CODEX_HERMES3D_SERVICE_HEALTH.md`

If all 6 ship cleanly + circuit breaker is happy, claim **HP-0.5.1-PERF** as a stretch goal. The brief is a stub (no full spec) but the 4 perf items are well-documented in PR #15's review comments — Codex can write the implementation directly from there if they're confident, otherwise treat as `[NEEDS-FULL-BRIEF]` and skip.

**Audit posture (overnight):**
- Round 1 (Claude's audit agents): COMPLETE — caught 16 critical issues across 4 briefs (master, BLENDER, v0.6, LOCAL-INTELLIGENCE). All fixed in this PR; LOCAL-INTELLIGENCE split into 4a/4b/4c.
- Round 2 (Claude's audit agents on the FIXED briefs + 3 NEW splits): pending.
- Round 3 (Codex's own audit pass): pending — Codex must verify each brief before claiming.
- Round 4 (overnight execution): only after rounds 1-3 PASS.

---

## Where the markdowns live

All overnight-queue briefs are at:

```
G:\Github\Hermes3D\handoffs\
  HANDOFF_TO_CODEX_OVERNIGHT_AUTOPILOT.md           ← master loop protocol (start here)
  HANDOFF_TO_CODEX_SOTA_MARKETING_V2.md             ← B5 / Task 1 (already on develop pre-overnight)
  HANDOFF_TO_CODEX_BLENDER_MCP_AUDIT.md             ← Task 2
  HANDOFF_TO_CODEX_HERMESPROOF_0.6_GATE_PACK.md     ← Task 3 (HermesProof repo, not Hermes3D)
  HANDOFF_TO_CODEX_HERMES3D_LOCAL_INTELLIGENCE.md   ← Task 4
  PROJECT_COMPLETION_ROADMAP.md                      ← this file (forward-look)
```

The HermesProof v0.6 task is implemented in a different repo
(`G:\Github\hermes3d-mcp-lock-orchestrator`), but the BRIEF lives here
(in Hermes3D's handoffs/) for queue discoverability. Codex needs to `cd` to
the HermesProof repo to actually do the work for that one task.

---

## Morning report convention

When the loop stops, Codex writes:

```
G:\Github\Hermes3D\handoffs\HANDOFF_TO_CLAUDE_OVERNIGHT_COMPLETE.md
```

Including: summary table, what's open for review, what blocked, surprises, recommended next steps. Then commits to `docs/overnight-results-<utc>` and opens a PR (which itself does NOT auto-merge).
