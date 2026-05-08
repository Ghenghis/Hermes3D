# hp-audit-codex

**Priority:** audit (HermesProof v0.7)

## Task

Codex's v0.7 audit branch. Codex was given the v0.6 codebase + the v0.7 design and asked to produce a structured audit. The branch contains the audit reports themselves (`docs: add Codex v0.7 audit reports`) plus two truth-gate features Codex implemented during the audit pass: WCAG-AA accessibility gate via axe-core/JSDOM (PR #29) and workflow-pinning gate ensuring every `uses:` is SHA-pinned (PR #25).

This is the Codex side of the "Codex audits Claude's briefs" adversarial-code-review pattern, with Codex playing the auditor role.

## Status

**MERGED** — branch `codex/v0.7-audit-2026-05-03`, HEAD `7e75713` (`docs: add Codex v0.7 audit reports`, 2026-05-03 11:04 PT). Truth-gate PRs #29 and #25 already merged.

## Outcome

- Codex v0.7 audit reports added to `docs/`
- PR #29 (`HP-V0.6-GATE-A11Y`) merged: WCAG-AA gate using axe-core via JSDOM
- PR #25 (`HP-V0.6-GATE-WFPIN`) merged: workflow-pinning gate (every `uses:` SHA-pinned)
- Truth-gate proofs refreshed (`529043a`, `9930d49`)

## Branch & PR

- Branch: `codex/v0.7-audit-2026-05-03`
- Linked PRs: #29, #25 (both merged)

## Key files / artifacts

1. `docs/` (Codex v0.7 audit reports)
2. `docs/ACCEPTANCE_GATES.md` (a11y + workflow-pinning entries)
3. `scripts/` (truth-gate WCAG-AA + workflow-pinning gates)
4. `.github/workflows/` (SHA-pinned uses)
5. `Missing-Features.md`
6. `FINAL_EVIDENCE_REPORT.md`
7. `PROOF/latest.json`
8. `policies/`
9. `handoffs/`
10. `CHANGELOG.md`

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-audit-codex — v0.7 audit + 2 gate features</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="20"  y="60"  width="120" height="55" rx="6" fill="#1e293b" stroke="#ec4899"/>
    <text x="80"  y="82"  text-anchor="middle">v0.7 design</text>
    <text x="80"  y="98"  text-anchor="middle" font-size="9" fill="#94a3b8">Claude brief</text>
    <rect x="180" y="60"  width="140" height="55" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="250" y="82"  text-anchor="middle">Codex audit</text>
    <text x="250" y="98"  text-anchor="middle" font-size="9" fill="#94a3b8">7e75713 reports</text>
    <rect x="360" y="60"  width="120" height="55" rx="6" fill="#1e293b" stroke="#22c55e"/>
    <text x="420" y="82"  text-anchor="middle">findings</text>
    <text x="420" y="98"  text-anchor="middle" font-size="9" fill="#94a3b8">→ feature gates</text>
    <rect x="40"  y="180" width="200" height="65" rx="6" fill="#0f172a" stroke="#a855f7"/>
    <text x="140" y="202" text-anchor="middle" fill="#a855f7" font-weight="bold">PR #29 GATE-A11Y</text>
    <text x="140" y="220" text-anchor="middle" fill="#94a3b8" font-size="10">axe-core via JSDOM</text>
    <text x="140" y="236" text-anchor="middle" fill="#94a3b8" font-size="10">WCAG-AA</text>
    <rect x="260" y="180" width="200" height="65" rx="6" fill="#0f172a" stroke="#a855f7"/>
    <text x="360" y="202" text-anchor="middle" fill="#a855f7" font-weight="bold">PR #25 GATE-WFPIN</text>
    <text x="360" y="220" text-anchor="middle" fill="#94a3b8" font-size="10">every uses: SHA-pinned</text>
    <text x="360" y="236" text-anchor="middle" fill="#94a3b8" font-size="10">supply-chain</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M140 87 L180 87"/><path d="M320 87 L360 87"/>
    <path d="M180 115 L140 180"/><path d="M320 115 L360 180"/>
  </g>
</svg>
