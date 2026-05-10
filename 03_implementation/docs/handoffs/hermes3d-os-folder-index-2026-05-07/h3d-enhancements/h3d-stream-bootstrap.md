# h3d-stream-bootstrap

- **Type**: ENHANCEMENT (DOCS / handoff protocol)
- **Status**: MERGED
- **Branch**: `docs/stream-protocol-bootstrap`
- **Last commit**: `a9fd5da docs(handoff): STREAM/ real-time anonymous handoff protocol + perpetual wakeup`
- **PR link**: [#39 — docs(handoff): STREAM/ real-time anonymous handoff protocol + perpetual wakeup](https://github.com/Ghenghis/Hermes3D/pull/39)
- **Repo**: `https://github.com/Ghenghis/Hermes3D`

## Goal

Bootstrap the `handoffs/STREAM/` real-time anonymous handoff protocol — a write-only inbox layout that lets Claude and Codex exchange tasks without coordinating on a single document. Adds the protocol spec, per-agent inboxes, ledger, watchdog brief, and the perpetual-wakeup handoff for Codex.

## Files changed (vs `origin/develop`)

| File | + / - |
| --- | --- |
| `handoffs/HANDOFF_TO_CODEX_PERPETUAL_WAKEUP.md` | +150 |
| `handoffs/STREAM/CLAUDE_INBOX.md` | +8 |
| `handoffs/STREAM/CLIENT_ADAPTERS.md` | +165 |
| `handoffs/STREAM/CODEX_INBOX.md` | +183 |
| `handoffs/STREAM/ENHANCEMENT_QUEUE.md` | +110 |
| `handoffs/STREAM/GATE_GAP_QUEUE.md` | +200 |
| `handoffs/STREAM/LEDGER.md` | +22 |
| `handoffs/STREAM/PROTOCOL.md` | +283 |
| `handoffs/STREAM/STATE.md` | +81 |
| `handoffs/STREAM/WATCHDOG.md` | +204 |

Total: 10 files changed, +1406 / -0. All additions, all docs — no source code touched.

## Notes

- Pure docs / process scaffolding; sets up the dual-agent (Claude + Codex) anonymous handoff loop the rest of the v5.3.0 work runs on.
- `PROTOCOL.md` is the canonical spec; the inbox / queue / ledger / watchdog files are the running surface.
- Squash-merged as PR #39.

## SVG diagram — change footprint

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 450 250" width="450" height="250" role="img" aria-label="h3d-stream-bootstrap change footprint">
  <style>
    .box { fill: #1f2937; stroke: #4b5563; stroke-width: 1; }
    .new { fill: #065f46; stroke: #10b981; }
    .label { fill: #f9fafb; font: 600 11px sans-serif; }
    .sub { fill: #d1d5db; font: 10px sans-serif; }
    .title { fill: #f9fafb; font: 700 14px sans-serif; }
    .arrow { stroke: #9ca3af; stroke-width: 1.4; fill: none; marker-end: url(#a); }
  </style>
  <defs>
    <marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#9ca3af"/>
    </marker>
  </defs>
  <rect width="450" height="250" fill="#0b1220"/>
  <text class="title" x="225" y="22" text-anchor="middle">handoffs/STREAM/ — anonymous dual-agent protocol</text>

  <rect class="box new" x="170" y="45" width="110" height="40" rx="5"/>
  <text class="label" x="180" y="62">PROTOCOL.md</text>
  <text class="sub"   x="180" y="78">+283 — spec</text>

  <rect class="box new" x="20" y="105" width="120" height="38" rx="5"/>
  <text class="label" x="30" y="122">CLAUDE_INBOX</text>
  <text class="sub"   x="30" y="136">+8</text>

  <rect class="box new" x="305" y="105" width="120" height="38" rx="5"/>
  <text class="label" x="315" y="122">CODEX_INBOX</text>
  <text class="sub"   x="315" y="136">+183</text>

  <rect class="box new" x="20" y="155" width="120" height="38" rx="5"/>
  <text class="label" x="30" y="172">ENHANCEMENT_Q</text>
  <text class="sub"   x="30" y="186">+110</text>

  <rect class="box new" x="160" y="155" width="130" height="38" rx="5"/>
  <text class="label" x="170" y="172">LEDGER · STATE</text>
  <text class="sub"   x="170" y="186">+22 · +81</text>

  <rect class="box new" x="305" y="155" width="120" height="38" rx="5"/>
  <text class="label" x="315" y="172">GATE_GAP_Q</text>
  <text class="sub"   x="315" y="186">+200</text>

  <rect class="box new" x="20" y="205" width="200" height="32" rx="5"/>
  <text class="label" x="30" y="225">CLIENT_ADAPTERS · WATCHDOG (+165 / +204)</text>

  <rect class="box new" x="240" y="205" width="190" height="32" rx="5"/>
  <text class="label" x="250" y="225">PERPETUAL_WAKEUP (+150)</text>

  <path class="arrow" d="M225,86 L80,103"/>
  <path class="arrow" d="M225,86 L365,103"/>
</svg>
```
