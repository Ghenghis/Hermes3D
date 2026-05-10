import { AppShell } from "./app/AppShell";
import { TABS } from "./app/routes";
import { TAB_TO_HASH, tabIdFromHash, useStore } from "./app/store";
import { SimpleHermesDashboard } from "./components/simple/SimpleHermesDashboard";
import { DashboardSimple } from "./components/dashboard/DashboardSimple";
import { DashboardAdvanced } from "./components/dashboard/DashboardAdvanced";
import { DashboardCustom } from "./components/dashboard/DashboardCustom";
import {
  modeFromHash as dashboardModeFromHash,
  modeFromQueryString,
  useDashboardModeStore,
} from "./components/dashboard/dashboardModeStore";
import { SourceOSTab } from "./tabs/SourceOS";
import { Dashboard } from "./tabs/Dashboard";
import { AutopilotTab } from "./tabs/Autopilot";
import { DesignTab } from "./tabs/Design";
import { Gen3DTab } from "./tabs/Gen3D";
import { JobsTab } from "./tabs/Jobs";
import { PrintersTab } from "./tabs/Printers";
import { ObserveTab } from "./tabs/Observe";
import { VoiceTab } from "./tabs/Voice";
import { AgentsTab } from "./tabs/Agents";
import { LearningTab } from "./tabs/Learning";
import { ArtifactsTab } from "./tabs/Artifacts";
import { ApprovalsTab } from "./tabs/Approvals";
import { PluginsTab } from "./tabs/Plugins";
import { SettingsTab } from "./tabs/Settings";
import { RoadmapTab } from "./tabs/Roadmap";
import { useEffect } from "react";

const TAB_COMPONENTS: Record<string, () => JSX.Element> = {
  source_os: SourceOSTab,
  dashboard: Dashboard,
  autopilot: AutopilotTab,
  design: DesignTab,
  gen3d: Gen3DTab,
  jobs: JobsTab,
  printers: PrintersTab,
  observe: ObserveTab,
  voice: VoiceTab,
  agents: AgentsTab,
  learning: LearningTab,
  artifacts: ArtifactsTab,
  approvals: ApprovalsTab,
  plugins: PluginsTab,
  settings: SettingsTab,
  roadmap: RoadmapTab,
};

export default function App() {
  const activeTabId = useStore((s) => s.activeTabId);
  const setActiveTabId = useStore((s) => s.setActiveTabId);
  const uiMode = useStore((s) => s.uiMode);
  const dashboardMode = useDashboardModeStore((s) => s.mode);
  const setDashboardMode = useDashboardModeStore((s) => s.setMode);
  const tab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];
  const baseComponent = TAB_COMPONENTS[tab.id] ?? UnavailableTab;
  const Component =
    tab.id === "dashboard" && uiMode === "full"
      ? dashboardComponentFor(dashboardMode)
      : baseComponent;

  useEffect(() => {
    const syncFromUrl = () => {
      const nextTabId = tabIdFromHash(window.location.hash);
      if (nextTabId && nextTabId !== useStore.getState().activeTabId) {
        setActiveTabId(nextTabId);
      }
      // Dashboard mode can be controlled by either the hash (`#dashboard:custom`)
      // or the `?mode=` query string. The hash takes precedence so the mode
      // stays sticky across refresh of a deep link.
      const hashMode = dashboardModeFromHash(window.location.hash);
      const queryMode = modeFromQueryString(window.location.search);
      const nextMode = hashMode ?? queryMode;
      if (nextMode && nextMode !== useDashboardModeStore.getState().mode) {
        setDashboardMode(nextMode);
      }
    };
    syncFromUrl();
    window.addEventListener("hashchange", syncFromUrl);
    window.addEventListener("popstate", syncFromUrl);
    const syncTimer = window.setInterval(syncFromUrl, 500);
    return () => {
      window.removeEventListener("hashchange", syncFromUrl);
      window.removeEventListener("popstate", syncFromUrl);
      window.clearInterval(syncTimer);
    };
  }, [setActiveTabId, setDashboardMode]);

  useEffect(() => {
    // Keep the URL hash authoritative for the active tab and the dashboard
    // mode. We use replaceState (not pushState) so navigating tabs does not
    // pollute browser history with every click.
    const baseHash = TAB_TO_HASH[activeTabId] ?? activeTabId;
    const nextHash =
      activeTabId === "dashboard" && uiMode === "full"
        ? `#${baseHash}:${dashboardMode}`
        : `#${baseHash}`;
    if (window.location.hash !== nextHash) {
      window.history.replaceState(null, "", nextHash);
    }
  }, [activeTabId, dashboardMode, uiMode]);

  if (uiMode === "simple") {
    return <SimpleHermesDashboard activeTabId={tab.id} activeLabel={tab.label} Content={baseComponent} />;
  }

  return (
    <AppShell>
      <Component />
    </AppShell>
  );
}

function dashboardComponentFor(mode: "simple" | "advanced" | "custom"): () => JSX.Element {
  switch (mode) {
    case "simple":
      return DashboardSimple;
    case "custom":
      return DashboardCustom;
    case "advanced":
    default:
      return DashboardAdvanced;
  }
}

function UnavailableTab() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <div className="text-muted text-sm uppercase tracking-wide">Route unavailable</div>
        <div className="mt-1 text-sm font-semibold text-fg">The selected tab is not registered in the live router.</div>
      </div>
    </div>
  );
}
