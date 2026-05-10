# h3dos-wire-* tasks — category index

Short-lived single-feature wiring branches (`h3dos-wire-*`) that connect one Hermes3D Web UI control to its backend endpoint (or to the cross-cutting Action Window). Each folder is a worktree of the `wire/<name>` branch in the Hermes3D repo and lands either directly on `develop` or on `main` via PR.

There are **18** wire-task folders total. This index covers all of them; each entry links to its per-folder markdown.

## All 18 wire-task folders

This batch (9 — indexed in this pass):
- [h3dos-wire-action-window-history](./h3dos-wire-action-window-history.md)
- [h3dos-wire-voice-state-status-pill](./h3dos-wire-voice-state-status-pill.md)
- [h3dos-wire-source-os-search](./h3dos-wire-source-os-search.md)
- [h3dos-wire-dashboard-queue-list](./h3dos-wire-dashboard-queue-list.md)
- [h3dos-wire-jobs-search-filter](./h3dos-wire-jobs-search-filter.md)
- [h3dos-wire-dashboard-events-tail](./h3dos-wire-dashboard-events-tail.md)
- [h3dos-wire-printers-row-click](./h3dos-wire-printers-row-click.md)
- [h3dos-wire-printers-discover-button](./h3dos-wire-printers-discover-button.md)
- [h3dos-wire-dashboard-fleet-list](./h3dos-wire-dashboard-fleet-list.md)

Parallel batch (9 — indexed by sibling agent; markdowns under same directory):
- [h3dos-wire-action-window-pin](./h3dos-wire-action-window-pin.md)
- [h3dos-wire-agents-list](./h3dos-wire-agents-list.md)
- [h3dos-wire-artifacts-row-click](./h3dos-wire-artifacts-row-click.md)
- [h3dos-wire-global-event-bus-logger](./h3dos-wire-global-event-bus-logger.md)
- [h3dos-wire-jobs-row-click](./h3dos-wire-jobs-row-click.md)
- [h3dos-wire-learning-topics](./h3dos-wire-learning-topics.md)
- [h3dos-wire-observe-camera-tile-click](./h3dos-wire-observe-camera-tile-click.md)
- [h3dos-wire-source-os-status-pills](./h3dos-wire-source-os-status-pills.md)
- [h3dos-wire-topbar-refresh-button](./h3dos-wire-topbar-refresh-button.md)

## Tabs map (UI surface -> wire task -> backend endpoint)

| Tab | Wire task | UI surface | Backend endpoint |
|---|---|---|---|
| Topbar | h3dos-wire-topbar-refresh-button | Refresh button | (re-pulls active tab data; multiple GETs) |
| Topbar / Voice | h3dos-wire-voice-state-status-pill | `#voiceStatusPill` | `GET /api/voice/state` |
| Dashboard | h3dos-wire-dashboard-fleet-list | `.printer-card` (fleet) | `GET /api/workspace` (printers[]) |
| Dashboard | h3dos-wire-dashboard-queue-list | `#dashboardJobs .job-card` | `GET /api/workspace` (jobs[]) |
| Dashboard | h3dos-wire-dashboard-events-tail | `#dashboardEvents .event-card` | `GET /api/workspace` (events[]) |
| Source OS | h3dos-wire-source-os-search | `#sourceSearch` input | client-only (manifest preloaded) |
| Source OS | h3dos-wire-source-os-status-pills | per-module status pill | `GET /api/sources/.../status` (INFERRED) |
| Agents | h3dos-wire-agents-list | agents list row | `GET /api/workspace` (agents) -> Action Window |
| Observe | h3dos-wire-observe-camera-tile-click | camera tile click | `GET /api/workspace` (camera streams) -> AW |
| Jobs | h3dos-wire-jobs-row-click | job row click | `GET /api/workspace` (jobs[]) -> AW |
| Jobs | h3dos-wire-jobs-search-filter | `#jobsSearch` + `.status-chip` | `GET /api/workspace` (client filter) |
| Learning | h3dos-wire-learning-topics | learning topic row | `GET /api/learning-mode/status` (INFERRED) -> AW |
| Artifacts | h3dos-wire-artifacts-row-click | artifact row click | `GET /api/workspace` (artifacts[]) -> AW |
| Printers | h3dos-wire-printers-row-click | `#printers .printer-card` | `GET /api/workspace` (printers[]) -> AW |
| Printers | h3dos-wire-printers-discover-button | `#printersDiscover` | `POST /api/printers/discover` |
| Action Window | h3dos-wire-action-window-history | Back/Fwd buttons | client-only history ring |
| Action Window | h3dos-wire-action-window-pin | Pin button | client-only (sticky AW) |
| (cross-cutting) | h3dos-wire-global-event-bus-logger | n/a (infra) | console / event bus |

## Master SVG — H3D Web UI tab layout with wire-task annotations

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500">
  <rect width="800" height="500" fill="#0e1116"/>
  <!-- Topbar -->
  <rect x="10" y="10" width="780" height="40" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="20" y="35" fill="#e5e7eb" font-family="sans-serif" font-size="13">Topbar</text>
  <text x="640" y="35" fill="#9ca3af" font-family="sans-serif" font-size="10">[Refresh] [Voice pill]</text>
  <text x="540" y="32" fill="#fbbf24" font-family="sans-serif" font-size="9" text-anchor="end">topbar-refresh-button -></text>
  <text x="780" y="62" fill="#fbbf24" font-family="sans-serif" font-size="9" text-anchor="end">voice-state-status-pill -></text>

  <!-- Dashboard tab -->
  <rect x="10" y="80" width="240" height="180" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="20" y="100" fill="#e5e7eb" font-family="sans-serif" font-size="13">Dashboard</text>
  <text x="20" y="120" fill="#9ca3af" font-family="sans-serif" font-size="10">.printer-card (fleet)</text>
  <text x="160" y="120" fill="#fbbf24" font-family="sans-serif" font-size="9">dashboard-fleet-list</text>
  <text x="20" y="140" fill="#9ca3af" font-family="sans-serif" font-size="10">#dashboardJobs .job-card</text>
  <text x="160" y="140" fill="#fbbf24" font-family="sans-serif" font-size="9">dashboard-queue-list</text>
  <text x="20" y="160" fill="#9ca3af" font-family="sans-serif" font-size="10">#dashboardEvents .event-card</text>
  <text x="160" y="160" fill="#fbbf24" font-family="sans-serif" font-size="9">dashboard-events-tail</text>

  <!-- Source OS -->
  <rect x="270" y="80" width="240" height="180" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="280" y="100" fill="#e5e7eb" font-family="sans-serif" font-size="13">Source OS</text>
  <text x="280" y="120" fill="#9ca3af" font-family="sans-serif" font-size="10">#sourceSearch</text>
  <text x="400" y="120" fill="#fbbf24" font-family="sans-serif" font-size="9">source-os-search</text>
  <text x="280" y="140" fill="#9ca3af" font-family="sans-serif" font-size="10">module status pill</text>
  <text x="400" y="140" fill="#fbbf24" font-family="sans-serif" font-size="9">source-os-status-pills</text>

  <!-- Agents -->
  <rect x="530" y="80" width="240" height="80" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="540" y="100" fill="#e5e7eb" font-family="sans-serif" font-size="13">Agents</text>
  <text x="540" y="120" fill="#9ca3af" font-family="sans-serif" font-size="10">agent row click</text>
  <text x="660" y="120" fill="#fbbf24" font-family="sans-serif" font-size="9">agents-list</text>

  <!-- Observe -->
  <rect x="530" y="180" width="240" height="80" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="540" y="200" fill="#e5e7eb" font-family="sans-serif" font-size="13">Observe</text>
  <text x="540" y="220" fill="#9ca3af" font-family="sans-serif" font-size="10">camera tile</text>
  <text x="660" y="220" fill="#fbbf24" font-family="sans-serif" font-size="9">observe-camera-tile-click</text>

  <!-- Jobs -->
  <rect x="10" y="280" width="240" height="100" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="20" y="300" fill="#e5e7eb" font-family="sans-serif" font-size="13">Jobs</text>
  <text x="20" y="320" fill="#9ca3af" font-family="sans-serif" font-size="10">job row click</text>
  <text x="140" y="320" fill="#fbbf24" font-family="sans-serif" font-size="9">jobs-row-click</text>
  <text x="20" y="340" fill="#9ca3af" font-family="sans-serif" font-size="10">#jobsSearch + .status-chip</text>
  <text x="140" y="360" fill="#fbbf24" font-family="sans-serif" font-size="9">jobs-search-filter</text>

  <!-- Learning -->
  <rect x="270" y="280" width="240" height="100" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="280" y="300" fill="#e5e7eb" font-family="sans-serif" font-size="13">Learning</text>
  <text x="280" y="320" fill="#9ca3af" font-family="sans-serif" font-size="10">topic row</text>
  <text x="400" y="320" fill="#fbbf24" font-family="sans-serif" font-size="9">learning-topics</text>

  <!-- Artifacts -->
  <rect x="530" y="280" width="240" height="100" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="540" y="300" fill="#e5e7eb" font-family="sans-serif" font-size="13">Artifacts</text>
  <text x="540" y="320" fill="#9ca3af" font-family="sans-serif" font-size="10">artifact row click</text>
  <text x="660" y="320" fill="#fbbf24" font-family="sans-serif" font-size="9">artifacts-row-click</text>

  <!-- Printers -->
  <rect x="10" y="400" width="370" height="90" rx="4" fill="#1f2937" stroke="#60a5fa"/>
  <text x="20" y="420" fill="#e5e7eb" font-family="sans-serif" font-size="13">Printers</text>
  <text x="20" y="440" fill="#9ca3af" font-family="sans-serif" font-size="10">#printers .printer-card</text>
  <text x="180" y="440" fill="#fbbf24" font-family="sans-serif" font-size="9">printers-row-click</text>
  <text x="20" y="460" fill="#9ca3af" font-family="sans-serif" font-size="10">#printersDiscover</text>
  <text x="180" y="460" fill="#fbbf24" font-family="sans-serif" font-size="9">printers-discover-button</text>

  <!-- Action Window (overlay) -->
  <rect x="400" y="400" width="370" height="90" rx="4" fill="#1f2937" stroke="#a78bfa"/>
  <text x="410" y="420" fill="#e5e7eb" font-family="sans-serif" font-size="13">Action Window (overlay)</text>
  <text x="410" y="440" fill="#9ca3af" font-family="sans-serif" font-size="10">Back / Fwd buttons</text>
  <text x="560" y="440" fill="#fbbf24" font-family="sans-serif" font-size="9">action-window-history</text>
  <text x="410" y="460" fill="#9ca3af" font-family="sans-serif" font-size="10">Pin button</text>
  <text x="560" y="460" fill="#fbbf24" font-family="sans-serif" font-size="9">action-window-pin</text>
  <text x="410" y="480" fill="#9ca3af" font-family="sans-serif" font-size="10">global event bus</text>
  <text x="560" y="480" fill="#fbbf24" font-family="sans-serif" font-size="9">global-event-bus-logger</text>

  <!-- Arrows from each tab into Action Window -->
  <line x1="130" y1="260" x2="500" y2="400" stroke="#a78bfa" stroke-width="0.6" stroke-dasharray="3,3"/>
  <line x1="390" y1="260" x2="500" y2="400" stroke="#a78bfa" stroke-width="0.6" stroke-dasharray="3,3"/>
  <line x1="650" y1="160" x2="585" y2="400" stroke="#a78bfa" stroke-width="0.6" stroke-dasharray="3,3"/>
  <line x1="650" y1="260" x2="585" y2="400" stroke="#a78bfa" stroke-width="0.6" stroke-dasharray="3,3"/>
  <line x1="130" y1="380" x2="500" y2="400" stroke="#a78bfa" stroke-width="0.6" stroke-dasharray="3,3"/>
  <line x1="390" y1="380" x2="500" y2="400" stroke="#a78bfa" stroke-width="0.6" stroke-dasharray="3,3"/>
  <line x1="650" y1="380" x2="585" y2="400" stroke="#a78bfa" stroke-width="0.6" stroke-dasharray="3,3"/>
  <line x1="190" y1="490" x2="450" y2="490" stroke="#a78bfa" stroke-width="0.6" stroke-dasharray="3,3"/>

  <text x="400" y="495" fill="#6b7280" font-family="sans-serif" font-size="9" text-anchor="middle">dashed lines = "click opens Action Window"</text>
</svg>
```

## Notes

- The dominant integration pattern is **`GET /api/workspace` -> click handler -> `openActionWindow(kind, entity)`**. All Dashboard, Printers-row, Jobs-row, Agents-list, Observe-camera, Artifacts-row tasks follow this shape.
- Genuinely new server endpoints introduced by this batch:
  - `POST /api/printers/discover` (printers-discover-button)
  - `GET /api/voice/state` (voice-state-status-pill)
- All 9 folders in this batch are **OPEN / IN-DEVELOP** (none merged to `origin/main` as of 2026-05-07). Half are already on `origin/develop`; the other half are still local-branch only.
- Several branches show develop-merge fix-up commits — typical symptom of the H3D 20-agent lock-collision pattern documented in memory.
