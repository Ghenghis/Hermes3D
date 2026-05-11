/**
 * W18-A25 — composition wrapper around AgentsTab that prepends the
 * active-tasks panel.
 *
 * Why a wrapper and not an edit to Agents.tsx? Agents.tsx is currently
 * locked by w18-a21 (W18-A21-PROVIDERS-HEALTH-GUI-2026-05-11). To avoid a
 * lock collision and a forced handoff round, we mount the new
 * ActiveTasksPanel at the top of the #agents tab via this wrapper, which
 * is what the App.tsx tab-router renders for the "agents" tab.
 *
 * Visual contract: the panel renders ABOVE the existing AGENT COMMAND
 * CENTER so the operator sees the live team-task work first when the
 * tab opens. The HermesAgentVersionRibbon is still the top-most element
 * because it lives inside the AgentsTab.
 *
 * No printer-control endpoints touched. No mocks.
 */
import { AgentsTab } from "../../tabs/Agents";
import { ActiveTasksPanel } from "./ActiveTasksPanel";

export function AgentsTabWithActiveTasks() {
  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="agents-tab-with-active-tasks">
      <div className="col-span-12">
        <ActiveTasksPanel />
      </div>
      <div className="col-span-12">
        <AgentsTab />
      </div>
    </div>
  );
}
