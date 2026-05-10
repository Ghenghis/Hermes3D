# hp-p1-agent-evidence

**Priority:** P1

## Task

Fix-branch addressing the audit finding that Hermes Agent decisions (the bridge that turns inbound user-session requests into orchestrator state changes) were not being appended to the evidence ledger. Without that, the chained ledger introduced in PR #47 (`single chained ledger + anon-orch hardening`) had a gap: evidence existed for lock claims but not for the Hermes-Agent-mediated USER decisions on top of them. This branch closed that gap.

The P1 weakness was reported during the post-PR#47 audit; this branch (`fix/p1-hermes-agent-decision-evidence`) added the evidence-emission path so every Hermes-Agent decision now appends a verifiable entry.

## Status

**MERGED (rolled forward)** — branch `fix/p1-hermes-agent-decision-evidence`, HEAD `e75686a` (`fix: evidence Hermes Agent decisions`, 2026-05-03 13:07 PT). Commit content reached main as `27cc3b6` after rebase on top of the legacy-lock-id fix.

## Outcome

- New evidence emission for every Hermes-Agent USER decision
- Evidence chain now covers anon-orch + USER bridge end-to-end
- Built on top of PR #47's chained ledger and PR #46's mutex helper

## Branch & PR

- Branch: `fix/p1-hermes-agent-decision-evidence`
- Upstream merged commit on main: `27cc3b6`
- Inherits: PR #47 (`7103c16`), PR #46 (`8beeac0`)

## Key files / artifacts

1. `src/` (Hermes Agent bridge + evidence appender)
2. `docs/ADR-016-hermes-agent-as-anonymous-user.md`
3. `docs/ADR-019-anonymous-orchestration-v0.7.md`
4. `docs/EVENT_SCHEMA.md`
5. `docs/HERMES_AGENT_ENABLE.md`
6. `policies/`
7. `PROOF/latest.json`
8. `FINAL_EVIDENCE_REPORT.md`
9. `Missing-Features.md`
10. `scripts/` (truth-gate evidence checks)

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-p1-agent-evidence — close USER-decision evidence gap</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="20"  y="70"  width="120" height="55" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="80"  y="92"  text-anchor="middle">PR #47 chain</text>
    <text x="80"  y="108" text-anchor="middle" font-size="9" fill="#94a3b8">single ledger</text>
    <rect x="170" y="70"  width="160" height="55" rx="6" fill="#1e293b" stroke="#fb923c"/>
    <text x="250" y="92"  text-anchor="middle">P1 audit gap</text>
    <text x="250" y="108" text-anchor="middle" font-size="9" fill="#94a3b8">USER decisions un-evidenced</text>
    <rect x="360" y="70"  width="120" height="55" rx="6" fill="#1e293b" stroke="#22c55e"/>
    <text x="420" y="92"  text-anchor="middle">e75686a</text>
    <text x="420" y="108" text-anchor="middle" font-size="9" fill="#94a3b8">→ 27cc3b6</text>
    <rect x="80"  y="180" width="340" height="60" rx="6" fill="#0f172a" stroke="#a855f7"/>
    <text x="250" y="205" text-anchor="middle" fill="#a855f7" font-weight="bold">end-to-end evidence: anon-orch + USER bridge</text>
    <text x="250" y="223" text-anchor="middle" fill="#94a3b8" font-size="10">PROOF/latest.json now records every Hermes-Agent decision</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M140 97 L170 97"/><path d="M330 97 L360 97"/><path d="M250 125 L250 180"/>
  </g>
</svg>
