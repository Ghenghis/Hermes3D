/**
 * Settings → Update Center subtab.
 *
 * Displays real-time data from GET /api/settings/update-center:
 *   - Component versions (UI, backend)
 *   - Desktop updater / Velopack readiness status
 *   - Provider health summary with live probes
 *   - Failsafe rollback availability per component
 *
 * No version strings are hardcoded here. All data comes from the backend.
 * The rollback flow delegates to the component-specific proof-gated routes;
 * this UI only surfaces availability and provides a one-click "request rollback"
 * that hits POST /api/settings/update-center/rollback/{component}.
 */
import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, Clock, Package, RefreshCw, RotateCcw, Server, XCircle } from "lucide-react";

type HermesImportMeta = ImportMeta & {
  env: { VITE_HERMES3D_BRIDGE_PORT?: string };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

// ─── Types mirroring the backend payload ────────────────────────────────────

type ComponentVersion = {
  component: string;
  name: string;
  version: string;
  source: string;
  found: boolean;
};

type VelopackStatus = {
  updater: string;
  status: "ready" | "not_configured" | "update_pending";
  ready: boolean;
  current_version: string | null;
  manifest_found: boolean;
  reason: string;
};

type BackupMeta = {
  backup_id: string;
  created_at: string;
  package_version: string | null;
  tag: string | null;
  commit: string | null;
} | null;

type RollbackEntry = {
  component: string;
  backup_available: boolean;
  latest_backup: BackupMeta;
  rollback_action: string | null;
};

type ProviderProbe = {
  provider_id: string;
  status: "green" | "amber" | "red" | "idle";
  last_probe_utc: string | null;
  http_status: number | null;
  latency_ms: number | null;
  stale: boolean;
};

type UpdateCenterPayload = {
  generated_at: string;
  components: ComponentVersion[];
  updater: VelopackStatus;
  rollback: {
    desktop: RollbackEntry;
    agent: RollbackEntry;
  };
  provider_health: {
    summary: { green: number; amber: number; red: number };
    providers: ProviderProbe[];
  };
};

// ─── Fetch helpers ──────────────────────────────────────────────────────────

async function fetchUpdateCenter(): Promise<UpdateCenterPayload> {
  const response = await fetch(`${BASE_URL}/api/settings/update-center`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Update center API returned ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as UpdateCenterPayload;
}

async function postRollbackRequest(component: string): Promise<{ message: string; next_step: string | null }> {
  const response = await fetch(
    `${BASE_URL}/api/settings/update-center/rollback/${encodeURIComponent(component)}`,
    { method: "POST", headers: { Accept: "application/json" }, cache: "no-store" },
  );
  const body = await response.json() as Record<string, unknown>;
  if (!response.ok) {
    const detail = body.detail as { reason?: string } | string | undefined;
    const reason =
      typeof detail === "object" && detail !== null
        ? (detail.reason ?? JSON.stringify(detail))
        : typeof detail === "string"
          ? detail
          : `Rollback request failed (${response.status})`;
    throw new Error(reason);
  }
  return {
    message: String(body.message ?? "Rollback surfaced."),
    next_step: body.next_step as string | null,
  };
}

// ─── Component ──────────────────────────────────────────────────────────────

type LoadState = "idle" | "loading" | "ready" | "error";

export function UpdateCenterSubtab() {
  const [data, setData] = useState<UpdateCenterPayload | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [rollbackStatus, setRollbackStatus] = useState<Record<string, string>>({});
  const [rollbackBusy, setRollbackBusy] = useState<Record<string, boolean>>({});

  const load = () => {
    setLoadState("loading");
    setErrorMsg(null);
    fetchUpdateCenter()
      .then((payload) => {
        setData(payload);
        setLoadState("ready");
      })
      .catch((err: unknown) => {
        setErrorMsg(err instanceof Error ? err.message : "Update center API unreachable.");
        setLoadState("error");
      });
  };

  useEffect(() => { load(); }, []);

  const requestRollback = (component: string) => {
    setRollbackBusy((prev) => ({ ...prev, [component]: true }));
    setRollbackStatus((prev) => ({ ...prev, [component]: "Requesting…" }));
    postRollbackRequest(component)
      .then(({ message }) => {
        setRollbackStatus((prev) => ({ ...prev, [component]: message }));
      })
      .catch((err: unknown) => {
        setRollbackStatus((prev) => ({
          ...prev,
          [component]: `Blocked: ${err instanceof Error ? err.message : "unknown error"}`,
        }));
      })
      .finally(() => {
        setRollbackBusy((prev) => ({ ...prev, [component]: false }));
      });
  };

  return (
    <div className="flex flex-col gap-4 text-xs" data-testid="settings-update-center">
      {/* Header */}
      <header className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-muted">
          <Package size={14} />
          <span className="text-fg font-medium">Update Center</span>
          <span className="text-[10px]">·</span>
          <span className="text-[10px]">live backend data — no hardcoded versions</span>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loadState === "loading"}
          className="flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw size={11} className={loadState === "loading" ? "animate-spin" : ""} />
          {loadState === "loading" ? "Loading…" : "Refresh"}
        </button>
      </header>

      {/* Error banner */}
      {loadState === "error" && (
        <div
          className="flex items-center gap-2 rounded border border-red-800/60 bg-red-950/40 px-3 py-2 text-red-300"
          data-testid="update-center-error"
        >
          <XCircle size={13} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Component versions */}
      {data && (
        <>
          <Section title="Installed Components" Icon={Server}>
            <div className="grid grid-cols-2 gap-2" data-testid="update-center-components">
              {data.components.map((c) => (
                <div
                  key={c.component}
                  className="flex flex-col gap-0.5 rounded border border-border bg-surface2/40 px-3 py-2"
                >
                  <span className="text-[10px] uppercase text-muted">{c.name}</span>
                  <span className="font-mono text-[12px] text-fg">{c.version}</span>
                  {!c.found && (
                    <span className="text-[10px] text-amber-400">source file not found</span>
                  )}
                </div>
              ))}
            </div>
            {data.generated_at && (
              <p className="mt-1 flex items-center gap-1 text-[10px] text-muted">
                <Clock size={10} />
                Probed at {data.generated_at}
              </p>
            )}
          </Section>

          {/* Velopack / app-updater readiness */}
          <Section title="App Updater (Velopack)" Icon={Package}>
            <UpdaterReadinessCard updater={data.updater} />
          </Section>

          {/* Provider health */}
          <Section title="Provider Health" Icon={Server}>
            <ProviderHealthPanel health={data.provider_health} />
          </Section>

          {/* Failsafe rollback */}
          <Section title="Failsafe Rollback" Icon={RotateCcw}>
            <div className="flex flex-col gap-2" data-testid="update-center-rollback">
              {Object.entries(data.rollback).map(([key, entry]) => (
                <RollbackCard
                  key={key}
                  entry={entry}
                  status={rollbackStatus[entry.component]}
                  busy={rollbackBusy[entry.component] ?? false}
                  onRequest={() => requestRollback(entry.component)}
                />
              ))}
            </div>
          </Section>
        </>
      )}

      {loadState === "idle" && !data && (
        <p className="text-muted">Loading update center data…</p>
      )}
    </div>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function Section({
  title,
  Icon,
  children,
}: {
  title: string;
  Icon: typeof Server;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg">
        <Icon size={12} />
        {title}
      </h3>
      {children}
    </section>
  );
}

function UpdaterReadinessCard({ updater }: { updater: VelopackStatus }) {
  const toneClass =
    updater.status === "ready"
      ? "border-green-800/50 bg-green-950/30 text-green-300"
      : updater.status === "update_pending"
        ? "border-amber-800/50 bg-amber-950/30 text-amber-200"
        : "border-border bg-surface2/40 text-muted";

  const Icon =
    updater.status === "ready"
      ? CheckCircle
      : updater.status === "update_pending"
        ? AlertTriangle
        : XCircle;

  return (
    <div
      className={`flex flex-col gap-1 rounded border px-3 py-2 ${toneClass}`}
      data-testid="update-center-velopack"
    >
      <div className="flex items-center gap-2">
        <Icon size={13} />
        <span className="font-medium">
          {updater.status === "ready"
            ? "Velopack ready"
            : updater.status === "update_pending"
              ? "Update pending"
              : "Not configured (source launch)"}
        </span>
        {updater.current_version && (
          <span className="ml-auto font-mono text-[11px]">{updater.current_version}</span>
        )}
      </div>
      <p className="text-[10px] opacity-80">{updater.reason}</p>
    </div>
  );
}

function ProviderHealthPanel({
  health,
}: {
  health: UpdateCenterPayload["provider_health"];
}) {
  const { summary, providers } = health;
  return (
    <div className="flex flex-col gap-2" data-testid="update-center-provider-health">
      <div className="flex gap-2">
        <Pill label="green" value={summary.green} tone="green" />
        <Pill label="amber" value={summary.amber} tone="amber" />
        <Pill label="red" value={summary.red} tone="red" />
      </div>
      <ul className="flex flex-col gap-1">
        {providers.map((p) => (
          <li
            key={p.provider_id}
            className="flex items-center gap-3 rounded border border-border bg-surface2/30 px-2 py-1.5"
          >
            <span className="w-24 shrink-0 font-medium text-fg">{p.provider_id}</span>
            <span className="flex-1 font-mono text-[11px] text-muted">
              {p.http_status != null ? `HTTP ${p.http_status}` : "no HTTP probe"}
            </span>
            <span className="hidden text-[10px] text-muted md:inline">
              {p.latency_ms != null ? `${p.latency_ms} ms` : "—"}
            </span>
            <StatusDot status={p.status} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function RollbackCard({
  entry,
  status,
  busy,
  onRequest,
}: {
  entry: RollbackEntry;
  status: string | undefined;
  busy: boolean;
  onRequest: () => void;
}) {
  return (
    <div
      className="flex flex-col gap-1 rounded border border-border bg-surface2/30 px-3 py-2"
      data-testid={`rollback-card-${entry.component}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-fg">{entry.component}</span>
        {entry.backup_available ? (
          <button
            type="button"
            disabled={busy}
            onClick={onRequest}
            className="flex items-center gap-1 rounded border border-amber-700/60 bg-amber-950/40 px-2 py-1 text-[11px] text-amber-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RotateCcw size={10} className={busy ? "animate-spin" : ""} />
            {busy ? "Requesting…" : "Request rollback"}
          </button>
        ) : (
          <span className="text-[10px] text-muted">No backup available</span>
        )}
      </div>

      {entry.backup_available && entry.latest_backup && (
        <div className="text-[10px] text-muted">
          Latest backup:{" "}
          <span className="font-mono">
            {entry.latest_backup.package_version ?? entry.latest_backup.tag ?? entry.latest_backup.backup_id}
          </span>{" "}
          · {entry.latest_backup.created_at}
        </div>
      )}

      {!entry.backup_available && entry.rollback_action && (
        <p className="text-[10px] text-muted">
          Create a backup first via{" "}
          <span className="font-mono">{entry.rollback_action.replace("POST ", "")}</span>
        </p>
      )}

      {status && (
        <p
          className={`mt-1 rounded px-2 py-1 text-[10px] ${status.startsWith("Blocked") ? "bg-red-950/40 text-red-300" : "bg-surface2 text-muted"}`}
        >
          {status}
        </p>
      )}
    </div>
  );
}

function Pill({ label, value, tone }: { label: string; value: number; tone: "green" | "amber" | "red" }) {
  const cls = {
    green: "bg-green-950/70 text-green-300",
    amber: "bg-amber-950/70 text-amber-200",
    red: "bg-red-950/70 text-red-300",
  }[tone];
  return (
    <span className={`rounded px-2 py-0.5 text-[10px] uppercase ${cls}`}>
      {value} {label}
    </span>
  );
}

function StatusDot({ status }: { status: ProviderProbe["status"] }) {
  const cls =
    status === "green"
      ? "bg-green-400"
      : status === "amber"
        ? "bg-amber-400"
        : status === "red"
          ? "bg-red-400"
          : "bg-surface2";
  return <span className={`size-2 rounded-full ${cls}`} title={status} />;
}
