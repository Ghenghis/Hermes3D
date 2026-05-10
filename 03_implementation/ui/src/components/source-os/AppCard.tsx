/**
 * AppCard — single tile in the 60-App Coverage Matrix.
 *
 * Honest readiness contract:
 *   - "Ready" only when proof_command is non-empty AND
 *     last_proof_status ∈ {"passed", "pass"}. Anything else renders as
 *     "Unknown" (em-dash placeholder + amber dot) or "Blocked"
 *     (failed proof). NEVER fabricate green.
 *
 * Navigation:
 *   - Click anywhere on the card → `window.location.hash = "apps/{id}"`
 *     which routes to AppRegistryTab → AppDetailPanel (W6-8/W8-2).
 *   - Click "Launch" → POST /api/modules/{id}/launch, then surface the
 *     accepted/blocked outcome inline.
 *
 * Sources consulted:
 *   - React Grid Layout card sizing
 *     <https://github.com/react-grid-layout/react-grid-layout> — small
 *     uniform tile pattern used by the matrix.
 *   - VS Code Marketplace extension card UI
 *     <https://marketplace.visualstudio.com/items?itemName=ms-python.python>
 *     — used the install-state pill + status dot idiom.
 *
 * Owner: claude-w15-a13-source-os.
 * Scope: NEW file. Does NOT replace AppRegistry/AppStatusPanel rows.
 */

import { useCallback, useState } from "react";
import { ExternalLink, Play, Shield } from "lucide-react";

export type AppCardProofStatus = "passed" | "failed" | "pending" | "unknown";

export interface AppCardData {
  id: string;
  /** Display name (falls back to id when missing). */
  name: string;
  /** Section/category id from the backend payload (e.g. "slicers"). */
  section: string;
  /** Pretty category label rendered as chip. */
  categoryLabel: string;
  /** Optional detected version. */
  version: string | null;
  /** Whether the backend has a `proof_command` on record. */
  hasProofCommand: boolean;
  /** Normalised last-proof status. */
  proofStatus: AppCardProofStatus;
  /** When proof_command is missing this short string explains the gap. */
  proofGapReason: string | null;
  /** Install state lifted from `/api/apps`. */
  installState: string;
  /** Optional repo / docs URL for the external-link affordance. */
  upstreamUrl: string | null;
  /** Update lane: stable / canary / frozen / experimental / unknown. */
  updateLane: string;
  /** Lifecycle status. */
  lifecycle: string;
  /** SPDX license. */
  license: string | null;
}

export interface AppCardProps {
  app: AppCardData;
  /**
   * Optional override for the navigate handler — defaults to setting
   * `window.location.hash = "apps/{id}"` so the existing AppRegistryTab
   * detail route (W6-8/W8-2) takes over.
   */
  onNavigate?: (id: string) => void;
  /**
   * Optional override for launch — defaults to POST
   * /api/modules/{id}/launch using `bridgeBaseUrl`.
   */
  onLaunch?: (id: string) => Promise<LaunchOutcome> | LaunchOutcome;
  /** Backend bridge base URL (e.g. http://127.0.0.1:8765). */
  bridgeBaseUrl: string;
  /** True when this card is currently focused via the rail. */
  selected?: boolean;
}

export interface LaunchOutcome {
  success: boolean;
  status: string;
  message: string;
}

function initials(name: string, id: string): string {
  const source = name && name.length > 0 ? name : id;
  const tokens = source
    .replace(/[_\-./]+/g, " ")
    .split(" ")
    .filter(Boolean);
  if (tokens.length === 0) {
    return "??";
  }
  if (tokens.length === 1) {
    return tokens[0].slice(0, 2).toUpperCase();
  }
  return (tokens[0][0] + tokens[1][0]).toUpperCase();
}

function statusDotClass(status: AppCardProofStatus, hasProof: boolean): string {
  if (!hasProof) return "bg-amber-700"; // honest unknown — missing proof_command
  if (status === "passed") return "bg-green-500";
  if (status === "failed") return "bg-rose-500";
  if (status === "pending") return "bg-cyan-500 animate-pulse";
  return "bg-amber-600"; // unknown despite having a proof_command
}

function readinessLabel(status: AppCardProofStatus, hasProof: boolean): string {
  if (!hasProof) return "—"; // honest em-dash; never "Ready"
  if (status === "passed") return "Ready";
  if (status === "failed") return "Blocked";
  if (status === "pending") return "Proving";
  return "Unknown";
}

function readinessTone(status: AppCardProofStatus, hasProof: boolean): string {
  if (!hasProof) return "bg-surface2 text-muted border border-border";
  if (status === "passed") return "bg-green-950/70 text-green-300 border border-green-700/50";
  if (status === "failed") return "bg-rose-950/70 text-rose-300 border border-rose-700/50";
  if (status === "pending") return "bg-cyan-950/70 text-cyan-200 border border-cyan-700/50";
  return "bg-amber-950/70 text-amber-200 border border-amber-700/50";
}

export function AppCard({
  app,
  onNavigate,
  onLaunch,
  bridgeBaseUrl,
  selected = false,
}: AppCardProps) {
  const [launchBusy, setLaunchBusy] = useState(false);
  const [launchResult, setLaunchResult] = useState<LaunchOutcome | null>(null);

  const navigate = useCallback(() => {
    if (onNavigate) {
      onNavigate(app.id);
      return;
    }
    if (typeof window !== "undefined") {
      window.location.hash = `apps/${encodeURIComponent(app.id)}`;
    }
  }, [app.id, onNavigate]);

  const handleLaunch = useCallback(
    async (event: React.MouseEvent) => {
      event.stopPropagation();
      setLaunchBusy(true);
      setLaunchResult(null);
      try {
        let outcome: LaunchOutcome;
        if (onLaunch) {
          outcome = await onLaunch(app.id);
        } else {
          const response = await fetch(
            `${bridgeBaseUrl}/api/modules/${encodeURIComponent(app.id)}/launch`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json", Accept: "application/json" },
              body: JSON.stringify({ actor: "operator" }),
              cache: "no-store",
            },
          );
          const payload = (await response.json().catch(() => null)) as
            | {
                module_id?: string;
                success?: boolean;
                status?: string;
                notes?: string;
                message?: string;
              }
            | null;
          outcome = {
            success: Boolean(payload?.success),
            status: payload?.status ?? (response.ok ? "ok" : "error"),
            message: payload?.notes ?? payload?.message ?? response.statusText,
          };
        }
        setLaunchResult(outcome);
      } catch (caught) {
        setLaunchResult({
          success: false,
          status: "error",
          message: caught instanceof Error ? caught.message : "launch failed",
        });
      } finally {
        setLaunchBusy(false);
      }
    },
    [app.id, bridgeBaseUrl, onLaunch],
  );

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      navigate();
    }
  };

  return (
    <article
      role="link"
      tabIndex={0}
      aria-label={`Open ${app.name} detail`}
      onClick={navigate}
      onKeyDown={handleKeyDown}
      data-testid={`app-card-${app.id}`}
      data-category={app.section}
      data-proof-status={app.hasProofCommand ? app.proofStatus : "no-proof-command"}
      className={[
        "group flex h-full cursor-pointer flex-col gap-2 rounded border bg-surface/70 p-2.5 text-left transition-colors",
        selected
          ? "border-accent-blue ring-1 ring-accent-blue/30"
          : "border-border hover:border-accent-blue/40 hover:bg-surface2/60",
      ].join(" ")}
    >
      {/* Top row: avatar + name + status dot */}
      <div className="flex items-start gap-2">
        <div
          aria-hidden
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded bg-accent-blue/15 font-mono text-[11px] font-bold text-accent-blue"
        >
          {initials(app.name, app.id)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${statusDotClass(app.proofStatus, app.hasProofCommand)}`}
              aria-hidden
            />
            <h3 className="min-w-0 truncate text-[12px] font-semibold text-fg">{app.name}</h3>
          </div>
          <p className="mt-0.5 truncate text-[10px] text-muted" title={app.id}>
            {app.categoryLabel} · {app.id}
          </p>
        </div>
      </div>

      {/* Chips row: version + readiness + lane */}
      <div className="flex flex-wrap items-center gap-1">
        <span
          className="rounded bg-surface2 px-1.5 py-0.5 font-mono text-[9px] uppercase text-muted"
          title="Detected version"
        >
          {app.version ?? "—"}
        </span>
        <span
          className={`rounded px-1.5 py-0.5 text-[9px] font-medium uppercase ${readinessTone(app.proofStatus, app.hasProofCommand)}`}
          title={
            app.hasProofCommand
              ? `proof_command present; last proof status = ${app.proofStatus}`
              : (app.proofGapReason ?? "No proof_command on record — not Ready")
          }
        >
          {readinessLabel(app.proofStatus, app.hasProofCommand)}
        </span>
        <span
          className="rounded bg-surface2 px-1.5 py-0.5 text-[9px] uppercase text-muted"
          title={`update lane: ${app.updateLane}`}
        >
          {app.updateLane}
        </span>
      </div>

      {/* Action row */}
      <div className="mt-auto flex items-center justify-between gap-1">
        <button
          type="button"
          onClick={handleLaunch}
          disabled={launchBusy}
          data-testid={`app-card-${app.id}-launch`}
          className="inline-flex items-center gap-1 rounded border border-border bg-bg/40 px-2 py-1 text-[10px] text-fg hover:border-accent-blue/40 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label={`Launch ${app.name}`}
        >
          <Play className="h-3 w-3" aria-hidden />
          {launchBusy ? "Launching" : "Launch"}
        </button>
        <div className="flex items-center gap-1">
          {app.upstreamUrl && (
            <a
              href={app.upstreamUrl}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-0.5 rounded border border-transparent px-1 py-1 text-[10px] text-muted hover:border-border hover:text-fg"
              aria-label={`Open upstream for ${app.name}`}
              title={app.upstreamUrl}
            >
              <ExternalLink className="h-3 w-3" aria-hidden />
            </a>
          )}
          <span
            className="inline-flex items-center gap-0.5 text-[10px] text-muted"
            title={app.hasProofCommand ? "Proof command available" : "No proof command — cannot be marked Ready"}
          >
            <Shield
              className={`h-3 w-3 ${app.hasProofCommand ? "text-green-400" : "text-amber-500"}`}
              aria-hidden
            />
          </span>
        </div>
      </div>

      {/* Launch result */}
      {launchResult && (
        <div
          role="status"
          data-testid={`app-card-${app.id}-launch-result`}
          className={`truncate rounded border px-1.5 py-1 text-[10px] ${
            launchResult.success
              ? "border-green-700/40 bg-green-950/50 text-green-200"
              : "border-amber-700/40 bg-amber-950/50 text-amber-200"
          }`}
          title={launchResult.message}
        >
          {launchResult.success ? "launched" : launchResult.status}: {launchResult.message}
        </div>
      )}
    </article>
  );
}
