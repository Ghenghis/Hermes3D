import { AppShell } from "./app/AppShell";
import { TABS } from "./app/routes";
import { useStore } from "./app/store";
import { Dashboard } from "./tabs/Dashboard";
import { AgentsTab } from "./tabs/Agents";
import { WorkflowsTab } from "./tabs/Workflows";
import { Gen3DTab } from "./tabs/Gen3D";
import { BlenderMCPTab } from "./tabs/BlenderMCP";
import { SlicingTab } from "./tabs/Slicing";
import { FleetTab } from "./tabs/Fleet";
import { PrintQueueTab } from "./tabs/PrintQueue";
import { PrinterControlTab } from "./tabs/PrinterControl";
import { DockedAppsTab } from "./tabs/DockedApps";
import { ProofTab } from "./tabs/Proof";
import { SystemLogsTab } from "./tabs/SystemLogs";
import { SettingsTab } from "./tabs/Settings";
import { ServiceHealthPage } from "./components/health/ServiceHealthPage";

/**
 * Phase 2 Tasks 27-38: every sidebar tab routes to its own mock-only
 * component. No real adapter calls, no external launches — every panel
 * pulls from `src/data/mock/*` and dangerous actions render `LockedAction`.
 */
const TAB_COMPONENTS: Record<string, () => JSX.Element> = {
  dashboard: Dashboard,
  agents: AgentsTab,
  workflows: WorkflowsTab,
  gen3d: Gen3DTab,
  blender_mcp: BlenderMCPTab,
  slicing: SlicingTab,
  fleet: FleetTab,
  queue: PrintQueueTab,
  control: PrinterControlTab,
  docked: DockedAppsTab,
  proof: ProofTab,
  logs: SystemLogsTab,
  service_health: ServiceHealthPage,
  settings: SettingsTab,
};

export default function App() {
  const activeTabId = useStore((s) => s.activeTabId);
  const tab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];
  const Component = TAB_COMPONENTS[tab.id] ?? FallbackPlaceholder;

  return (
    <AppShell>
      <Component />
    </AppShell>
  );
}

function FallbackPlaceholder() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <div className="text-muted text-sm uppercase tracking-wide">Tab not found</div>
        <div className="text-fg text-2xl font-bold mt-1">unknown</div>
      </div>
    </div>
  );
}
