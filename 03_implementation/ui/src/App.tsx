import { AppShell } from "./app/AppShell";
import { TABS } from "./app/routes";
import { TAB_TO_HASH, tabIdFromHash, useStore } from "./app/store";
import { SimpleHermesDashboard } from "./components/simple/SimpleHermesDashboard";
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
  const tab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];
  const Component = TAB_COMPONENTS[tab.id] ?? UnavailableTab;

  useEffect(() => {
    const syncFromHash = () => {
      const nextTabId = tabIdFromHash(window.location.hash);
      if (nextTabId && nextTabId !== useStore.getState().activeTabId) {
        setActiveTabId(nextTabId);
      }
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    window.addEventListener("popstate", syncFromHash);
    const syncTimer = window.setInterval(syncFromHash, 500);
    return () => {
      window.removeEventListener("hashchange", syncFromHash);
      window.removeEventListener("popstate", syncFromHash);
      window.clearInterval(syncTimer);
    };
  }, [setActiveTabId]);

  useEffect(() => {
    const nextHash = `#${TAB_TO_HASH[activeTabId] ?? activeTabId}`;
    if (window.location.hash !== nextHash) {
      window.history.replaceState(null, "", nextHash);
    }
  }, [activeTabId]);

  if (uiMode === "simple") {
    return <SimpleHermesDashboard activeTabId={tab.id} activeLabel={tab.label} Content={Component} />;
  }

  return (
    <AppShell>
      <Component />
    </AppShell>
  );
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
