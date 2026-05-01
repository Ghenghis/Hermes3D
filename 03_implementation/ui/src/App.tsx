import { AppShell } from "./app/AppShell";
import { TABS } from "./app/routes";
import { useStore } from "./app/store";
import { Dashboard } from "./tabs/Dashboard";

/**
 * Phase 2 routing. Dashboard tab renders the recreated UI-Final dashboard
 * (Tasks 19-26). All other tabs still show the placeholder until their own
 * checkpoint (Tasks 27-38).
 */
export default function App() {
  const activeTabId = useStore((s) => s.activeTabId);
  const tab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];

  if (tab.id === "dashboard") {
    return (
      <AppShell>
        <Dashboard />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <TabPlaceholder label={tab.label} />
    </AppShell>
  );
}

function TabPlaceholder({ label }: { label: string }) {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <div className="text-muted text-sm uppercase tracking-wide">Tab</div>
        <div className="text-fg text-3xl font-bold mt-1">{label}</div>
        <div className="text-muted text-sm mt-3 max-w-md">
          Content lands in Phase 2 Tasks 27-38. Shell + reusable primitives + Dashboard
          (CHECKPOINT 4) are in place.
        </div>
      </div>
    </div>
  );
}
