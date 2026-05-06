import { useEffect, useState } from "react";
import { Cloud, Cpu, Server } from "lucide-react";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";
import { adapters } from "../../api/adapters";
import type { ProviderHealth } from "../../types/provider";

type ProviderRow = {
  id: string;
  label: string;
  endpoint: string;
  detail: string;
  tone: StatusTone;
  status: string;
};

export function ProvidersSubtab() {
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "unavailable">("loading");

  const load = () => {
    let mounted = true;
    setState("loading");
    void adapters.getProviderHealth()
      .then((rows) => {
        if (!mounted) return;
        setProviders(rows.map(providerHealthToRow));
        setState("ready");
      })
      .catch(() => {
        if (!mounted) return;
        setProviders([]);
        setState("unavailable");
      });
    return () => {
      mounted = false;
    };
  };

  useEffect(() => {
    const cleanup = load();
    return () => {
      cleanup();
    };
  }, []);

  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="settings-providers">
      <header className="flex items-center gap-2 text-muted">
        <Server size={14} />
        <span className="text-fg font-medium">LLM provider configuration</span>
        <span className="text-[10px]">·</span>
        <span className="text-[10px]">live provider health</span>
      </header>

      <ProviderGroup
        title="Provider probes"
        Icon={Cpu}
        rows={providers}
        state={state}
        testid="settings-providers-local"
      />
      <ProviderGroup
        title="Cloud providers"
        Icon={Cloud}
        rows={[]}
        state="ready"
        testid="settings-providers-cloud"
      />

      <footer className="flex items-center justify-between pt-2 border-t border-border">
        <span className="text-muted text-[10px]">
          Provider rows come from <span className="font-mono">/api/providers/health</span>. No row is shown unless the backend reports it.
        </span>
        <div className="flex gap-1.5">
          <button type="button" onClick={load} className="rounded border border-border px-2 py-1 text-xs text-fg">
            Reload provider probes
          </button>
        </div>
      </footer>
    </div>
  );
}

function ProviderGroup({
  title,
  Icon,
  rows,
  state,
  testid,
}: {
  title: string;
  Icon: typeof Cpu;
  rows: ProviderRow[];
  state: "loading" | "ready" | "unavailable";
  testid: string;
}) {
  return (
    <section className="flex flex-col gap-1" data-testid={testid}>
      <h3 className="flex items-center gap-1.5 text-fg text-[11px] uppercase tracking-wide">
        <Icon size={12} />
        {title}
      </h3>
      {rows.length > 0 ? (
        <ul className="flex flex-col gap-1">
          {rows.map((r) => (
          <li
            key={r.id}
            className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border"
          >
            <span className="text-fg text-[11px] font-medium w-32 shrink-0 truncate">
              {r.label}
            </span>
            <span className="text-fg font-mono text-[11px] flex-1 truncate">{r.endpoint}</span>
            <span className="text-muted text-[10px] hidden md:inline truncate">{r.detail}</span>
            <StatusBadge tone={r.tone} label={r.status} />
          </li>
          ))}
        </ul>
      ) : (
        <div className="rounded border border-border bg-surface2/30 px-3 py-2 text-muted">
          {state === "loading" && "Loading provider health from the backend."}
          {state === "ready" && "No provider rows returned by the backend."}
          {state === "unavailable" && "Provider health endpoint is unavailable."}
        </div>
      )}
    </section>
  );
}

function providerHealthToRow(provider: ProviderHealth): ProviderRow {
  return {
    id: provider.provider_id,
    label: provider.provider_id,
    endpoint: provider.http_status == null ? "no HTTP probe" : `HTTP ${provider.http_status}`,
    detail: provider.last_probe_utc
      ? `${provider.latency_ms ?? "-"} ms · ${provider.last_probe_utc}`
      : "not probed",
    tone: providerStatusTone(provider.status),
    status: provider.stale ? `${provider.status} stale` : provider.status,
  };
}

function providerStatusTone(status: ProviderHealth["status"]): StatusTone {
  if (status === "green") return "green";
  if (status === "amber") return "amber";
  if (status === "red") return "red";
  return "muted";
}
