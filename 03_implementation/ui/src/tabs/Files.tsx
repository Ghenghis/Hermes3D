/**
 * Files tab — honest blocked state.
 *
 * Per W15-A3 backend route inventory, the `/api/files/*` surface is NOT yet
 * implemented. Rather than show fake rows, this tab:
 *   1. Probes a small set of candidate file endpoints
 *      (`/api/files/list`, `/api/files`, `/api/artifacts`) so the page
 *      auto-promotes itself once the backend ships, and
 *   2. Renders an explicit "Files API not available" message in the meantime,
 *      including the upstream tracking link.
 *
 * The `/api/artifacts` probe also lets the page render the existing Artifacts
 * surface as a read-only preview while the dedicated Files API matures. This
 * keeps the tab routed and usable without violating the no-fake-data rule.
 */

import { useCallback, useState } from "react";
import { FileText, RefreshCw } from "lucide-react";
import { adapters } from "../api/adapters";
import { PANEL_POLL_MS, usePollingEffect } from "../hooks/_useQuery";
import type { Artifact } from "../types/artifact";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

type ProbeStatus = "pending" | "available" | "missing" | "error";

interface ProbeResult {
  path: string;
  status: ProbeStatus;
  http_status?: number | null;
  detail?: string;
}

const CANDIDATE_PATHS = ["/api/files", "/api/files/list", "/api/files/index"];

async function probe(path: string): Promise<ProbeResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (response.status === 404) {
      return { path, status: "missing", http_status: 404 };
    }
    if (!response.ok) {
      return {
        path,
        status: "error",
        http_status: response.status,
        detail: response.statusText,
      };
    }
    return { path, status: "available", http_status: response.status };
  } catch (err) {
    return {
      path,
      status: "error",
      http_status: null,
      detail: err instanceof Error ? err.message : "fetch failed",
    };
  }
}

export function FilesTab() {
  const [probes, setProbes] = useState<ProbeResult[]>(
    CANDIDATE_PATHS.map((p) => ({ path: p, status: "pending" })),
  );
  const [artifacts, setArtifacts] = useState<Artifact[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await Promise.all(CANDIDATE_PATHS.map(probe));
      setProbes(next);
      // Always also pull artifacts as the runtime preview — this is the
      // existing live source for file-like records, so showing it here is
      // honest (it's the same data the Artifacts tab renders).
      try {
        const arts = await adapters.getArtifacts();
        setArtifacts(arts);
        setError(null);
      } catch (artErr) {
        setError(artErr instanceof Error ? artErr.message : "Artifacts unavailable.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // W21-MVP-5: lag-protected 15 s polling. The Files tab was previously
  // a one-shot mount fetch — operators had to manually reload after
  // any backend change. ``usePollingEffect`` cancels overlap and cleans
  // up on unmount.
  usePollingEffect(refresh, PANEL_POLL_MS, [refresh]);

  const dedicatedFilesApiAvailable = probes.some((p) => p.status === "available");

  return (
    <div data-testid="files-root" className="flex h-full flex-col gap-3">
      <header className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-surface p-3">
        <div>
          <h2 className="text-sm font-semibold text-fg">Files</h2>
          <p className="text-xs text-muted">
            Probes <code className="font-mono text-[10px]">/api/files/*</code>; falls back to the live Artifacts surface
            when the dedicated Files API is not yet shipped.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          data-testid="files-refresh"
          className="flex items-center gap-1.5 rounded border border-border px-2 py-1 text-[11px] text-muted hover:border-accent-cyan/40 hover:text-fg disabled:opacity-50"
        >
          <RefreshCw size={11} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </header>

      {!dedicatedFilesApiAvailable && (
        <div
          data-testid="files-blocked"
          role="status"
          className="rounded border border-amber-700/50 bg-amber-950/30 p-3 text-xs text-amber-200"
        >
          <div className="font-semibold">Files API not available</div>
          <p className="mt-1 leading-5 text-amber-100/80">
            None of the candidate paths returned a live index; the dedicated Files API has not yet shipped. The
            "Artifacts" surface below is the closest live source the backend currently exposes.
          </p>
          <ul className="mt-2 space-y-0.5 font-mono text-[10px]">
            {probes.map((p) => (
              <li key={p.path} data-testid={`files-probe-${p.path.replace(/[^a-z0-9]+/gi, "_")}`}>
                <span className="text-amber-200">{p.path}</span>{" "}
                <span className="text-amber-100/60">
                  · {p.status}
                  {p.http_status != null ? ` (${p.http_status})` : ""}
                  {p.detail ? ` — ${p.detail}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <div role="alert" data-testid="files-error" className="rounded border border-red-800/50 bg-red-950/30 p-2 font-mono text-[11px] text-red-200">
          {error}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-auto rounded border border-border bg-surface p-3">
        <h3 className="text-xs font-semibold uppercase text-muted">
          Artifacts (live fallback)
        </h3>
        <div className="mt-2">
          {artifacts === null ? (
            <div className="rounded border border-border bg-bg/40 p-3 text-xs text-muted">
              Loading artifacts…
            </div>
          ) : artifacts.length === 0 ? (
            <div
              data-testid="files-empty"
              className="rounded border border-border bg-bg/40 p-3 text-xs text-muted"
            >
              No artifacts returned by GET /api/artifacts.
            </div>
          ) : (
            <ul className="space-y-1">
              {artifacts.map((a) => (
                <li
                  key={a.id}
                  data-testid={`files-artifact-${a.id}`}
                  className="flex items-center justify-between gap-2 rounded border border-border bg-bg/40 px-3 py-1.5 text-xs"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <FileText size={12} className="shrink-0 text-muted" />
                    <span className="truncate text-fg">{a.name}</span>
                    <span className="shrink-0 rounded bg-surface px-1.5 py-0.5 font-mono text-[10px] text-muted">
                      {a.type}
                    </span>
                  </span>
                  <span className="shrink-0 font-mono text-[10px] text-muted">
                    {typeof a.sizeBytes === "number" && a.sizeBytes > 0
                      ? `${Math.round(a.sizeBytes / 1024)} kB`
                      : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
