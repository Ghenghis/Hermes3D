import { TABS, type TabDef } from "../../app/routes";
import { useStore } from "../../app/store";

/**
 * Left rail per visual contract: ~220px wide, dense vertical list of 13 tabs,
 * each row with lucide icon + label. Active row gets a cyan-glow ring + bold
 * text. Bottom slot reserved for "Quick Actions" / "Truth Engine" badges
 * (lands with Dashboard tab in Task 19+).
 */
export function Sidebar() {
  const { activeTabId, setActiveTabId } = useStore();
  return (
    <aside
      className="w-[220px] shrink-0 border-r border-border bg-surface flex flex-col"
      aria-label="Primary navigation"
    >
      <div className="px-4 py-4 border-b border-border">
        <div className="text-fg font-semibold tracking-tight">HERMES3D OS</div>
        <div className="text-muted text-xs mt-0.5">v5.3</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {TABS.map((tab) => (
          <SidebarRow
            key={tab.id}
            tab={tab}
            active={tab.id === activeTabId}
            onSelect={() => setActiveTabId(tab.id)}
          />
        ))}
      </nav>
    </aside>
  );
}

function SidebarRow({
  tab,
  active,
  onSelect,
}: {
  tab: TabDef;
  active: boolean;
  onSelect: () => void;
}) {
  const Icon = tab.icon;
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={active ? "page" : undefined}
      className={[
        "w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors",
        active
          ? "bg-surface2 text-fg font-semibold shadow-glow border-l-2 border-accent-cyan"
          : "text-muted hover:bg-surface2 hover:text-fg border-l-2 border-transparent",
      ].join(" ")}
    >
      <Icon size={18} />
      <span className="truncate">{tab.label}</span>
    </button>
  );
}
