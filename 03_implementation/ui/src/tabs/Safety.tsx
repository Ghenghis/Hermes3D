/**
 * Safety tab — per-printer safety state aggregator.
 *
 * Per W6-9, each printer is expected to expose
 *   GET /api/printers/{id}/safety-state
 * The endpoint is NOT yet shipped at the time this tab was added (W15-A3 route
 * inventory), so this page:
 *   1. Lists every printer from the live `GET /api/printers` adapter, and
 *   2. Probes the candidate safety-state endpoint per printer; rows for which
 *      the probe returns 404 are rendered with an explicit "endpoint not yet
 *      shipped" placeholder. Rows that return data are rendered fully — the
 *      tab will auto-promote itself once the backend implements the route.
 *   3. The locked-state info from `GET /api/printers/{id}/lock` (which IS
 *      shipped) is rendered next to every row so the page is useful today.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Lock, RefreshCw, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { adapters } from "../api/adapters";
import type { Printer, PrinterStatus } from "../types/printer";
import type { PrinterLock } from "../types/printer-lock";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const REFRESH_INTERVAL_MS = 20_000;

type SafetyProbeStatus =
  | { kind: "pending" }
  | { kind: "missing"; http_status: number }
  | { kind: "available"; payload: SafetyStatePayload }
  | { kind: "error"; detail: string };

interface SafetyStatePayload {
  printer_id?: string;
  policy?: string;
  write_enabled?: boolean;
  ok?: boolean;
  reason?: string;
  bed_clear?: boolean;
  temp_within_limits?: boolean;
  klippy_state?: string;
  last_check_utc?: string;
  [key: string]: unknown;
}

const STATUS_TONE: Record<PrinterStatus, string> = {
  online: "text-accent-green",
  active: "text-accent-cyan",
  printing: "text-accent-cyan",
  paused: "text-accent-amber",
  maintenance: "text-accent-amber",
  offline: "text-muted",
  error: "text-accent-red",
};

async function probeSafetyState(printerId: string): Promise<SafetyProbeStatus> {
  try {
    const response = await fetch(
      `${LIVE_BASE_URL}/api/printers/${encodeURIComponent(printerId)}/safety-state`,
      { method: "GET", headers: { Accept: "application/json" }, cache: "no-store" },
    );
    if (response.status === 404) {
      return { kind: "missing", http_status: 404 };
    }
    if (!response.ok) {
      return { kind: "error", detail: `${response.status} ${response.statusText}` };
    }
    const payload = (await response.json()) as SafetyStatePayload;
    return { kind: "available", payload };
  } catch (err) {
    return { kind: "error", detail: err instanceof Error ? err.message : "fetch failed" };
  }
}

export function SafetyTab() {
  const [printers, setPrinters] = useState<Printer[] | null>(null);
  const [locks, setLocks] = useState<Record<string, PrinterLock>>({});
  const [safety, setSafety] = useState<Record<string, SafetyProbeStatus>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const list = await adapters.getPrinters();
      setPrinters(list);
      setError(null);
      // Pull lock + safety state per printer in parallel. The lock API is
      // shipped (W14); safety-state is probed honestly.
      const lockEntries = await Promise.all(
        list.map((p) =>
          adapters.getPrinterLockState(p.id).then(
            (lock) => [p.id, lock] as const,
            (lockErr) =>
              [
                p.id,
                {
                  printer_id: p.id,
                  locked: false,
                  reason: lockErr instanceof Error ? lockErr.message : "lock probe failed",
                  locked_by: null,
                  locked_at: null,
                } as PrinterLock,
              ] as const,
          ),
        ),
      );
      setLocks(Object.fromEntries(lockEntries));

      const safetyEntries = await Promise.all(
        list.map(async (p) => [p.id, await probeSafetyState(p.id)] as const),
      );
      setSafety(Object.fromEntries(safetyEntries));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load printer list.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const t = window.setInterval(() => void refresh(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(t);
  }, [refresh]);

  const counts = useMemo(() => {
    let available = 0;
    let missing = 0;
    let errored = 0;
    for (const v of Object.values(safety)) {
      if (v.kind === "available") available += 1;
      else if (v.kind === "missing") missing += 1;
      else if (v.kind === "error") errored += 1;
    }
    return { available, missing, errored, total: Object.keys(safety).length };
  }, [safety]);

  return (
    <div data-testid="safety-root" className="flex h-full flex-col gap-3">
      <header className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-surface p-3">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-fg">
            <ShieldCheck size={14} className="text-muted" /> Printer Safety
          </h2>
          <p className="text-xs text-muted">
            Probes <code className="font-mono text-[10px]">/api/printers/&lt;id&gt;/safety-state</code> per printer; lock
            state comes from <code className="font-mono text-[10px]">/api/printers/&lt;id&gt;/lock</code>.
            {printers
              ? ` · ${printers.length} printers · ${counts.available} safety live · ${counts.missing} endpoint-pending`
              : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          data-testid="safety-refresh"
          className="flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[11px] text-muted hover:border-accent-cyan/40 hover:text-fg disabled:opacity-50"
        >
          <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </header>

      {error && (
        <div role="alert" data-testid="safety-error" className="rounded border border-red-800/50 bg-red-950/30 p-2 font-mono text-[11px] text-red-200">
          {error}
        </div>
      )}

      {printers && printers.length === 0 ? (
        <div data-testid="safety-empty" className="rounded border border-border bg-surface p-4 text-center text-xs text-muted">
          No printers registered. Onboard a printer from the Printers tab.
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-auto">
          <ul className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
            {(printers ?? []).map((p) => {
              const lock = locks[p.id];
              const probe = safety[p.id] ?? { kind: "pending" as const };
              return (
                <li
                  key={p.id}
                  data-testid={`safety-printer-${p.id}`}
                  className="rounded border border-border bg-surface p-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-fg">{p.name}</div>
                      <div className="font-mono text-[10px] text-muted">
                        {p.id} · {p.model}
                      </div>
                    </div>
                    <span className={`text-[10px] uppercase ${STATUS_TONE[p.status] ?? "text-muted"}`}>
                      {p.status}
                    </span>
                  </div>

                  <div className="mt-3 grid gap-1.5 text-xs">
                    <Row
                      icon={lock?.locked ? <Lock size={12} className="text-accent-amber" /> : <ShieldCheck size={12} className="text-accent-green" />}
                      label="Lock"
                      value={
                        lock
                          ? lock.locked
                            ? `locked by ${lock.locked_by ?? "?"}`
                            : "unlocked"
                          : "probing…"
                      }
                      detail={lock?.reason}
                    />
                    <SafetyRow probe={probe} />
                    <Row
                      icon={<ShieldQuestion size={12} className="text-muted" />}
                      label="Policy"
                      value={p.safety_policy ?? "unknown"}
                      detail={p.write_enabled === true ? "write_enabled=true" : "write_enabled=false"}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function Row({
  icon,
  label,
  value,
  detail,
}: {
  icon: JSX.Element;
  label: string;
  value: string;
  detail?: string | null;
}) {
  return (
    <div className="flex items-start gap-2 rounded border border-border bg-bg/40 px-2 py-1.5">
      <span className="mt-0.5 shrink-0">{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2 text-[10px] uppercase text-muted">
          <span>{label}</span>
        </div>
        <div className="truncate text-fg">{value}</div>
        {detail && <div className="truncate text-[10px] text-muted">{detail}</div>}
      </div>
    </div>
  );
}

function SafetyRow({ probe }: { probe: SafetyProbeStatus }) {
  if (probe.kind === "pending") {
    return (
      <Row icon={<ShieldQuestion size={12} className="text-muted" />} label="Safety" value="probing…" />
    );
  }
  if (probe.kind === "missing") {
    return (
      <Row
        icon={<ShieldAlert size={12} className="text-accent-amber" />}
        label="Safety"
        value="endpoint not yet shipped"
        detail={`HTTP ${probe.http_status} on /safety-state`}
      />
    );
  }
  if (probe.kind === "error") {
    return (
      <Row
        icon={<ShieldAlert size={12} className="text-accent-red" />}
        label="Safety"
        value="probe failed"
        detail={probe.detail}
      />
    );
  }
  const { payload } = probe;
  const ok = payload.ok ?? null;
  const policy = payload.policy ?? "unknown";
  const writeEnabled =
    typeof payload.write_enabled === "boolean" ? payload.write_enabled : null;
  return (
    <Row
      icon={
        ok === true ? (
          <ShieldCheck size={12} className="text-accent-green" />
        ) : ok === false ? (
          <ShieldAlert size={12} className="text-accent-red" />
        ) : (
          <ShieldQuestion size={12} className="text-muted" />
        )
      }
      label="Safety"
      value={`${policy}${writeEnabled != null ? ` · write=${writeEnabled}` : ""}`}
      detail={payload.reason ?? null}
    />
  );
}
