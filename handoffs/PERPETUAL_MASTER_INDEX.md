# PERPETUAL MASTER INDEX — total completion plan, both projects

> **Status:** ACTIVE until total completion of both Hermes3D-OS and HermesProof.
> **Authorized by user:** 2026-05-03. No exit until both projects are
> release-ready for daily use. No skipping, no bypass, no AI slop. All
> tasks complete or explicitly DEFERRED with documented reason.
>
> **Audience:** Both Claude (architect+builder) and Codex (builder+critic),
> plus any other client (KiloCode, Cursor, Windsurf, VSCode+Copilot) that
> joins via STREAM/.

---

## How to use this file

1. Read it top-to-bottom on first cycle (one time, cache it).
2. Every 3-5 minutes, re-read **§ Live status** + **§ Open PRs** to see what changed.
3. Pick the **highest-priority unclaimed item** from § Remaining work and start.
4. Post `TASK_CLAIMED` to `handoffs/STREAM/CODEX_INBOX.md` (or `CLAUDE_INBOX.md` if you want the other side to see).
5. When done, post `FIX_PUSHED` or `GATE_LANDED` and pick the next.
6. **There is no exit condition.** When the queue is empty, idle-poll continues. The user wakes up and says "stop" or merges everything.

---

## All handoff files by path (read these on first cycle)

```
Hermes3D repo (G:\Github\Hermes3D\handoffs\):
  PERPETUAL_MASTER_INDEX.md                            ← this file
  HANDOFF_TO_CODEX_OVERNIGHT_AUTOPILOT.md              ← original master (§3 stop condition REPLACED)
  HANDOFF_TO_CODEX_PERPETUAL_WAKEUP.md                 ← supersedes §3 of autopilot
  HANDOFF_TO_CODEX_RESUME_NOW.md                       ← paste-ready resume prompt
  HANDOFF_TO_CODEX_BLENDER_MCP_AUDIT.md                ← merged (ADR-014)
  HANDOFF_TO_CODEX_HERMESPROOF_0.6_GATE_PACK.md        ← v0.6 gate pack (in progress across multiple PRs)
  HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md         ← shipped (PR #40)
  HANDOFF_TO_CODEX_HERMES3D_MNEMOSYNE_RECALL.md        ← shipped (PR #34)
  HANDOFF_TO_CODEX_HERMES3D_SERVICE_HEALTH.md          ← shipped (PR #42)
  HANDOFF_TO_CODEX_SOTA_MARKETING_V2.md                ← shipped (PR #36 merged)
  HANDOFF_TO_CLAUDE_OVERNIGHT_COMPLETE.md              ← Codex's morning report (PR #38)
  HERMES_AGENT_ENABLE.md                                ← Hermes Agent activation guide (PR #44)
  PROJECT_COMPLETION_ROADMAP.md                        ← forward-look table
  STREAM/PROTOCOL.md                                   ← message format + polling cadence
  STREAM/STATE.md                                      ← live snapshot
  STREAM/CLAUDE_INBOX.md                               ← messages for Claude
  STREAM/CODEX_INBOX.md                                ← messages for Codex
  STREAM/LEDGER.md                                     ← append-only audit
  STREAM/GATE_GAP_QUEUE.md                             ← unclaimed gates
  STREAM/ENHANCEMENT_QUEUE.md                          ← unclaimed enhancements
  STREAM/WATCHDOG.md                                   ← stuck/idle detection spec
  STREAM/CLIENT_ADAPTERS.md                            ← per-client setup

HermesProof repo (G:\Github\hermes3d-mcp-lock-orchestrator\handoffs\):
  STREAM/PROTOCOL.md                                   ← mirror of Hermes3D PROTOCOL
  STREAM/STATE.md                                      ← HermesProof side snapshot
  STREAM/CLAUDE_INBOX.md / CODEX_INBOX.md / LEDGER.md
  STREAM/GATE_GAP_QUEUE.md / ENHANCEMENT_QUEUE.md
```

---

## Live status (snapshot 2026-05-03 ~13:00Z; refresh from STREAM/STATE.md)

**Open PRs across both repos: 24 total**

### HermesProof (13 open)
| PR | Title | CI | Notes |
|---|---|---|---|
| #20 | feat(v0.6): anonymous role rotation + Hermes Agent USER bridge | green | Codex flagged auth issue — see § Audit findings |
| #21 | feat(gate): licenses.scan | green | mergeable |
| #22 | feat(0.5.1): perf companion | green | mergeable |
| #23 | feat(gate): dependency.fresh | green | mergeable |
| #24 | feat(gate): sbom.cyclonedx_generated | green | mergeable |
| #25 | feat(gate): workflow-pinning | green | mergeable |
| #26 | ci: mechanical-review reruns on edits | Codex fixing | almost green |
| #27 | feat(gate): mcp-scan-static | green | mergeable |
| #28 | ci: STREAM watchdog cron | Codex fixing | hardening commit pushed |
| #29 | feat(gate): accessibility-wcag-aa | green | mergeable |
| #30 | feat(gates): perf-budget + docs + release + coderabbit-review | retriggered | mergeable on rerun |
| #31 | feat(0.6): secret-rotation-evidence-gate | Codex fixing body | mech-review pending |
| #32 | feat(gates): provider-registry + 7 truth gates | Codex fixing body | mech-review pending |

### Hermes3D (11 open)
| PR | Title | CI | Notes |
|---|---|---|---|
| #34 | feat(memory): Mnemosyne recall layer | green | mergeable |
| #35 | feat(ui): Settings tab (4 subtabs) | green | mergeable |
| #37 | [partial] scaffolds | red | superseded by #42 — close on merge |
| #38 | docs(handoff): overnight audit summary | green | mergeable |
| #39 | docs(handoff): STREAM/ + perpetual wakeup | green | mergeable |
| #40 | feat(llm): LM Studio + Ollama + Hipfire | green | mergeable |
| #41 | feat(security): in-house OWASP LLM-01 scanner | green | Codex flagged scanner gaps — see § Audit findings |
| #42 | feat(ui): Service Health page + probe | green | Codex flagged health semantics — see § Audit findings |
| #43 | feat(safety): 4 P1 3D-printing safety gates | retriggered | check status |
| #44 | docs(handoff): mirror HERMES_AGENT_ENABLE.md | green | mergeable |
| #45 | docs(readme): sync sprint copy to v5.3.0 RC | unverified | check status |

---

## Audit findings (Codex's CRITIC verdicts — fix BEFORE merge)

### PR #20 (HermesProof v0.6 — Hermes Agent bridge)
- **Auth surface issue** (Codex flagged as fail-worthy). Need to identify exact concern: likely the `granted_by` enum allowing `ci` without further capability scoping, or the bridge auto-granting AS_USER from `hermes-agent` without an explicit human-issued bootstrap signature.
- **Action:** read Codex's PR review comments verbatim; address each point with a code commit; do not merge until Codex re-reviews and posts LGTM.

### PR #41 (Hermes3D in-house injection scanner)
- **Scanner miss / false-positive gaps**: raw G-code temperature misses (e.g. `M104 S500` not caught as a thermal-runaway injection vector); curated_inhouse.yaml needs additional patterns.
- **Action:** extend `patterns/curated_inhouse.yaml` with M104/M109 over-temperature, M140 over-bed-temp, thermistor disable patterns; add 5+ tests; push fix.

### PR #42 (Hermes3D Service Health)
- **Health semantics issues**: probe might be reporting healthy when the printer responds but with a stale or error response body. Need a stricter readiness check beyond TCP connect.
- **Action:** extend `core/health/probe.py` to optionally do an HTTP-level readiness check (Moonraker `/server/info` returning JSON with `klippy_state: "ready"`); make it a follow-up PR if the brief said TCP-only is acceptable.

---

## Remaining work — queue, prioritized

### P0 (blocks total completion today)

1. **Fix every audit finding above** (PR #20 auth, #41 scanner gaps, #42 health semantics). Don't merge until Codex's CRITIC posts LGTM.
2. **Get all 24 PRs to GREEN.** No reds at end of day.
3. **Architect-merge the green PRs** in dependency order (license/sbom/dep-fresh first; then v0.5.1 perf; then v0.6 anonymous + bridge; then gate batches; then Hermes3D feature PRs).
4. **Cut Hermes3D v5.3.0 release** — but this requires user authorization (DEFERRED until user wakes; document the cut steps).
5. **Cut HermesProof v0.6.0 release** — same, DEFERRED.

### P1 (ship today if possible)

6. **Sigstore signing of PROOF/latest.json** — Phase 2 from the original plan: `cosign sign-blob` step in truth-gates.yml after the existing commit. ~10 lines YAML, $0, ~5s. Earns SLSA Build L2.
7. **GitHub Artifact Attestations** — `actions/attest-build-provenance` over PROOF/latest.json + the SVG bundle. `gh attestation verify` for downstream.
8. **Claude Code hook bundle** at `examples/claude_code/settings.hooks.json` + `examples/claude_code/skills/hermesproof/SKILL.md`. SessionStart→`hermes_doctor`; PreToolUse Edit|Write|MultiEdit→`hermes_get_state`; PostToolUse→`hermes_append_evidence`; SubagentStop→`hermes_release_files`.
9. **Cursor + VSCode Copilot bundles** at `examples/cursor/` and `examples/vscode/` — drop-in MCP configs + rules files.
10. **KiloCode + Windsurf bundles** at `examples/kilocode/` and `examples/windsurf/`.
11. **VHS terminal demo** — `tape/quickstart.tape` recording `npm run truth-gates`; render to `docs/demos/quickstart.gif` (target <1MB) via `charmbracelet/vhs-action` in CI.
12. **Theme-aware SVGs** for the README — 3 most-prominent SVGs with `*-light.svg` palette flips wrapped in `<picture>`.
13. **Lighthouse a11y CI** in `.github/workflows/pages.yml` — `treosh/lighthouse-ci-action`, fail PR if a11y <95 or perf <90.

### P2 (nice-to-have, document-then-ship)

14. **Fencing tokens** in `lock-manager.mjs` — monotonic counter at `.hermes3d_orchestrator/fence.json`, stamped into lock metadata + every evidence entry. Closes Kleppmann's zombie-write hole.
15. **Hash-chain integrity tool** — `hermes_verify_evidence` already exists; add a CI gate that asserts the chain validates on every PR.
16. **Hermes3D printer-firmware-version gate** — assert connected printer's firmware version is in an allowlist (Klipper >=0.12, Marlin >=2.1, Prusa >=3.13). Gate `safety.firmware_version_pass`.
17. **Print-history-failure-rate gate** — last 10 prints on a printer: ≤3 failures. Otherwise emit advisory and require operator confirm. Gate `safety.print_history_failure_rate`.
18. **Hermes3D Settings tab full impl** — provider config form, env-var management UI, validation. PR #35 ships the 4 subtabs as scaffolds; this completes the env-var management subtab.
19. **Screenshot capture (22 shots)** — Playwright-driven launcher screenshots → `site/screenshots/`.
20. **Anytype docs / knowledge graph integration** — DEFERRED post-v6.

### Already DEFERRED (don't claim; document only)

- **Release cuts** (v5.3.0 Hermes3D, v0.6.0 HermesProof) — need user authorization
- **Azure Artifact Signing** — pending user signing up for paid service
- **Hipfire AMD provider activation** — only meaningful when AMD inference node spins up
- **v0.7 anonymous orchestration full impl** — next sprint per roadmap

---

## How to claim work without collisions

1. Pick a queue item that's `unclaimed`.
2. Post in the OTHER side's inbox: `TASK_CLAIMED` with the queue ID as `correlation`.
3. Lock files via `hermes_lock_files` (HermesProof MCP). If MCP is offline, fall back to manual: write a short `claim:` line into the queue file marking your owner-string.
4. Build in a fresh git worktree (`git worktree add ../my-task origin/<base>`).
5. Open a PR. Body MUST include `Task ID: <ID>`, `Hermes evidence chain: PASS`, and a literal `hermes_run_gate` reference.
6. Await CI green; do NOT auto-merge.
7. Post `FIX_PUSHED` or `GATE_LANDED` with PR # + CI URL.
8. Cleanup worktree; release locks.
9. Pick next unclaimed item.

---

## Boundaries — never cross

- NO auto-merge of any PR (architect/user merges)
- NO push to main directly (PRs only; branch protection enforces this)
- NO release tags or `gh release create` (DEFERRED)
- NO VPS / private path reads (`G:\private\` and `C:\Users\Admin\Downloads\VPS\` are off-limits)
- NO secret writes / echoes (API keys live in `G:\private\.env`; never commit, never log)
- NO modifying CI gating workflows in ways that bypass them
- NO `--no-verify` on git commits
- NO bypass / skip / "fix later" — fix it now or document explicitly as DEFERRED

---

## Communication discipline

- All cross-side messages flow through `handoffs/STREAM/CLAUDE_INBOX.md` and `CODEX_INBOX.md`
- Use timestamped IDs `msg-YYYY-MM-DDTHH-MM-SSZ-NNN`
- Acknowledge any open message addressed to your role within 15 min
- Post HEARTBEAT on tasks > 90 min
- Escalate via BLOCKED only when truly stuck — circuit-breaker fires after 3 strikes

---

## When the queue empties

There is no "queue empty → done" condition. When everything visible is claimed:

1. Re-poll STREAM/ + GATE_GAP_QUEUE.md + ENHANCEMENT_QUEUE.md every 3-5 min
2. Audit any green PR you haven't audited yet (post AUDIT_VERDICT)
3. Pick a P2 item
4. Pick a DEFERRED item and document the missing precondition
5. Improve test coverage on shipped code
6. Improve docs

The user wakes up and decides what's done. Until then, you keep going.

---

*Master Index v1 — 2026-05-03 ~13:00Z. Update this file's § Live status section as PRs land or new items appear.*
