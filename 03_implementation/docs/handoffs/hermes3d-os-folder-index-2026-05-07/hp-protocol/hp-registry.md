# hp-registry

**Priority:** audit (PR #32 follow-up)

## Task

Codex follow-up branch closing audit gaps left by PR #32. Sits on `codex/hp-pr32-audit-fixes` with HEAD `80595b8` (`fix(gates): close PR32 audit gaps`). Earlier in the branch's history are forward-merges from PR #20 (`feat(v0.6): anonymous role rotation + Hermes Agent USER bridge`) and PR #33 (supervisor test union), so this branch also acts as the integration point where the v0.6 anon-role-rotation + USER-bridge work was reconciled with the supervisor test union and the PR#32 audit-fix gates.

Despite the folder name "hp-registry", the branch's actual subject is post-PR#32 gate hardening rather than the `agents/hermes_agent` MCP-registry entry; the registry-related changes are inherited via the upstream PR #20 USER bridge merge.

## Status

**ACTIVE / pending merge to main** — last commit 2026-05-03 09:36 PT, ahead of the merged sweep on `main` only by the audit-gap fixes. Likely already integrated by the time the P0/P1 sweep landed.

## Outcome

- PR #32 audit gaps closed via `80595b8`
- Forward-merged PR #20 (anon role rotation + Hermes Agent USER bridge) — `fa18cf7`, `fc851c0`
- Forward-merged PR #33 (supervisor test union) — `87fd5e7`
- Anonymous-test union + CSV-schema fix carried in

## Branch & PR

- Branch: `codex/hp-pr32-audit-fixes`
- Linked PRs (already merged upstream): #32, #33, #20

## Key files / artifacts

1. `policies/agents/` (Hermes Agent registry entry, via PR #20)
2. `docs/HERMES_AGENT_ENABLE.md`
3. `docs/ADR-016-hermes-agent-as-anonymous-user.md`
4. `scripts/` (truth-gate audit-fix gates)
5. `Missing-Features.md`
6. `FINAL_EVIDENCE_REPORT.md`
7. `PROOF/latest.json`
8. `src/` (anon role rotation + USER bridge)
9. `handoffs/`
10. `CHANGELOG.md`

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-registry — PR#32 audit-gap closeout</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="20"  y="60"  width="130" height="50" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="85"  y="80"  text-anchor="middle">PR #20</text>
    <text x="85"  y="96"  text-anchor="middle" font-size="9" fill="#94a3b8">anon rotation + USER bridge</text>
    <rect x="180" y="60"  width="130" height="50" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="245" y="80"  text-anchor="middle">PR #33</text>
    <text x="245" y="96"  text-anchor="middle" font-size="9" fill="#94a3b8">supervisor test union</text>
    <rect x="340" y="60"  width="130" height="50" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="405" y="80"  text-anchor="middle">PR #32</text>
    <text x="405" y="96"  text-anchor="middle" font-size="9" fill="#94a3b8">audit gaps</text>
    <rect x="100" y="170" width="300" height="60" rx="6" fill="#0f172a" stroke="#22c55e"/>
    <text x="250" y="195" text-anchor="middle" fill="#22c55e" font-weight="bold">80595b8 — close PR32 audit gaps</text>
    <text x="250" y="213" text-anchor="middle" fill="#94a3b8" font-size="10">forward-merged onto v0.6 USER-bridge base</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M85 110 L250 170"/><path d="M245 110 L250 170"/><path d="M405 110 L250 170"/>
  </g>
</svg>
