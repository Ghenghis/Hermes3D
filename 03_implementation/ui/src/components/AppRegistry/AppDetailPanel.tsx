/**
 * AppDetailPanel — full metadata + last 5 proof results for one app.
 *
 * Backend: GET /api/apps/{id}  (W6-7 owns the route)
 *
 * Surfaced via the `#apps/<id>` hash route. The panel reads the id from
 * a prop so the consuming tab is responsible for parsing the URL — that
 * keeps this component pure and testable.
 */

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Clock, ExternalLink, Loader2, RotateCcw, XCircle } from "lucide-react";
import { appsClient, redactProofReason } from "../../api/appsClient";
import type {
  AppProofResult,
  ProofStatus,
  RegistryAppDetail,
} from "../../types/app-registry";

export interface AppDetailPanelProps {
  appId: string;
  /** Called when the user clicks the back/close affordance. */
  onClose?: () => void;
}

export function AppDetailPanel({ appId, onClose }: AppDetailPanelProps) {
  const [detail, setDetail] = useState<RegistryAppDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const next = await appsClient.getApp(appId, signal);
        if (signal?.aborted) {
          return;
        }
        setDetail(next);
        setError(null);
      } catch (caught) {
        if (signal?.aborted) {
          return;
        }
        setError(errorMessage(caught));
      }
    },
    [appId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const runProof = useCallback(async () => {
    setBusy(true);
    try {
      await appsClient.runProof(appId);
      await load();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }, [appId, load]);

  if (!detail && !error) {
    return (
      <div data-testid="app-detail-loading" aria-busy="true" className="space-y-2">
        <div className="h-6 w-48 animate-pulse rounded bg-surface2" />
        <div className="h-4 w-72 animate-pulse rounded bg-surface2" />
        <div className="h-32 w-full animate-pulse rounded bg-surface2" />
      </div>
    );
  }

  return (
    <section
      data-testid="app-detail-panel"
      className="flex min-h-0 w-full flex-col gap-3"
      aria-label={detail ? `${detail.name} app detail` : "App detail"}
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-fg">{detail?.name ?? appId}</h2>
          <p className="mt-0.5 text-[11px] text-muted">{detail?.id ?? appId}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-border px-2 py-1 text-[11px] text-fg hover:bg-surface2"
            >
              Back
            </button>
          )}
          <button
            type="button"
            onClick={() => void runProof()}
            disabled={busy}
            data-testid="app-detail-run-proof"
            className="rounded border border-border px-2 py-1 text-[11px] text-fg hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Running…" : "Run proof"}
          </button>
        </div>
      </header>

      {error && (
        <div
          role="alert"
          data-testid="app-detail-error"
          className="rounded border border-amber-700/50 bg-amber-950/30 px-3 py-2 text-xs text-amber-200"
        >
          App detail unreachable: {error}
        </div>
      )}

      {detail && (
        <>
          <dl
            data-testid="app-detail-versions"
            className="grid grid-cols-1 gap-3 rounded border border-border bg-surface p-3 text-[11px] sm:grid-cols-2"
          >
            <Field label="Current version" value={detail.current_version ?? "—"} />
            <Field
              label="License"
              value={`${detail.license?.label ?? detail.license?.spdx ?? "Unknown"}`}
            />
            <Field label="Lifecycle" value={detail.lifecycle} />
            <Field label="Update lane" value={detail.update_lane} />
            <Field
              label="Tested versions"
              value={
                (detail.tested_versions ?? []).length
                  ? detail.tested_versions.join(", ")
                  : "(none on record)"
              }
            />
            <Field label="Rollback supported" value={detail.rollback_supported ? "yes" : "no"} />
            {detail.upstream_url && (
              <div className="sm:col-span-2">
                <dt className="text-[10px] uppercase text-muted">Upstream</dt>
                <dd className="mt-0.5">
                  <a
                    href={detail.upstream_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-cyan-200 hover:underline"
                  >
                    {detail.upstream_url}
                    <ExternalLink className="h-3 w-3" aria-hidden />
                  </a>
                </dd>
              </div>
            )}
            {detail.description && (
              <div className="sm:col-span-2">
                <dt className="text-[10px] uppercase text-muted">Description</dt>
                <dd className="mt-0.5 text-fg">{detail.description}</dd>
              </div>
            )}
          </dl>

          <section
            data-testid="app-detail-proofs"
            aria-label="Recent proof results"
            className="rounded border border-border bg-surface"
          >
            <header className="flex items-center justify-between border-b border-border/60 px-3 py-2">
              <h3 className="text-xs font-semibold uppercase text-muted">Recent proofs</h3>
              <span className="text-[10px] text-muted">last 5</span>
            </header>
            <ul className="divide-y divide-border/60">
              {(detail.recent_proofs ?? []).length === 0 && (
                <li className="px-3 py-2 text-[11px] text-muted">No proofs on record yet.</li>
              )}
              {(detail.recent_proofs ?? []).slice(0, 5).map((proof, idx) => (
                <li
                  key={proof.proof_event_id ?? `proof-${idx}`}
                  data-testid={`app-detail-proof-${idx}`}
                  className="flex flex-wrap items-center gap-3 px-3 py-2 text-[11px]"
                >
                  <ProofIcon status={proof.status} />
                  <span className="font-mono text-muted">{proof.proof_event_id ?? "—"}</span>
                  <span className="text-muted">{formatTimestamp(proof.at)}</span>
                  <span className="grow text-fg">
                    {redactProofReason(proof.reason ?? null) || "—"}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {detail.rollback_supported && (
            <section
              data-testid="app-detail-rollback"
              className="rounded border border-amber-700/40 bg-amber-950/20 p-3 text-[11px] text-amber-100"
            >
              <h3 className="flex items-center gap-2 text-xs font-semibold uppercase">
                <RotateCcw className="h-3.5 w-3.5" aria-hidden /> Rollback runbook
              </h3>
              <p className="mt-1 text-amber-200/90">
                Read the runbook before initiating rollback. The backend gates rollback on a
                fresh proof of the prior version.
              </p>
              {detail.rollback_runbook_url ? (
                <a
                  href={detail.rollback_runbook_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-amber-100 hover:underline"
                >
                  Open runbook
                  <ExternalLink className="h-3 w-3" aria-hidden />
                </a>
              ) : (
                <p className="mt-2 text-amber-200/80">
                  No runbook URL provided by the backend.
                </p>
              )}
            </section>
          )}
        </>
      )}
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase text-muted">{label}</dt>
      <dd className="mt-0.5 text-fg">{value}</dd>
    </div>
  );
}

function ProofIcon({ status }: { status: ProofStatus }) {
  const common = "h-4 w-4";
  if (status === "pass") {
    return <CheckCircle2 className={`${common} text-green-300`} aria-label="pass" />;
  }
  if (status === "fail") {
    return <XCircle className={`${common} text-rose-300`} aria-label="fail" />;
  }
  if (status === "pending") {
    return <Loader2 className={`${common} animate-spin text-cyan-200`} aria-label="pending" />;
  }
  return <Clock className={`${common} text-muted`} aria-label="unknown" />;
}

function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return iso;
  return new Date(ts).toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Backend rejected the request.";
}

// Re-export the AppProofResult type so consumers don't need to reach into
// the types module separately when extending this panel.
export type { AppProofResult };
