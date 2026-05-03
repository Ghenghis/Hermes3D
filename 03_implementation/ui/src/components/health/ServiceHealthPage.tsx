/**
 * ServiceHealthPage — main view for the Service Health tab
 * (CP-HERMES3D-SERVICE-HEALTH).
 *
 * On mount it calls ``GET /api/health/services`` and renders a grid of
 * :class:`ServiceCard`s grouped by category. Auto-refreshes every 30 s by
 * default; refreshing can be paused with the toggle button.
 *
 * The endpoint is on the Hermes REST API (default ``http://localhost:7861``).
 * In dev (Vite on :5173) we use the absolute URL so the request reaches the
 * REST API directly. When the backend is unreachable, the page shows the
 * error rather than failing silently.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Pause, Play, RefreshCcw } from "lucide-react";
import { Panel } from "../layout/Panel";
import { ServiceCard, type ServiceProbe } from "./ServiceCard";

const REFRESH_INTERVAL_MS = 30_000;

function apiBase(): string {
  const env = (import.meta as ImportMeta & { env: { VITE_HERMES3D_API?: string } }).env;
  if (env?.VITE_HERMES3D_API) {
    return env.VITE_HERMES3D_API.replace(/\/$/, "");
  }
  // Default: Hermes REST API on the canonical port (run.bat / docs).
  if (typeof window !== "undefined" && window.location.port === "5173") {
    return `${window.location.protocol}//${window.location.hostname}:7861`;
  }
  return "";
}

interface HealthResponse {
  ok: boolean;
  ts_unix: number;
  count: number;
  services: ServiceProbe[];
}

export function ServiceHealthPage(): JSX.Element {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [paused, setPaused] = useState<boolean>(false);
  const timer = useRef<number | null>(null);

  const fetchHealth = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase()}/api/health/services`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const payload = (await res.json()) as HealthResponse;
      setData(payload);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchHealth();
  }, [fetchHealth]);

  useEffect(() => {
    if (paused) {
      if (timer.current !== null) {
        window.clearInterval(timer.current);
        timer.current = null;
      }
      return;
    }
    timer.current = window.setInterval(() => {
      void fetchHealth();
    }, REFRESH_INTERVAL_MS);
    return () => {
      if (timer.current !== null) {
        window.clearInterval(timer.current);
        timer.current = null;
      }
    };
  }, [paused, fetchHealth]);

  const grouped = useMemo<Record<string, ServiceProbe[]>>(() => {
    const out: Record<string, ServiceProbe[]> = {};
    for (const s of data?.services ?? []) {
      const cat = s.category || "other";
      if (!out[cat]) {
        out[cat] = [];
      }
      out[cat].push(s);
    }
    return out;
  }, [data]);

  const categoryOrder = useMemo<string[]>(
    () =>
      Object.keys(grouped).sort((a, b) => {
        const score = (k: string) =>
          ({ hermes: 0, llm: 1, modeling: 2, monitoring: 3, printer: 4 } as Record<
            string,
            number
          >)[k] ?? 99;
        return score(a) - score(b) || a.localeCompare(b);
      }),
    [grouped],
  );

  return (
    <Panel
      panelId="service_health.main"
      title="Service Health"
      subtitle="TCP reachability for Hermes services and per-printer Moonraker"
      data-panel-id="service_health.main"
    >
      <div data-testid="service-health-page" className="flex flex-col gap-4">
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs text-zinc-400">
            {loading
              ? "Probing…"
              : error
                ? `Error: ${error}`
                : data
                  ? `Probed ${data.count} services at ${new Date(data.ts_unix * 1000).toLocaleTimeString()}`
                  : ""}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              data-action="refresh"
              onClick={() => void fetchHealth()}
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs border border-zinc-700/60 hover:bg-zinc-800/80"
            >
              <RefreshCcw size={12} />
              Refresh
            </button>
            <button
              type="button"
              data-action="toggle-pause"
              data-paused={paused}
              onClick={() => setPaused((p) => !p)}
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs border border-zinc-700/60 hover:bg-zinc-800/80"
            >
              {paused ? <Play size={12} /> : <Pause size={12} />}
              {paused ? "Resume" : "Pause"} auto-refresh
            </button>
          </div>
        </div>

        {error && !data ? (
          <div className="rounded-md border border-rose-700/60 bg-rose-900/20 p-3 text-sm text-rose-200">
            Could not reach <code>/api/health/services</code>: {error}. Confirm the Hermes REST
            API is running on port <code>7861</code>.
          </div>
        ) : null}

        {categoryOrder.map((cat) => (
          <section key={cat} data-testid={`service-group-${cat}`} className="flex flex-col gap-2">
            <h3 className="text-xs uppercase tracking-wide text-zinc-400">{cat}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {grouped[cat].map((probe) => (
                <ServiceCard key={`${probe.name}-${probe.host}-${probe.port}`} probe={probe} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </Panel>
  );
}
