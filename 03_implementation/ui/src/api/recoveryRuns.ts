/**
 * Recovery Runs API client.
 *
 * Thin wrapper around `GET /api/code-operator/recovery/runs` (RC v2 read-only
 * registry). Reuses the same multi-port base-URL strategy as `adapters.live.ts`
 * — 127.0.0.1:8765 first, then 8766/8767 fallbacks. The endpoint is read-only
 * by design (BLK-026): all mutations go through W6-2's RC v2 routes.
 *
 * State enum is sourced from `recovery_controller.RecoveryState`. The wire
 * values are stable; do not rename.
 */

type RecoveryImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
    VITE_API_BASE?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as RecoveryImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;

/**
 * Same fallback set as the rest of the live adapters — fixes flaky local dev
 * where the bridge sometimes ends up on 8766/8767 if 8765 is taken.
 */
export const RECOVERY_API_BASE_URLS: readonly string[] = Array.from(
  new Set([
    (import.meta as RecoveryImportMeta).env.VITE_API_BASE ?? `http://127.0.0.1:${LIVE_BRIDGE_PORT}`,
    `http://127.0.0.1:${LIVE_BRIDGE_PORT}`,
    `http://127.0.0.1:${DEFAULT_BRIDGE_PORT}`,
    "http://127.0.0.1:8766",
    "http://127.0.0.1:8767",
  ]),
);

/** Union of state strings emitted by `recovery_controller.RecoveryState`. */
export type RecoveryRunState =
  | "created"
  | "proposing"
  | "reviewing"
  | "awaiting_human_confirm"
  | "applying"
  | "re_running_gate"
  | "recovered"
  | "retry_failed"
  | "escalated"
  | "cancelled";

/** RC v1 outcome statuses surfaced as terminal_status. */
export type RecoveryTerminalStatus =
  | "recovered"
  | "retry_failed"
  | "escalated"
  | "cancelled"
  | null;

/** Decision branch a fresh run took from the failure-class table. */
export type RecoveryRunBranch =
  | "propose_review_apply_rerun"
  | "propose_with_reduced_context"
  | "refresh_context_then_retry_step"
  | "rollback_then_retry"
  | "refresh_context_retry_once"
  | "propose_review_apply_rerun_visual"
  | "escalate_immediately";

/** History entry as emitted by `_transition` in recovery_controller. */
export interface RecoveryHistoryEntry {
  ts_utc: string;
  from: string;
  to: string;
  note: string;
}

/**
 * Public payload from `RecoveryRun.to_state_payload`. Keep field names
 * verbatim — they are stable wire shapes, mirrored in pytest fixtures.
 */
export interface RecoveryRun {
  attempt_id: string;
  task_id: string;
  state: RecoveryRunState;
  branch: RecoveryRunBranch;
  failure_class: string;
  failed_step_type: string;
  failure_fingerprint: string;
  retry_count: number;
  retry_budget_max: number;
  actor: string;
  confirm: boolean;
  started_utc: string;
  last_event_utc: string;
  last_event_summary: string;
  proposal_id: string | null;
  review_evidence_id: string | null;
  apply_evidence_id: string | null;
  retry_gate_id: string | null;
  terminal_status: RecoveryTerminalStatus;
  cancelled_reason: string | null;
  is_terminal: boolean;
  is_cancellable: boolean;
  // Commit 2 enrichment fields — present from RC v2.
  locked_files?: string[];
  pre_snapshot_ids?: string[];
  freeze_event_utc?: string;
  // Optional commit-3+ fields.
  next_action?: string;
  history?: RecoveryHistoryEntry[];
}

/** Payload shape for `GET /api/code-operator/recovery/runs`. */
export interface RecoveryRunsResponse {
  count: number;
  by_state: Partial<Record<RecoveryRunState, number>>;
  runs: RecoveryRun[];
  task_id_filter: string | null;
}

const EMPTY_RESPONSE: RecoveryRunsResponse = {
  count: 0,
  by_state: {},
  runs: [],
  task_id_filter: null,
};

export interface FetchRecoveryRunsOptions {
  taskId?: string;
  signal?: AbortSignal;
  /** Override base URL list — exposed for tests. */
  baseUrls?: readonly string[];
  /** Override the global fetch — exposed for tests. */
  fetcher?: typeof fetch;
}

export class RecoveryRunsFetchError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "RecoveryRunsFetchError";
    this.status = status;
  }
}

/**
 * Fetch active recovery runs. Mirrors the multi-port retry strategy used by
 * `adapters.live.ts::fetchApiResponse`: only 5xx and 404/405/502/503 retry.
 *
 * On total failure, throws `RecoveryRunsFetchError` so the polling hook can
 * apply exponential backoff. On AbortError, the abort propagates.
 */
export async function fetchRecoveryRuns(
  opts: FetchRecoveryRunsOptions = {},
): Promise<RecoveryRunsResponse> {
  const baseUrls = opts.baseUrls ?? RECOVERY_API_BASE_URLS;
  const fetcher = opts.fetcher ?? fetch;
  const path = opts.taskId
    ? `/api/code-operator/recovery/runs?task_id=${encodeURIComponent(opts.taskId)}`
    : "/api/code-operator/recovery/runs";

  let lastStatus = 0;
  let lastBody = "";
  for (const baseUrl of baseUrls) {
    let response: Response;
    try {
      response = await fetcher(`${baseUrl}${path}`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal: opts.signal,
      });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        throw err;
      }
      // Network error — try next base URL.
      lastStatus = 0;
      lastBody = err instanceof Error ? err.message : String(err);
      continue;
    }
    if (response.ok) {
      const payload = (await response.json()) as unknown;
      return normalizeRunsResponse(payload);
    }
    if (!isRetryable(response)) {
      throw new RecoveryRunsFetchError(response.status, await safeBody(response));
    }
    lastStatus = response.status;
    lastBody = await safeBody(response);
  }
  if (lastStatus === 0) {
    // All base URLs failed at the network layer — surface an empty response so
    // the UI keeps rendering. The polling hook will apply backoff.
    throw new RecoveryRunsFetchError(0, lastBody || "all recovery API base URLs failed");
  }
  throw new RecoveryRunsFetchError(lastStatus, lastBody);
}

export function emptyRunsResponse(): RecoveryRunsResponse {
  return { ...EMPTY_RESPONSE, by_state: {}, runs: [] };
}

function isRetryable(response: Response): boolean {
  return (
    response.status === 404 ||
    response.status === 405 ||
    response.status === 502 ||
    response.status === 503 ||
    response.status >= 500
  );
}

async function safeBody(response: Response): Promise<string> {
  try {
    const text = await response.text();
    return text.length > 400 ? `${text.slice(0, 400)}…` : text;
  } catch {
    return "";
  }
}

function normalizeRunsResponse(payload: unknown): RecoveryRunsResponse {
  if (!isRecord(payload)) {
    return emptyRunsResponse();
  }
  const runs = Array.isArray(payload.runs)
    ? payload.runs.filter(isRecord).map(normalizeRun)
    : [];
  const byState = isRecord(payload.by_state)
    ? Object.fromEntries(
        Object.entries(payload.by_state).filter(([, v]) => typeof v === "number"),
      )
    : {};
  return {
    count: typeof payload.count === "number" ? payload.count : runs.length,
    by_state: byState as Partial<Record<RecoveryRunState, number>>,
    runs,
    task_id_filter:
      typeof payload.task_id_filter === "string" ? payload.task_id_filter : null,
  };
}

function normalizeRun(record: Record<string, unknown>): RecoveryRun {
  return {
    attempt_id: stringField(record.attempt_id),
    task_id: stringField(record.task_id),
    state: (stringField(record.state) || "created") as RecoveryRunState,
    branch: (stringField(record.branch) || "escalate_immediately") as RecoveryRunBranch,
    failure_class: stringField(record.failure_class),
    failed_step_type: stringField(record.failed_step_type),
    failure_fingerprint: stringField(record.failure_fingerprint),
    retry_count: numberField(record.retry_count),
    retry_budget_max: numberField(record.retry_budget_max),
    actor: stringField(record.actor) || "user",
    confirm: Boolean(record.confirm),
    started_utc: stringField(record.started_utc),
    last_event_utc: stringField(record.last_event_utc),
    last_event_summary: stringField(record.last_event_summary),
    proposal_id: nullableStringField(record.proposal_id),
    review_evidence_id: nullableStringField(record.review_evidence_id),
    apply_evidence_id: nullableStringField(record.apply_evidence_id),
    retry_gate_id: nullableStringField(record.retry_gate_id),
    terminal_status: (nullableStringField(record.terminal_status) ??
      null) as RecoveryTerminalStatus,
    cancelled_reason: nullableStringField(record.cancelled_reason),
    is_terminal: Boolean(record.is_terminal),
    is_cancellable: Boolean(record.is_cancellable),
    locked_files: Array.isArray(record.locked_files)
      ? record.locked_files.filter((v): v is string => typeof v === "string")
      : undefined,
    pre_snapshot_ids: Array.isArray(record.pre_snapshot_ids)
      ? record.pre_snapshot_ids.filter((v): v is string => typeof v === "string")
      : undefined,
    freeze_event_utc: stringField(record.freeze_event_utc) || undefined,
    next_action: stringField(record.next_action) || undefined,
    history: Array.isArray(record.history)
      ? record.history
          .filter(isRecord)
          .map((entry) => ({
            ts_utc: stringField(entry.ts_utc),
            from: stringField(entry.from),
            to: stringField(entry.to),
            note: stringField(entry.note),
          }))
      : undefined,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringField(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function nullableStringField(value: unknown): string | null {
  if (typeof value === "string") return value;
  return null;
}

function numberField(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}
