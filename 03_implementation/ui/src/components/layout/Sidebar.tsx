import { PRIMARY_TABS, type TabDef } from "../../app/routes";
import { useStore } from "../../app/store";
import { AgentChatMirror } from "../agents/AgentChatMirror";
import { HermesAgentBanner } from "../agents/HermesAgentBanner";
import { ResizablePane } from "./ResizablePane";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useEffect, useState } from "react";

const SIDEBAR_COLLAPSED_KEY = "h3d.mainSidebar.collapsed";

// W15-A11: Sidebar defaultWidth lowered 260 -> 220 to match the Images-GUI
// reference sidebar (~12% of viewport — 152px at 1280, 220 at 1536, 228 at
// 1920). Per W14-A4 rank 2 HIGH-confidence finding. Persisted user-resize
// widths in `h3d.mainSidebar.width` localStorage continue to override this
// default — only fresh sessions pick up the new value.
export function Sidebar() {
  const { activeTabId, setActiveTabId } = useStore();
  const [collapsed, setCollapsed] = useState(() => readSidebarCollapsed());

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
    } catch {
      /* local shell preference is best-effort */
    }
  }, [collapsed]);

  if (collapsed) {
    return (
      <aside
        aria-label="Collapsed primary navigation"
        data-testid="main-left-rail"
        data-collapsed="true"
        className="flex h-screen w-12 shrink-0 flex-col items-center border-r border-border bg-surface"
      >
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="mt-3 rounded border border-border bg-bg/50 p-2 text-muted hover:bg-surface2 hover:text-fg"
          title="Open left panel"
          aria-label="Open left panel"
        >
          <PanelLeftOpen size={17} />
        </button>
        <nav className="mt-3 flex min-h-0 flex-1 flex-col items-center gap-1 overflow-y-auto px-1 pb-3">
          {PRIMARY_TABS.map((tab) => (
            <SidebarIconRow
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

  return (
    <ResizablePane
      storageKey="h3d.mainSidebar.width"
      defaultWidth={220}
      minWidth={200}
      maxWidth={560}
      label="left panel"
      role="navigation"
      dataTestId="main-left-rail"
      className="flex h-screen min-h-0 w-[var(--pane-width)] shrink-0 flex-col border-r border-border bg-surface"
      ariaLabel="Primary navigation"
    >
      <div className="shrink-0 border-b border-border px-4 py-4">
        <div className="flex items-center justify-between gap-2">
          <div className="text-fg font-semibold tracking-tight">HERMES3D OS</div>
          <button
            type="button"
            onClick={() => setCollapsed(true)}
            className="rounded border border-border bg-bg/40 p-1.5 text-muted hover:bg-surface2 hover:text-fg"
            title="Close left panel"
            aria-label="Close left panel"
          >
            <PanelLeftClose size={15} />
          </button>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className="text-muted text-xs">v5.3</span>
          {/* W6-5: live Hermes Agent banner. Polls /api/agents/update/status. */}
          <HermesAgentBanner compact />
        </div>
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
      <div className="min-h-0 shrink overflow-hidden">
        <AgentChatMirror />
      </div>
    </ResizablePane>
  );
}

function readSidebarCollapsed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
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

function SidebarIconRow({
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
      title={tab.label}
      aria-label={tab.label}
      className={[
        "grid h-9 w-9 place-items-center rounded border text-[13px] transition-colors",
        active
          ? "border-accent-cyan/60 bg-surface2 text-fg shadow-glow"
          : "border-transparent text-muted hover:border-border hover:bg-surface2 hover:text-fg",
      ].join(" ")}
    >
      <Icon size={18} />
    </button>
  );
}
