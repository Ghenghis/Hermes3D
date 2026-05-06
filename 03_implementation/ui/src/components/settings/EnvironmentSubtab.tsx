import { useEffect, useState } from "react";
import { Eye, EyeOff, Terminal } from "lucide-react";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";
import { adapters } from "../../api/adapters";
import type { RuntimeReadiness } from "../../types/system";
import type { SourceModuleRuntimeSetupQueue } from "../../types/source-os";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

type EnvVar = {
  name: string;
  description: string;
  set: boolean;
  sensitive: boolean;
};

export function EnvironmentSubtab() {
  const [vars, setVars] = useState<EnvVar[]>([]);
  const [runtimeReadiness, setRuntimeReadiness] = useState<RuntimeReadiness | null>(null);
  const [setupQueue, setSetupQueue] = useState<SourceModuleRuntimeSetupQueue | null>(null);
  const [setupQueueBusy, setSetupQueueBusy] = useState(false);
  const [setupQueueMessage, setSetupQueueMessage] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "unavailable">("loading");

  useEffect(() => {
    let mounted = true;
    void fetch(`${LIVE_BASE_URL}/api/env/status`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
      .then((response) => response.ok ? response.json() as Promise<{ variables?: unknown[] }> : null)
      .then((payload) => {
        if (!mounted) return;
        setVars((payload?.variables ?? []).map(parseEnvVar).filter((item): item is EnvVar => item != null));
        setState("ready");
      })
      .catch(() => {
        if (!mounted) return;
        setVars([]);
        setState("unavailable");
      });
    void adapters.getRuntimeReadiness()
      .then((payload) => {
        if (!mounted) return;
        setRuntimeReadiness(payload);
      })
      .catch(() => {
        if (!mounted) return;
        setRuntimeReadiness(null);
      });
    void adapters.getModuleRuntimeSetupQueue()
      .then((payload) => {
        if (!mounted) return;
        setSetupQueue(payload);
      })
      .catch(() => {
        if (!mounted) return;
        setSetupQueue(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const planSetupQueue = () => {
    setSetupQueueBusy(true);
    setSetupQueueMessage(null);
    void adapters.planModuleRuntimeSetupQueue()
      .then((payload) => {
        setSetupQueue(payload);
        setSetupQueueMessage(`Plan recorded${payload.proof_event_id ? ` with proof ${payload.proof_event_id}` : ""}.`);
      })
      .catch((error) => {
        setSetupQueueMessage(error instanceof Error ? error.message : "Runtime setup queue is unavailable.");
      })
      .finally(() => setSetupQueueBusy(false));
  };

  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="settings-environment">
      <header className="flex items-center gap-2 text-muted">
        <Terminal size={14} />
        <span className="text-fg font-medium">Environment variables</span>
        <span className="text-[10px]">·</span>
        <span className="text-[10px]">presence only · values redacted</span>
      </header>

      <div
        className="rounded border border-accent-amber/40 bg-accent-amber/10 px-3 py-2 text-[11px] text-accent-amber"
        role="note"
      >
        <span className="font-semibold">Privacy:</span> only the presence of each variable is
        shown. Actual values are never read into the UI or rendered, so screenshots and proof
        artifacts cannot leak credentials.
      </div>

      {runtimeReadiness ? (
        <section className="rounded border border-border bg-surface2/30 p-2">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="text-[11px] font-semibold uppercase text-fg">Runtime Readiness</div>
              <div className="text-[10px] text-muted">Truth ledger from <span className="font-mono">/api/system/runtime-readiness</span>.</div>
            </div>
            <div className="flex flex-wrap gap-1">
              <StatusBadge tone="green" label={`${runtimeReadiness.summary.ready} ready`} />
              <StatusBadge tone="amber" label={`${runtimeReadiness.summary.partial} partial`} />
              <StatusBadge tone="red" label={`${runtimeReadiness.summary.blocked} blocked`} />
            </div>
          </div>
          <ul className="grid gap-1 xl:grid-cols-2">
            {runtimeReadiness.runtimes.map((runtime) => (
              <li key={runtime.id} className="rounded border border-border bg-bg/50 p-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-[11px] font-semibold text-fg">{runtime.label}</div>
                    <div className="truncate font-mono text-[10px] text-muted">{runtime.category} · {runtime.source}</div>
                  </div>
                  <StatusBadge tone={runtimeTone(runtime.status)} label={runtime.status} />
                </div>
                <div className="mt-1 text-[10px] text-muted">{runtime.reason}</div>
                {runtime.required_env.length > 0 && (
                  <div className="mt-1 truncate font-mono text-[10px] text-accent-amber">{runtime.required_env.join(", ")}</div>
                )}
                <div className="mt-1 truncate font-mono text-[10px] text-accent-cyan">{runtime.proof}</div>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <div className="rounded border border-border bg-surface2/30 px-3 py-2 text-muted">
          Runtime readiness endpoint is unavailable.
        </div>
      )}

      <section className="rounded border border-border bg-surface2/30 p-2" data-testid="settings-runtime-setup-queue">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-[11px] font-semibold uppercase text-fg">Source App Setup Queue</div>
            <div className="text-[10px] text-muted">
              Read-only status from <span className="font-mono">/api/modules/runtime/setup-queue</span>; the button records a proof-backed plan.
            </div>
          </div>
          <button
            type="button"
            disabled={setupQueueBusy}
            onClick={planSetupQueue}
            className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
          >
            {setupQueueBusy ? "Planning" : "Plan setup queue"}
          </button>
        </div>
        {setupQueue ? (
          <>
            <div className="flex flex-wrap gap-1">
              <StatusBadge tone="muted" label={`${setupQueue.count} apps`} />
              <StatusBadge tone="green" label={`${setupQueue.counts.runtime_ready} runtime ready`} />
              <StatusBadge tone={setupQueue.counts.runner_not_registered > 0 ? "amber" : "muted"} label={`${setupQueue.counts.runner_not_registered} need runners`} />
              <StatusBadge tone={setupQueue.counts.source_install_available > 0 ? "amber" : "muted"} label={`${setupQueue.counts.source_install_available} install ready`} />
              <StatusBadge tone={setupQueue.counts.blocked > 0 ? "red" : "muted"} label={`${setupQueue.counts.blocked} blocked`} />
            </div>
            <div className="mt-2 text-[10px] text-muted">{setupQueue.agent_gate}</div>
            {setupQueueMessage && <div className="mt-2 rounded border border-border bg-bg/50 px-2 py-1 text-[10px] text-muted">{setupQueueMessage}</div>}
          </>
        ) : (
          <div className="rounded border border-border bg-bg/50 px-2 py-1 text-[10px] text-muted">Source app setup queue endpoint is unavailable.</div>
        )}
      </section>

      {vars.length > 0 ? (
        <ul className="flex flex-col gap-1">
          {vars.map((v) => (
          <li
            key={v.name}
            data-testid={`settings-environment-row-${v.name}`}
            className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border"
          >
            <span className="flex items-center gap-1.5 w-72 shrink-0">
              {v.sensitive ? (
                <EyeOff size={11} className="text-accent-amber shrink-0" />
              ) : (
                <Eye size={11} className="text-muted shrink-0" />
              )}
              <span className="text-fg font-mono text-[11px] truncate">{v.name}</span>
            </span>
            <span className="text-muted text-[10px] flex-1 truncate">{v.description}</span>
            <span
              data-testid={`settings-environment-status-${v.name}`}
              className="font-mono text-[11px] text-fg"
            >
              {v.set ? "[set]" : "[not set]"}
            </span>
            <StatusBadge tone={v.set ? "green" : "muted"} label={v.set ? "set" : "not set"} />
          </li>
          ))}
        </ul>
      ) : (
        <div className="rounded border border-border bg-surface2/30 px-3 py-2 text-muted">
          {state === "loading" && "Loading environment status from the backend."}
          {state === "ready" && "No environment variables returned by the backend."}
          {state === "unavailable" && "Environment status endpoint is unavailable."}
        </div>
      )}

      <footer className="text-muted text-[10px] pt-2 border-t border-border">
        Sensitive variables (API keys) are flagged with the closed-eye icon. The UI never has
        access to their contents.
      </footer>
    </div>
  );
}

function runtimeTone(status: string): StatusTone {
  if (status === "ready") return "green";
  if (status === "partial" || status === "locked") return "amber";
  if (status === "blocked") return "red";
  return "muted";
}

function parseEnvVar(value: unknown): EnvVar | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }
  const record = value as Record<string, unknown>;
  if (typeof record.name !== "string") {
    return null;
  }
  return {
    name: record.name,
    description: typeof record.description === "string" ? record.description : "",
    set: record.set === true,
    sensitive: record.sensitive === true,
  };
}
