import { AppShell } from "./app/AppShell";
import { TABS, UTILITY_TAB_IDS } from "./app/routes";
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
import { AppRegistryTab } from "./tabs/AppRegistry";
import { PluginsTab } from "./tabs/Plugins";
import { SettingsTab } from "./tabs/Settings";
import { RoadmapTab } from "./tabs/Roadmap";
// ---- W15-A19 utility tabs ----
import { WorkflowsTab } from "./tabs/Workflows";
import { PrintQueueTab } from "./tabs/PrintQueue";
import { FilesTab } from "./tabs/Files";
import { SystemLogsTab } from "./tabs/SystemLogs";
import { ProofTab } from "./tabs/Proof";
import { ServiceHealthTab } from "./tabs/ServiceHealth";
import { NotificationsTab } from "./tabs/Notifications";
import { SafetyTab } from "./tabs/Safety";
import { useEffect } from "react";

/**
 * Hash routing for the W15-A19 utility tabs.
 *
 * The 8 utility tabs (workflows, print_queue, files, system_logs, proof,
 * service_health, notifications, safety) are intentionally NOT registered in
 * `store.ts#TAB_IDS` from this branch because A17 (Settings) currently holds
 * the lock on `store.ts` for adding settings subtab routing. To avoid a lock
 * contention we keep the utility-tab hash table here in App.tsx; A17's patch
 * is purely additive on a different part of the file, so a follow-up that
 * merges these entries into TAB_IDS after A17 lands is a trivial cherry-pick.
 *
 * Until that follow-up lands, the utility tabs are reached via this fallback
 * router — every utility tab still has an honest data-testid, hash, and
 * sidebar entry. The function delegates to the store's hash resolver first so
 * the "stock" tab list (dashboard, jobs, …) keeps working unchanged.
 */
const UTILITY_TAB_HASHES: Record<string, string> = {
  workflows: "workflows",
  print_queue: "print_queue",
  "print-queue": "print_queue",
  printqueue: "print_queue",
  queue: "print_queue",
  files: "files",
  system_logs: "system_logs",
  "system-logs": "system_logs",
  systemlogs: "system_logs",
  logs: "system_logs",
  proof: "proof",
  service_health: "service_health",
  "service-health": "service_health",
  servicehealth: "service_health",
  // NOTE: `#health` is intercepted by main.tsx today (W11-2 standalone gate);
  // when that gate is removed, this entry takes over and falls through to
  // the tab system. Both routes render the same `ServiceHealthPage`.
  health: "service_health",
  notifications: "notifications",
  notify: "notifications",
  safety: "safety",
};

function utilityTabIdFromHash(hash: string): string | null {
  const raw = hash.replace(/^#/, "").trim();
  if (!raw) return null;
  const head = raw.split(/[:/.]/, 1)[0] ?? raw;
  const id = UTILITY_TAB_HASHES[head.toLowerCase()];
  return id && UTILITY_TAB_IDS.includes(id) ? id : null;
}

function resolveTabIdFromHash(hash: string): string | null {
  return utilityTabIdFromHash(hash) ?? tabIdFromHash(hash);
}

const UTILITY_TAB_TO_HASH: Record<string, string> = {
  workflows: "workflows",
  print_queue: "print_queue",
  files: "files",
  system_logs: "system_logs",
  proof: "proof",
  service_health: "service_health",
  notifications: "notifications",
  safety: "safety",
};

function resolveTabToHash(tabId: string): string {
  return UTILITY_TAB_TO_HASH[tabId] ?? TAB_TO_HASH[tabId] ?? tabId;
}

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
  apps: AppRegistryTab,
  plugins: PluginsTab,
  // ---- W15-A19 utility tabs ----
  workflows: WorkflowsTab,
  print_queue: PrintQueueTab,
  files: FilesTab,
  system_logs: SystemLogsTab,
  proof: ProofTab,
  service_health: ServiceHealthTab,
  notifications: NotificationsTab,
  safety: SafetyTab,
  // ---- meta ----
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
      const nextTabId = resolveTabIdFromHash(window.location.hash);
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
    //
    // Tabs with nested routing (e.g. `#apps/<id>`) own their trailing
    // segment after a "/" separator. Only rewrite the hash when the head
    // segment doesn't already match the active tab.
    const baseHash = resolveTabToHash(activeTabId);
    const nextHash =
      activeTabId === "dashboard" && uiMode === "full"
        ? `#${baseHash}:${dashboardMode}`
        : `#${baseHash}`;
    const currentHead = window.location.hash.replace(/^#/, "").split("/", 2)[0] ?? "";
    const expectedHead = baseHash;
    if (currentHead === expectedHead) return;
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
