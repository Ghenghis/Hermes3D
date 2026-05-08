# hp-p1-docs

**Priority:** P1

## Task

Documentation-only branch focused on the count-drift detected on 2026-05-03: the public `docs/ACCEPTANCE_GATES.md` and tool-count tables were out of sync with the actual `truth-gates.mjs` and MCP tool registry. This branch produced PR #52 (`docs: sync gate and tool counts`) and is the upstream of `hp-p1-audit-update`. It also carried two adjacent fix commits (`27cc3b6` evidence Hermes Agent decisions, `5c42f0c` harden legacy lock ids) which became part of the P1 wave.

## Status

**MERGED** — branch `docs/p1-count-drift-2026-05-03`, HEAD `7cbe16e` is PR #52 merged 2026-05-03 13:13 PT.

## Outcome

- PR #52 merged: gate count + MCP tool count documentation synchronized to live repo state
- Adjacent fixes carried: legacy-lock-id hardening, Hermes Agent evidence-decision fix
- Truth-gate proof refreshed (`544df86`, `8561139`)

## Branch & PR

- Branch: `docs/p1-count-drift-2026-05-03`
- Linked PR: #52 (merged)

## Key files / artifacts

1. `docs/ACCEPTANCE_GATES.md`
2. `README.md` (gate-count badge area)
3. `Missing-Features.md`
4. `FINAL_EVIDENCE_REPORT.md`
5. `PROOF/latest.json`
6. `policies/`
7. `src/` (lock id hardening + evidence fix landed here pre-PR)
8. `scripts/` (truth-gates.mjs)
9. `CHANGELOG.md`
10. `handoffs/STREAM/`

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-p1-docs — count-drift sync (PR #52)</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="20"  y="70"  width="110" height="55" rx="6" fill="#1e293b" stroke="#fb923c"/>
    <text x="75"  y="92"  text-anchor="middle">drift detected</text>
    <text x="75"  y="108" text-anchor="middle" font-size="9" fill="#94a3b8">gates·tools</text>
    <rect x="150" y="70"  width="110" height="55" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="205" y="92"  text-anchor="middle">doc rewrite</text>
    <text x="205" y="108" text-anchor="middle" font-size="9" fill="#94a3b8">acceptance gates</text>
    <rect x="280" y="70"  width="110" height="55" rx="6" fill="#1e293b" stroke="#a855f7"/>
    <text x="335" y="92"  text-anchor="middle">PR #52</text>
    <text x="335" y="108" text-anchor="middle" font-size="9" fill="#94a3b8">7cbe16e merged</text>
    <rect x="20"  y="180" width="170" height="55" rx="6" fill="#1e293b" stroke="#22c55e"/>
    <text x="105" y="202" text-anchor="middle">+ legacy-lock-id fix</text>
    <text x="105" y="218" text-anchor="middle" font-size="9" fill="#94a3b8">5c42f0c</text>
    <rect x="220" y="180" width="170" height="55" rx="6" fill="#1e293b" stroke="#22c55e"/>
    <text x="305" y="202" text-anchor="middle">+ evidence-decision fix</text>
    <text x="305" y="218" text-anchor="middle" font-size="9" fill="#94a3b8">27cc3b6</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M130 97 L150 97"/><path d="M260 97 L280 97"/>
  </g>
</svg>
