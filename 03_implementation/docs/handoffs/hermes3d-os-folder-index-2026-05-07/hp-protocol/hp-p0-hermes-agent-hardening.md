# hp-p0-hermes-agent-hardening

**Priority:** P0 (HermesProof main checkout — current `main`)

## Task

This is the canonical/main-branch HermesProof checkout used as the integration target for the P0 + P1 hardening sweep that landed on 2026-05-03. It contains the merged result of the chain-break fix, atomic-write fix, lockmgr path-traversal fix, audit-update sync, agent-evidence chain, and shared-mutex RMW work. All sibling `hp-*` folders are downstream branches that flowed back into this checkout via PRs #44–#48 plus the post-merge doc closeout.

The folder also functions as the rendezvous point where Claude/Codex run truth-gate refreshes (the `[skip ci]` proof-refresh commits) after each merge. It is the closest mirror of the public repo state.

## Status

**MERGED / ACTIVE main** — checked out at `main` HEAD, last commit 2026-05-03 20:26 UTC (proof refresh). All P0/P1 work for the 2026-05-03 sweep is integrated here.

## Outcome

- PR #48: `fix(P1): server shutdown handlers + truth-gate tests.unit reads npm manifest`
- PR #47: `fix(P0): single chained ledger + anon-orch hardening + grant_user_session lockdown`
- PR #46: `fix(P0): shared Mutex helper + apply to 5 RMW state mutators`
- PR #44: `feat(registry): regenerate LM-Studio catalog from live filesystem (87 → 91)`
- Docs closeout: `docs: close P1 audit queue updates`
- Truth-gate proofs auto-refreshed by CI after every squash-merge.

## Branch & PR

- Branch: `main`
- Linked PRs: #48, #47, #46, #44 (all merged)

## Key files / artifacts

1. `README.md` — public landing page with hero/pipeline SVGs
2. `FINAL_EVIDENCE_REPORT.md`
3. `PROOF/latest.json` + `PROOF/latest.json.cosign.bundle` + `PROOF/sbom.json`
4. `PROOF_E2E_REPORT.md`, `PROOF_LOCAL_TEST.md`, `PROOF_SANDBOX_TEST.md`
5. `Missing-Features.md`
6. `hermesproof_claude20_codex_handoff_master_prompt.md`
7. `handoffs/HANDOFF_TO_CODEX_CP-HERMESPROOF-0.4.md` (and 0.4.1, 0.5)
8. `docs/ACCEPTANCE_GATES.md`
9. `docs/ADR-016-hermes-agent-as-anonymous-user.md`, `ADR-019-anonymous-orchestration-v0.7.md`
10. `policies/`, `scripts/`, `src/`

## Diagram

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <rect width="500" height="300" fill="#0b0f1a"/>
  <text x="250" y="24" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#a855f7" font-weight="bold">hp-p0-hermes-agent-hardening — main integration</text>
  <g font-family="sans-serif" font-size="11" fill="#e2e8f0">
    <rect x="20"  y="60"  width="100" height="50" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="70"  y="82"  text-anchor="middle">P0 fixes</text>
    <text x="70"  y="98"  text-anchor="middle" font-size="9" fill="#94a3b8">writeJsonAtomic·mutex</text>
    <rect x="140" y="60"  width="100" height="50" rx="6" fill="#1e293b" stroke="#06b6d4"/>
    <text x="190" y="82"  text-anchor="middle">P1 fixes</text>
    <text x="190" y="98"  text-anchor="middle" font-size="9" fill="#94a3b8">lockmgr·evidence</text>
    <rect x="260" y="60"  width="100" height="50" rx="6" fill="#1e293b" stroke="#22c55e"/>
    <text x="310" y="82"  text-anchor="middle">main merge</text>
    <text x="310" y="98"  text-anchor="middle" font-size="9" fill="#94a3b8">PR #46 #47 #48</text>
    <rect x="380" y="60"  width="100" height="50" rx="6" fill="#1e293b" stroke="#ec4899"/>
    <text x="430" y="82"  text-anchor="middle">Truth gates</text>
    <text x="430" y="98"  text-anchor="middle" font-size="9" fill="#94a3b8">proof refresh</text>
    <rect x="100" y="170" width="300" height="60" rx="6" fill="#0f172a" stroke="#a855f7"/>
    <text x="250" y="195" text-anchor="middle" fill="#a855f7" font-weight="bold">PROOF/latest.json + cosign bundle + sbom</text>
    <text x="250" y="215" text-anchor="middle" fill="#94a3b8" font-size="10">FINAL_EVIDENCE_REPORT.md</text>
    <text x="250" y="265" text-anchor="middle" fill="#22c55e" font-size="10">→ docs: close P1 audit queue updates (HEAD)</text>
  </g>
  <g stroke="#475569" fill="none">
    <path d="M120 85 L140 85"/><path d="M240 85 L260 85"/><path d="M360 85 L380 85"/>
    <path d="M250 110 L250 170"/>
  </g>
</svg>
