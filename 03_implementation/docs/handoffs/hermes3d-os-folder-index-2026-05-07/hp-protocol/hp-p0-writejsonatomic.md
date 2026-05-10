# hp-p0-writejsonatomic

**Priority:** P0

## Task

Fix branch for the P0 chain-break root cause identified by `hp-p0-chain-break-investigation`: the `writeJsonAtomic` helper used a non-unique temp filename, so concurrent writes (or a crashed write whose temp file lingered) could collide and produce either a corrupted or stale committed file. This branch rewrites the helper to use unique temp files (`ee58a52`) and adds cleanup-on-failure (`53f9200`).

This is the actual P0 code fix that closed the evidence-chain-break incident; the companion docs branch (`hp-p0-chain-break-investigation`) tells the story.

## Status

**MERGED (rolled forward)** — branch `fix/p0-writejsonatomic-uniqueness`, HEAD `53f9200` (`fix: clean up failed atomic writes`, 2026-05-03 11:55 PT). Reached main as `a8df47b` (`fix: harden writeJsonAtomic temp writes`).

## Outcome

- Unique temp filenames per write (collision-free)
- Cleanup of orphan temp files on write failure
- Restored continuity of `PROOF/latest.json` chain
- Carried PR #44 (`feat(registry): regenerate LM-Studio catalog 87 → 91`) and PR #41 (v0.7 audit report) commits

## Branch & PR

- Branch: `fix/p0-writejsonatomic-uniqueness`
- Upstream merged commit on main: `a8df47b`
- Adjacent merged PRs: #44, #41

## Key files / artifacts

1. `src/` (writeJsonAtomic helper)
2. `scripts/` (truth-gate atomic-write check)
3. `PROOF/latest.json`
4. `PROOF/latest.json.cosign.bundle`
5. `PROOF/sbom.json`
6. `FINAL_EVIDENCE_REPORT.md`
7. `Missing-Features.md`
8. `policies/`
9. `docs/ACCEPTANCE_GATES.md`
10. `CHANGELOG.md`

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-p0-writejsonatomic — unique temp + cleanup</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="20"  y="70"  width="120" height="55" rx="6" fill="#1e293b" stroke="#ef4444"/>
    <text x="80"  y="92"  text-anchor="middle">temp collision</text>
    <text x="80"  y="108" text-anchor="middle" font-size="9" fill="#94a3b8">P0 chain break</text>
    <rect x="160" y="70"  width="120" height="55" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="220" y="92"  text-anchor="middle">unique temp</text>
    <text x="220" y="108" text-anchor="middle" font-size="9" fill="#94a3b8">ee58a52</text>
    <rect x="300" y="70"  width="120" height="55" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="360" y="92"  text-anchor="middle">cleanup-on-fail</text>
    <text x="360" y="108" text-anchor="middle" font-size="9" fill="#94a3b8">53f9200</text>
    <rect x="80"  y="190" width="340" height="60" rx="6" fill="#0f172a" stroke="#22c55e"/>
    <text x="250" y="215" text-anchor="middle" fill="#22c55e" font-weight="bold">a8df47b on main — chain continuous again</text>
    <text x="250" y="233" text-anchor="middle" fill="#94a3b8" font-size="10">PROOF/latest.json + cosign bundle stable</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M140 97 L160 97"/><path d="M280 97 L300 97"/><path d="M250 125 L250 190"/>
  </g>
</svg>
