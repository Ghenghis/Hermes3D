import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, Pause, Play, RefreshCw } from "lucide-react";
import { Panel } from "../layout/Panel";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";
import { adapters } from "../../api/adapters";
import { MOCK_SERVICE_HEALTH } from "../../data/mock/serviceHealth";
import type {
  ServiceCategory,
  ServiceHealthEntry,
  ServiceStatus,
} from "../../types/serviceHealth";
import { ServiceCard } from "./ServiceCard";

/**
 * Top-level Service Health page. Replaces the broken stub PR #37 left
 * behind (which imported a non-existent ``ServiceCard`` and passed Panel
 * props that did not exist). The page:
 *
 *   - fetches `GET /api/health/services` on mount via the adapters layer
 *     (mock-mode by default; ``?adapter=live`` switches to the real fetch);
 *   - auto-refreshes every 30 s, with a Pause toggle;
 *   - groups results by category with a header summary pill row.
 */

const REFRESH_INTERVAL_MS = 30_000;

const CATEGORY_ORDER: ServiceCategory[] = [
  "mcp",
  "llm",
  "modeling",
  "printer",
  "api",
  "tunnel",
];

const CATEGORY_LABEL: Record<ServiceCategory, string> = {
  mcp: "MCP servers",
  llm: "LLM providers",
  modeling: "Modeling",
  printer: "Printers (Moonraker)",
  api: "Hermes services",
  tunnel: "Tunnels",
};

const STATUS_TONE: Record<ServiceStatus, StatusTone> = {
  online: "green",
  offline: "red",
  unreachable: "amber",
  "auth-required": "blue",
  disabled: "muted",
  unknown: "muted",
};

export function ServiceHealthPage() {
  const [entries, setEntries] = useState<ServiceHealthEntry[]>(MOCK_SERVICE_HEALTH);
  const [loading, setLoading] = useState(false);
  const [paused, setPaused] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const [now, setNow] = useState<Date>(() => new Date());
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await adapters.getServiceHealth();
      if (!mounted.current) return;
      setEntries(next);
      setLastError(null);
      setNow(new Date());
    } catch (err) {
      if (!mounted.current) return;
      setLastError(err instanceof Error ? err.message : "probe failed");
    } finally {
      if (mounted.current) {
        setLoading(false);
      }
    }
  }, []);

  // Mount: fetch once, kick off refresh loop.
  useEffect(() => {
    mounted.current = true;
    void refresh();
    return () => {
      mounted.current = false;
    };
  }, [refresh]);

  useEffect(() => {
    if (paused) return;
    const handle = window.setInterval(() => {
      void refresh();
    }, REFRESH_INTERVAL_MS);
    return () => {
      window.clearInterval(handle);
    };
  }, [paused, refresh]);

  // Tick "now" every second so relative timestamps stay accurate without
  // re-fetching.
  useEffect(() => {
    const tick = window.setInterval(() => setNow(new Date()), 1_000);
    return () => window.clearInterval(tick);
  }, []);

  const grouped = useMemo(() => groupByCategory(entries), [entries]);
  const summary = useMemo(() => summariseByStatus(entries), [entries]);

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="service-health-root">
      <div className="col-span-12">
        <Panel
          id="service-health.summary"
          title="SERVICE HEALTH"
          dense
          status={{
            tone: summary.online === entries.length ? "green" : summary.offline > 0 ? "red" : "amber",
            label: `${summary.online} / ${entries.length} online`,
          }}
          headerExtra={
            <div className="flex items-center gap-1.5" data-testid="service-health-actions">
              <button
                type="button"
                onClick={() => void refresh()}
                disabled={loading}
                aria-label="Re-probe services now"
                title="Re-probe services now"
                data-testid="service-health-reprobe"
                className={[
                  "flex items-center gap-1 px-2 py-1 rounded text-[11px] border",
                  "border-border text-muted hover:text-fg hover:border-accent-cyan/40",
                  loading ? "opacity-60 cursor-not-allowed" : "",
                ].join(" ")}
              >
                <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
                Re-probe now
              </button>
              <button
                type="button"
                onClick={() => setPaused((p) => !p)}
                aria-label={paused ? "Resume auto-refresh" : "Pause auto-refresh"}
                title={paused ? "Resume auto-refresh" : "Pause auto-refresh"}
                data-testid="service-health-pause"
                aria-pressed={paused}
                className={[
                  "flex items-center gap-1 px-2 py-1 rounded text-[11px] border",
                  paused
                    ? "border-accent-amber/40 text-accent-amber"
                    : "border-border text-muted hover:text-fg",
                ].join(" ")}
              >
                {paused ? <Play size={11} /> : <Pause size={11} />}
                {paused ? "Paused" : "Auto 30s"}
              </button>
            </div>
          }
          className="min-h-[120px]"
        >
          <div className="flex flex-col gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-1.5" data-testid="service-health-summary">
              {(Object.keys(summary) as ServiceStatus[])
                .filter((k) => summary[k] > 0)
                .map((status) => (
                  <span key={status} data-testid={`summary-${status}`}>
                    <StatusBadge tone={STATUS_TONE[status]} label={`${summary[status]} ${status}`} />
                  </span>
                ))}
              <span className="ml-auto flex items-center gap-1 text-muted" aria-live="polite">
                <Activity size={11} />
                <span data-testid="service-health-last-update">
                  {loading ? "probing…" : `last update ${formatNow(now)}`}
                </span>
              </span>
            </div>
            {lastError && (
              <div
                role="alert"
                data-testid="service-health-error"
                className="text-accent-red text-[11px] font-mono"
              >
                {lastError}
              </div>
            )}
          </div>
        </Panel>
      </div>

      {CATEGORY_ORDER.filter((cat) => (grouped[cat]?.length ?? 0) > 0).map((category) => {
        const items = grouped[category] ?? [];
        return (
          <div key={category} className="col-span-12">
            <Panel
              id={`service-health.${category}`}
              title={CATEGORY_LABEL[category].toUpperCase()}
              dense
              status={{ tone: "cyan", label: `${items.length} svc` }}
            >
              <div
                data-testid={`service-health-group-${category}`}
                className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2.5"
              >
                {items.map((entry) => (
                  <ServiceCard key={entry.name} entry={entry} now={now} />
                ))}
              </div>
            </Panel>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function groupByCategory(
  entries: ServiceHealthEntry[],
): Partial<Record<ServiceCategory, ServiceHealthEntry[]>> {
  const out: Partial<Record<ServiceCategory, ServiceHealthEntry[]>> = {};
  for (const e of entries) {
    const list = out[e.category] ?? [];
    list.push(e);
    out[e.category] = list;
  }
  return out;
}

function summariseByStatus(entries: ServiceHealthEntry[]): Record<ServiceStatus, number> {
  const acc: Record<ServiceStatus, number> = {
    online: 0,
    offline: 0,
    unreachable: 0,
    "auth-required": 0,
    disabled: 0,
    unknown: 0,
  };
  for (const e of entries) {
    acc[e.status] = (acc[e.status] ?? 0) + 1;
  }
  return acc;
}

function formatNow(now: Date): string {
  return now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
