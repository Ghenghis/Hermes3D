/**
 * PlannerQueue — Wave 15 A14.
 *
 * Display widget for the autopilot planner queue. Reads `Workflow[]` from
 * `adapters.getActiveWorkflows()` (which hits `/api/workflows/active`) and
 * surfaces a compact, honest view of in-flight planner work.
 *
 * Strict rules:
 *   - No fake fallback data. If the API returns `[]` we render an empty
 *     state. If the API throws we surface an "unreachable" notice.
 *   - No write actions here — this component is read-only.
 */
import { useEffect, useState } from "react";
import { adapters } from "../../api/adapters";
import type { Workflow } from "../../types/workflow";

type LoadState = "loading" | "ready" | "error";

export interface PlannerQueueProps {
  /** Optional caller-supplied workflows (e.g. for tests). When omitted the component fetches itself. */
  workflows?: Workflow[];
}

export function PlannerQueue({ workflows: propWorkflows }: PlannerQueueProps = {}) {
  const [workflows, setWorkflows] = useState<Workflow[]>(propWorkflows ?? []);
  const [state, setState] = useState<LoadState>(propWorkflows ? "ready" : "loading");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (propWorkflows) {
      setWorkflows(propWorkflows);
      setState("ready");
      return;
    }
    let mounted = true;
    const load = () => {
      setState((prev) => (prev === "error" ? "loading" : prev));
      adapters
        .getActiveWorkflows()
        .then((next) => {
          if (!mounted) {
            return;
          }
          setWorkflows(next);
          setState("ready");
          setErrorMsg(null);
        })
        .catch((error) => {
          if (!mounted) {
            return;
          }
          setState("error");
          setErrorMsg(error instanceof Error ? error.message : "workflows API unreachable");
        });
    };
    load();
    const timer = window.setInterval(load, 15_000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [propWorkflows]);

  return (
    <section
      id="autopilot.planner_queue"
      data-testid="autopilot-planner-queue"
      className="flex min-h-0 flex-col rounded border border-border bg-surface p-4"
    >
      <header className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-fg">PLANNER QUEUE</h2>
          <p className="text-xs text-muted">Active workflows reported by the live backend.</p>
        </div>
        <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted" data-testid="autopilot-planner-queue-count">
          {state === "loading" ? "loading…" : `${workflows.length} active`}
        </span>
      </header>
      <div className="mt-3 grid min-h-0 flex-1 content-start gap-2 overflow-auto">
        {state === "error" && (
          <div className="rounded border border-amber-700/60 bg-amber-950/30 p-3 text-xs text-amber-100">
            Blocked: planner queue endpoint unreachable. {errorMsg ?? ""}
          </div>
        )}
        {state === "ready" && workflows.length === 0 && (
          <div className="rounded border border-border bg-bg/40 p-3 text-xs text-muted">
            No active workflows returned by the live workflows API.
          </div>
        )}
        {workflows.map((workflow) => (
          <article
            key={workflow.id}
            data-testid="autopilot-planner-queue-item"
            data-workflow-status={workflow.status}
            className="grid grid-cols-[1fr_auto] items-center gap-2 rounded border border-border bg-bg/40 px-3 py-2 text-sm"
          >
            <div className="min-w-0">
              <div className="truncate font-medium text-fg">{workflow.name}</div>
              <div className="truncate text-xs text-muted">
                stage {workflow.active_stage + 1}/{workflow.stages.length} · started{" "}
                {workflow.started_utc ? new Date(workflow.started_utc).toLocaleTimeString() : "—"}
              </div>
            </div>
            <span className={`rounded px-2 py-1 text-xs uppercase ${workflowTone(workflow.status)}`}>
              {workflow.status}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

function workflowTone(status: Workflow["status"]): string {
  if (status === "active") {
    return "bg-cyan-900/40 text-cyan-200";
  }
  if (status === "completed") {
    return "bg-green-900/40 text-green-200";
  }
  if (status === "failed") {
    return "bg-red-900/40 text-red-200";
  }
  return "bg-surface2 text-muted";
}
