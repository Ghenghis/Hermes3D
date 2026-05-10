/**
 * Settings → MCP subtab (W8-2 GUI breadth pages).
 *
 * Shows the live MCP-lock state from the Hermes locks server. We read via
 * GET /api/mcp/locks if the bridge exposes it; otherwise we surface an honest
 * "MCP locks API unavailable" placeholder.
 *
 * No write actions: forcibly releasing another agent's lock is a privileged
 * operation owned by the orchestrator, not the GUI. This subtab is
 * read-only and refreshes every 10s.
 *
 * Sources consulted:
 *   - WAI-ARIA APG, "Table" pattern · https://www.w3.org/WAI/ARIA/apg/patterns/table/
 *     for column-header/row semantics on a static lock list.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, Lock, RefreshCw } from "lucide-react";

type HermesImportMeta = ImportMeta & {
  env: { VITE_HERMES3D_BRIDGE_PORT?: string };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const POLL_MS = 10_000;

export interface McpLockEntry {
  file: string;
  owner: string;
  role: string;
  taskId: string | null;
  acquiredAt: string | null;
  expiresAt: string | null;
  stale: boolean;
}

function readString(record: Record<string, unknown>, key: string): string | null {
  const v = record[key];
  return typeof v === "string" && v.length > 0 ? v : null;
}

function readBool(record: Record<string, unknown>, key: string): boolean {
  return Boolean(record[key]);
}

function normalize(entry: unknown): McpLockEntry | null {
  if (!entry || typeof entry !== "object") return null;
  const r = entry as Record<string, unknown>;
  const file = readString(r, "file") ?? readString(r, "path");
  const owner = readString(r, "owner");
  if (!file || !owner) return null;
  return {
    file,
    owner,
    role: readString(r, "role") ?? "agent",
    taskId: readString(r, "taskId") ?? readString(r, "task_id"),
    acquiredAt: readString(r, "acquiredAt") ?? readString(r, "acquired_at"),
    expiresAt: readString(r, "expiresAt") ?? readString(r, "expires_at"),
    stale: readBool(r, "stale"),
  };
}

async function fetchLocks(signal?: AbortSignal): Promise<McpLockEntry[]> {
  const response = await fetch(`${BASE_URL}/api/mcp/locks`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    throw new Error(`bridge returned ${response.status}`);
  }
  const data = (await response.json()) as
    | { locks?: unknown[] }
    | unknown[]
    | null;
  if (!data) return [];
  const raw = Array.isArray(data) ? data : Array.isArray(data.locks) ? data.locks : [];
  return raw
    .map(normalize)
    .filter((e): e is McpLockEntry => e !== null)
    .sort((a, b) => a.file.localeCompare(b.file));
}

interface FetchProps {
  /** Test seam: override the HTTP fetch with a controlled mock. */
  fetcher?: (signal?: AbortSignal) => Promise<McpLockEntry[]>;
  /** Test seam: override the polling interval. Pass 0 to disable. */
  pollIntervalMs?: number;
}

export function McpSubtab({ fetcher = fetchLocks, pollIntervalMs = POLL_MS }: FetchProps = {}) {
  const [locks, setLocks] = useState<McpLockEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(async (signal?: AbortSignal) => {
    setRefreshing(true);
    try {
      const next = await fetcherRef.current(signal);
      if (signal?.aborted) return;
      setLocks(next);
      setError(null);
    } catch (caught) {
      if (signal?.aborted) return;
      setError(caught instanceof Error ? caught.message : "MCP locks API unavailable");
      setLocks((prev) => prev ?? []);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    if (pollIntervalMs <= 0) {
      return () => controller.abort();
    }
    const interval = window.setInterval(() => {
      void load(controller.signal);
    }, pollIntervalMs);
    return () => {
      window.clearInterval(interval);
      controller.abort();
    };
  }, [load, pollIntervalMs]);

  const total = locks?.length ?? 0;
  const stale = (locks ?? []).filter((l) => l.stale).length;

  return (
    <section data-testid="settings-mcp" className="flex flex-col gap-3 text-xs">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-muted">
          <Lock size={14} />
          <span className="text-fg font-medium">MCP Locks</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded bg-surface2 px-2 py-0.5 text-[10px] uppercase text-muted">
            {total} active
          </span>
          {stale > 0 && (
            <span className="rounded bg-amber-950/60 px-2 py-0.5 text-[10px] uppercase text-amber-200">
              {stale} stale
            </span>
          )}
          <button
            type="button"
            onClick={() => void load()}
            disabled={refreshing}
            data-testid="settings-mcp-refresh"
            className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] text-fg hover:bg-surface2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw size={11} className={refreshing ? "animate-spin" : ""} aria-hidden />
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>

      <p className="text-[10px] text-muted">
        Read-only view of the active MCP file locks held by Hermes agents.
        Refreshes every {Math.round(pollIntervalMs / 1000)}s. The orchestrator
        is the only authority that may force-release another agent&apos;s lock.
      </p>

      {error && (
        <div
          role="alert"
          data-testid="settings-mcp-error"
          className="rounded border border-amber-700/50 bg-amber-950/30 px-3 py-2 text-[11px] text-amber-200"
        >
          {error}. Showing last-known data.
        </div>
      )}

      <div className="overflow-x-auto rounded border border-border bg-surface">
        <table role="table" className="min-w-full border-collapse text-left text-[11px]">
          <thead role="rowgroup" className="bg-surface2 text-[10px] uppercase text-muted">
            <tr role="row">
              <th role="columnheader" scope="col" className="px-3 py-1.5">
                File
              </th>
              <th role="columnheader" scope="col" className="px-3 py-1.5">
                Owner
              </th>
              <th role="columnheader" scope="col" className="px-3 py-1.5">
                Role
              </th>
              <th role="columnheader" scope="col" className="px-3 py-1.5">
                Task
              </th>
              <th role="columnheader" scope="col" className="px-3 py-1.5">
                Expires
              </th>
              <th role="columnheader" scope="col" className="px-3 py-1.5">
                State
              </th>
            </tr>
          </thead>
          <tbody role="rowgroup">
            {locks === null && !error && (
              <tr role="row">
                <td role="cell" colSpan={6} className="px-3 py-3 text-center text-muted">
                  Loading locks…
                </td>
              </tr>
            )}
            {locks !== null && locks.length === 0 && !error && (
              <tr role="row">
                <td role="cell" colSpan={6} className="px-3 py-3 text-center text-muted">
                  No MCP locks held.
                </td>
              </tr>
            )}
            {(locks ?? []).map((lock) => (
              <tr
                role="row"
                key={`${lock.file}|${lock.owner}`}
                data-testid={`settings-mcp-row-${lock.owner}`}
                className={`border-t border-border/60 ${lock.stale ? "bg-amber-950/20" : ""}`}
              >
                <td role="cell" className="px-3 py-1.5 font-mono text-[10px] text-fg">
                  {lock.file}
                </td>
                <td role="cell" className="px-3 py-1.5 text-fg">
                  {lock.owner}
                </td>
                <td role="cell" className="px-3 py-1.5 text-muted">
                  {lock.role}
                </td>
                <td role="cell" className="px-3 py-1.5 font-mono text-[10px] text-muted">
                  {lock.taskId ?? "—"}
                </td>
                <td role="cell" className="px-3 py-1.5 text-[10px] text-muted">
                  {formatExpires(lock.expiresAt)}
                </td>
                <td role="cell" className="px-3 py-1.5">
                  {lock.stale ? (
                    <span className="inline-flex items-center gap-1 rounded bg-amber-950/60 px-1.5 py-0.5 text-[10px] uppercase text-amber-200">
                      <Activity size={10} aria-hidden /> stale
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded bg-green-950/60 px-1.5 py-0.5 text-[10px] uppercase text-green-300">
                      <Activity size={10} aria-hidden /> active
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatExpires(iso: string | null): string {
  if (!iso) return "—";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return iso;
  const diffMs = ts - Date.now();
  if (diffMs <= 0) return "expired";
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  return `${hours}h`;
}
