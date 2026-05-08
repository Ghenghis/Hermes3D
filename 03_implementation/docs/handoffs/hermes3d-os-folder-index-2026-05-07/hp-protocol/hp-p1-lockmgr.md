# hp-p1-lockmgr

**Priority:** P1

## Task

Branch addressing a P1 audit finding: the legacy lock-id format was insufficiently constrained, allowing path-traversal-shaped strings (`..`, encoded slashes) to slip through the lock-id validator. Even though the lockmgr does not resolve those ids to filesystem paths directly, the audit flagged it as a defensive-depth weakness because the same id is later interpolated into evidence rows, log lines, and gate output. This branch hardens the legacy id parser/validator and rejects malformed ids before they reach state.

## Status

**MERGED (rolled forward)** — branch `fix/p1-lockmgr-path-traversal`, HEAD `18f990a` (`fix: harden legacy lock ids`, 2026-05-03 13:07 PT). Reached main as `5c42f0c`.

## Outcome

- Legacy lock-id validator hardened against path-traversal-shaped input
- Defensive-depth fix; no exploit reported, but evidence/log injection vector closed
- Built on PR #47 chained ledger + PR #46 mutex helper

## Branch & PR

- Branch: `fix/p1-lockmgr-path-traversal`
- Upstream merged commit on main: `5c42f0c`
- Inherits: PR #47 (`7103c16`), PR #46 (`8beeac0`)

## Key files / artifacts

1. `src/` (lockmgr id parser/validator)
2. `policies/` (lock-id format policy)
3. `docs/ARCHITECTURE.md`
4. `docs/ACCEPTANCE_GATES.md`
5. `Missing-Features.md`
6. `FINAL_EVIDENCE_REPORT.md`
7. `PROOF/latest.json`
8. `scripts/` (truth-gate validators)
9. `CHANGELOG.md`
10. `handoffs/STREAM/`

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-p1-lockmgr — legacy lock-id hardening</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="20"  y="80"  width="130" height="55" rx="6" fill="#1e293b" stroke="#fb923c"/>
    <text x="85"  y="102" text-anchor="middle">audit finding</text>
    <text x="85"  y="118" text-anchor="middle" font-size="9" fill="#94a3b8">id path-traversal</text>
    <rect x="180" y="80"  width="140" height="55" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="250" y="102" text-anchor="middle">validator rewrite</text>
    <text x="250" y="118" text-anchor="middle" font-size="9" fill="#94a3b8">reject malformed</text>
    <rect x="350" y="80"  width="130" height="55" rx="6" fill="#1e293b" stroke="#22c55e"/>
    <text x="415" y="102" text-anchor="middle">5c42f0c on main</text>
    <text x="415" y="118" text-anchor="middle" font-size="9" fill="#94a3b8">defense-in-depth</text>
    <rect x="80"  y="190" width="340" height="55" rx="6" fill="#0f172a" stroke="#a855f7"/>
    <text x="250" y="212" text-anchor="middle" fill="#a855f7" font-weight="bold">evidence/log injection vector closed</text>
    <text x="250" y="230" text-anchor="middle" fill="#94a3b8" font-size="10">malformed ids never reach PROOF/latest.json</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M150 107 L180 107"/><path d="M320 107 L350 107"/><path d="M250 135 L250 190"/>
  </g>
</svg>
