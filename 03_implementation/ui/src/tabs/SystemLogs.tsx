/**
 * System Logs tab — live tail from `GET /api/logs`.
 *
 * Renders the unified log envelope (level, source, message, ts_utc) that the
 * dashboard's mini panel already consumes. This tab adds:
 *   - level/source filters (computed from the actual returned data — no
 *     hard-coded enum that could lie if the backend introduces new sources),
 *   - free-text search,
 *   - pause toggle for auto-refresh,
 *   - explicit empty/error states.
 *
 * No mock data; the empty state describes what the API returned.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Pause, Play, RefreshCw } from "lucide-react";
import { adapters } from "../api/adapters";
import type { LogEntry, LogLevel } from "../types/log";

const REFRESH_INTERVAL_MS = 5_000;
const LEVELS: LogLevel[] = ["error", "warn", "info", "debug"];

const LEVEL_CLASS: Record<LogLevel, string> = {
  error: "text-accent-red",
  warn: "text-accent-amber",
  info: "text-fg",
  debug: "text-muted",
};

export function SystemLogsTab() {
  const [logs, setLogs] = useState<LogEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [levelFilter, setLevelFilter] = useState<Set<LogLevel>>(() => new Set(LEVELS));
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [search, setSearch] = useState<string>("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await adapters.getLogs();
      setLogs(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load logs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (paused) return;
    const t = window.setInterval(() => void refresh(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(t);
  }, [paused, refresh]);

  // Build source filter options from actual data (avoids fake hard-coded
  // sources that the backend may not emit).
  const sources = useMemo(() => {
    if (!logs) return [];
    const set = new Set<string>();
    for (const l of logs) set.add(l.source);
    return Array.from(set).sort();
  }, [logs]);

  const filtered = useMemo(() => {
    if (!logs) return [];
    const q = search.trim().toLowerCase();
    return logs.filter((l) => {
      if (!levelFilter.has(l.level)) return false;
      if (sourceFilter && l.source !== sourceFilter) return false;
      if (q && !l.message.toLowerCase().includes(q) && !l.source.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });
  }, [logs, levelFilter, sourceFilter, search]);

  const toggleLevel = (lvl: LogLevel) => {
    setLevelFilter((prev) => {
      const next = new Set(prev);
      if (next.has(lvl)) next.delete(lvl);
      else next.add(lvl);
      return next;
    });
  };

  return (
    <div data-testid="system-logs-root" className="flex h-full flex-col gap-3">
      <header className="rounded border border-border bg-surface p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-fg">System Logs</h2>
            <p className="text-xs text-muted">
              Live from <code className="font-mono text-[10px]">GET /api/logs</code>
              {logs ? ` · ${logs.length} returned · ${filtered.length} visible` : ""}
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => void refresh()}
              disabled={loading}
              data-testid="system-logs-refresh"
              className="flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[11px] text-muted hover:border-accent-cyan/40 hover:text-fg disabled:opacity-50"
            >
              <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
            <button
              type="button"
              onClick={() => setPaused((v) => !v)}
              aria-pressed={paused}
              data-testid="system-logs-pause"
              className={[
                "flex items-center gap-1.5 rounded border px-2 py-1 text-[11px]",
                paused
                  ? "border-accent-amber/40 text-accent-amber"
                  : "border-border text-muted hover:border-accent-cyan/40 hover:text-fg",
              ].join(" ")}
            >
              {paused ? <Play size={11} /> : <Pause size={11} />}
              {paused ? "Paused" : "Auto 5s"}
            </button>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap items-center gap-1" data-testid="system-logs-level-filters">
            {LEVELS.map((lvl) => {
              const on = levelFilter.has(lvl);
              return (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => toggleLevel(lvl)}
                  data-testid={`system-logs-level-${lvl}`}
                  aria-pressed={on}
                  className={[
                    "rounded px-2 py-0.5 text-[10px] uppercase",
                    on
                      ? `${LEVEL_CLASS[lvl]} bg-surface2 ring-1 ring-border`
                      : "text-muted",
                  ].join(" ")}
                >
                  {lvl}
                </button>
              );
            })}
          </div>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            aria-label="Filter logs by source"
            data-testid="system-logs-source-filter"
            className="rounded border border-border bg-bg px-2 py-0.5 text-[11px] text-fg"
          >
            <option value="">All sources</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search…"
            aria-label="Search log messages"
            data-testid="system-logs-search"
            className="ml-auto w-40 rounded border border-border bg-bg px-2 py-0.5 text-[11px] text-fg placeholder:text-muted"
          />
        </div>
      </header>

      {error && (
        <div role="alert" data-testid="system-logs-error" className="rounded border border-red-800/50 bg-red-950/30 p-2 font-mono text-[11px] text-red-200">
          {error}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-auto rounded border border-border bg-surface font-mono text-[11px]">
        {logs === null ? (
          <div className="p-3 text-muted">Loading…</div>
        ) : filtered.length === 0 ? (
          <div data-testid="system-logs-empty" className="p-3 text-muted">
            {logs.length === 0
              ? "GET /api/logs returned no entries."
              : "No log entries match the current filters."}
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {filtered.map((l, i) => (
              <li
                key={`${l.ts_utc}-${i}`}
                data-testid={`system-logs-entry`}
                className="grid grid-cols-[120px_70px_120px_1fr] gap-2 px-3 py-1 hover:bg-surface2/40"
              >
                <span className="truncate text-muted">{shortTs(l.ts_utc)}</span>
                <span className={`shrink-0 uppercase ${LEVEL_CLASS[l.level] ?? "text-fg"}`}>{l.level}</span>
                <span className="truncate text-muted">{l.source}</span>
                <span className="break-words text-fg">{l.message}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function shortTs(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleTimeString();
}
