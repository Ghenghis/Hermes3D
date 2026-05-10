/**
 * appsClient — thin client for the 60-app registry endpoints.
 *
 * Owners:
 *   - GET  /api/source-os/modules                  → W6-7 backend (consume only)
 *   - GET  /api/source-os/modules/{id}             → W6-7 backend (consume only)
 *   - POST /api/source-os/modules/{id}/run-proof   → W6-7 backend (consume only)
 *
 * Coordination with W6-5:
 *   The W6-8 brief mentioned a shared `appsClient` from
 *   `01_app/src/api/hermes3dClient.ts`. That client landed on a
 *   parallel branch and is not yet in the base branch this lane forks
 *   from. To keep W6-8 unblocked we ship a self-contained client here.
 *   The two clients are interoperable: this module exports the same
 *   `appsClient` symbol with `listApps`, `getApp`, and `runProof`
 *   methods, so consumers can later swap the implementation by
 *   re-exporting from the hermes3dClient version without touching
 *   call sites.
 *
 * Security:
 *   - Never echoes raw `proof_command` output. The `reason` strings the
 *     backend returns are passed through `redactProofReason` which
 *     strips control characters and caps length to 280 chars; this is
 *     defense in depth on top of backend redaction.
 */

import type {
  ProofStatus,
  RegistryApp,
  RegistryAppDetail,
  RegistryRunProofResponse,
} from "../types/app-registry";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const APPS_LIST_URL = `${LIVE_BASE_URL}/api/source-os/modules`;
const appsDetailUrl = (id: string) =>
  `${LIVE_BASE_URL}/api/source-os/modules/${encodeURIComponent(id)}`;
const appsRunProofUrl = (id: string) =>
  `${LIVE_BASE_URL}/api/source-os/modules/${encodeURIComponent(id)}/run-proof`;

const KNOWN_LIFECYCLES = new Set([
  "stable",
  "canary",
  "frozen",
  "unknown",
] as const);
const KNOWN_LANES = new Set([
  "core",
  "stable",
  "canary",
  "frozen",
  "experimental",
  "unknown",
] as const);
const KNOWN_PROOF_STATUSES = new Set<ProofStatus>([
  "pass",
  "fail",
  "pending",
  "unknown",
]);

function readString(record: Record<string, unknown>, key: string): string | null {
  const v = record[key];
  return typeof v === "string" && v.length > 0 ? v : null;
}

function readBool(record: Record<string, unknown>, key: string): boolean {
  return record[key] === true;
}

function readArray(record: Record<string, unknown>, key: string): unknown[] {
  const v = record[key];
  return Array.isArray(v) ? v : [];
}

function readProofStatus(value: unknown): ProofStatus {
  if (typeof value === "string" && KNOWN_PROOF_STATUSES.has(value as ProofStatus)) {
    return value as ProofStatus;
  }
  return "unknown";
}

/** Cap proof reasons to a sane width and strip control characters defensively. */
export function redactProofReason(reason: string | null | undefined): string {
  if (!reason) {
    return "";
  }
  // eslint-disable-next-line no-control-regex
  const stripped = reason.replace(/[\x00-\x09\x0B-\x1F\x7F]/g, " ");
  if (stripped.length <= 280) {
    return stripped;
  }
  return `${stripped.slice(0, 279)}…`;
}

/** Map any backend record (current `AppEntry` payload or future enriched
 *  shape) into the rich `RegistryApp` the GUI table consumes. Missing
 *  fields are surfaced as honest "unknown" placeholders downstream. */
export function toRegistryApp(record: Record<string, unknown>): RegistryApp {
  const lifecycleRaw = readString(record, "lifecycle") ?? readString(record, "status");
  const lifecycle =
    lifecycleRaw && (KNOWN_LIFECYCLES as ReadonlySet<string>).has(lifecycleRaw)
      ? (lifecycleRaw as RegistryApp["lifecycle"])
      : "unknown";
  const laneRaw =
    readString(record, "update_lane") ??
    readString(record, "lane") ??
    readString(record, "category");
  const lane =
    laneRaw && (KNOWN_LANES as ReadonlySet<string>).has(laneRaw)
      ? (laneRaw as RegistryApp["update_lane"])
      : "unknown";
  const licenseRaw = record.license;
  let license: RegistryApp["license"];
  if (licenseRaw && typeof licenseRaw === "object") {
    const obj = licenseRaw as Record<string, unknown>;
    license = {
      spdx: readString(obj, "spdx") ?? readString(obj, "id") ?? "Unknown",
      label: readString(obj, "label") ?? undefined,
      url: readString(obj, "url"),
    };
  } else if (typeof licenseRaw === "string" && licenseRaw.length > 0) {
    license = { spdx: licenseRaw };
  } else {
    license = { spdx: "Unknown" };
  }
  const lastProofRaw = record.last_proof ?? record.proof ?? null;
  let last_proof: RegistryApp["last_proof"] = null;
  if (lastProofRaw && typeof lastProofRaw === "object") {
    const obj = lastProofRaw as Record<string, unknown>;
    last_proof = {
      proof_event_id: readString(obj, "proof_event_id") ?? readString(obj, "id"),
      status: readProofStatus(obj.status),
      at: readString(obj, "at") ?? readString(obj, "timestamp"),
      reason: readString(obj, "reason"),
    };
  }
  return {
    id: (typeof record.id === "string" ? record.id : "") || "(unknown)",
    name:
      (typeof record.name === "string" ? record.name : null) ??
      (typeof record.display === "string" ? record.display : null) ??
      (typeof record.id === "string" ? record.id : "(unknown)"),
    current_version: readString(record, "current_version") ?? readString(record, "version"),
    tested_versions: readArray(record, "tested_versions").filter(
      (v): v is string => typeof v === "string" && v.length > 0,
    ),
    license,
    update_lane: lane,
    lifecycle,
    last_proof,
    rollback_supported: readBool(record, "rollback_supported") || readBool(record, "rollback"),
    description: readString(record, "description"),
    upstream_url: readString(record, "upstream_url") ?? readString(record, "repo_url"),
  };
}

export function toRegistryAppDetail(record: Record<string, unknown>): RegistryAppDetail {
  const base = toRegistryApp(record);
  const recentRaw = readArray(record, "recent_proofs");
  const recent_proofs = recentRaw
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const obj = item as Record<string, unknown>;
      return {
        proof_event_id: readString(obj, "proof_event_id") ?? readString(obj, "id"),
        status: readProofStatus(obj.status),
        at: readString(obj, "at") ?? readString(obj, "timestamp"),
        reason: readString(obj, "reason"),
      };
    })
    .filter((p): p is NonNullable<typeof p> => p !== null);
  return {
    ...base,
    recent_proofs,
    rollback_runbook_url: readString(record, "rollback_runbook_url"),
    proof_command: readString(record, "proof_command"),
    metadata: undefined,
  };
}

/** GET /api/source-os/modules — list all registry apps (mapped). */
export async function listApps(signal?: AbortSignal): Promise<RegistryApp[]> {
  const response = await fetch(APPS_LIST_URL, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`apps list request failed: ${response.status} ${response.statusText}`);
  }
  const payload = (await response.json()) as
    | Record<string, unknown>[]
    | { apps?: Record<string, unknown>[] }
    | { modules?: Record<string, unknown>[] };
  if (Array.isArray(payload)) {
    return payload.map(toRegistryApp);
  }
  if (payload && Array.isArray((payload as { apps?: unknown[] }).apps)) {
    return (payload as { apps: Record<string, unknown>[] }).apps.map(toRegistryApp);
  }
  if (payload && Array.isArray((payload as { modules?: unknown[] }).modules)) {
    return (payload as { modules: Record<string, unknown>[] }).modules.map(toRegistryApp);
  }
  return [];
}

/** GET /api/source-os/modules/{id} — full detail for a single app. */
export async function getApp(id: string, signal?: AbortSignal): Promise<RegistryAppDetail> {
  const response = await fetch(appsDetailUrl(id), {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`app detail request failed: ${response.status} ${response.statusText}`);
  }
  const payload = (await response.json()) as Record<string, unknown>;
  return toRegistryAppDetail(payload);
}

/** POST /api/source-os/modules/{id}/run-proof — request a fresh proof run. */
export async function runProof(
  id: string,
  reason = "operator requested from Hermes3D UI",
  signal?: AbortSignal,
): Promise<RegistryRunProofResponse> {
  const response = await fetch(appsRunProofUrl(id), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ reason }),
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    return {
      accepted: false,
      proof_event_id: null,
      status: "unknown",
      reason: redactProofReason(
        `run-proof request failed: ${response.status} ${response.statusText}`,
      ),
    };
  }
  const payload = (await response.json()) as {
    accepted?: boolean;
    proof_event_id?: string | null;
    status?: ProofStatus | string;
    reason?: string | null;
  };
  return {
    accepted: payload.accepted ?? true,
    proof_event_id: payload.proof_event_id ?? null,
    status: readProofStatus(payload.status),
    reason: redactProofReason(payload.reason ?? null),
  };
}

/**
 * Convenience client object. Mirrors the shape W6-5 ships in
 * `hermes3dClient.ts` (where `appsClient` is a sibling of `agentsClient`,
 * `mcpClient`, etc.).
 */
export const appsClient = {
  listApps,
  getApp,
  runProof,
} as const;

export type AppsClient = typeof appsClient;

/** Error thrown when both `/api/apps` and `/api/source-os/modules` endpoints
 *  return non-OK responses for the same operation. Used by the W8-2 detail
 *  page to render an honest blocked state instead of fabricating data. */
export class AppsClientError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AppsClientError";
  }
}

/** Test-seam factory: build an `AppsClient` over a custom base URL and
 *  optional fetcher. Used by Vitest unit tests and (eventually) by the
 *  W6-5 hermes3dClient when it consolidates clients. The returned object
 *  has the same `listApps`/`getApp`/`runProof` shape as the singleton
 *  `appsClient`, but tries `/api/apps` first and falls back to
 *  `/api/source-os/modules` when the registry endpoint is not yet wired. */
export function createAppsClient(options: {
  baseUrl: string;
  fetcher?: typeof fetch;
}): AppsClient {
  const { baseUrl, fetcher = fetch } = options;
  const appsUrl = `${baseUrl}/api/apps`;
  const modulesUrl = `${baseUrl}/api/source-os/modules`;
  const appUrl = (id: string) => `${baseUrl}/api/apps/${encodeURIComponent(id)}`;
  const moduleUrl = (id: string) =>
    `${baseUrl}/api/source-os/modules/${encodeURIComponent(id)}`;
  const runProofUrl = (id: string) =>
    `${baseUrl}/api/apps/${encodeURIComponent(id)}/run-proof`;
  const moduleRunProofUrl = (id: string) =>
    `${baseUrl}/api/source-os/modules/${encodeURIComponent(id)}/run-proof`;

  function extractList(payload: unknown): RegistryApp[] {
    if (Array.isArray(payload)) {
      return payload.map((entry) => toRegistryApp(entry as Record<string, unknown>));
    }
    if (payload && typeof payload === "object") {
      const obj = payload as { apps?: unknown[]; modules?: unknown[] };
      if (Array.isArray(obj.apps)) {
        return obj.apps.map((entry) => toRegistryApp(entry as Record<string, unknown>));
      }
      if (Array.isArray(obj.modules)) {
        return obj.modules.map((entry) => toRegistryApp(entry as Record<string, unknown>));
      }
    }
    return [];
  }

  return {
    async listApps(signal?: AbortSignal): Promise<RegistryApp[]> {
      const init: RequestInit = {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal,
      };
      const primary = await fetcher(appsUrl, init);
      if (primary.ok) {
        return extractList(await primary.json());
      }
      const fallback = await fetcher(modulesUrl, init);
      if (fallback.ok) {
        return extractList(await fallback.json());
      }
      throw new AppsClientError(
        `apps registry not found in registry: ${primary.status}/${fallback.status}`,
      );
    },
    async getApp(id: string, signal?: AbortSignal): Promise<RegistryAppDetail> {
      const init: RequestInit = {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
        signal,
      };
      const primary = await fetcher(appUrl(id), init);
      if (primary.ok) {
        return toRegistryAppDetail((await primary.json()) as Record<string, unknown>);
      }
      const fallback = await fetcher(moduleUrl(id), init);
      if (fallback.ok) {
        return toRegistryAppDetail((await fallback.json()) as Record<string, unknown>);
      }
      throw new AppsClientError(
        `app "${id}" not found in registry: ${primary.status}/${fallback.status}`,
      );
    },
    async runProof(
      id: string,
      reason = "operator requested from Hermes3D UI",
      signal?: AbortSignal,
    ): Promise<RegistryRunProofResponse> {
      const init: RequestInit = {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reason }),
        cache: "no-store",
        signal,
      };
      const primary = await fetcher(runProofUrl(id), init);
      if (primary.ok) {
        const payload = (await primary.json()) as {
          accepted?: boolean;
          proof_event_id?: string | null;
          status?: ProofStatus | string;
          reason?: string | null;
        };
        return {
          accepted: payload.accepted ?? true,
          proof_event_id: payload.proof_event_id ?? null,
          status: readProofStatus(payload.status),
          reason: redactProofReason(payload.reason ?? null),
        };
      }
      const fallback = await fetcher(moduleRunProofUrl(id), init);
      if (fallback.ok) {
        const payload = (await fallback.json()) as {
          accepted?: boolean;
          proof_event_id?: string | null;
          status?: ProofStatus | string;
          reason?: string | null;
        };
        return {
          accepted: payload.accepted ?? true,
          proof_event_id: payload.proof_event_id ?? null,
          status: readProofStatus(payload.status),
          reason: redactProofReason(payload.reason ?? null),
        };
      }
      return {
        accepted: false,
        proof_event_id: null,
        status: "unknown",
        reason: redactProofReason(
          `run-proof not found in registry: ${primary.status}/${fallback.status}`,
        ),
      };
    },
  };
}
