/**
 * Workflows tab — honest re-creation of the workflows page that W15 PR-3
 * removed when it deleted the unrouted fake-data tab.
 *
 * Data source: `GET /api/workflows` via `adapters.getActiveWorkflows()`.
 *
 * Empty/blocked states are explicit: when the backend returns `[]` (or a
 * fetch error) we render an "No active workflows" message rather than
 * sample/placeholder rows. There is no mock data in this file.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import { adapters } from "../api/adapters";
import type { Workflow, WorkflowStatus } from "../types/workflow";

const REFRESH_INTERVAL_MS = 15_000;

const STATUS_CLASS: Record<WorkflowStatus, string> = {
  active: "border-cyan-700/60 bg-cyan-950/30 text-cyan-200",
  completed: "border-green-700/60 bg-green-950/30 text-green-200",
  failed: "border-red-700/60 bg-red-950/30 text-red-200",
  queued: "border-amber-700/60 bg-amber-950/30 text-amber-200",
};

export function WorkflowsTab() {
  const [workflows, setWorkflows] = useState<Workflow[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await adapters.getActiveWorkflows();
      setWorkflows(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workflows.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const t = window.setInterval(() => void refresh(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(t);
  }, [refresh]);

  const grouped = useMemo(() => {
    if (!workflows) return null;
    const byStatus: Record<WorkflowStatus, Workflow[]> = {
      active: [],
      queued: [],
      failed: [],
      completed: [],
    };
    for (const wf of workflows) {
      const key = (byStatus[wf.status] ? wf.status : "active") as WorkflowStatus;
      byStatus[key].push(wf);
    }
    return byStatus;
  }, [workflows]);

  return (
    <div data-testid="workflows-root" className="flex h-full flex-col gap-3">
      <header className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-surface p-3">
        <div>
          <h2 className="text-sm font-semibold text-fg">Workflows</h2>
          <p className="text-xs text-muted">
            Live from <code className="font-mono text-[10px]">GET /api/workflows</code>
            {workflows ? ` · ${workflows.length} returned` : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          data-testid="workflows-refresh"
          className="flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[11px] text-muted hover:border-accent-cyan/40 hover:text-fg disabled:opacity-50"
        >
          <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </header>

      {error && (
        <div role="alert" data-testid="workflows-error" className="rounded border border-red-800/50 bg-red-950/30 p-2 font-mono text-[11px] text-red-200">
          {error}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-auto">
        {workflows === null && !error ? (
          <EmptyHint label="Loading workflows…" />
        ) : workflows && workflows.length === 0 ? (
          <EmptyHint
            data-testid="workflows-empty"
            label="No active workflows"
            detail="GET /api/workflows returned an empty list. Workflows are created by the Hermes Agent pipeline (Prompt → 3D Gen → … → Proof)."
          />
        ) : (
          <div className="grid gap-2">
            {grouped &&
              (Object.keys(grouped) as WorkflowStatus[])
                .filter((s) => grouped[s].length > 0)
                .map((status) => (
                  <section
                    key={status}
                    data-testid={`workflows-group-${status}`}
                    className="rounded border border-border bg-surface p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-xs font-semibold uppercase text-muted">{status}</h3>
                      <span className="rounded bg-bg/40 px-2 py-0.5 font-mono text-[10px] text-muted">
                        {grouped[status].length}
                      </span>
                    </div>
                    <ul className="mt-2 space-y-2">
                      {grouped[status].map((wf) => (
                        <li
                          key={wf.id}
                          data-testid={`workflow-${wf.id}`}
                          className={`rounded border px-3 py-2 text-xs ${STATUS_CLASS[wf.status] ?? STATUS_CLASS.active}`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="truncate font-semibold">{wf.name}</span>
                            <span className="rounded bg-bg/40 px-2 py-0.5 font-mono text-[10px] uppercase">
                              {wf.status}
                            </span>
                          </div>
                          <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-muted">
                            <span className="flex items-center gap-1">
                              <Activity size={10} /> stage {wf.active_stage + 1} / {wf.stages.length}
                            </span>
                            <span>progress {Math.round(wf.progress)}%</span>
                            <span className="font-mono text-[10px]">
                              {new Date(wf.started_utc).toLocaleString()}
                            </span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </section>
                ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyHint({
  label,
  detail,
  "data-testid": testId,
}: {
  label: string;
  detail?: string;
  "data-testid"?: string;
}) {
  return (
    <div
      data-testid={testId}
      className="flex h-full flex-col items-center justify-center rounded border border-border bg-surface p-4 text-center"
    >
      <div className="text-sm font-medium text-fg">{label}</div>
      {detail && <div className="mt-1 max-w-md text-xs text-muted">{detail}</div>}
    </div>
  );
}
