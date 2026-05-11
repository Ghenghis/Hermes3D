/**
 * W18-A12 — thin client for POST/GET /api/slice.
 *
 * STRICT operator freeze: the slicer route produces a G-code FILE on disk
 * and stops. This module does NOT include a "send to printer" verb and
 * intentionally hides nothing behind a generic dispatcher.
 */

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

export interface SliceRequestBody {
  stl_path: string;
  printer_profile?: string | null;
  options?: Record<string, unknown>;
}

export interface SliceAccepted {
  status: "accepted";
  accepted: true;
  job_id: string;
  id: string;
  stl_path: string;
  printer_profile: string | null;
  freeze: { no_printer_writes: boolean; no_dispatch: boolean };
}

export type SliceStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export interface SliceState {
  id: string;
  job_id: string;
  status: SliceStatus;
  name?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  dry_run?: boolean;
  proof_event_id?: string | null;
  gcode_path?: string | null;
  sha256?: string | null;
  size_bytes?: number | null;
  layer_count?: number | null;
  motion_lines?: number | null;
  estimated_print_time_min?: number | null;
  estimated_filament_g?: number | null;
  slicer_binary?: string | null;
  gcode_artifact_id?: string | null;
  proof_path?: string | null;
  proof_artifact_id?: string | null;
  error?: string | null;
  failure_payload?: Record<string, unknown> | null;
}

/** Throws on non-2xx; returns the parsed body otherwise. */
async function _json<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.text().catch(() => "");
    throw new Error(
      `HTTP ${resp.status} ${resp.statusText} on ${resp.url}: ${body.slice(0, 500)}`,
    );
  }
  return (await resp.json()) as T;
}

export async function startSlice(
  body: SliceRequestBody,
  init?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<SliceAccepted> {
  const controller = new AbortController();
  const timeout = init?.timeoutMs ?? 30_000;
  const timer = window.setTimeout(() => controller.abort("startSlice timeout"), timeout);
  const signal = init?.signal
    ? mergeAbortSignals(init.signal, controller.signal)
    : controller.signal;
  try {
    const resp = await fetch(`${LIVE_BASE_URL}/api/slice`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal,
    });
    return await _json<SliceAccepted>(resp);
  } finally {
    window.clearTimeout(timer);
  }
}

export async function getSlice(
  jobId: string,
  init?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<SliceState> {
  const controller = new AbortController();
  const timeout = init?.timeoutMs ?? 10_000;
  const timer = window.setTimeout(() => controller.abort("getSlice timeout"), timeout);
  const signal = init?.signal
    ? mergeAbortSignals(init.signal, controller.signal)
    : controller.signal;
  try {
    const resp = await fetch(`${LIVE_BASE_URL}/api/slice/${encodeURIComponent(jobId)}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal,
    });
    return await _json<SliceState>(resp);
  } finally {
    window.clearTimeout(timer);
  }
}

/**
 * Poll GET /api/slice/{job_id} every `intervalMs` until the job terminates
 * or `signal` aborts. Calls `onProgress` for every fetched state.
 */
export async function pollSliceUntilTerminal(
  jobId: string,
  opts: {
    intervalMs?: number;
    maxMs?: number;
    onProgress?: (state: SliceState) => void;
    signal?: AbortSignal;
  } = {},
): Promise<SliceState> {
  const interval = opts.intervalMs ?? 2000;
  const maxMs = opts.maxMs ?? 30 * 60_000; // 30 min hard cap
  const deadline = Date.now() + maxMs;
  let last: SliceState | null = null;
  while (Date.now() < deadline) {
    if (opts.signal?.aborted) {
      throw new Error("pollSliceUntilTerminal aborted by caller");
    }
    last = await getSlice(jobId, { signal: opts.signal, timeoutMs: 10_000 });
    opts.onProgress?.(last);
    const s = (last.status || "").toLowerCase();
    if (s === "completed" || s === "failed" || s === "cancelled") {
      return last;
    }
    await new Promise<void>((resolve) => window.setTimeout(resolve, interval));
  }
  throw new Error(
    `pollSliceUntilTerminal timed out after ${maxMs} ms; last_state=${JSON.stringify(last)}`,
  );
}

/** Download URL for the produced G-code via /api/artifacts/{id}/download. */
export function gcodeDownloadUrl(state: SliceState): string | null {
  if (!state.gcode_artifact_id) return null;
  return `${LIVE_BASE_URL}/api/artifacts/${encodeURIComponent(state.gcode_artifact_id)}/download`;
}

function mergeAbortSignals(a: AbortSignal, b: AbortSignal): AbortSignal {
  if (a.aborted) return a;
  if (b.aborted) return b;
  const ctl = new AbortController();
  const onAbort = (reason?: unknown) => ctl.abort(reason);
  a.addEventListener("abort", () => onAbort(a.reason), { once: true });
  b.addEventListener("abort", () => onAbort(b.reason), { once: true });
  return ctl.signal;
}
