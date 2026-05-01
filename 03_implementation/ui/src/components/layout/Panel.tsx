import { ChevronDown, MoreHorizontal } from "lucide-react";
import type { ReactNode } from "react";
import { useStore } from "../../app/store";
import { DockModeToggle } from "../dock/DockModeToggle";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";

/**
 * Generic panel wrapper per `TAB_SPECS.md` §"Universal shell":
 *   "Every panel has: title, status badge, actions menu, collapse, undock,
 *    fullscreen."
 *
 * Phase 2 ships CSS-only dock/undock/fullscreen via the zustand store. Native
 * detached windows land in a later phase; the contract surface stays stable.
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
};

export function Panel({
  id,
  title,
  status,
  headerExtra,
  children,
  className,
}: PanelProps) {
  const dock = useStore((s) => s.panelDock[id] ?? "docked");
  const isFullscreen = dock === "external"; // CSS-only fullscreen in Phase 2

  return (
    <section
      className={[
        "bg-surface border border-border rounded-card overflow-hidden flex flex-col",
        isFullscreen ? "fixed inset-4 z-40 shadow-glow" : "",
        className ?? "",
      ].join(" ")}
      aria-label={title}
    >
      <header className="h-10 px-4 flex items-center justify-between border-b border-border shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-fg text-sm font-semibold truncate">{title}</span>
          {status && <StatusBadge tone={status.tone} label={status.label} />}
        </div>
        <div className="flex items-center gap-2">
          {headerExtra}
          <DockModeToggle panelId={id} />
          <button
            type="button"
            aria-label="Collapse panel"
            className="text-muted hover:text-fg p-1"
          >
            <ChevronDown size={14} />
          </button>
          <button
            type="button"
            aria-label="More actions"
            className="text-muted hover:text-fg p-1"
          >
            <MoreHorizontal size={14} />
          </button>
        </div>
      </header>
      <div className="flex-1 p-4 overflow-auto">{children}</div>
    </section>
  );
}
