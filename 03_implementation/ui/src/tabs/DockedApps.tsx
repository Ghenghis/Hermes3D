/**
 * Docked Apps tab — Phase 2 mock-only per TAB_SPECS.md §10.
 *
 * Hosts external GUIs (Fluidd / Mainsail / OctoPrint / slicer / Blender) as
 * dock placeholders. Phase 2 ships visual-only placeholders — no embeds are
 * mounted, no external launches happen, no CSP fallback decisions are made
 * until the dock state machine lands (Tasks 39-42).
 */
import { Panel } from "../components/layout/Panel";
import { LockedAction } from "../components/badges/LockedAction";
import { StatusBadge } from "../components/badges/StatusBadge";
import { ExternalLink, Layout } from "lucide-react";

const APPS = [
  { id: "fluidd", name: "Fluidd", note: "Klipper web UI", host: "192.168.0.10:80", state: "available" as const },
  { id: "mainsail", name: "Mainsail", note: "Klipper alt UI", host: "192.168.0.11:80", state: "available" as const },
  { id: "octoprint", name: "OctoPrint", note: "OctoPi 1.10.3", host: "192.168.0.12:5000", state: "maintenance" as const },
  { id: "prusa", name: "PrusaSlicer", note: "v2.8.1 native", host: "local exe", state: "available" as const },
  { id: "orca", name: "OrcaSlicer", note: "v2.1.1 native", host: "local exe", state: "available" as const },
  { id: "blender", name: "Blender", note: "v4.2.3 + ahujasid MCP", host: "local exe + MCP bridge", state: "available" as const },
];

export function DockedAppsTab() {
  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="docked-root">
      {APPS.map((app) => (
        <div key={app.id} className="col-span-12 sm:col-span-6 lg:col-span-4">
          <Panel
            id={`docked.${app.id}`}
            title={app.name.toUpperCase()}
            dense
            status={{
              tone: app.state === "available" ? "green" : "amber",
              label: app.state,
            }}
            headerExtra={
              <span className="text-muted text-[10px] truncate max-w-[120px]">{app.note}</span>
            }
            className="h-[270px]"
          >
            <div className="h-full flex flex-col gap-2 text-xs">
              <div className="flex-1 bg-gradient-to-br from-surface2 to-bg border border-dashed border-border rounded flex flex-col items-center justify-center gap-1.5 text-muted">
                <Layout size={20} className="opacity-50" />
                <div className="text-[10px] uppercase tracking-wide">dock placeholder</div>
                <div className="text-[10px] font-mono">{app.host}</div>
                <div className="text-[9px] text-center max-w-[200px] mt-1">
                  embedded tool surfaces remain locked in this mock UI phase.
                </div>
              </div>
              <div className="flex items-center justify-between">
                <StatusBadge tone="muted" label="not mounted" />
                <div className="flex gap-1.5">
                  <LockedAction label="Launch" hint="locked · external app launch is a Phase 6 capability" />
                  <button
                    type="button"
                    disabled
                    title="locked · adapter phase"
                    className="text-muted hover:text-fg p-1 rounded disabled:cursor-not-allowed disabled:opacity-60"
                    aria-label="Open external (locked)"
                  >
                    <ExternalLink size={12} />
                  </button>
                </div>
              </div>
            </div>
          </Panel>
        </div>
      ))}
    </div>
  );
}
