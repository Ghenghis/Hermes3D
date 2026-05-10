# hp-protocol — Hermes Protocol P0/P1 hardening folder index

Index of nine `hp-*` checkouts under `G:\Github\` that participated in the 2026-05-03 HermesProof P0/P1 hardening sweep. All folders are clones/branches of `Ghenghis/HermesProof`; each markdown describes the slice of work that branch carried.

## Files

| Folder | Priority | Branch | Subject |
|---|---|---|---|
| [hp-audit-codex](./hp-audit-codex.md) | audit | `codex/v0.7-audit-2026-05-03` | Codex v0.7 audit + PR #29 a11y gate + PR #25 workflow-pinning gate |
| [hp-registry](./hp-registry.md) | audit | `codex/hp-pr32-audit-fixes` | PR#32 audit-gap closeout on top of PR #20 USER-bridge |
| [hp-p0-writejsonatomic](./hp-p0-writejsonatomic.md) | P0 | `fix/p0-writejsonatomic-uniqueness` | unique temp + cleanup-on-fail (→ `a8df47b`) |
| [hp-p0-chain-break-investigation](./hp-p0-chain-break-investigation.md) | P0 | `docs/p0-chain-break-investigation` | RCA + queue reference for the chain-break incident |
| [hp-p1-agent-evidence](./hp-p1-agent-evidence.md) | P1 | `fix/p1-hermes-agent-decision-evidence` | evidence USER-bridge decisions (→ `27cc3b6`) |
| [hp-p1-lockmgr](./hp-p1-lockmgr.md) | P1 | `fix/p1-lockmgr-path-traversal` | harden legacy lock ids (→ `5c42f0c`) |
| [hp-p1-docs](./hp-p1-docs.md) | P1 | `docs/p1-count-drift-2026-05-03` | sync gate + tool counts (PR #52) |
| [hp-p1-audit-update](./hp-p1-audit-update.md) | P1 | `docs/p1-postmerge-audit-updates` | close P1 audit queue updates (`89fd06c`) |
| [hp-p0-hermes-agent-hardening](./hp-p0-hermes-agent-hardening.md) | P0 (integration) | `main` | integrated tip — PRs #44, #46, #47, #48 |

## Master timeline (2026-05-03 PT)

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 500" width="700" height="500">
  <rect width="700" height="500" fill="#0b0f1a"/>
  <text x="350" y="28" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#a855f7" font-weight="bold">Hermes Protocol — P0/P1 hardening sweep, 2026-05-03</text>
  <text x="350" y="48" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#94a3b8">audit → P0 fixes → P1 fixes → docs sync → main</text>

  <!-- horizontal axis -->
  <line x1="40" y1="420" x2="660" y2="420" stroke="#475569" stroke-width="2"/>
  <g font-family="sans-serif" font-size="9" fill="#94a3b8">
    <text x="40"  y="445" text-anchor="middle">09:30</text>
    <text x="115" y="445" text-anchor="middle">10:30</text>
    <text x="190" y="445" text-anchor="middle">11:00</text>
    <text x="290" y="445" text-anchor="middle">11:55</text>
    <text x="355" y="445" text-anchor="middle">12:06</text>
    <text x="455" y="445" text-anchor="middle">13:07</text>
    <text x="535" y="445" text-anchor="middle">13:13</text>
    <text x="600" y="445" text-anchor="middle">13:16</text>
    <text x="650" y="445" text-anchor="middle">13:25</text>
    <text x="350" y="475" text-anchor="middle" font-size="10" fill="#64748b">commit times (Pacific)</text>
  </g>

  <!-- timeline pins -->
  <g font-family="sans-serif" font-size="10" fill="#e2e8f0">
    <!-- audit lane -->
    <text x="20" y="100" font-size="11" fill="#ec4899" font-weight="bold">audit</text>
    <circle cx="40"  cy="120" r="9" fill="#ec4899"/><text x="40"  y="143" text-anchor="middle" font-size="9">hp-registry</text><text x="40" y="156" text-anchor="middle" font-size="8" fill="#94a3b8">PR#32 fix</text>
    <line x1="40" y1="129" x2="40" y2="420" stroke="#ec4899" stroke-dasharray="2,3" opacity="0.4"/>
    <circle cx="190" cy="120" r="9" fill="#ec4899"/><text x="190" y="143" text-anchor="middle" font-size="9">hp-audit-codex</text><text x="190" y="156" text-anchor="middle" font-size="8" fill="#94a3b8">v0.7 reports</text>
    <line x1="190" y1="129" x2="190" y2="420" stroke="#ec4899" stroke-dasharray="2,3" opacity="0.4"/>

    <!-- P0 lane -->
    <text x="20" y="195" font-size="11" fill="#ef4444" font-weight="bold">P0</text>
    <circle cx="290" cy="215" r="9" fill="#ef4444"/><text x="290" y="238" text-anchor="middle" font-size="9">hp-p0-writejsonatomic</text><text x="290" y="251" text-anchor="middle" font-size="8" fill="#94a3b8">a8df47b</text>
    <line x1="290" y1="224" x2="290" y2="420" stroke="#ef4444" stroke-dasharray="2,3" opacity="0.4"/>
    <circle cx="355" cy="215" r="9" fill="#ef4444"/><text x="355" y="238" text-anchor="middle" font-size="9">hp-p0-chain-break</text><text x="355" y="251" text-anchor="middle" font-size="8" fill="#94a3b8">RCA docs</text>
    <line x1="355" y1="224" x2="355" y2="420" stroke="#ef4444" stroke-dasharray="2,3" opacity="0.4"/>

    <!-- P1 lane -->
    <text x="20" y="290" font-size="11" fill="#fb923c" font-weight="bold">P1</text>
    <circle cx="455" cy="310" r="9" fill="#fb923c"/><text x="455" y="333" text-anchor="middle" font-size="9">hp-p1-agent-evidence</text><text x="455" y="346" text-anchor="middle" font-size="8" fill="#94a3b8">+ hp-p1-lockmgr</text>
    <line x1="455" y1="319" x2="455" y2="420" stroke="#fb923c" stroke-dasharray="2,3" opacity="0.4"/>
    <circle cx="535" cy="310" r="9" fill="#fb923c"/><text x="535" y="333" text-anchor="middle" font-size="9">hp-p1-docs</text><text x="535" y="346" text-anchor="middle" font-size="8" fill="#94a3b8">PR #52</text>
    <line x1="535" y1="319" x2="535" y2="420" stroke="#fb923c" stroke-dasharray="2,3" opacity="0.4"/>
    <circle cx="600" cy="310" r="9" fill="#fb923c"/><text x="600" y="333" text-anchor="middle" font-size="9">hp-p1-audit-update</text><text x="600" y="346" text-anchor="middle" font-size="8" fill="#94a3b8">queue closeout</text>
    <line x1="600" y1="319" x2="600" y2="420" stroke="#fb923c" stroke-dasharray="2,3" opacity="0.4"/>

    <!-- main -->
    <text x="20" y="385" font-size="11" fill="#22c55e" font-weight="bold">main</text>
    <circle cx="650" cy="395" r="10" fill="#22c55e"/>
    <text x="650" y="418" text-anchor="middle" font-size="9" fill="#22c55e">main HEAD</text>
    <line x1="650" y1="405" x2="650" y2="420" stroke="#22c55e"/>
  </g>

  <!-- legend -->
  <g font-family="sans-serif" font-size="10" fill="#e2e8f0">
    <rect x="40"  y="65" width="14" height="14" fill="#ec4899"/><text x="60" y="76">audit</text>
    <rect x="120" y="65" width="14" height="14" fill="#ef4444"/><text x="140" y="76">P0</text>
    <rect x="180" y="65" width="14" height="14" fill="#fb923c"/><text x="200" y="76">P1</text>
    <rect x="250" y="65" width="14" height="14" fill="#22c55e"/><text x="270" y="76">merged main</text>
  </g>

  <!-- progression arrow -->
  <path d="M40 460 L660 460" stroke="#a855f7" stroke-width="1.5" fill="none" marker-end="url(#arrow)"/>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
      <path d="M0 0 L10 5 L0 10 z" fill="#a855f7"/>
    </marker>
  </defs>
  <text x="350" y="490" text-anchor="middle" font-size="10" fill="#a855f7">audit → P0 → P1 → main</text>
</svg>

## Notes

- All nine folders share the HermesProof tree (same top-level files: `README.md`, `PROOF/`, `docs/`, `handoffs/`, `policies/`, `scripts/`, `src/`). They differ only by branch.
- Bonus folder `hp-hermes-agent-bridge` exists under `G:\Github\` but was not in the requested set of nine, so it is not indexed here.
- Truth-gate proof refresh commits (`[skip ci]`) are CI-generated after each squash merge; they are not separate work items.
