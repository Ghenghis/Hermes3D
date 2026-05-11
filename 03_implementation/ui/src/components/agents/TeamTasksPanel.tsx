/**
 * W18-A21 (2026-05-11): Team Tasks panel for the #agents tab.
 *
 * Renders recent MiniMax-builders / DeepSeek-reviewers code-operator runs
 * by reading the read-only ``/api/code-operator/teams/team-tasks`` and
 * ``/api/code-operator/teams/provider-smoke-history`` endpoints. The
 * previous #agents tab surfaced only the readiness contract and the
 * smoke results — operators could not see that real team tasks had run.
 *
 * Auto-refresh cadence: 10 s. The panel never writes; it only displays
 * proof_events rows + the local provider-smoke-status.json summary.
 */
import { useEffect, useState } from "react";
import { Panel } from "../layout/Panel";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;
const TEAM_TASKS_URL = `${LIVE_BASE_URL}/api/code-operator/teams/team-tasks?limit=15`;
const PROVIDER_SMOKE_HISTORY_URL = `${LIVE_BASE_URL}/api/code-operator/teams/provider-smoke-history?limit=10`;
const REFRESH_INTERVAL_MS = 10_000;

export type TeamTaskItem = {
  id: string;
  event_type: string;
  run_type: string;
  team_id: string;
  provider_id: string;
  task_id: string;
  run_id: string;
  files: string[];
  response_sha256: string | null;
  prompt_sha256: string | null;
  ts_utc: string;
  source_agent: string;
};

export type ProviderSmokeHistoryItem = {
  provider_id: string;
  status: string;
  accepted: boolean;
  ts_utc: string;
  evidence_id: string | null;
  content_sha256: string | null;
  base_url_label: string | null;
  model: string | null;
  blocked_reasons: string[];
};

type PanelState = {
  loading: boolean;
  error: string | null;
  tasks: TeamTaskItem[];
  smokes: ProviderSmokeHistoryItem[];
  lastFetched: string | null;
};

const INITIAL_STATE: PanelState = {
  loading: true,
  error: null,
  tasks: [],
  smokes: [],
  lastFetched: null,
};

function smokeTone(status: string, accepted: boolean): StatusTone {
  const value = (status || "").toLowerCase();
  if (accepted && value === "ready") return "green";
  if (value === "missing_config") return "muted";
  if (value === "blocked" || value === "auth_failed" || value === "smoke_failed") return "red";
  if (value === "stale_smoke") return "amber";
  return "muted";
}

function runTypeTone(runType: string): StatusTone {
  const value = (runType || "").toLowerCase();
  if (value === "coding_plan") return "cyan";
  if (value === "code_review") return "amber";
  return "muted";
}

function shortHash(value: string | null | undefined): string {
  if (!value) return "—";
  return value.slice(0, 10) + (value.length > 10 ? "…" : "");
}

function shortTimestamp(value: string): string {
  if (!value) return "—";
  // Accept ISO 8601 or SQL datetime — keep up to seconds.
  return value.replace("T", " ").slice(0, 19);
}

export function TeamTasksPanel() {
  const [state, setState] = useState<PanelState>(INITIAL_STATE);

  useEffect(() => {
    let cancelled = false;

    const fetchOnce = async () => {
      try {
        const [tasksResponse, smokeResponse] = await Promise.all([
          fetch(TEAM_TASKS_URL, { cache: "no-store", headers: { Accept: "application/json" } }),
          fetch(PROVIDER_SMOKE_HISTORY_URL, { cache: "no-store", headers: { Accept: "application/json" } }),
        ]);
        if (!tasksResponse.ok) {
          throw new Error(`team-tasks HTTP ${tasksResponse.status}`);
        }
        if (!smokeResponse.ok) {
          throw new Error(`provider-smoke-history HTTP ${smokeResponse.status}`);
        }
        const tasksBody: { items?: TeamTaskItem[] } = await tasksResponse.json();
        const smokeBody: { items?: ProviderSmokeHistoryItem[] } = await smokeResponse.json();
        if (cancelled) return;
        setState({
          loading: false,
          error: null,
          tasks: Array.isArray(tasksBody.items) ? tasksBody.items : [],
          smokes: Array.isArray(smokeBody.items) ? smokeBody.items : [],
          lastFetched: new Date().toISOString(),
        });
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "fetch failed";
        setState((previous) => ({
          ...previous,
          loading: false,
          error: `Team-tasks unavailable: ${message}`,
        }));
      }
    };

    void fetchOnce();
    const interval = window.setInterval(() => {
      void fetchOnce();
    }, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const statusLabel = state.error
    ? "backend unreachable"
    : state.loading
      ? "loading…"
      : `${state.tasks.length} task${state.tasks.length === 1 ? "" : "s"}`;
  const statusTone: StatusTone = state.error
    ? "red"
    : state.tasks.length > 0
      ? "green"
      : "muted";

  return (
    <Panel
      id="agents.team-tasks"
      title="HERMES AGENT TEAM TASKS"
      dense
      status={{ tone: statusTone, label: statusLabel }}
      className="min-h-[260px]"
    >
      <div className="grid gap-2 text-xs" data-testid="agents-team-tasks-root">
        <div className="rounded border border-border bg-bg/40 p-2" data-testid="agents-team-tasks-smoke-history">
          <div className="text-[10px] uppercase text-muted">Live provider smoke history (code_provider_smoke)</div>
          {state.smokes.length === 0 ? (
            <div className="mt-1 text-muted" data-testid="agents-team-tasks-smoke-empty">
              {state.loading
                ? "Loading provider smoke history…"
                : "No provider smokes recorded. Run /api/code-operator/providers/smoke to register one."}
            </div>
          ) : (
            <ul className="mt-1 grid gap-1">
              {state.smokes.map((smoke) => (
                <li
                  key={`${smoke.provider_id}-${smoke.ts_utc}`}
                  className="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded border border-border/70 bg-surface1/50 px-2 py-1"
                  data-testid={`agents-team-tasks-smoke-${smoke.provider_id}`}
                >
                  <span className="font-semibold uppercase text-fg">{smoke.provider_id}</span>
                  <span className="min-w-0 truncate font-mono text-[10px] text-muted">
                    {smoke.model ?? "model unset"} · {smoke.base_url_label ?? "base unset"} · ev {shortHash(smoke.evidence_id)}
                  </span>
                  <StatusBadge tone={smokeTone(smoke.status, smoke.accepted)} label={smoke.status || "unknown"} />
                  {smoke.blocked_reasons.length > 0 && (
                    <div className="col-span-3 text-[10px] text-muted">{smoke.blocked_reasons[0]}</div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded border border-border bg-bg/40 p-2" data-testid="agents-team-tasks-runs">
          <div className="flex items-center justify-between">
            <div className="text-[10px] uppercase text-muted">Recent team-task runs (code_provider.coding_plan / code_review)</div>
            <div className="text-[10px] text-muted" data-testid="agents-team-tasks-last-fetched">
              {state.lastFetched ? `refreshed ${shortTimestamp(state.lastFetched)}` : ""}
            </div>
          </div>
          {state.error && (
            <div className="mt-1 text-accent-red" data-testid="agents-team-tasks-error">{state.error}</div>
          )}
          {!state.error && state.tasks.length === 0 ? (
            <div className="mt-1 text-muted" data-testid="agents-team-tasks-empty">
              {state.loading
                ? "Loading team tasks…"
                : "No team-task runs recorded yet. Invoke /api/code-operator/teams/run-coding-pass to register the first one."}
            </div>
          ) : (
            <ul className="mt-1 grid gap-1 max-h-[260px] overflow-auto">
              {state.tasks.map((task) => (
                <li
                  key={task.id}
                  className="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded border border-border/70 bg-surface1/50 px-2 py-1"
                  data-testid={`agents-team-tasks-run-${task.id}`}
                >
                  <span className="font-semibold uppercase text-fg">{task.provider_id || "?"}</span>
                  <span className="min-w-0 truncate font-mono text-[10px] text-muted">
                    {task.team_id || "?"} · {task.task_id || "task-id?"} · resp {shortHash(task.response_sha256)} · files {task.files.length}
                  </span>
                  <StatusBadge tone={runTypeTone(task.run_type)} label={task.run_type || task.event_type} />
                  <div className="col-span-3 grid grid-cols-2 gap-x-2 gap-y-0 text-[10px] text-muted">
                    <span>{shortTimestamp(task.ts_utc)}</span>
                    <span className="truncate text-right">{task.source_agent}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Panel>
  );
}
