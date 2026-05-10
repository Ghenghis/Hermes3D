/**
 * Hermes3D-OS typed API client (W6-5 GUI-to-backend wiring layer).
 *
 * Domains:
 *   - agentsClient    -> /api/agents/update/* (Hermes Agent self-update)
 *   - openCodeClient  -> /api/code-operator/cli-runners/* (runner_id="opencode")
 *   - openHandsClient -> /api/code-operator/cli-runners/* (runner_id="openhands")
 *   - providersClient -> /api/code-operator/providers/* + /api/providers/health
 *   - mcpClient       -> /api/code-operator/mcp-locks/*
 *   - appsClient      -> /api/source-os/modules (60-app registry, ships from W6-8)
 *   - recoveryClient  -> /api/code-operator/recovery/*
 *
 * Conventions:
 *   - All fetchers return either typed payloads or throw `Error` with a
 *     redacted message. Polling endpoints use `safe*` variants that swallow
 *     errors and return `null` so banners don't crash on transient outages.
 *   - URLs come from `VITE_HERMES3D_BRIDGE_PORT`; we never hardcode port 8765
 *     into the call site itself, only in the env-fallback chain.
 *   - Auth is opt-in: if `getBearerToken()` returns a value, it's added as
 *     `Authorization: Bearer <token>`. Tokens are NEVER logged anywhere in
 *     this module — error messages route through `redactSensitive()`.
 *   - This file intentionally has zero React imports. Hooks live in
 *     `../hooks/*` and consume these functions.
 */

type HermesImportMeta = ImportMeta & {
  env?: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
    VITE_HERMES3D_BEARER_TOKEN?: string;
  };
};

// `import.meta.env` is a Vite-injected object; it's `undefined` under the
// Node test runner (`node --test`). Read defensively so the module can be
// imported in both contexts.
const viteEnv = (import.meta as HermesImportMeta).env ?? {};
const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  viteEnv.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;

export const API_BASE_URLS: readonly string[] = Array.from(
  new Set([
    `http://127.0.0.1:${LIVE_BRIDGE_PORT}`,
    `http://127.0.0.1:${DEFAULT_BRIDGE_PORT}`,
    "http://127.0.0.1:8766",
    "http://127.0.0.1:8767",
  ]),
);

/** Bearer token lookup. The default reader checks the build-time env var; a
 * runtime replacement (e.g. wired to a Zustand store after sign-in) can
 * override it via `setBearerTokenProvider`.
 */
let bearerTokenProvider: () => string | null = () => {
  const fromEnv = viteEnv.VITE_HERMES3D_BEARER_TOKEN;
  return typeof fromEnv === "string" && fromEnv.length > 0 ? fromEnv : null;
};

export function setBearerTokenProvider(provider: () => string | null): void {
  bearerTokenProvider = provider;
}

function authHeaders(): Record<string, string> {
  const token = bearerTokenProvider();
  if (!token) return {};
  // Length check only — never include the token in a log/error message.
  return { Authorization: `Bearer ${token}` };
}

/**
 * Redact patterns that may slip into HTTP error messages from upstream
 * payloads (e.g. a backend that echoes a query string with `token=...`).
 * Mirrors `hermes3d.gateways.redaction.redact_text` shape so client-side and
 * server-side render the same `***` marker.
 *
 * Patterns covered:
 *   1. `Bearer <token>` (RFC 6750)
 *   2. `?token=...` / `&access_token=...` (query strings)
 *   3. `token=...` / `api_key=...` (free-form, after whitespace or `:` etc.)
 *   4. `*_KEY=...` (shell-style env markers)
 */
const SECRET_RE =
  /(bearer\s+)[A-Za-z0-9._~+/=-]+|([?&](?:token|key|api_key|access_token)=)[^&\s]+|((?:^|[\s:;,])(?:token|key|api_key|access_token)=)[^\s,;]+|([A-Za-z0-9_]*KEY=)[^\s]+/gi;

export function redactSensitive(text: string): string {
  return text.replace(SECRET_RE, (
    _match,
    p1: string | undefined,
    p2: string | undefined,
    p3: string | undefined,
    p4: string | undefined,
  ) => {
    if (p1) return `${p1}***`;
    if (p2) return `${p2}***`;
    if (p3) return `${p3}***`;
    if (p4) return `${p4}***`;
    return "***";
  });
}

export interface FetchOptions {
  signal?: AbortSignal;
}

async function fetchApiResponse(
  path: string,
  init: RequestInit,
): Promise<Response> {
  let lastError: unknown = null;
  let lastResponse: Response | null = null;
  for (const baseUrl of API_BASE_URLS) {
    try {
      const response = await fetch(`${baseUrl}${path}`, init);
      if (response.ok || !isRetryableApiMiss(response)) {
        return response;
      }
      lastResponse = response;
    } catch (error) {
      lastError = error;
    }
  }
  if (lastResponse) return lastResponse;
  throw new Error(
    redactSensitive(
      lastError instanceof Error ? lastError.message : "all API base URLs failed",
    ),
  );
}

function isRetryableApiMiss(response: Response): boolean {
  return (
    response.status === 404 ||
    response.status === 405 ||
    response.status === 502 ||
    response.status === 503
  );
}

export async function getJson<T>(path: string, opts?: FetchOptions): Promise<T> {
  const response = await fetchApiResponse(path, {
    method: "GET",
    headers: { Accept: "application/json", ...authHeaders() },
    cache: "no-store",
    signal: opts?.signal,
  });
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    throw new Error(
      redactSensitive(httpFailureReason(payload, response, path)),
    );
  }
  return payload as T;
}

/** Polling-friendly variant: never throws, returns null on any failure. */
export async function safeGetJson<T>(
  path: string,
  opts?: FetchOptions,
): Promise<T | null> {
  try {
    return await getJson<T>(path, opts);
  } catch {
    return null;
  }
}

export async function postJson<T>(
  path: string,
  body: unknown,
  opts?: FetchOptions,
): Promise<T> {
  const response = await fetchApiResponse(path, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify(body),
    cache: "no-store",
    signal: opts?.signal,
  });
  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    throw new Error(
      redactSensitive(httpFailureReason(payload, response, path)),
    );
  }
  return payload as T;
}

function httpFailureReason(
  value: unknown,
  response: Response,
  label: string,
): string {
  if (value && typeof value === "object" && "detail" in (value as Record<string, unknown>)) {
    const detail = (value as Record<string, unknown>).detail;
    if (typeof detail === "string" && detail.length > 0) {
      return `${label} failed (${response.status}): ${detail}`;
    }
  }
  return `${label} failed with HTTP ${response.status}`;
}

/* ------------------------------------------------------------------ */
/* Typed payload contracts                                            */
/* ------------------------------------------------------------------ */

export interface HermesAgentUpdateStatus {
  available?: boolean;
  repo_url: string;
  checkout_path: string;
  repo_ready: boolean;
  current: {
    repo_ready?: boolean;
    commit?: string;
    exact_tag?: string | null;
    nearest_tag?: string | null;
    branch?: string;
    dirty?: boolean;
    dirty_entries?: string[];
    reason?: string;
  };
  latest_release: {
    tag?: string | null;
    name?: string | null;
    published_at?: string | null;
    html_url?: string | null;
    source?: string;
  };
  outdated: boolean;
  outdated_by: number;
  pending_tags: string[];
  backup_available: boolean;
  latest_backup: HermesAgentBackup | null;
  strategy: string;
  rollback: string;
  reason?: string;
}

export interface HermesAgentBackup {
  backup_id: string;
  created_at: string;
  note: string;
  checkout_path: string;
  bundle_path: string;
  dirty_zip_path: string | null;
  tag: string | null;
  commit: string;
  dirty: boolean;
  dirty_entries: string[];
}

export interface HermesAgentUpdateResult {
  available?: boolean;
  status: string;
  updated?: boolean;
  backup?: HermesAgentBackup | null;
  steps?: Array<{ tag: string; ok: boolean; checks: Array<{ name: string; status: string; output?: string }> }>;
  current?: HermesAgentUpdateStatus["current"];
  latest_release?: HermesAgentUpdateStatus["latest_release"];
  remaining_tags?: string[];
  reason?: string;
}

export interface CliRunnerReadiness {
  opencode_detected?: boolean;
  opencode_version?: string | null;
  openhands_detected?: boolean;
  openhands_image?: string | null;
  ready?: boolean;
  reason?: string;
  [key: string]: unknown;
}

export interface CliRunnerPreflightResult {
  available?: boolean;
  runner_id: string;
  exit_code: number;
  elapsed_ms: number;
  stdout?: string;
  stderr_sha256?: string | null;
  ready?: boolean;
  reason?: string;
}

export interface CliRunnerBoundedTaskResult {
  available?: boolean;
  runner_id: string;
  task_id: string;
  exit_code: number;
  elapsed_ms: number;
  stdout?: string;
  stderr_sha256?: string | null;
  status: string;
  reason?: string;
}

export interface ProviderTeamReadiness {
  teams: Array<{ id: string; ready: boolean; reason?: string; [k: string]: unknown }>;
  ready?: boolean;
  reason?: string;
}

export interface ProviderSmokeResult {
  available?: boolean;
  provider_id: string;
  status: string;
  ready: boolean;
  reason?: string;
}

export interface ProviderHealthEntry {
  id: string;
  name: string;
  status: string;
  reason?: string;
  [k: string]: unknown;
}

export interface McpLockState {
  ok?: boolean;
  workspace_root?: string;
  count?: number;
  locks: Array<{
    lock_id: string;
    file: string;
    owner: string;
    role?: string;
    task_id?: string | null;
    reason?: string;
    expires_utc?: string;
    is_stale?: boolean;
  }>;
}

export interface McpReadiness {
  ready: boolean;
  reason?: string;
  server_url?: string;
  [k: string]: unknown;
}

export interface RecoveryRunsResponse {
  runs: Array<{
    attempt_id?: string;
    task_id: string;
    state?: string;
    branch?: string | null;
    locked_files?: string[];
    pre_snapshot_ids?: string[];
    freeze_event_utc?: string | null;
    next_action?: string | null;
    [k: string]: unknown;
  }>;
}

export interface RecoveryStateResponse {
  attempts: Array<{
    attempt_id: string;
    task_id: string;
    status: string;
    failed_step?: string;
    failure_class?: string;
    [k: string]: unknown;
  }>;
}

export interface AppEntry {
  id: string;
  name: string;
  status?: string;
  category?: string;
  [k: string]: unknown;
}

/* ------------------------------------------------------------------ */
/* Domain clients                                                     */
/* ------------------------------------------------------------------ */

export const agentsClient = {
  /** GET /api/agents/update/status — Hermes Agent version info. */
  getUpdateStatus(opts?: FetchOptions) {
    return safeGetJson<HermesAgentUpdateStatus>("/api/agents/update/status", opts);
  },
  /** POST /api/agents/update/backup — make a pre-update bundle. */
  backup(note?: string, opts?: FetchOptions) {
    return postJson<HermesAgentBackup>(
      "/api/agents/update/backup",
      { note: note ?? "" },
      opts,
    );
  },
  /** POST /api/agents/update/staged — apply the next pending release. */
  stagedUpdate(
    body: { target_tag?: string | null; max_steps?: number; create_backup?: boolean; run_checks?: boolean; actor?: string },
    opts?: FetchOptions,
  ) {
    return postJson<HermesAgentUpdateResult>(
      "/api/agents/update/staged",
      {
        target_tag: body.target_tag ?? null,
        max_steps: body.max_steps ?? 1,
        create_backup: body.create_backup ?? true,
        run_checks: body.run_checks ?? true,
        actor: body.actor ?? "hermes-agent",
      },
      opts,
    );
  },
  /** POST /api/agents/update/rollback — restore a backup. */
  rollback(body: { backup_id?: string; tag?: string; actor?: string }, opts?: FetchOptions) {
    return postJson<HermesAgentUpdateResult>(
      "/api/agents/update/rollback",
      {
        backup_id: body.backup_id ?? null,
        tag: body.tag ?? null,
        actor: body.actor ?? "hermes-agent",
      },
      opts,
    );
  },
  /** GET /api/agents — live agent roster. */
  listAgents(opts?: FetchOptions) {
    return safeGetJson<unknown[]>("/api/agents", opts);
  },
  /** GET /api/agents/health — fleet health. */
  health(opts?: FetchOptions) {
    return safeGetJson<{ available: boolean; healthy: boolean; status: string; agents?: Record<string, string> }>(
      "/api/agents/health",
      opts,
    );
  },
};

function cliRunnerClient(runnerId: "opencode" | "openhands") {
  return {
    /** GET /api/code-operator/cli-runners — runtime status for both runners. */
    getReadiness(opts?: FetchOptions) {
      return safeGetJson<CliRunnerReadiness>(
        "/api/code-operator/cli-runners",
        opts,
      );
    },
    /** GET /api/code-operator/sandbox/readiness — sandbox readiness (network=none, denied paths, image). */
    getSandboxReadiness(opts?: FetchOptions) {
      return safeGetJson<CliRunnerReadiness>(
        "/api/code-operator/sandbox/readiness",
        opts,
      );
    },
    /** GET /api/code-operator/cli-runners/preflight — non-mutating dry-run. */
    preflight(taskId?: string, opts?: FetchOptions) {
      const qs = new URLSearchParams({ runner_id: runnerId });
      // Backend ignores missing task_id on the GET dry-run path.
      const path = `/api/code-operator/cli-runners/preflight?${qs.toString()}`;
      return safeGetJson<CliRunnerPreflightResult>(path, opts).then((result) => {
        if (result || !taskId) return result;
        // Fallback to POST variant which requires a task_id.
        return postJson<CliRunnerPreflightResult>(
          "/api/code-operator/cli-runners/preflight",
          { runner_id: runnerId, task_id: taskId },
          opts,
        );
      });
    },
    /** POST /api/code-operator/cli-runners/run-bounded-task — single-file sandbox run. */
    spawnBoundedTask(
      body: { task_id: string; title: string; files: [string] },
      opts?: FetchOptions,
    ) {
      return postJson<CliRunnerBoundedTaskResult>(
        "/api/code-operator/cli-runners/run-bounded-task",
        {
          runner_id: runnerId,
          task_id: body.task_id,
          title: body.title,
          files: body.files,
        },
        opts,
      );
    },
  };
}

export const openCodeClient = cliRunnerClient("opencode");
export const openHandsClient = cliRunnerClient("openhands");

export const providersClient = {
  /** GET /api/providers/health — all configured LLM providers (live shape). */
  list(opts?: FetchOptions) {
    return safeGetJson<ProviderHealthEntry[]>("/api/providers/health", opts);
  },
  /** GET /api/code-operator/teams/readiness — provider team execution readiness. */
  getTeamReadiness(opts?: FetchOptions) {
    return safeGetJson<ProviderTeamReadiness>(
      "/api/code-operator/teams/readiness",
      opts,
    );
  },
  /** POST /api/code-operator/providers/smoke — single provider smoke test. */
  smoke(
    body: { provider_id: "minimax" | "deepseek" | string; task_id: string },
    opts?: FetchOptions,
  ) {
    return postJson<ProviderSmokeResult>(
      "/api/code-operator/providers/smoke",
      body,
      opts,
    );
  },
};

export const mcpClient = {
  /** GET /api/code-operator/mcp-locks/state — list active hermes3d-locks locks. */
  listLocks(opts?: FetchOptions) {
    return safeGetJson<McpLockState>(
      "/api/code-operator/mcp-locks/state",
      opts,
    );
  },
  /** GET /api/code-operator/mcp-locks/readiness — MCP server reachability. */
  readiness(opts?: FetchOptions) {
    return safeGetJson<McpReadiness>(
      "/api/code-operator/mcp-locks/readiness",
      opts,
    );
  },
  /** POST /api/code-operator/mcp-locks/heartbeat — refresh task lock TTL. */
  heartbeat(taskId: string, opts?: FetchOptions) {
    return postJson<{ ok: boolean }>(
      "/api/code-operator/mcp-locks/heartbeat",
      { task_id: taskId },
      opts,
    );
  },
};

export const appsClient = {
  /** GET /api/source-os/modules — 60-app registry from W6-8. */
  list(opts?: FetchOptions) {
    return safeGetJson<AppEntry[]>("/api/source-os/modules", opts);
  },
  /** GET /api/source-os/modules/{id} — single app detail. */
  detail(id: string, opts?: FetchOptions) {
    return safeGetJson<AppEntry>(
      `/api/source-os/modules/${encodeURIComponent(id)}`,
      opts,
    );
  },
  /** GET /api/source-os/modules/update-readiness — module update readiness summary. */
  updateReadiness(opts?: FetchOptions) {
    return safeGetJson<{ ready: boolean; reason?: string; modules?: unknown[] }>(
      "/api/source-os/modules/update-readiness",
      opts,
    );
  },
};

export const recoveryClient = {
  /** GET /api/code-operator/recovery/runs — RC v2 active runs (in-memory). */
  listRuns(taskId?: string, opts?: FetchOptions) {
    const qs = taskId ? `?task_id=${encodeURIComponent(taskId)}` : "";
    return safeGetJson<RecoveryRunsResponse>(
      `/api/code-operator/recovery/runs${qs}`,
      opts,
    );
  },
  /** GET /api/code-operator/recovery/state — JSONL ledger of attempts. */
  getState(taskId?: string, opts?: FetchOptions) {
    const qs = taskId ? `?task_id=${encodeURIComponent(taskId)}` : "";
    return safeGetJson<RecoveryStateResponse>(
      `/api/code-operator/recovery/state${qs}`,
      opts,
    );
  },
  /** POST /api/code-operator/recovery/record-failure — propose a recovery (freeze + snapshot). */
  proposeFailure(body: Record<string, unknown>, opts?: FetchOptions) {
    return postJson<{ attempt_id: string; status: string; [k: string]: unknown }>(
      "/api/code-operator/recovery/record-failure",
      body,
      opts,
    );
  },
  /** POST /api/code-operator/recovery/mark-outcome — review/apply outcome. */
  markOutcome(
    body: {
      attempt_id: string;
      status: "applied" | "review_failed" | "skipped" | string;
      recovery_summary?: string;
      proposal_id?: string;
      review_evidence_id?: string;
      apply_evidence_id?: string;
      retry_gate_id?: string;
    },
    opts?: FetchOptions,
  ) {
    return postJson<{ ok: boolean; attempt_id: string; status: string }>(
      "/api/code-operator/recovery/mark-outcome",
      body,
      opts,
    );
  },
};

/** Aggregated default export for convenience. */
export const hermes3dClient = {
  agents: agentsClient,
  openCode: openCodeClient,
  openHands: openHandsClient,
  providers: providersClient,
  mcp: mcpClient,
  apps: appsClient,
  recovery: recoveryClient,
};

export type Hermes3dClient = typeof hermes3dClient;
