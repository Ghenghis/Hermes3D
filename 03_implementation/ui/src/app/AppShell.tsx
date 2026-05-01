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

  return (
    <div className="min-h-screen flex bg-bg text-fg">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar activeLabel={activeTab.label} />
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
