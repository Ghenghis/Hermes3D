/**
 * W18-A25 — #agents tab "Active Tasks" panel.
 *
 * Operator verified that prior to this PR the #agents tab read
 * "0 active · 0 tasks · 0/8 roster" because the backend had no
 * /api/agents/tasks endpoint surfacing the team-task work the
 * MiniMax/DeepSeek providers had done. This panel:
 *
 *   - Mounts above the AGENT CODE WORKBENCH inside the
 *     AgentsTabActiveTasksWrapper so we avoid editing the
 *     w18-a21-locked Agents.tsx.
 *   - Fetches GET /api/agents/tasks on mount and every 10s.
 *   - Honestly renders "No recent code-team tasks" when the env
 *     legitimately has none — no faked rows, no "Coming soon".
 *   - Surfaces provider_id (`minimax` / `deepseek`) per row and
 *     a "provider smoke latest" header so the GUI exposes the
 *     live providers' last verification.
 *
 * No printer-control endpoints touched. No mocks. No secrets.
 */
import { useEffect, useMemo, useState } from "react";
import { Panel } from "../layout/Panel";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";
import { adapters } from "../../api/adapters";
import type {
  AgentTaskEntry,
  AgentTasksFeed,
  AgentTasksProviderSmokeLatest,
} from "../../types/agent-actions";

const REFRESH_INTERVAL_MS = 10_000;
const DEFAULT_LIMIT = 50;

type LoadState = "loading" | "ready" | "unavailable";

function statusTone(status: string): StatusTone {
  const normalized = status.toLowerCase();
  if (
    normalized === "completed" ||
    normalized === "ready" ||
    normalized === "passed" ||
    normalized === "smoke_passed" ||
    normalized === "assigned"
  ) {
    return "green";
  }
  if (
    normalized === "claimed" ||
    normalized === "coding_plan_recorded" ||
    normalized === "review_recorded" ||
    normalized === "in_progress"
  ) {
    return "cyan";
  }
  if (normalized === "blocked" || normalized === "failed") {
    return "amber";
  }
  if (normalized === "error" || normalized === "rejected") {
    return "red";
  }
  return "muted";
}

function formatTimestamp(iso: string): string {
  if (!iso) {
    return "—";
  }
  // SQLite stores "YYYY-MM-DD HH:MM:SS" with a space; treat as UTC.
  const normalized = iso.includes("T") ? iso : iso.replace(" ", "T") + "Z";
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toISOString().replace("T", " ").slice(0, 19) + "Z";
}

function relativeAge(iso: string): string {
  if (!iso) {
    return "";
  }
  const normalized = iso.includes("T") ? iso : iso.replace(" ", "T") + "Z";
  const parsed = new Date(normalized).getTime();
  if (Number.isNaN(parsed)) {
    return "";
  }
  const deltaMs = Date.now() - parsed;
  if (deltaMs < 0) {
    return "just now";
  }
  const seconds = Math.floor(deltaMs / 1000);
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function ActiveTasksPanel() {
  const [feed, setFeed] = useState<AgentTasksFeed | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    async function pull() {
      try {
        const next = await adapters.getAgentTasks(DEFAULT_LIMIT);
        if (cancelled) {
          return;
        }
        setFeed(next);
        setLoadState(next.schema_version === "agent-tasks-unavailable" ? "unavailable" : "ready");
        setError(next.schema_version === "agent-tasks-unavailable"
          ? "Hermes Agent tasks API did not respond — showing no rows."
          : null);
      } catch (caught) {
        if (cancelled) {
          return;
        }
        setLoadState("unavailable");
        setError(caught instanceof Error ? caught.message : "agents tasks backend unreachable");
      }
    }

    void pull();
    timer = setInterval(() => {
      void pull();
    }, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (timer) {
        clearInterval(timer);
      }
    };
  }, []);

  const tasks = feed?.tasks ?? [];
  const providerSmokes = feed?.provider_smoke_latest ?? [];
  const activeCount = feed?.active_count ?? 0;
  const totalCount = feed?.total_count ?? tasks.length;

  const panelTone = useMemo<StatusTone>(() => {
    if (loadState === "loading") {
      return "muted";
    }
    if (loadState === "unavailable") {
      return "amber";
    }
    if (activeCount > 0) {
      return "cyan";
    }
    if (totalCount > 0) {
      return "green";
    }
    return "muted";
  }, [loadState, activeCount, totalCount]);

  const statusLabel = loadState === "loading"
    ? "loading"
    : loadState === "unavailable"
      ? "unavailable"
      : `${activeCount} active · ${totalCount} recent`;

  return (
    <Panel
      id="agents.active-tasks"
      title="ACTIVE TASKS"
      dense
      status={{ tone: panelTone, label: statusLabel }}
      className="min-h-[200px]"
    >
      <div className="grid gap-2 text-xs" data-testid="agents-active-tasks-panel">
        <ProviderSmokeStrip smokes={providerSmokes} />
        <TaskList
          tasks={tasks}
          loadState={loadState}
          error={error}
        />
      </div>
    </Panel>
  );
}

function ProviderSmokeStrip({ smokes }: { smokes: AgentTasksProviderSmokeLatest[] }) {
  if (!smokes.length) {
    return null;
  }
  return (
    <div
      className="flex flex-wrap gap-2 rounded border border-border bg-bg/40 p-1.5"
      data-testid="agents-active-tasks-smokes"
    >
      <span className="text-[10px] uppercase text-muted">Provider smokes</span>
      {smokes.map((smoke) => (
        <span
          key={`${smoke.provider_id}-${smoke.evidence_id}`}
          className="flex items-center gap-1 rounded border border-border/70 bg-surface1/60 px-1.5 py-0.5 text-[10px]"
          data-provider-id={smoke.provider_id}
          data-testid={`agents-active-tasks-smoke-${smoke.provider_id}`}
        >
          <span className="font-semibold uppercase text-fg">{smoke.provider_id}</span>
          <StatusBadge tone={statusTone(smoke.status)} label={smoke.status} />
          <span className="text-muted">{relativeAge(smoke.created_utc)}</span>
        </span>
      ))}
    </div>
  );
}

function TaskList({
  tasks,
  loadState,
  error,
}: {
  tasks: AgentTaskEntry[];
  loadState: LoadState;
  error: string | null;
}) {
  if (loadState === "loading") {
    return (
      <div className="rounded border border-border bg-surface2/40 px-2 py-3 text-center text-muted" data-testid="agents-active-tasks-loading">
        Loading recent Hermes Agent code-team tasks…
      </div>
    );
  }
  if (loadState === "unavailable") {
    return (
      <div className="rounded border border-accent-amber/50 bg-accent-amber/10 px-2 py-3 text-accent-amber" data-testid="agents-active-tasks-unavailable">
        Active Tasks API unavailable. {error ?? "The /api/agents/tasks endpoint returned no payload."}
      </div>
    );
  }
  if (!tasks.length) {
    return (
      <div className="rounded border border-border bg-surface2/40 px-2 py-3 text-center text-muted" data-testid="agents-active-tasks-empty">
        No recent Hermes Agent code-team tasks in the last 7 days. Run a provider smoke or assign a team task to see live rows.
      </div>
    );
  }
  return (
    <ul className="flex flex-col gap-1" data-testid="agents-active-tasks-list">
      {tasks.map((task) => (
        <li
          key={task.evidence_id || `${task.action_id}-${task.created_utc}`}
          className="grid grid-cols-[1fr_auto] items-start gap-2 rounded border border-border bg-surface2/40 px-2 py-1.5"
          data-testid="agents-active-tasks-row"
          data-task-kind={task.kind}
          data-task-action-id={task.action_id}
          data-task-provider-id={task.provider_id ?? ""}
          data-task-team-id={task.team_id ?? ""}
        >
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="truncate font-semibold text-fg">{task.title}</span>
              <StatusBadge tone={statusTone(task.status)} label={task.status} />
            </div>
            <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-muted">
              <span>kind <span className="font-mono text-fg">{task.kind}</span></span>
              {task.provider_id ? (
                <span data-testid="agents-active-tasks-row-provider">
                  provider <span className="font-mono text-fg">{task.provider_id}</span>
                </span>
              ) : null}
              {task.team_id ? (
                <span>team <span className="font-mono text-fg">{task.team_id}</span></span>
              ) : null}
              {task.task_id ? (
                <span>task <span className="font-mono text-fg">{task.task_id}</span></span>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-muted">
              <span className="font-mono">{task.action_id}</span>
              <span className="font-mono">{task.evidence_id || "no-evidence"}</span>
            </div>
          </div>
          <div className="text-right text-[10px] text-muted">
            <div>{relativeAge(task.created_utc)}</div>
            <div className="font-mono">{formatTimestamp(task.created_utc)}</div>
          </div>
        </li>
      ))}
    </ul>
  );
}
