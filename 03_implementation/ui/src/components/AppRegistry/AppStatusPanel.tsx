/**
 * AppStatusPanel — table view of the 60-app registry.
 *
 * Backend: GET /api/apps  (W6-7 owns the route)
 * Polls every 30s.
 * Row actions:
 *   - Run proof   → POST /api/apps/{id}/run-proof
 *   - View detail → expand inline, or open #apps/<id>
 *   - Rollback    → only when rollback_supported is true
 *
 * Accessibility: rendered as a single ARIA grid (role="table") with
 * column headers and row groups so screen readers can navigate the
 * registry. Per
 * https://www.w3.org/WAI/ARIA/apg/patterns/table/ — static tables use
 * role="table" with role="rowgroup", role="row", role="columnheader",
 * role="cell".
 *
 * Sources consulted:
 *   - TanStack Table docs: https://tanstack.com/table/v8 (we don't add
 *     the dep — the registry is small and a hand-rolled <table> keeps
 *     bundle weight low and matches the rest of the UI).
 *   - ARIA APG table pattern (link above) — used for column header and
 *     sort-button semantics.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, Clock, Loader2, RotateCcw, XCircle } from "lucide-react";
import { appsClient, redactProofReason } from "../../api/appsClient";
import type {
  AppLifecycleStatus,
  AppUpdateLane,
  ProofStatus,
  RegistryApp,
} from "../../types/app-registry";

const POLL_INTERVAL_MS = 30_000;

type ToastTone = "info" | "success" | "error";

interface ToastState {
  id: number;
  tone: ToastTone;
  title: string;
  body?: string;
}

interface PendingAction {
  id: string;
  kind: "run-proof" | "rollback";
}

export interface AppStatusPanelProps {
  /**
   * Optional override for navigation when "View details" is clicked.
   * Defaults to setting `window.location.hash` to `apps/<id>`.
   */
  onNavigateDetail?: (appId: string) => void;
  /**
   * Test seam: replace the polling interval. Default 30s.
   * Pass 0 to disable polling.
   */
  pollIntervalMs?: number;
}

export function AppStatusPanel({
  onNavigateDetail,
  pollIntervalMs = POLL_INTERVAL_MS,
}: AppStatusPanelProps) {
  const [apps, setApps] = useState<RegistryApp[] | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastState[]>([]);
  const toastIdRef = useRef(0);

  const pushToast = useCallback((next: Omit<ToastState, "id">) => {
    toastIdRef.current += 1;
    const id = toastIdRef.current;
    setToasts((prev) => [...prev, { ...next, id }]);
    // Auto-dismiss after 6s; tests can read DOM synchronously before that.
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6000);
  }, []);

  const loadApps = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const next = await appsClient.listApps(signal);
        if (signal?.aborted) {
          return;
        }
        setApps(next);
        setLoadingError(null);
      } catch (error) {
        if (signal?.aborted) {
          return;
        }
        const message = errorMessage(error);
        setLoadingError(message);
        // Keep last-known apps for graceful degradation; only toast on a
        // first transition from healthy to errored state.
        setApps((prev) => prev ?? []);
      }
    },
    [],
  );

  // Initial load + 30s poll.
  useEffect(() => {
    const controller = new AbortController();
    void loadApps(controller.signal);
    if (pollIntervalMs <= 0) {
      return () => controller.abort();
    }
    const interval = window.setInterval(() => {
      void loadApps(controller.signal);
    }, pollIntervalMs);
    return () => {
      window.clearInterval(interval);
      controller.abort();
    };
  }, [loadApps, pollIntervalMs]);

  const runProof = useCallback(
    async (app: RegistryApp) => {
      setPending({ id: app.id, kind: "run-proof" });
      try {
        const result = await appsClient.runProof(app.id);
        const tone: ToastTone = result.accepted ? "success" : "error";
        pushToast({
          tone,
          title: result.accepted
            ? `${app.name}: proof requested`
            : `${app.name}: proof rejected`,
          body:
            redactProofReason(result.reason ?? null) ||
            (result.proof_event_id ? `event ${result.proof_event_id}` : undefined),
        });
        // Optimistic refresh; the next poll will reconcile.
        await loadApps();
      } catch (error) {
        pushToast({
          tone: "error",
          title: `${app.name}: proof request failed`,
          body: errorMessage(error),
        });
      } finally {
        setPending(null);
      }
    },
    [loadApps, pushToast],
  );

  const requestRollback = useCallback(
    (app: RegistryApp) => {
      // Rollback is intentionally surfaced as a navigation to the detail
      // page where the operator can read the runbook before confirming.
      // We never invoke a destructive endpoint directly from the table.
      pushToast({
        tone: "info",
        title: `${app.name}: review rollback runbook`,
        body: "Open the app detail page to confirm rollback target.",
      });
      navigateToDetail(app.id);
    },
    [pushToast],
  );

  const navigateToDetail = useCallback(
    (id: string) => {
      if (onNavigateDetail) {
        onNavigateDetail(id);
        return;
      }
      window.location.hash = `apps/${id}`;
    },
    [onNavigateDetail],
  );

  const totals = useMemo(() => summarize(apps ?? []), [apps]);

  if (apps === null && !loadingError) {
    return <LoadingSkeleton />;
  }

  return (
    <section
      data-testid="app-status-panel"
      className="flex min-h-0 w-full flex-col gap-3"
      aria-label="Hermes app registry status"
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-fg">App Registry Status</h2>
          <p className="mt-0.5 text-[11px] text-muted">
            Live view of the {apps?.length ?? 0}-app registry. Polls every {Math.round(pollIntervalMs / 1000)}s.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <CountPill label="apps" value={totals.total} />
          <CountPill label="proof pass" value={totals.pass} tone="green" />
          <CountPill label="proof fail" value={totals.fail} tone={totals.fail ? "amber" : "muted"} />
          <CountPill label="never proofed" value={totals.unknown} tone={totals.unknown ? "cyan" : "muted"} />
        </div>
      </header>

      {loadingError && (
        <div
          role="alert"
          data-testid="app-status-panel-error"
          className="rounded border border-amber-700/50 bg-amber-950/30 px-3 py-2 text-xs text-amber-200"
        >
          App registry unreachable: {loadingError}. Showing last-known data.
        </div>
      )}

      <div className="overflow-x-auto rounded border border-border bg-surface">
        <table
          role="table"
          aria-rowcount={(apps ?? []).length + 1}
          className="min-w-full border-collapse text-left text-xs"
        >
          <thead role="rowgroup" className="bg-surface2 text-[11px] uppercase text-muted">
            <tr role="row">
              <th role="columnheader" scope="col" className="px-3 py-2">
                Name
              </th>
              <th role="columnheader" scope="col" className="px-3 py-2">
                Version
              </th>
              <th role="columnheader" scope="col" className="px-3 py-2">
                Tested
              </th>
              <th role="columnheader" scope="col" className="px-3 py-2">
                License
              </th>
              <th role="columnheader" scope="col" className="px-3 py-2">
                Lane
              </th>
              <th role="columnheader" scope="col" className="px-3 py-2">
                Last proof
              </th>
              <th role="columnheader" scope="col" className="px-3 py-2">
                When
              </th>
              <th role="columnheader" scope="col" className="px-3 py-2 text-right">
                Actions
              </th>
            </tr>
          </thead>
          <tbody role="rowgroup">
            {(apps ?? []).length === 0 && !loadingError && (
              <tr role="row">
                <td role="cell" colSpan={8} className="px-3 py-4 text-center text-muted">
                  No apps returned by the registry. The backend may still be initializing.
                </td>
              </tr>
            )}
            {(apps ?? []).map((app, idx) => {
              const expanded = expandedId === app.id;
              return (
                <Row
                  key={app.id}
                  app={app}
                  rowIndex={idx + 2}
                  expanded={expanded}
                  busy={pending?.id === app.id}
                  onToggleExpand={() => setExpandedId(expanded ? null : app.id)}
                  onRunProof={() => void runProof(app)}
                  onViewDetail={() => navigateToDetail(app.id)}
                  onRollback={() => requestRollback(app)}
                />
              );
            })}
          </tbody>
        </table>
      </div>

      <div
        aria-live="polite"
        data-testid="app-status-toasts"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-72 flex-col gap-2"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.tone === "error" ? "alert" : "status"}
            data-testid={`app-status-toast-${toast.tone}`}
            className={`pointer-events-auto rounded border px-3 py-2 text-xs shadow-lg ${toastClass(toast.tone)}`}
          >
            <div className="font-semibold">{toast.title}</div>
            {toast.body && <div className="mt-0.5 text-[11px] opacity-90">{toast.body}</div>}
          </div>
        ))}
      </div>
    </section>
  );
}

interface RowProps {
  app: RegistryApp;
  rowIndex: number;
  expanded: boolean;
  busy: boolean;
  onToggleExpand: () => void;
  onRunProof: () => void;
  onViewDetail: () => void;
  onRollback: () => void;
}

function Row({
  app,
  rowIndex,
  expanded,
  busy,
  onToggleExpand,
  onRunProof,
  onViewDetail,
  onRollback,
}: RowProps) {
  const proof = app.last_proof;
  const tested = app.tested_versions ?? [];
  return (
    <>
      <tr
        role="row"
        aria-rowindex={rowIndex}
        data-testid={`app-row-${app.id}`}
        className="border-t border-border/60 align-top text-fg hover:bg-surface2/40"
      >
        <th role="rowheader" scope="row" className="px-3 py-2 text-xs font-semibold">
          <button
            type="button"
            onClick={onToggleExpand}
            aria-expanded={expanded}
            aria-controls={`app-row-${app.id}-detail`}
            className="text-left text-fg hover:underline"
          >
            {app.name}
          </button>
          <div className="text-[10px] font-normal text-muted">{app.id}</div>
        </th>
        <td role="cell" className="px-3 py-2 font-mono text-[11px]">
          {app.current_version ?? <UnknownPlaceholder />}
        </td>
        <td role="cell" className="px-3 py-2">
          <div className="flex flex-wrap gap-1">
            {tested.length === 0 && <UnknownPlaceholder />}
            {tested.slice(0, 4).map((version) => (
              <span
                key={version}
                className="rounded bg-surface2 px-1.5 py-0.5 font-mono text-[10px] text-muted"
              >
                {version}
              </span>
            ))}
            {tested.length > 4 && (
              <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] text-muted">
                +{tested.length - 4}
              </span>
            )}
          </div>
        </td>
        <td role="cell" className="px-3 py-2">
          <LicenseBadge spdx={app.license?.spdx ?? "Unknown"} label={app.license?.label} />
        </td>
        <td role="cell" className="px-3 py-2">
          <LaneBadge lane={app.update_lane} lifecycle={app.lifecycle} />
        </td>
        <td role="cell" className="px-3 py-2">
          <ProofStatusIcon status={proof?.status ?? "unknown"} />
        </td>
        <td role="cell" className="px-3 py-2 text-[11px] text-muted">
          {formatRelative(proof?.at ?? null)}
        </td>
        <td role="cell" className="px-3 py-2 text-right">
          <div className="inline-flex flex-wrap gap-1">
            <button
              type="button"
              onClick={onRunProof}
              disabled={busy}
              data-testid={`app-row-${app.id}-run-proof`}
              className="rounded border border-border px-2 py-1 text-[11px] text-fg hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? "Running…" : "Run proof"}
            </button>
            <button
              type="button"
              onClick={onViewDetail}
              data-testid={`app-row-${app.id}-detail`}
              className="rounded border border-border px-2 py-1 text-[11px] text-fg hover:bg-surface2"
            >
              View details
            </button>
            {app.rollback_supported && (
              <button
                type="button"
                onClick={onRollback}
                data-testid={`app-row-${app.id}-rollback`}
                className="inline-flex items-center gap-1 rounded border border-amber-700/60 px-2 py-1 text-[11px] text-amber-200 hover:bg-amber-950/40"
              >
                <RotateCcw className="h-3 w-3" aria-hidden /> Rollback
              </button>
            )}
          </div>
        </td>
      </tr>
      {expanded && (
        <tr role="row" id={`app-row-${app.id}-detail`} className="bg-surface2/40">
          <td role="cell" colSpan={8} className="px-3 py-3">
            <dl className="grid grid-cols-1 gap-2 text-[11px] text-muted sm:grid-cols-2">
              <div>
                <dt className="text-[10px] uppercase">Description</dt>
                <dd className="mt-0.5 text-fg">{app.description ?? "No description provided."}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase">Lifecycle</dt>
                <dd className="mt-0.5 text-fg">{app.lifecycle}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase">Tested versions</dt>
                <dd className="mt-0.5 break-words font-mono text-[11px] text-fg">
                  {tested.length ? tested.join(", ") : "(none on record)"}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase">Last proof reason</dt>
                <dd className="mt-0.5 text-fg">
                  {redactProofReason(proof?.reason ?? null) || "(none)"}
                </dd>
              </div>
            </dl>
          </td>
        </tr>
      )}
    </>
  );
}

function LoadingSkeleton() {
  return (
    <div data-testid="app-status-panel-loading" aria-busy="true" className="space-y-2">
      <div className="h-6 w-48 animate-pulse rounded bg-surface2" />
      <div className="h-4 w-72 animate-pulse rounded bg-surface2" />
      <div className="rounded border border-border bg-surface p-3">
        {[0, 1, 2, 3].map((row) => (
          <div key={row} className="my-2 h-5 animate-pulse rounded bg-surface2" />
        ))}
      </div>
    </div>
  );
}

function CountPill({
  label,
  value,
  tone = "muted",
}: {
  label: string;
  value: number;
  tone?: "green" | "amber" | "cyan" | "muted";
}) {
  const toneClass = {
    green: "bg-green-950/70 text-green-300",
    amber: "bg-amber-950/70 text-amber-200",
    cyan: "bg-cyan-950/70 text-cyan-200",
    muted: "bg-surface2 text-muted",
  }[tone];
  return (
    <span className={`rounded px-2 py-1 text-[10px] uppercase ${toneClass}`}>
      {value} {label}
    </span>
  );
}

function LicenseBadge({ spdx, label }: { spdx: string; label?: string }) {
  const display = label ?? spdx;
  const isUnknown = spdx === "Unknown" || !spdx;
  return (
    <span
      title={`SPDX: ${spdx}`}
      className={`inline-block rounded px-1.5 py-0.5 text-[10px] uppercase ${
        isUnknown ? "bg-amber-950/50 text-amber-200" : "bg-surface2 text-muted"
      }`}
    >
      {display}
    </span>
  );
}

function LaneBadge({ lane, lifecycle }: { lane: AppUpdateLane; lifecycle: AppLifecycleStatus }) {
  const tone =
    lane === "stable" || lifecycle === "stable"
      ? "bg-green-950/60 text-green-300"
      : lane === "canary" || lifecycle === "canary"
      ? "bg-cyan-950/60 text-cyan-200"
      : lane === "frozen" || lifecycle === "frozen"
      ? "bg-amber-950/60 text-amber-200"
      : "bg-surface2 text-muted";
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] uppercase ${tone}`}>
      {lane}
    </span>
  );
}

function ProofStatusIcon({ status }: { status: ProofStatus }) {
  const common = "h-4 w-4";
  if (status === "pass") {
    return (
      <span
        className="inline-flex items-center gap-1 text-green-300"
        aria-label="proof pass"
        title="Last proof passed"
      >
        <CheckCircle2 className={common} aria-hidden />
        <span className="sr-only">pass</span>
      </span>
    );
  }
  if (status === "fail") {
    return (
      <span
        className="inline-flex items-center gap-1 text-rose-300"
        aria-label="proof fail"
        title="Last proof failed"
      >
        <XCircle className={common} aria-hidden />
        <span className="sr-only">fail</span>
      </span>
    );
  }
  if (status === "pending") {
    return (
      <span
        className="inline-flex items-center gap-1 text-cyan-200"
        aria-label="proof pending"
        title="Proof is running"
      >
        <Loader2 className={`${common} animate-spin`} aria-hidden />
        <span className="sr-only">pending</span>
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 text-muted"
      aria-label="proof unknown"
      title="No proof on record"
    >
      <Clock className={common} aria-hidden />
      <span className="sr-only">unknown</span>
    </span>
  );
}

function UnknownPlaceholder() {
  return (
    <span className="text-muted" aria-label="value unknown">
      —
    </span>
  );
}

function toastClass(tone: ToastTone): string {
  if (tone === "success") {
    return "border-green-800/60 bg-green-950/80 text-green-100";
  }
  if (tone === "error") {
    return "border-rose-800/60 bg-rose-950/80 text-rose-100";
  }
  return "border-cyan-800/60 bg-cyan-950/80 text-cyan-100";
}

function summarize(apps: RegistryApp[]) {
  let pass = 0;
  let fail = 0;
  let unknown = 0;
  for (const app of apps) {
    const status = app.last_proof?.status ?? "unknown";
    if (status === "pass") pass += 1;
    else if (status === "fail") fail += 1;
    else unknown += 1;
  }
  return { total: apps.length, pass, fail, unknown };
}

function formatRelative(iso: string | null): string {
  if (!iso) return "never";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return iso;
  const diffMs = Date.now() - ts;
  const seconds = Math.round(diffMs / 1000);
  if (Math.abs(seconds) < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Backend rejected the request.";
}
