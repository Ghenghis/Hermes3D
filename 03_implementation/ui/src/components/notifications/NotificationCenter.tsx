import { AlertTriangle, Bell, CheckCircle2, Info, XCircle } from "lucide-react";
import { StatusBadge } from "../badges/StatusBadge";
import { Panel } from "../layout/Panel";
import type { Notification, NotificationSeverity } from "../../types/notification";

const NOTIFICATION_ICON: Record<NotificationSeverity, typeof Info> = {
  info: Info,
  success: CheckCircle2,
  warn: AlertTriangle,
  error: XCircle,
};

const NOTIFICATION_TONE: Record<NotificationSeverity, string> = {
  info: "text-accent-cyan",
  success: "text-accent-green",
  warn: "text-accent-amber",
  error: "text-accent-red",
};

export function NotificationCenter({ notifications }: { notifications: Notification[] }) {
  const unread = notifications.filter((item) => !item.read).length;
  const urgent = notifications.filter((item) => item.severity === "error" || item.severity === "warn").length;

  return (
    <Panel
      id="notifications.center"
      title="NOTIFICATION CENTER"
      dense
      status={{ tone: unread > 0 ? "amber" : "muted", label: `${unread} unread` }}
      headerExtra={<Bell size={12} className="text-muted" />}
      className="h-[360px]"
    >
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_180px] gap-2 h-full min-h-0">
        {notifications.length > 0 ? (
          <ul className="flex flex-col gap-1.5 overflow-auto">
            {notifications.map((item) => (
              <NotificationRow key={item.id} item={item} />
            ))}
          </ul>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-1 text-center text-xs">
            <div className="font-medium text-fg">No notifications</div>
            <div className="max-w-[260px] text-muted">The live notification inbox is empty or unavailable.</div>
          </div>
        )}
        <aside className="rounded border border-border bg-surface2/30 p-2 text-xs">
          <div className="text-[10px] uppercase text-muted">Routes</div>
          <div className="mt-2 flex flex-col gap-1.5">
            <RouteRow name="UI inbox" state="armed" />
            <RouteRow name="Discord" state="env gated" />
            <RouteRow name="Slack" state="env gated" />
            <RouteRow name="Generic webhook" state="env gated" />
          </div>
          <div className="mt-3 border-t border-border pt-2">
            <StatusBadge tone={urgent > 0 ? "amber" : "green"} label={`${urgent} needs review`} />
          </div>
        </aside>
      </div>
    </Panel>
  );
}

function NotificationRow({ item }: { item: Notification }) {
  const Icon = NOTIFICATION_ICON[item.severity];

  return (
    <li className="flex items-start gap-2 rounded border border-border bg-surface2/40 px-2 py-1.5 text-xs">
      <Icon size={14} className={`${NOTIFICATION_TONE[item.severity]} mt-0.5 shrink-0`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate font-semibold text-fg">{item.title}</span>
          {!item.read && <span className="h-1.5 w-1.5 rounded-full bg-accent-amber" aria-label="Unread" />}
        </div>
        <div className="truncate text-muted">{item.message}</div>
        <div className="mt-0.5 font-mono text-[10px] text-muted">{item.ts_utc}</div>
      </div>
    </li>
  );
}

function RouteRow({ name, state }: { name: string; state: string }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded bg-surface px-2 py-1">
      <span className="truncate text-fg">{name}</span>
      <span className="shrink-0 text-[10px] uppercase text-muted">{state}</span>
    </div>
  );
}
