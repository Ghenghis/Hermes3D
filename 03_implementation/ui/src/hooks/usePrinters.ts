/**
 * usePrinters — live wiring for the #printers tab.
 *
 * Why this hook exists (W17-FIX-PRINTERS-API):
 *   The legacy path was `adapters.getPrinters()` → `getLivePrinters` in
 *   `adapters.live.ts`, which swallows ALL fetch / parse errors and returns
 *   an empty array. That made every failure mode (backend down, CORS
 *   misconfigured, wrong port, parse mismatch) look identical to "no
 *   printers configured" in the UI, so operators saw
 *   "No printer inventory returned from the live printer API" even when the
 *   backend was returning 4 records on `/api/printers`. This hook fetches
 *   `/api/printers` itself and surfaces the failure mode as an `error`
 *   value, so the component can distinguish:
 *
 *     - loading       (isLoading=true)
 *     - api unreachable / parse error (error != null) ← was hidden before
 *     - api reachable, zero printers (data=[], error=null)
 *     - api reachable, N printers   (data=[...N], error=null)
 *
 *   The hook does NOT call the legacy `adapters.getPrinters` helper because
 *   that wrapper hides the very error we need to display.
 *
 * Contract:
 *   - Polls every `STATUS_POLL_MS` (5 s).
 *   - Aborts in-flight requests on unmount via the AbortController from
 *     `_useQuery.useQuery`.
 *   - Reads the bridge port from `VITE_HERMES3D_BRIDGE_PORT`, falling back
 *     to the default `8765`, matching `adapters.live.ts`.
 *   - Returns `Printer[]` (never null) so the component never has to
 *     null-check the success branch.
 *   - Treats unparseable payload entries as a parse error (visible to the
 *     operator) instead of silently dropping rows.
 */
import type { Printer, PrinterAdapter, PrinterDataSource, PrinterStatus } from "../types/printer";
import { STATUS_POLL_MS, useQuery, type QueryResult } from "./_useQuery";

type HermesImportMeta = ImportMeta & {
  env?: { VITE_HERMES3D_BRIDGE_PORT?: string };
};

const DEFAULT_BRIDGE_PORT = "8765";

function bridgePort(): string {
  const env = (import.meta as HermesImportMeta).env ?? {};
  return env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
}

/** Visible for testing — the canonical printer list URL. */
export function printersUrl(): string {
  return `http://127.0.0.1:${bridgePort()}/api/printers`;
}

// Validation predicates — must stay in sync with backend
// `hermes3d.services.local_state.local_printers()`.
const MODELS = new Set<Printer["model"]>(["FLSUN T1", "FLSUN S1", "FLSUN V400", "Generic"]);
const STATUSES = new Set<PrinterStatus>(["online", "active", "printing", "paused", "maintenance", "offline", "error"]);
const ADAPTERS = new Set<PrinterAdapter>(["moonraker", "octoprint", "printrun", "manual"]);
const DATA_SOURCES = new Set<PrinterDataSource>(["live", "degraded", "error", "policy", "config"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parsePrinter(value: unknown): Printer | null {
  if (!isRecord(value)) return null;
  const id = value.id;
  const name = value.name;
  const model = value.model;
  const ip = value.ip;
  const status = value.status;
  const adapter = value.adapter;
  const dataSource = value.data_source;
  const tempHot = value.temp_hot;
  const tempBed = value.temp_bed;
  const progress = value.progress;
  const currentJob = value.current_job;
  const maintenanceFlag = value.maintenance_flag;
  const cameraUrl = value.camera_url;
  if (
    typeof id !== "string" ||
    typeof name !== "string" ||
    typeof model !== "string" ||
    !MODELS.has(model as Printer["model"]) ||
    !(ip === null || typeof ip === "string") ||
    typeof status !== "string" ||
    !STATUSES.has(status as PrinterStatus) ||
    typeof adapter !== "string" ||
    !ADAPTERS.has(adapter as PrinterAdapter) ||
    typeof dataSource !== "string" ||
    !DATA_SOURCES.has(dataSource as PrinterDataSource) ||
    !(tempHot === null || (typeof tempHot === "number" && Number.isFinite(tempHot))) ||
    !(tempBed === null || (typeof tempBed === "number" && Number.isFinite(tempBed))) ||
    !(progress === null || (typeof progress === "number" && Number.isFinite(progress))) ||
    !(currentJob === null || typeof currentJob === "string") ||
    typeof maintenanceFlag !== "boolean" ||
    !(cameraUrl === null || typeof cameraUrl === "string")
  ) {
    return null;
  }
  const sourceRefs = isRecord(value.source_refs) ? value.source_refs : {};
  return {
    id,
    name,
    model: model as Printer["model"],
    ip,
    status: status as PrinterStatus,
    adapter: adapter as PrinterAdapter,
    data_source: dataSource as PrinterDataSource,
    temp_hot: tempHot,
    temp_bed: tempBed,
    progress,
    current_job: currentJob,
    maintenance_flag: maintenanceFlag,
    camera_url: cameraUrl,
    moonraker_url:
      value.moonraker_url === null || typeof value.moonraker_url === "string"
        ? (value.moonraker_url as string | null)
        : undefined,
    safety_policy: typeof value.safety_policy === "string" ? value.safety_policy : undefined,
    write_enabled: typeof value.write_enabled === "boolean" ? value.write_enabled : undefined,
    onboarded: typeof value.onboarded === "boolean" ? value.onboarded : undefined,
    status_source: typeof value.status_source === "string" ? value.status_source : undefined,
    source_refs: sourceRefs as Printer["source_refs"],
  };
}

/** Fetch + parse `/api/printers`. Throws on network failure, non-2xx
 * response, JSON parse error, or unparseable payload. The throw is what
 * lets `useQuery` set its `error` state so the component renders the real
 * reason instead of a silent empty list (the W17 bug). */
export async function fetchPrinters(signal?: AbortSignal): Promise<Printer[]> {
  const url = printersUrl();
  const response = await fetch(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`Printer API responded with HTTP ${response.status} from ${url}`);
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (cause) {
    throw new Error(
      `Printer API returned non-JSON payload from ${url}: ${
        cause instanceof Error ? cause.message : String(cause)
      }`,
    );
  }
  if (!Array.isArray(payload)) {
    throw new Error(
      `Printer API returned non-array payload from ${url} (got ${typeof payload}); expected list of printers.`,
    );
  }
  const printers: Printer[] = [];
  for (let i = 0; i < payload.length; i += 1) {
    const parsed = parsePrinter(payload[i]);
    if (!parsed) {
      throw new Error(
        `Printer API record ${i} from ${url} did not match the expected shape (id/name/model/status/adapter/data_source/maintenance_flag).`,
      );
    }
    printers.push(parsed);
  }
  return printers;
}

export function usePrinters(): QueryResult<Printer[]> {
  return useQuery<Printer[]>({
    queryKey: "printers/list",
    queryFn: async ({ signal }) => {
      const result = await fetchPrinters(signal);
      return result;
    },
    refetchInterval: STATUS_POLL_MS,
  });
}
