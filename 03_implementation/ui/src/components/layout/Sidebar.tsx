import { PRIMARY_TABS, type TabDef } from "../../app/routes";
import { useStore } from "../../app/store";
import { AgentChatMirror } from "../agents/AgentChatMirror";
import { ResizablePane } from "./ResizablePane";

export function Sidebar() {
  const { activeTabId, setActiveTabId } = useStore();

  return (
    <ResizablePane
      storageKey="h3d.mainSidebar.width"
      defaultWidth={260}
      minWidth={200}
      maxWidth={560}
      label="left panel"
      role="navigation"
      dataTestId="main-left-rail"
      className="flex h-screen min-h-0 w-[var(--pane-width)] shrink-0 flex-col border-r border-border bg-surface"
      ariaLabel="Primary navigation"
    >
      <div className="shrink-0 border-b border-border px-4 py-4">
        <div className="text-fg font-semibold tracking-tight">HERMES3D OS</div>
        <div className="text-muted text-xs mt-0.5">v5.3</div>
      </div>
      <nav className="min-h-0 flex-1 overflow-y-auto py-2">
        {PRIMARY_TABS.map((tab) => (
          <SidebarRow
            key={tab.id}
            tab={tab}
            active={tab.id === activeTabId}
            onSelect={() => setActiveTabId(tab.id)}
          />
        ))}
      </nav>
      <AgentChatMirror />
    </ResizablePane>
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
        "w-full flex items-center gap-3 px-4 py-2.5 text-[13px] transition-colors",
        active
          ? "bg-surface2 text-fg font-semibold shadow-glow border-l-2 border-accent-cyan"
          : "text-muted hover:bg-surface2 hover:text-fg border-l-2 border-transparent",
      ].join(" ")}
    >
      <Icon size={18} className="shrink-0" />
      <span className="truncate">{tab.label}</span>
    </button>
  );
}
