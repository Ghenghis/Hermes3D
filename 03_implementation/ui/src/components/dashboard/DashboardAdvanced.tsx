/**
 * Dashboard Advanced mode — W6-3 lane.
 *
 * Contract (from `Images-GUI/01-dashboard-modes/advanced-dashboard-*.png`):
 *  - Reuses the existing full live `Dashboard` component (16-tab parity, KPI
 *    grid, fleet, pipeline, agents, system resources, recent jobs, proof,
 *    logs, notifications). The Hermes Agents chat-mirror dock is rendered by
 *    the AppShell's `Sidebar` and is therefore always present in advanced
 *    mode.
 *  - Adds a small floating "Action Window" launcher chip in the top-right of
 *    the dashboard area so the user can jump to the live Action Window
 *    without leaving the dashboard.
 *
 * The advanced mode does *not* add any extra data fetches — it forwards to
 * the existing dashboard which already pulls live data via `adapters`.
 */
import { Maximize2 } from "lucide-react";
import { Dashboard } from "../../tabs/Dashboard";
import { useStore } from "../../app/store";

export function DashboardAdvanced() {
  return (
    <div
      className="dashboard-advanced-shell relative flex h-full min-h-0 flex-col"
      data-testid="dashboard-advanced-root"
      data-dashboard-mode="advanced"
    >
      <div className="absolute right-2 top-1 z-10 flex items-center gap-2">
        <ActionWindowButton />
      </div>
      <div className="min-h-0 flex-1">
        <Dashboard />
      </div>
    </div>
  );
}

function ActionWindowButton() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  return (
    <button
      type="button"
      data-testid="dashboard-advanced-action-window-btn"
      onClick={() => setActiveTabId("autopilot")}
      title="Open the Hermes Action Window"
      className="inline-flex items-center gap-1.5 rounded-md border border-accent-blue/40 bg-accent-blue/15 px-2.5 py-1 text-[12px] font-semibold text-accent-blue hover:bg-accent-blue/25"
    >
      <Maximize2 size={13} />
      Action Window
    </button>
  );
}
