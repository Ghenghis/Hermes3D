import { AppShell } from "./app/AppShell";
import { TABS } from "./app/routes";
import { useStore } from "./app/store";

/**
 * Phase 2 Tasks 6-12 deliver the shell + reusable primitives only. Tab
 * content lands in Tasks 19+ — for now, every tab renders the placeholder
 * below so the shell + sidebar nav can be visually verified.
 */
export default function App() {
  const activeTabId = useStore((s) => s.activeTabId);
  const tab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];
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
          Content lands in Phase 2 Tasks 19+. Shell + reusable primitives are in place
          (CHECKPOINT 2 of 7).
        </div>
      </div>
    </div>
  );
}
