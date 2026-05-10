/**
 * Notifications tab — live from `GET /api/notifications`.
 *
 * Renders the full notification inbox (severity, title, message, ts) with
 * read/unread separation. The compact `NotificationCenter` component is used
 * for the Dashboard mini-panel; this tab is the standalone view with filters
 * + search.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bell, CheckCircle2, Info, RefreshCw, XCircle } from "lucide-react";
import { adapters } from "../api/adapters";
import type { Notification, NotificationSeverity } from "../types/notification";

const REFRESH_INTERVAL_MS = 15_000;
const SEVERITIES: NotificationSeverity[] = ["error", "warn", "info", "success"];

const SEVERITY_ICON: Record<NotificationSeverity, typeof Info> = {
  info: Info,
  success: CheckCircle2,
  warn: AlertTriangle,
  error: XCircle,
};
const SEVERITY_TONE: Record<NotificationSeverity, string> = {
  info: "text-accent-cyan",
  success: "text-accent-green",
  warn: "text-accent-amber",
  error: "text-accent-red",
};
const SEVERITY_BORDER: Record<NotificationSeverity, string> = {
  info: "border-accent-cyan/30",
  success: "border-accent-green/30",
  warn: "border-accent-amber/30",
  error: "border-accent-red/30",
};

export function NotificationsTab() {
  const [items, setItems] = useState<Notification[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<Set<NotificationSeverity>>(() => new Set(SEVERITIES));
  const [showRead, setShowRead] = useState<boolean>(true);
  const [search, setSearch] = useState<string>("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await adapters.getNotifications();
      setItems(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const t = window.setInterval(() => void refresh(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(t);
  }, [refresh]);

  const filtered = useMemo(() => {
    if (!items) return [];
    const q = search.trim().toLowerCase();
    return items.filter((n) => {
      if (!severityFilter.has(n.severity)) return false;
      if (!showRead && n.read) return false;
      if (q) {
        const hay = `${n.title} ${n.message}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [items, severityFilter, showRead, search]);

  const counts = useMemo(() => {
    const c = { unread: 0, urgent: 0, total: items?.length ?? 0 };
    for (const n of items ?? []) {
      if (!n.read) c.unread += 1;
      if (n.severity === "error" || n.severity === "warn") c.urgent += 1;
    }
    return c;
  }, [items]);

  const toggleSeverity = (s: NotificationSeverity) => {
    setSeverityFilter((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  return (
    <div data-testid="notifications-root" className="flex h-full flex-col gap-3">
      <header className="rounded border border-border bg-surface p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-fg">
              <Bell size={14} className="text-muted" />
              Notifications
            </h2>
            <p className="text-xs text-muted">
              Live from <code className="font-mono text-[10px]">GET /api/notifications</code>
              {items ? ` · ${counts.total} total · ${counts.unread} unread · ${counts.urgent} urgent` : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={loading}
            data-testid="notifications-refresh"
            className="flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[11px] text-muted hover:border-accent-cyan/40 hover:text-fg disabled:opacity-50"
          >
            <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap items-center gap-1" data-testid="notifications-severity-filters">
            {SEVERITIES.map((s) => {
              const on = severityFilter.has(s);
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => toggleSeverity(s)}
                  aria-pressed={on}
                  data-testid={`notifications-severity-${s}`}
                  className={[
                    "rounded px-2 py-0.5 text-[10px] uppercase",
                    on ? `${SEVERITY_TONE[s]} bg-surface2 ring-1 ring-border` : "text-muted",
                  ].join(" ")}
                >
                  {s}
                </button>
              );
            })}
          </div>
          <label className="flex items-center gap-1.5 text-[11px] text-muted">
            <input
              type="checkbox"
              checked={showRead}
              onChange={(e) => setShowRead(e.target.checked)}
              data-testid="notifications-show-read"
            />
            Show read
          </label>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search…"
            aria-label="Search notifications"
            data-testid="notifications-search"
            className="ml-auto w-40 rounded border border-border bg-bg px-2 py-0.5 text-[11px] text-fg placeholder:text-muted"
          />
        </div>
      </header>

      {error && (
        <div role="alert" data-testid="notifications-error" className="rounded border border-red-800/50 bg-red-950/30 p-2 font-mono text-[11px] text-red-200">
          {error}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-auto rounded border border-border bg-surface">
        {items === null ? (
          <div className="p-3 text-xs text-muted">Loading…</div>
        ) : filtered.length === 0 ? (
          <div data-testid="notifications-empty" className="p-3 text-xs text-muted">
            {items.length === 0
              ? "GET /api/notifications returned no entries."
              : "No notifications match the current filters."}
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {filtered.map((n) => {
              const Icon = SEVERITY_ICON[n.severity];
              return (
                <li
                  key={n.id}
                  data-testid={`notifications-item-${n.id}`}
                  className={`flex items-start gap-3 border-l-2 px-3 py-2 text-xs ${SEVERITY_BORDER[n.severity]}`}
                >
                  <Icon size={14} className={`${SEVERITY_TONE[n.severity]} mt-0.5 shrink-0`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-semibold text-fg">{n.title}</span>
                      {!n.read && (
                        <span className="h-1.5 w-1.5 rounded-full bg-accent-amber" aria-label="Unread" />
                      )}
                      {n.priority && (
                        <span className="rounded bg-bg/40 px-1.5 py-0.5 font-mono text-[9px] uppercase text-muted">
                          {n.priority}
                        </span>
                      )}
                    </div>
                    <p className="text-muted">{n.message}</p>
                    <div className="mt-0.5 flex flex-wrap items-center gap-2 font-mono text-[10px] text-muted">
                      <span>{n.ts_utc}</span>
                      {n.source_tab && <span>tab: {n.source_tab}</span>}
                      {n.source_agent_id && <span>agent: {n.source_agent_id}</span>}
                    </div>
                  </div>
                  {n.action_url && (
                    <a
                      href={n.action_url}
                      target="_blank"
                      rel="noreferrer"
                      className="shrink-0 rounded border border-border px-2 py-1 text-[10px] text-fg hover:border-accent-cyan/40"
                    >
                      {n.action_label ?? "Open"}
                    </a>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
