# h3dos-wire-source-os-status-pills

- **UI surface**: Per-module install status pill (`.status-pill`) inside each `#sourceModuleList` button
- **Tab**: Source OS
- **Backend endpoint**: INFERRED — `GET /api/source/apps/status` (the existing `sourceAppStatus(module)` helper reads `install_status` from a pre-fetched manifest/state; no new endpoint is wired in this commit, only the read of `appStatus.install_status` already populated by Source OS module loader)
- **Files changed** (commit `e67803d`):
  - `apps/web/source-os.js` — +18 lines (`renderModuleStatusPill()` reading `install_status`, classes `pill-green/yellow/blue/gray`)
  - `apps/web/styles.css` — +32 lines (status-pill colour classes)
  - `tests/e2e/wire-source-os-status-pills.spec.ts` — +15 lines
- **Status**: OPEN (single feature commit; no PR-merge marker)
- **Branch & last commit**: `wire/source-os-status-pills` @ `e67803d wire(source-os-status-pills): per-module install status pill`
- **Path**: `G:\Github\h3dos-wire-source-os-status-pills`

## SVG diagram

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
  <style>
    .box { fill:#1f2937; stroke:#a78bfa; stroke-width:1.5; }
    .label { fill:#e5e7eb; font:12px sans-serif; }
    .small { fill:#9ca3af; font:10px sans-serif; }
    .arrow { stroke:#a78bfa; stroke-width:1.5; fill:none; marker-end:url(#a); }
    .green { fill:#10b981; } .yellow { fill:#fbbf24; } .blue { fill:#3b82f6; } .gray { fill:#6b7280; }
  </style>
  <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#a78bfa"/></marker></defs>
  <rect class="box" x="10" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="20" y="62">#sourceModuleList</text>
  <text class="small" x="20" y="80">module button</text>
  <text class="small" x="20" y="95">renderModuleStatusPill</text>
  <path class="arrow" d="M130,70 L180,70"/>
  <rect class="box" x="180" y="40" width="120" height="60" rx="6"/>
  <text class="label" x="190" y="62">sourceAppStatus()</text>
  <text class="small" x="190" y="80">reads install_status</text>
  <text class="small" x="190" y="95">from manifest</text>
  <path class="arrow" d="M300,70 L340,70"/>
  <rect class="box" x="340" y="40" width="55" height="60" rx="6"/>
  <text class="small" x="346" y="62">/api/</text>
  <text class="small" x="346" y="76">source/</text>
  <text class="small" x="346" y="90">status</text>
  <text class="label" x="20" y="160">Pill colours:</text>
  <circle class="green" cx="100" cy="156" r="6"/><text class="small" x="112" y="160">installed</text>
  <circle class="yellow" cx="170" cy="156" r="6"/><text class="small" x="182" y="160">installing</text>
  <circle class="blue" cx="240" cy="156" r="6"/><text class="small" x="252" y="160">available</text>
  <circle class="gray" cx="310" cy="156" r="6"/><text class="small" x="322" y="160">unknown</text>
  <rect class="box" x="80" y="190" width="240" height="40" rx="6"/>
  <text class="small" x="92" y="215">Response: { install_status: string }</text>
</svg>
```
