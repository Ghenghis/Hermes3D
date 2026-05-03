import type { ServiceHealthEntry } from "../../types/serviceHealth";
import { StatusPill } from "./StatusPill";

/**
 * Single-service summary card rendered by {@link ServiceHealthPage}. Surfaces
 * status, host:port, latency, and a relative "last probed" timestamp for
 * at-a-glance situational awareness.
 *
 * Does NOT use the generic ``Panel`` wrapper — Panel exposes dock/collapse
 * controls that don't make sense for a per-service status tile. Cards are
 * intentionally lightweight and stateless.
 */
export interface ServiceCardProps {
  entry: ServiceHealthEntry;
  /** Reference timestamp for the relative "n s ago" label. Defaults to now. */
  now?: Date;
}

export function ServiceCard({ entry, now }: ServiceCardProps) {
  const probedAtRelative = formatRelative(entry.probed_at, now ?? new Date());
  const port = entry.port === 0 ? "stdio" : entry.port;
  const latency = formatLatency(entry.status, entry.latency_ms);

  return (
    <div
      data-testid="service-card"
      data-service-name={entry.name}
      data-service-status={entry.status}
      data-service-category={entry.category}
      className={[
        "flex flex-col gap-2 rounded-card border border-border bg-surface p-3",
        "shadow-sm hover:border-accent-cyan/40 transition-colors",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              data-testid="service-card-name"
              className="text-fg text-[13px] font-semibold truncate"
            >
              {entry.name}
            </span>
            <span
              data-testid="service-card-category"
              className="text-[10px] uppercase tracking-wide text-muted"
            >
              {entry.category}
            </span>
          </div>
          <div className="text-muted text-[11px] font-mono truncate">
            {entry.host}:{port}
          </div>
        </div>
        <StatusPill status={entry.status} />
      </div>

      <div className="flex items-center justify-between text-[11px] text-muted">
        <span data-testid="service-card-latency">{latency}</span>
        <span data-testid="service-card-probed-at" title={entry.probed_at}>
          {probedAtRelative}
        </span>
      </div>

      {entry.detail && (
        <div
          data-testid="service-card-detail"
          className="text-muted text-[10px] font-mono truncate"
          title={entry.detail}
        >
          {entry.detail}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Formatting helpers (kept private — exported only for unit testing if needed)
// ---------------------------------------------------------------------------

export function formatRelative(probedAtIso: string, now: Date): string {
  const parsed = Date.parse(probedAtIso);
  if (Number.isNaN(parsed)) {
    return "—";
  }
  const deltaSec = Math.max(0, Math.round((now.getTime() - parsed) / 1000));
  if (deltaSec < 5) return "just now";
  if (deltaSec < 60) return `${deltaSec}s ago`;
  if (deltaSec < 3600) return `${Math.floor(deltaSec / 60)}m ago`;
  if (deltaSec < 86_400) return `${Math.floor(deltaSec / 3600)}h ago`;
  return `${Math.floor(deltaSec / 86_400)}d ago`;
}

function formatLatency(status: ServiceHealthEntry["status"], latencyMs: number): string {
  if (status === "disabled" || status === "unknown") {
    return "—";
  }
  if (latencyMs <= 0) {
    return "—";
  }
  if (latencyMs < 10) {
    return `${latencyMs.toFixed(1)} ms`;
  }
  return `${Math.round(latencyMs)} ms`;
}
