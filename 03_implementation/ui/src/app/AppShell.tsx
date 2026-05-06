import type { ReactNode } from "react";
import { Sidebar } from "../components/layout/Sidebar";
import { TopBar } from "../components/layout/TopBar";
import { TABS } from "./routes";
import { useStore } from "./store";

/**
 * Universal shell per `TAB_SPECS.md` §"Universal shell":
 *  - Left vertical sidebar with icons + labels.
 *  - Top header with system state, branch/release, proof status.
 *  - Main content uses responsive grid cards.
 *  - Right inspector rail appears where helpful (per-tab, not in shell).
 */
export function AppShell({ children }: { children?: ReactNode }) {
  const activeTabId = useStore((s) => s.activeTabId);
  const activeTab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];
  const dashboard = activeTab.id === "dashboard";

  return (
    <div className="flex h-screen overflow-hidden bg-bg text-fg">
      <Sidebar />
      <div className="flex min-h-0 flex-1 flex-col">
        <TopBar activeLabel={activeTab.label} />
        <main className={dashboard ? "min-h-0 flex-1 overflow-auto p-2.5 lg:overflow-hidden" : "min-h-0 flex-1 overflow-auto p-2.5"}>
          {children}
        </main>
      </div>
    </div>
  );
}
