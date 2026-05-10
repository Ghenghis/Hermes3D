# STREAM/STATE.md — Live snapshot

> Updated by either side anytime material state changes. Both sides treat
> this as the **fast path** to current reality (faster than re-running gh + hermes_get_state every cycle).

---

## Last update

- **UTC:** 2026-05-03T11:30:00Z
- **By role:** SCRIBE (Claude-side, agent-driver)
- **Reason:** Initial bootstrap of STREAM/ protocol

---

## Active correlations (open + acknowledged)

| Correlation | Type | Status | Owner | Aged |
|---|---|---|---|---|
| boot-stream-v1 | STATE_UPDATE | open | SCRIBE | 0min |

---

## Open PRs — Hermes3D

| PR | Title | Branch | CI | Awaiting |
|---|---|---|---|---|
| #34 | feat(memory): Mnemosyne recall layer (recovered) | feat/cp-h3d-mnemosyne-recall-recovered | Layer A FAIL (I001), Layer M FAIL (cascade) | BUILDER fix push |
| #35 | feat(ui): Settings tab (4 subtabs) | feat/cp-h3d-settings-tab-recovered | ALL GREEN ✅ | architect merge |
| #37 | [partial] scaffolds (registry+security+health) | feat/cp-h3d-partial-scaffolds | Layer A FAIL (format), D2 FAIL, M FAIL (cascade) | BUILDER fix push |
| #38 | docs(handoff): overnight audit summary | codex/overnight-complete-handoff | 9/13 green, D/D3/T in progress | CI completion |
| #33 | docs(release): draft v5.3.0 release notes | codex/release-notes-v5.3.0-draft | (last seen green per Codex LGTM) | architect merge |

---

## Open PRs — HermesProof

None at this snapshot. v0.5.0 + v0.6 hardening shipped (PRs #18, #19 merged).

---

## Locks held (HermesProof state)

- Last `hermes_doctor`: ok=true (per Codex's most recent report)
- Active locks: 0 codex-impl-* locks held (per Codex morning summary)
- Active tasks: PR #38 lock pending Codex's audit completion + LGTM
- Evidence ledger length: see `gh api .../evidence` or `hermes_verify_evidence`

---

## Queue depth

- **GATE_GAP_QUEUE.md:** unclaimed = 18 (P0:6, P1:8, P2:4)
- **ENHANCEMENT_QUEUE.md:** unclaimed = 9

---

## Health / circuit breakers

- Codex 3-strike circuit: 0/3 (clean)
- Claude agent collisions tonight: 1 (recovered into PR #34/#35/#36/#37)
- MCP disconnect events tonight: 1 (mid-session). Current control rule:
  `gh`/`git` fallback is read-only status only; writes, commits, pushes,
  merges, installs, updates, and printer actions stay blocked until MCP
  reconnects with exact-worktree locks.
- Last user touchpoint: ~04:25Z — explicit YOLO authorization for overnight loop

---

## What's running right now

- **Claude:** building STREAM/ protocol; about to spawn parallel agents on missing gates + unfinished work
- **Codex:** auditing PR #38 (Gibbs + Mendel agents); awaiting CI completion to LGTM + release lock

---

## Tonight's headline targets (in priority order)

1. Drain GATE_GAP_QUEUE P0 items (6) — license, SBOM, dep-fresh, workflow-pinning, accessibility-WCAG-AA, mcp-scan-static
2. Complete Service Health page integration (PR #37 partial → finish ServiceCard + endpoint wiring)
3. Implement LM Studio provider (Task 4a — never opened a PR)
4. Land HermesProof v0.5.1 perf companion
5. Implement Hermes Agent injection scanner full port (Task #37 stub → real)
6. Add 3D-printing stability/perf gates (the 80% gap user flagged) — needs research pass first
