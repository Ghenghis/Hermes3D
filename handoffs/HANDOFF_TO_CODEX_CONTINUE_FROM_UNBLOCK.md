# HANDOFF_TO_CODEX — CONTINUE FROM UNBLOCK

> **Status:** ACTIVE. Paste this entire prompt into Codex CLI to resume.
> Codex's session stopped after completing the unblock work (closing
> audit subagents, posting no-hold comments). The user wants Codex back
> on the perpetual loop **now**, not after all merges land. New PRs will
> keep appearing as Claude's merge-master agents land conflict fixes;
> Codex audits them as they arrive.

---

## Paste-ready Codex prompt

```
Resume the perpetual loop. Your unblock work is COMPLETE — that was a
sub-task, not a stop condition. Continue from there.

Read first:
  G:\Github\Hermes3D\handoffs\PERPETUAL_MASTER_INDEX.md   ← top of file
  G:\Github\Hermes3D\handoffs\HANDOFF_TO_CODEX_PERPETUAL_WAKEUP.md
  G:\Github\Hermes3D\handoffs\STREAM\PROTOCOL.md
  G:\Github\Hermes3D\handoffs\STREAM\STATE.md
  G:\Github\Hermes3D\handoffs\STREAM\CODEX_INBOX.md
  G:\Github\hermes3d-mcp-lock-orchestrator\handoffs\STREAM\CODEX_INBOX.md

Confirmation of where things stand (UTC ~2026-05-03 13:30Z):

Hermes3D — fully merged (12 PRs landed; #37 closed superseded).
HermesProof — 4 of 14 merged so far:
  ✅ #21 licenses.scan
  ✅ #22 v0.5.1 perf companion
  ✅ #26 mechanical-review on body edits
  ✅ #28 cron watchdog
The remaining 10 are mergeStateStatus=DIRTY (real merge conflicts on
truth-gates.mjs / README.md / package.json — every gate PR added a
gate registration block, conflict at base after #21+#22+#26+#28
landed). Two of Claude's merge-master agents are working through the
conflict resolutions sequentially. As each PR lands, the next batch's
merge state shifts — you can keep auditing them as they re-rebase.

Codex unblock state confirmed (your prior status):
  hermes_doctor: ok=true
  hermes_get_state: active locks = 0
  hermes_list_locks: count = 0
  audit subagents: closed
  no-hold comments posted on #29, #31
  No reviewDecision blocks anywhere.

Your continuing role this cycle:

1. POLL STREAM/CODEX_INBOX.md every 3-5 min for new TASK_CLAIMED,
   FIX_PUSHED, AUDIT_REQUEST, or REASSIGN_REQUEST messages from
   Claude's merge agents.

2. As Claude's merge agents land each PR (#23, #24, #25, #27, #29, #20,
   #30, #31, #32, #33), the merged code becomes available on main.
   Pick something from the queue to audit:
     - GATE_GAP_QUEUE.md still has unclaimed P1/P2 items
       (thermal-runaway-detection-gate, gcode-bounds-precondition-gate,
       material-temperature-window-gate, printer-availability-heartbeat-gate,
       emergency-stop-timing-gate, perf-budget-gate, bed-adhesion-precondition-gate,
       print-history-failure-rate-gate, release-checksum-gate, coderabbit-review-gate,
       docs-changes-reflected-gate). Some may have shipped already — verify
       against gates currently registered in scripts/truth-gates.mjs.
     - ENHANCEMENT_QUEUE.md has unclaimed items (Sigstore signing follow-up,
       GitHub Artifact Attestations, Claude Code hook bundle examples, Cursor
       + Windsurf + VSCode adapter examples, VHS terminal demo, theme-aware
       SVGs, Lighthouse a11y CI, fencing tokens in lock-manager).

3. Once all HP merged, the user's standing rule (saved in Claude's
   memory at memory/feedback_merge_authorization.md) is: merge all
   green ASAP without per-merge confirmation. You can use the same
   merge command as Claude:
     gh pr merge <N> -R Ghenghis/HermesProof --squash --delete-branch
   for any PR you author OR audit-LGTM that's CI-green.

4. Hermes Agent USER bridge will be available the moment PR #20 lands.
   That gives YOU access to:
     - hermes_anonymous_claim / release / state
     - hermes_user_grant_session / revoke_session / check_authorization
     - hermes_agent_health (DeepSeek → MiniMax → SiliconFlow → LM Studio
       → Ollama → Hipfire failover; reads keys from G:\private\.env)
     - hermes_agent_request_user_session / resolve_blocked / revoke_session
   Once enabled (HERMES_AGENT_ENABLED=1 + HERMES_AGENT_PROJECT_GOALS=...),
   you can call hermes_agent_resolve_blocked on STREAM BLOCKED
   escalations to close them without waking the user.

5. MCP supervisor (PR #33) gives you auto-reconnect when the
   hermes3d-locks server crashes. Once merged, the user's MCP client
   config should switch from args:["src/server.mjs"] to
   args:["scripts/mcp-supervisor.mjs"]. Until then, manually restart
   the server when you see the disconnect — the supervisor doesn't
   help while it's still in a feature branch.

6. Provider registry (PR #32) ships 7 new gates + the 62 LLM provider
   classes. Once merged, the bridge accepts any of those 62 providers
   for which the user has supplied an API key in env. Per the user's
   directive: don't exclude any providers.

Hard rules unchanged:
  - NO --force / --force-with-lease pushes (blocked anyway)
  - NO --no-verify on commits
  - NO direct push to main
  - NO release tags or `gh release create` (DEFERRED until user wakes)
  - NO secret reads from G:\private\.env (only env-var passthrough)
  - When CI is RED, fix the cause; never bypass

Heartbeat: post TASK_CLAIMED in STREAM/CODEX_INBOX.md when starting
work; post FIX_PUSHED / AUDIT_VERDICT / GATE_LANDED when done. If a
correlation goes >20 min with no progress, post HEARTBEAT or BLOCKED.

There is no exit condition. Loop forever until the user says stop.

Specific items I'd love you to pick up first:

  A. As each of the 10 conflict-blocked HP PRs lands (#23, #24, #25,
     #27, #29 first, then #20, #30, #31, #32, #33), do a fresh
     post-merge sanity audit on main: run npm test + truth-gates locally
     and confirm no regressions slipped in during conflict resolution.

  B. KiloCode + Cursor + Windsurf + VSCode adapter examples per
     handoffs/STREAM/CLIENT_ADAPTERS.md. Drop-in 2-3 files per client
     under examples/<client>/streamhooks/. Wire into
     scripts/install-clients.mjs as new install targets.

  C. Sigstore keyless signing of PROOF/latest.json — Phase 2 from the
     master prompt. Add cosign sign-blob step to truth-gates.yml after
     the existing commit step. ~10 lines of YAML, $0, ~5s. Earns SLSA
     Build L2.

  D. GitHub Artifact Attestations — actions/attest-build-provenance over
     PROOF/latest.json + the SVG bundle. gh attestation verify for
     downstream consumers.

  E. Live-printer integration tests — user has t1 + v400 online and
     reachable. Run existing service-health probe + bed-adhesion +
     printer-availability gates against real hardware via
     HERMES3D_HEALTH_LIVE=1 + printers.user.toml entries.

Pick whichever lane is most useful given current main state. There's
plenty of work; nothing is blocking you.
```

---

## Why Codex stopped (root cause)

The previous loop worked while Codex had concrete tasks. Once Codex
finished its unblock work (closing audit subagents, posting no-hold
comments) and the new tasks all required *waiting* for Claude's merge
agents to land conflict fixes, Codex's session had nothing actionable
and exited. The fix is items A-E above: tasks that don't require
waiting for the merge queue to drain.

Each of A-E is independent of the merge queue and can be picked up at
any time.

---

*Continue handoff v1 — 2026-05-03 ~13:30Z*
