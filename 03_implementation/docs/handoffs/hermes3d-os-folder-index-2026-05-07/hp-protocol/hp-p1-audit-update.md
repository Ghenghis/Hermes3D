# hp-p1-audit-update

**Priority:** P1

## Task

P1 post-merge documentation cleanup branch. After PR #52 (`docs: sync gate and tool counts`) landed, the audit queue had a number of stale numbers and finished-but-not-marked items. This branch produced the `docs: close P1 audit queue updates` commit that closes those entries on the audit register. It is the documentation-facing tail of the P1 wave: gate counts, tool counts, and the "queue updates" closeout text.

## Status

**MERGED** — branch `docs/p1-postmerge-audit-updates`, last commit 2026-05-03 13:16 PT. PR #52 merged via `7cbe16e`; the closeout commit `89fd06c` followed and was rolled forward to main.

## Outcome

- Closed P1 audit queue items
- Synced gate count and tool count documentation to the actual repo state (PR #52)
- Picked up evidence-decision fix (`27cc3b6`) and legacy lock-id hardening (`5c42f0c`) from upstream

## Branch & PR

- Branch: `docs/p1-postmerge-audit-updates`
- Linked PR: #52 (merged) — `docs: sync gate and tool counts`

## Key files / artifacts

1. `docs/ACCEPTANCE_GATES.md` (gate count source-of-truth)
2. `docs/HERMESPROOF_SETUP_AUDIT.md`
3. `Missing-Features.md`
4. `FINAL_EVIDENCE_REPORT.md`
5. `PROOF/latest.json`
6. `PROOF/latest.json.cosign.bundle`
7. `PROOF/sbom.json`
8. `handoffs/STREAM/`
9. `policies/`
10. `CHANGELOG.md`

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-p1-audit-update — doc count sync + queue closeout</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="30"  y="80"  width="120" height="60" rx="6" fill="#1e293b" stroke="#fb923c"/>
    <text x="90"  y="105" text-anchor="middle">stale counts</text>
    <text x="90"  y="122" text-anchor="middle" font-size="9" fill="#94a3b8">gates·tools drift</text>
    <rect x="190" y="80"  width="120" height="60" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="250" y="105" text-anchor="middle">PR #52 sync</text>
    <text x="250" y="122" text-anchor="middle" font-size="9" fill="#94a3b8">7cbe16e</text>
    <rect x="350" y="80"  width="120" height="60" rx="6" fill="#1e293b" stroke="#22c55e"/>
    <text x="410" y="105" text-anchor="middle">audit closeout</text>
    <text x="410" y="122" text-anchor="middle" font-size="9" fill="#94a3b8">89fd06c</text>
    <rect x="120" y="200" width="260" height="50" rx="6" fill="#0f172a" stroke="#a855f7"/>
    <text x="250" y="222" text-anchor="middle" fill="#a855f7">→ rolled into main</text>
    <text x="250" y="240" text-anchor="middle" fill="#94a3b8" font-size="10">docs/ACCEPTANCE_GATES.md authoritative</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M150 110 L190 110"/><path d="M310 110 L350 110"/><path d="M250 140 L250 200"/>
  </g>
</svg>
