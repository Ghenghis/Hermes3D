import { ChevronDown, ChevronUp, MoreHorizontal } from "lucide-react";
import type { ReactNode } from "react";
import { useStore } from "../../app/store";
import { DockModeToggle } from "../dock/DockModeToggle";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";

/**
 * Generic panel wrapper per `TAB_SPECS.md` §"Universal shell":
 *   "Every panel has: title, status badge, actions menu, collapse, undock,
 *    fullscreen."
 *
 * Phase 2 dock state machine (see `app/store.ts` DockMode):
 *   - docked      → standard inline panel (default)
 *   - undocked    → CSS-only floating overlay (mock; Phase 3+ may wire native)
 *   - fullscreen  → CSS-only `fixed inset-4 z-40 shadow-glow` overlay
 *
 * Collapse state is independent and stored in `panelCollapsed`. Collapsed
 * panels keep header chrome visible but hide the body — header acts as a
 * preview row in dense lists.
 *
 * NO native windows, BrowserWindow, WebView, or external processes are
 * spawned — every transition is store-only and rendered via CSS.
 */
export type PanelProps = {
  id: string;
  title: string;
  status?: { tone: StatusTone; label: string };
  /** Optional right-aligned header content (filters, counts, etc.). */
  headerExtra?: ReactNode;
  children: ReactNode;
  /** Tailwind className(s) appended to the outer container. */
  className?: string;
  /** Tighter header (h-8) + content padding (p-2.5) — used by the dense Dashboard. */
  dense?: boolean;
};

export function Panel({
  id,
  title,
  status,
  headerExtra,
  children,
  className,
  dense = false,
}: PanelProps) {
  const dock = useStore((s) => s.panelDock[id] ?? "docked");
  const collapsed = useStore((s) => s.panelCollapsed[id] ?? false);
  const togglePanelCollapsed = useStore((s) => s.togglePanelCollapsed);

  const isFullscreen = dock === "fullscreen";
  const isUndocked = dock === "undocked";

  const headerCls = dense ? "h-8 px-3" : "h-10 px-4";
  const bodyCls = dense ? "flex-1 p-2.5 overflow-auto" : "flex-1 p-4 overflow-auto";

  const ChevronIcon = collapsed ? ChevronUp : ChevronDown;

  return (
    <section
      className={[
        "bg-surface border border-border rounded-card overflow-hidden flex flex-col",
        isFullscreen ? "" : (className ?? ""),
        // Fullscreen overrides any parent-supplied height/width with !important
        // so panels with `h-[300px]` etc. fill the viewport when expanded.
        isFullscreen ? "fixed inset-4 z-40 shadow-glow !h-auto !w-auto" : "",
        isUndocked ? "ring-1 ring-accent-cyan/30 shadow-glow" : "",
      ].join(" ")}
      aria-label={title}
      data-panel-id={id}
      data-dock-state={dock}
      data-collapsed={collapsed}
    >
      <header
        className={`${headerCls} flex items-center justify-between border-b border-border shrink-0`}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-fg text-[11px] font-semibold uppercase tracking-wide truncate">
            {title}
          </span>
          {status && <StatusBadge tone={status.tone} label={status.label} />}
        </div>
        <div className="flex items-center gap-1">
          {headerExtra}
          <DockModeToggle panelId={id} />
          <button
            type="button"
            aria-label={collapsed ? "Expand panel" : "Collapse panel"}
            aria-expanded={!collapsed}
            aria-controls={`panel-body-${id}`}
            title={collapsed ? "Expand panel body" : "Collapse panel body"}
            data-action="collapse"
            onClick={() => togglePanelCollapsed(id)}
            className="text-muted hover:text-fg p-1 rounded-sm transition-colors"
          >
            <ChevronIcon size={13} />
          </button>
          <button
            type="button"
            aria-label="More actions"
            title="Actions menu (Phase 3 wires the menu)"
            data-action="more"
            className="text-muted hover:text-fg p-1 rounded-sm"
          >
            <MoreHorizontal size={13} />
          </button>
        </div>
      </header>
      {!collapsed && (
        <div id={`panel-body-${id}`} className={bodyCls} data-panel-body>
          {children}
        </div>
      )}
    </section>
  );
}
