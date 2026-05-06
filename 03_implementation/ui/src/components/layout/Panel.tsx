import { ChevronDown, ChevronUp, MoreHorizontal } from "lucide-react";
import { useState, type ReactNode } from "react";
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
 *   - undocked    → CSS-only floating overlay
 *   - fullscreen  → CSS-only `fixed inset-4 z-40 shadow-glow` overlay
 *
 * Collapse state is independent and stored in `panelCollapsed`. Collapsed
 * panels keep header chrome visible but hide the body — header acts as a
 * preview row in dense lists.
 *
 * No launch-capable path exists in Phase 2; every transition is store-only
 * and rendered via CSS.
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
  const [actionsOpen, setActionsOpen] = useState(false);

  const isFullscreen = dock === "fullscreen";
  const isUndocked = dock === "undocked";

  const headerCls = dense ? "h-8 px-3" : "h-10 px-4";
  const bodyCls = dense ? "min-h-0 flex-1 overflow-hidden p-2.5" : "min-h-0 flex-1 overflow-auto p-4";

  const ChevronIcon = collapsed ? ChevronUp : ChevronDown;

  return (
    <section
      className={[
        "bg-surface border border-border rounded-card flex flex-col",
        actionsOpen ? "overflow-visible" : "overflow-hidden",
        isFullscreen ? "" : (className ?? ""),
        // Fullscreen overrides any parent-supplied height/width with !important
        // so panels with `h-[300px]` etc. fill the viewport when expanded.
        isFullscreen ? "fixed inset-4 z-40 shadow-glow !h-auto !w-auto" : "",
        isUndocked
          ? "fixed top-24 right-6 z-30 shadow-glow ring-1 ring-accent-cyan/30 !h-[min(560px,calc(100vh-7rem))] !w-[min(760px,calc(100vw-48px))]"
          : "",
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
          {status && (
            <span data-panel-header-status>
              <StatusBadge tone={status.tone} label={status.label} />
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {headerExtra}
          <DockModeToggle panelId={id} panelTitle={title} />
          <button
            type="button"
            aria-label={collapsed ? `Expand ${title} panel` : `Collapse ${title} panel`}
            aria-expanded={!collapsed}
            aria-controls={`panel-body-${id}`}
            title={collapsed ? `Expand ${title} panel body` : `Collapse ${title} panel body`}
            data-action="collapse"
            onClick={() => togglePanelCollapsed(id)}
            className="text-muted hover:text-fg p-1 rounded-sm transition-colors"
          >
            <ChevronIcon size={13} />
          </button>
          <div className="relative">
            <button
              type="button"
              aria-label={`Open actions menu for ${title}`}
              aria-haspopup="menu"
              aria-expanded={actionsOpen}
              title={`Actions menu for ${title}`}
              data-action="more"
              onClick={() => setActionsOpen((open) => !open)}
              className="text-muted hover:text-fg p-1 rounded-sm"
            >
              <MoreHorizontal size={13} />
            </button>
            {actionsOpen && (
              <div
                role="menu"
                aria-label={`${title} actions`}
                className="absolute right-0 top-7 z-50 w-44 rounded-md border border-border bg-surface shadow-glow p-1 text-[11px]"
              >
                <button
                  type="button"
                  role="menuitem"
                  disabled
                  aria-disabled="true"
                  title="Locked in Phase 2"
                  className="w-full rounded px-2 py-1 text-left text-muted opacity-70 cursor-not-allowed"
                >
                  Refresh unavailable
                </button>
                <button
                  type="button"
                  role="menuitem"
                  disabled
                  aria-disabled="true"
                  title="Locked in Phase 2"
                  className="w-full rounded px-2 py-1 text-left text-muted opacity-70 cursor-not-allowed"
                >
                  Capture proof snapshot
                </button>
                <button
                  type="button"
                  role="menuitem"
                  disabled
                  aria-disabled="true"
                  title="Locked in Phase 2"
                  className="w-full rounded px-2 py-1 text-left text-muted opacity-70 cursor-not-allowed"
                >
                  Launch surface
                </button>
              </div>
            )}
          </div>
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
