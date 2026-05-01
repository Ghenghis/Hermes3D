/**
 * System Logs tab — Phase 2 mock-only per TAB_SPECS.md §12.
 *
 * Unified logs · filters by level/source/search · export (locked).
 */
import { useMemo, useState } from "react";
import { Panel } from "../components/layout/Panel";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { LockedAction } from "../components/badges/LockedAction";
import { MOCK_LOGS } from "../data/mock/logs";
import type { LogLevel } from "../types/log";
import { Search } from "lucide-react";

const LEVEL_TONE: Record<LogLevel, StatusTone> = {
  info: "cyan",
  warn: "amber",
  error: "red",
  debug: "muted",
};

const LEVELS: LogLevel[] = ["info", "warn", "error", "debug"];

export function SystemLogsTab() {
  const [levelFilter, setLevelFilter] = useState<Set<LogLevel>>(new Set(LEVELS));
  const [search, setSearch] = useState("");

  const sources = useMemo(
    () => Array.from(new Set(MOCK_LOGS.map((l) => l.source))).sort(),
    [],
  );
  const filtered = MOCK_LOGS.filter(
    (l) =>
      levelFilter.has(l.level) &&
      (search === "" ||
        l.message.toLowerCase().includes(search.toLowerCase()) ||
        l.source.toLowerCase().includes(search.toLowerCase())),
  );

  const counts = LEVELS.reduce(
    (acc, lvl) => {
      acc[lvl] = MOCK_LOGS.filter((l) => l.level === lvl).length;
      return acc;
    },
    {} as Record<LogLevel, number>,
  );

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="logs-root">
      <div className="col-span-12 lg:col-span-3">
        <Panel
          id="logs.filters"
          title="FILTERS"
          dense
          status={{ tone: "cyan", label: `${filtered.length}/${MOCK_LOGS.length}` }}
          className="h-[480px]"
        >
          <div className="flex flex-col gap-3 h-full text-xs">
            <div className="flex flex-col gap-1.5">
              <div className="text-muted text-[10px] uppercase tracking-wide">Search</div>
              <div className="flex items-center gap-1 px-2 py-1 rounded bg-surface2/40 border border-border">
                <Search size={11} className="text-muted shrink-0" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="message or source…"
                  className="bg-transparent text-fg text-[11px] outline-none flex-1 min-w-0"
                />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="text-muted text-[10px] uppercase tracking-wide">Severity</div>
              {LEVELS.map((lvl) => (
                <label
                  key={lvl}
                  className="flex items-center gap-2 cursor-pointer px-1 py-0.5 rounded hover:bg-surface2/40"
                >
                  <input
                    type="checkbox"
                    checked={levelFilter.has(lvl)}
                    onChange={() => {
                      const next = new Set(levelFilter);
                      if (next.has(lvl)) {
                        next.delete(lvl);
                      } else {
                        next.add(lvl);
                      }
                      setLevelFilter(next);
                    }}
                    className="accent-accent-cyan"
                  />
                  <StatusBadge tone={LEVEL_TONE[lvl]} label={lvl} />
                  <span className="text-muted text-[10px] font-mono ml-auto">{counts[lvl]}</span>
                </label>
              ))}
            </div>
            <div className="flex flex-col gap-1">
              <div className="text-muted text-[10px] uppercase tracking-wide">Sources</div>
              <div className="flex flex-wrap gap-1">
                {sources.map((s) => (
                  <span
                    key={s}
                    className="px-1.5 py-0.5 rounded bg-surface2/40 border border-border text-fg font-mono text-[10px]"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-auto flex flex-wrap gap-1.5">
              <LockedAction label="Export CSV" hint="locked · file write is Phase 6" />
              <LockedAction label="Tail live" />
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-9">
        <Panel
          id="logs.feed"
          title="UNIFIED LOG FEED"
          dense
          status={{ tone: "cyan", label: `${filtered.length} entries` }}
          className="h-[480px]"
        >
          <div className="w-full overflow-auto h-full">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-surface z-10">
                <tr className="text-muted text-[10px] uppercase tracking-wide border-b border-border">
                  <th className="text-left py-1.5 px-2 font-medium w-32">Time</th>
                  <th className="text-left py-1.5 px-2 font-medium w-20">Level</th>
                  <th className="text-left py-1.5 px-2 font-medium w-32">Source</th>
                  <th className="text-left py-1.5 px-2 font-medium">Message</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-muted text-center py-6 text-xs">
                      No matching log entries.
                    </td>
                  </tr>
                ) : (
                  filtered.map((log, i) => (
                    <tr
                      key={`${log.ts_utc}-${i}`}
                      className="border-b border-border/30 hover:bg-surface2/50"
                    >
                      <td className="py-1 px-2 text-muted font-mono text-[10px]">
                        {log.ts_utc.slice(11, 19)}Z
                      </td>
                      <td className="py-1 px-2">
                        <StatusBadge tone={LEVEL_TONE[log.level]} label={log.level} />
                      </td>
                      <td className="py-1 px-2 text-muted font-mono">{log.source}</td>
                      <td className="py-1 px-2 text-fg truncate">{log.message}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </div>
  );
}
