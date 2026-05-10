import { Bell, Clock3, ShieldCheck } from "lucide-react";
import { StatusBadge } from "../badges/StatusBadge";
import type { Notification } from "../../types/notification";

export function WhileAwayBanner({ notifications }: { notifications: Notification[] }) {
  const unread = notifications.filter((item) => !item.read).length;
  const risk = notifications.some((item) => item.severity === "error" || item.severity === "warn");

  return (
    <section
      className="col-span-12 rounded-card border border-border bg-surface px-3 py-2"
      aria-label="While-away summary"
      data-testid="while-away-banner"
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <Clock3 size={15} className="shrink-0 text-accent-cyan" />
          <span className="truncate font-semibold text-fg">While away</span>
          <span className="truncate text-muted">Showing live notification state from the backend.</span>
        </div>
        <StatusBadge tone={risk ? "amber" : "green"} label={risk ? "review needed" : "clear"} />
        <div className="flex items-center gap-1 rounded bg-surface2 px-2 py-1 text-muted">
          <Bell size={12} />
          <span>{unread} unread</span>
        </div>
        <div className="flex items-center gap-1 rounded bg-surface2 px-2 py-1 text-muted">
          <ShieldCheck size={12} />
          <span>write-safe</span>
        </div>
      </div>
    </section>
  );
}
