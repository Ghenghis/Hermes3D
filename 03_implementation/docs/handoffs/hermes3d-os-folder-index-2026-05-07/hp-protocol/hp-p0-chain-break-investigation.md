# hp-p0-chain-break-investigation

**Priority:** P0

## Task

Investigation branch for a P0 evidence-chain-break event observed on 2026-05-03 morning. The PROOF chain (`PROOF/latest.json` + cosign bundle) showed a discontinuity, traced to the `writeJsonAtomic` temp-file collision and an inconsistent recovery path. This branch documents the root-cause investigation and the queue-reference fix (`46f11d8`), and rolls in the upstream atomic-write fix (`a8df47b`).

The investigation produced the chain-break report under `docs/` and seeded the `fix/p0-writejsonatomic-uniqueness` companion branch (sibling folder `hp-p0-writejsonatomic`).

## Status

**MERGED (docs)** — branch `docs/p0-chain-break-investigation`, HEAD `46f11d8` (`docs: fix P0 chain-break queue reference`, 2026-05-03 12:06 PT). Followed `4fc1854` (`docs: investigate P0 evidence chain break`).

## Outcome

- Chain-break root cause documented (writeJsonAtomic temp-file collision)
- P0 queue reference corrected
- Linked to atomic-write fix `a8df47b` (already on main when this branch was cut)
- Truth-gate proof refreshed by CI

## Branch & PR

- Branch: `docs/p0-chain-break-investigation`
- Companion branch: `fix/p0-writejsonatomic-uniqueness` (folder `hp-p0-writejsonatomic`)
- No standalone PR — investigation docs flowed forward with the fix PRs

## Key files / artifacts

1. `docs/` (chain-break investigation note)
2. `FINAL_EVIDENCE_REPORT.md`
3. `Missing-Features.md`
4. `PROOF/latest.json`
5. `PROOF/latest.json.cosign.bundle`
6. `PROOF/sbom.json`
7. `PROOF_E2E_REPORT.md`
8. `PROOF_LOCAL_TEST.md`
9. `PROOF_SANDBOX_TEST.md`
10. `policies/`

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-p0-chain-break-investigation — RCA + queue fix</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="20"  y="70"  width="120" height="55" rx="6" fill="#1e293b" stroke="#ef4444"/>
    <text x="80"  y="92"  text-anchor="middle">chain break</text>
    <text x="80"  y="108" text-anchor="middle" font-size="9" fill="#94a3b8">PROOF discontinuity</text>
    <rect x="160" y="70"  width="120" height="55" rx="6" fill="#1e293b" stroke="#fb923c"/>
    <text x="220" y="92"  text-anchor="middle">RCA</text>
    <text x="220" y="108" text-anchor="middle" font-size="9" fill="#94a3b8">writeJsonAtomic race</text>
    <rect x="300" y="70"  width="120" height="55" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="360" y="92"  text-anchor="middle">queue ref fix</text>
    <text x="360" y="108" text-anchor="middle" font-size="9" fill="#94a3b8">46f11d8</text>
    <rect x="100" y="180" width="300" height="60" rx="6" fill="#0f172a" stroke="#22c55e"/>
    <text x="250" y="205" text-anchor="middle" fill="#22c55e" font-weight="bold">→ fix branch: hp-p0-writejsonatomic</text>
    <text x="250" y="223" text-anchor="middle" fill="#94a3b8" font-size="10">unique temp + cleanup-on-fail</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M140 97 L160 97"/><path d="M280 97 L300 97"/><path d="M250 125 L250 180"/>
  </g>
</svg>
