/**
 * TaskMonitorDrawer — slide-out drawer pinned to the right edge.
 *
 * Lists active recovery runs (RC v2 read-only registry). Each row is
 * clickable; clicking expands the row to show the proof event timeline
 * (`history`, sorted by `ts_utc`). A "Clear completed" button is a UI-only
 * filter that hides terminal runs locally — it never mutates server state
 * (RC v2 is read-only on this endpoint by design, BLK-026).
 *
 * Polling is delegated to `useRecoveryRunsPoll` (5s default, abort-on-unmount,
 * exponential backoff on 5xx).
 */

import { ChevronDown, ChevronRight, RotateCw, X as CloseIcon } from "lucide-react";
import { useMemo, useState } from "react";
import {
  type RecoveryHistoryEntry,
  type RecoveryRun,
  type RecoveryRunState,
  type RecoveryRunsResponse,
} from "../../api/recoveryRuns";
import {
  useRecoveryRunsPoll,
  type UseRecoveryRunsPollOptions,
} from "./useRecoveryRunsPoll";

export interface TaskMonitorDrawerProps {
  open: boolean;
  onClose: () => void;
  /** Override for tests / Storybook. */
  pollOptions?: UseRecoveryRunsPollOptions;
  /** Inject pre-fetched data — bypasses the polling hook entirely. */
  staticData?: RecoveryRunsResponse;
}

const STATE_LABELS: Record<RecoveryRunState, string> = {
  created: "CREATED",
  proposing: "PROPOSING",
  reviewing: "REVIEWING",
  awaiting_human_confirm: "AWAITING CONFIRM",
  applying: "APPLYING",
  re_running_gate: "RE-RUNNING GATE",
  recovered: "RECOVERED",
  retry_failed: "RETRY FAILED",
  escalated: "ESCALATED",
  cancelled: "CANCELLED",
};

const STATE_TONES: Record<RecoveryRunState, "blue" | "amber" | "green" | "red" | "muted"> = {
  created: "blue",
  proposing: "blue",
  reviewing: "blue",
  awaiting_human_confirm: "amber",
  applying: "amber",
  re_running_gate: "amber",
  recovered: "green",
  retry_failed: "red",
  escalated: "red",
  cancelled: "muted",
};

const TERMINAL_STATES: ReadonlySet<RecoveryRunState> = new Set([
  "recovered",
  "retry_failed",
  "escalated",
  "cancelled",
]);

export function TaskMonitorDrawer({
  open,
  onClose,
  pollOptions,
  staticData,
}: TaskMonitorDrawerProps) {
  const poll = useRecoveryRunsPoll({ enabled: open && !staticData, ...(pollOptions ?? {}) });
  const data: RecoveryRunsResponse = staticData ?? poll.data;

  const [hideCompleted, setHideCompleted] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const visibleRuns = useMemo<RecoveryRun[]>(() => {
    const runs = data.runs ?? [];
    if (!hideCompleted) return runs;
    return runs.filter((run) => !TERMINAL_STATES.has(run.state));
  }, [data.runs, hideCompleted]);

  return (
    <aside
      data-testid="task-monitor-drawer"
      data-open={open ? "true" : "false"}
      role="complementary"
      aria-label="Task Monitor"
      className={[
        "fixed right-0 top-0 z-40 flex h-screen w-full max-w-[420px] transform flex-col border-l border-border bg-surface text-fg shadow-2xl transition-transform duration-200",
        open ? "translate-x-0" : "translate-x-full",
      ].join(" ")}
      aria-hidden={open ? "false" : "true"}
    >
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border bg-surface2 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-muted">Task Monitor</span>
          <span
            data-testid="task-monitor-count"
            className="rounded-full bg-accent-blue/15 px-2 py-0.5 text-[10px] font-semibold text-accent-blue"
          >
            {data.count}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={() => setHideCompleted((v) => !v)}
            aria-pressed={hideCompleted}
            data-testid="task-monitor-clear-completed"
            className={[
              "rounded-md px-2 py-1 text-xs font-semibold transition-colors",
              hideCompleted
                ? "bg-accent-blue/20 text-accent-blue"
                : "bg-surface text-muted hover:bg-surface hover:text-fg",
            ].join(" ")}
          >
            {hideCompleted ? "Show completed" : "Clear completed"}
          </button>
          {!staticData && (
            <button
              type="button"
              onClick={poll.refetch}
              aria-label="Refresh task monitor"
              className="rounded-md p-1 text-muted hover:bg-surface hover:text-fg"
              data-testid="task-monitor-refresh"
            >
              <RotateCw size={14} className={poll.loading ? "animate-spin" : ""} />
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close Task Monitor"
            className="rounded-md p-1 text-muted hover:bg-surface hover:text-fg"
          >
            <CloseIcon size={14} />
          </button>
        </div>
      </header>

      <PollDiagnostics
        loading={!staticData && poll.loading}
        error={!staticData ? poll.error : null}
        backoffStep={!staticData ? poll.backoffStep : 0}
      />

      <div className="min-h-0 flex-1 overflow-auto" data-testid="task-monitor-list">
        {visibleRuns.length === 0 ? (
          <EmptyRuns hideCompleted={hideCompleted} totalCount={data.count} />
        ) : (
          <ul className="divide-y divide-border">
            {visibleRuns.map((run) => (
              <RunRow
                key={run.attempt_id}
                run={run}
                expanded={expanded === run.attempt_id}
                onToggle={() =>
                  setExpanded((current) => (current === run.attempt_id ? null : run.attempt_id))
                }
              />
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

function PollDiagnostics({
  loading,
  error,
  backoffStep,
}: {
  loading: boolean;
  error: string | null;
  backoffStep: number;
}) {
  if (!loading && !error && backoffStep === 0) return null;
  return (
    <div
      data-testid="task-monitor-diagnostics"
      className="shrink-0 border-b border-border px-3 py-1.5 text-[11px] text-muted"
    >
      {loading && <span>Polling…</span>}
      {error && <span className="text-accent-red">Error: {error}</span>}
      {!error && backoffStep > 0 && (
        <span className="text-accent-amber">
          Backoff x{Math.pow(2, Math.min(backoffStep, 6))} (server unhealthy)
        </span>
      )}
    </div>
  );
}

function EmptyRuns({ hideCompleted, totalCount }: { hideCompleted: boolean; totalCount: number }) {
  let label = "No active recovery runs.";
  if (totalCount > 0 && hideCompleted) {
    label = `${totalCount} completed run${totalCount === 1 ? "" : "s"} hidden — toggle to view.`;
  }
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="text-center text-muted">
        <div className="text-xs uppercase tracking-wide">Task Monitor</div>
        <div className="mt-1 text-sm">{label}</div>
      </div>
    </div>
  );
}

function RunRow({
  run,
  expanded,
  onToggle,
}: {
  run: RecoveryRun;
  expanded: boolean;
  onToggle: () => void;
}) {
  const tone = STATE_TONES[run.state] ?? "muted";
  const Caret = expanded ? ChevronDown : ChevronRight;
  return (
    <li data-testid="task-monitor-row" data-attempt-id={run.attempt_id} data-state={run.state}>
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-start gap-2 px-3 py-2 text-left text-xs hover:bg-surface2"
        aria-expanded={expanded}
      >
        <span className="mt-0.5 shrink-0 text-muted">
          <Caret size={14} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-1.5">
            <StateBadge state={run.state} tone={tone} />
            <span className="truncate font-mono text-[11px] text-muted">
              {run.attempt_id.slice(0, 12)}
            </span>
          </span>
          <span className="mt-1 block truncate text-fg">
            {run.task_id || "(no task id)"}
          </span>
          <span className="mt-0.5 block truncate text-[11px] text-muted">
            {run.failure_class} · branch:{run.branch} · retries {run.retry_count}/
            {run.retry_budget_max}
          </span>
        </span>
      </button>
      {expanded && <RunTimeline run={run} />}
    </li>
  );
}

function RunTimeline({ run }: { run: RecoveryRun }) {
  const events = useMemo<RecoveryHistoryEntry[]>(() => {
    const list = run.history ?? [];
    return [...list].sort((a, b) => {
      const ta = Date.parse(a.ts_utc) || 0;
      const tb = Date.parse(b.ts_utc) || 0;
      return ta - tb;
    });
  }, [run.history]);

  return (
    <div
      className="border-t border-border bg-surface2 px-3 py-2 text-[11px]"
      data-testid="task-monitor-timeline"
      data-attempt-id={run.attempt_id}
    >
      {events.length === 0 ? (
        <div className="text-muted">No events recorded yet.</div>
      ) : (
        <ol className="space-y-1">
          {events.map((event, idx) => (
            <li key={`${event.ts_utc}-${idx}`} className="flex gap-2">
              <span className="shrink-0 font-mono text-muted">{shortTime(event.ts_utc)}</span>
              <span className="shrink-0 text-muted">{event.from} →</span>
              <span className="shrink-0 text-fg">{event.to}</span>
              <span className="truncate text-muted" title={event.note}>
                {event.note}
              </span>
            </li>
          ))}
        </ol>
      )}
      {run.terminal_status && (
        <div className="mt-2 border-t border-border pt-1.5 text-muted">
          Terminal: <span className="text-fg">{run.terminal_status}</span>
          {run.cancelled_reason && <span> · {run.cancelled_reason}</span>}
        </div>
      )}
    </div>
  );
}

function StateBadge({
  state,
  tone,
}: {
  state: RecoveryRunState;
  tone: "blue" | "amber" | "green" | "red" | "muted";
}) {
  const toneClass = {
    blue: "bg-accent-blue/15 text-accent-blue",
    amber: "bg-accent-amber/15 text-accent-amber",
    green: "bg-accent-green/15 text-accent-green",
    red: "bg-accent-red/15 text-accent-red",
    muted: "bg-surface text-muted",
  }[tone];
  return (
    <span
      data-testid="task-monitor-state-badge"
      data-state={state}
      className={[
        "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
        toneClass,
      ].join(" ")}
    >
      {STATE_LABELS[state] ?? state}
    </span>
  );
}

function shortTime(iso: string): string {
  const t = iso.split("T")[1];
  if (!t) return iso || "—";
  return t.slice(0, 8);
}
