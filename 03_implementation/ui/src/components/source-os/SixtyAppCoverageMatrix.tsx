/**
 * SixtyAppCoverageMatrix — top-level panel matching
 * `Images-GUI/04-source-os/source-os-60-app-coverage-matrix.png`.
 *
 * Layout:
 *   - Left rail: 11 category pills with proof-coverage bars.
 *   - Centre: AppCard grid (auto-fill, ~10 cols at 1672x941).
 *   - Footer: aggregate coverage score (passed / 60), per-category bars,
 *     license density, blocked count.
 *
 * Honest-readiness contract:
 *   - Aggregate "passed" count requires BOTH `proof_command` populated
 *     AND `last_proof_status ∈ {passed, pass}`. Anything else falls
 *     into "unknown" — never fabricated as Ready.
 *   - When the backend is unreachable the panel renders an explicit
 *     amber banner instead of pretending data exists.
 *
 * Coordination:
 *   - W15-A6 (60/60 truth audit): the matrix surfaces exactly the
 *     count the backend returns; we re-assert 60/60 in `WorkbenchHeader`
 *     and in the test assertion when `/api/apps` is reachable.
 *   - W13-7 verified `/api/apps` returns 60 items; this component is the
 *     visual oracle for that fact in the Source OS tab.
 *
 * Sources consulted:
 *   - React Grid Layout sizing primitives
 *     <https://github.com/react-grid-layout/react-grid-layout>
 *   - VS Code Marketplace 60-extensions browse pattern
 *     <https://marketplace.visualstudio.com/vscode>
 *
 * Owner: claude-w15-a13-source-os.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Shield } from "lucide-react";
import { AppCard, type AppCardData, type AppCardProofStatus } from "./AppCard";
import { AppMatrixGrid } from "./AppMatrixGrid";
import { CategoryCoverageBar } from "./CategoryCoverageBar";

// Section metadata mirrors `/api/apps` payload + W13-7 audit categories.
// Keep this list explicit so the UI never silently drops a backend section.
export const SOURCE_OS_CATEGORIES: Array<{ id: string; label: string }> = [
  { id: "modelers", label: "Modelers" },
  { id: "slicers", label: "Slicers" },
  { id: "print_farm", label: "Print Farm" },
  { id: "firmware", label: "Firmware" },
  { id: "three_d_generation", label: "3D Generation" },
  { id: "agents", label: "Agents" },
  { id: "hardware", label: "Hardware" },
  { id: "materials", label: "Materials" },
  { id: "library", label: "Library" },
  { id: "research", label: "Research" },
  { id: "utilities", label: "Utilities" },
];

interface RawApp {
  id?: string;
  display_name?: string;
  display?: string;
  section?: string;
  priority?: string;
  license?: string;
  license_spdx?: string;
  repo_url?: string;
  upstream_url?: string;
  local_path?: string;
  install_state?: string;
  detected_version?: string | null;
  health?: string;
  launch_kind?: string;
  tested_versions?: string[];
  rollback_supported?: boolean;
  proof_command?: string | null;
  update_lane?: string;
  lifecycle?: string;
  last_proof_status?: string | null;
  last_proof_at?: string | null;
}

interface AppsPayload {
  count?: number;
  apps?: RawApp[];
}

function normaliseProofStatus(raw: string | null | undefined): AppCardProofStatus {
  if (raw == null) return "unknown";
  const v = String(raw).toLowerCase();
  if (v === "passed" || v === "pass") return "passed";
  if (v === "failed" || v === "fail") return "failed";
  if (v === "pending" || v === "running") return "pending";
  return "unknown";
}

function categoryLabel(sectionId: string): string {
  const found = SOURCE_OS_CATEGORIES.find((c) => c.id === sectionId);
  if (found) return found.label;
  // Honest fallback — never invent a label, surface the raw section id.
  return sectionId
    .split("_")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function toAppCard(raw: RawApp): AppCardData | null {
  if (!raw.id) return null;
  const section = raw.section ?? "utilities";
  const hasProofCommand = typeof raw.proof_command === "string" && raw.proof_command.trim().length > 0;
  return {
    id: raw.id,
    name: raw.display_name ?? raw.display ?? raw.id,
    section,
    categoryLabel: categoryLabel(section),
    version: raw.detected_version ?? null,
    hasProofCommand,
    proofStatus: normaliseProofStatus(raw.last_proof_status),
    proofGapReason: hasProofCommand ? null : "No proof_command on record",
    installState: raw.install_state ?? "unknown",
    upstreamUrl: raw.upstream_url ?? raw.repo_url ?? null,
    updateLane: raw.update_lane ?? "unknown",
    lifecycle: raw.lifecycle ?? "unknown",
    license: raw.license_spdx ?? raw.license ?? null,
  };
}

export interface SixtyAppCoverageMatrixProps {
  bridgeBaseUrl: string;
  /**
   * Optional test seam — when provided overrides the network fetch.
   * Returns the raw `/api/apps` payload shape.
   */
  fetcher?: (url: string) => Promise<AppsPayload>;
  /** Optional callback when the user navigates into a card. */
  onNavigate?: (id: string) => void;
}

export function SixtyAppCoverageMatrix({
  bridgeBaseUrl,
  fetcher,
  onNavigate,
}: SixtyAppCoverageMatrixProps) {
  const [apps, setApps] = useState<AppCardData[] | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [search, setSearch] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setBusy(true);
      try {
        let payload: AppsPayload;
        if (fetcher) {
          payload = await fetcher(`${bridgeBaseUrl}/api/apps`);
        } else {
          const response = await fetch(`${bridgeBaseUrl}/api/apps`, {
            method: "GET",
            headers: { Accept: "application/json" },
            cache: "no-store",
            signal,
          });
          if (!response.ok) {
            throw new Error(`HTTP ${response.status} ${response.statusText}`);
          }
          payload = (await response.json()) as AppsPayload;
        }
        if (signal?.aborted) return;
        const raws = Array.isArray(payload.apps) ? payload.apps : [];
        const mapped: AppCardData[] = [];
        for (const raw of raws) {
          const card = toAppCard(raw);
          if (card) mapped.push(card);
        }
        setApps(mapped);
        setCount(payload.count ?? mapped.length);
        setLoadError(null);
      } catch (caught) {
        if (signal?.aborted) return;
        setLoadError(caught instanceof Error ? caught.message : "fetch failed");
        // Preserve last-known apps so the operator can still read the matrix.
        setApps((prev) => prev ?? []);
      } finally {
        setBusy(false);
      }
    },
    [bridgeBaseUrl, fetcher],
  );

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const categoryBuckets = useMemo(() => {
    const buckets: Record<string, AppCardData[]> = {};
    for (const cat of SOURCE_OS_CATEGORIES) buckets[cat.id] = [];
    for (const app of apps ?? []) {
      if (!buckets[app.section]) {
        buckets[app.section] = [];
      }
      buckets[app.section].push(app);
    }
    return buckets;
  }, [apps]);

  const coverageStats = useMemo(() => {
    let passed = 0;
    let failed = 0;
    let unknown = 0;
    for (const app of apps ?? []) {
      if (app.hasProofCommand && app.proofStatus === "passed") {
        passed += 1;
      } else if (app.hasProofCommand && app.proofStatus === "failed") {
        failed += 1;
      } else {
        unknown += 1;
      }
    }
    return { passed, failed, unknown, total: (apps ?? []).length };
  }, [apps]);

  const categoryStats = useMemo(() => {
    const out: Record<string, { passed: number; failed: number; unknown: number; total: number }> = {};
    for (const cat of SOURCE_OS_CATEGORIES) {
      const bucket = categoryBuckets[cat.id] ?? [];
      let passed = 0;
      let failed = 0;
      let unknown = 0;
      for (const app of bucket) {
        if (app.hasProofCommand && app.proofStatus === "passed") passed += 1;
        else if (app.hasProofCommand && app.proofStatus === "failed") failed += 1;
        else unknown += 1;
      }
      out[cat.id] = { passed, failed, unknown, total: bucket.length };
    }
    return out;
  }, [categoryBuckets]);

  const licenseDensity = useMemo(() => {
    const out: Record<string, number> = {};
    for (const app of apps ?? []) {
      const key = app.license && app.license.toLowerCase() !== "unknown" ? app.license : "Unknown";
      out[key] = (out[key] ?? 0) + 1;
    }
    return out;
  }, [apps]);

  const filteredApps = useMemo(() => {
    const lower = search.trim().toLowerCase();
    return (apps ?? []).filter((app) => {
      if (activeCategory !== "all" && app.section !== activeCategory) return false;
      if (!lower) return true;
      return (
        app.id.toLowerCase().includes(lower) ||
        app.name.toLowerCase().includes(lower) ||
        app.categoryLabel.toLowerCase().includes(lower)
      );
    });
  }, [apps, activeCategory, search]);

  const grandTotal = count ?? coverageStats.total;
  const truth60 = grandTotal === 60;

  return (
    <section
      data-testid="source-os-60-app-matrix"
      data-app-count={grandTotal}
      className="flex min-h-0 w-full flex-col gap-3 p-3"
      aria-label="60-app coverage matrix"
    >
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-semibold text-fg">60-App Workbench</h2>
          <p
            className="mt-0.5 truncate text-[11px] text-muted"
            title={
              truth60
                ? "Backend returned 60 apps — matrix is the visual oracle for that fact."
                : `Backend returned ${grandTotal} apps. 60/60 truth NOT preserved — investigate /api/apps.`
            }
          >
            <span data-testid="matrix-truth-claim">{grandTotal} of 60 apps loaded</span>
            {!truth60 && (
              <span className="ml-2 rounded border border-amber-700/60 bg-amber-950/40 px-1.5 py-0.5 text-[10px] uppercase text-amber-200">
                truth gap
              </span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="relative">
            <Search
              className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted"
              aria-hidden
            />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter by name, id, or category"
              className="w-56 rounded border border-border bg-bg/60 py-1 pl-7 pr-2 text-xs text-fg outline-none placeholder:text-muted focus:border-accent-blue/60"
              data-testid="matrix-search"
              aria-label="Filter apps"
            />
          </label>
          <button
            type="button"
            onClick={() => void load()}
            disabled={busy}
            data-testid="matrix-refresh"
            className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-[11px] text-fg hover:border-accent-blue/40 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${busy ? "animate-spin" : ""}`} aria-hidden />
            {busy ? "Refreshing" : "Refresh"}
          </button>
        </div>
      </header>

      {loadError && (
        <div
          role="alert"
          data-testid="matrix-error-banner"
          className="rounded border border-amber-700/50 bg-amber-950/30 px-3 py-2 text-xs text-amber-200"
        >
          App registry unreachable: {loadError}. Showing last-known data — counts may lag the backend.
        </div>
      )}

      {/* Category rail + matrix */}
      <div className="flex min-h-0 flex-1 flex-col gap-3 lg:flex-row">
        {/* Category rail */}
        <aside
          className="flex shrink-0 flex-row flex-wrap gap-1.5 overflow-x-auto lg:w-56 lg:flex-col lg:flex-nowrap"
          aria-label="Filter by category"
          data-testid="matrix-category-rail"
        >
          <CategoryCoverageBar
            label="All Apps"
            total={coverageStats.total}
            passed={coverageStats.passed}
            failed={coverageStats.failed}
            unknown={coverageStats.unknown}
            onSelect={() => setActiveCategory("all")}
            active={activeCategory === "all"}
          />
          {SOURCE_OS_CATEGORIES.map((cat) => {
            const stats = categoryStats[cat.id] ?? { passed: 0, failed: 0, unknown: 0, total: 0 };
            return (
              <CategoryCoverageBar
                key={cat.id}
                label={cat.label}
                total={stats.total}
                passed={stats.passed}
                failed={stats.failed}
                unknown={stats.unknown}
                onSelect={() => setActiveCategory(cat.id)}
                active={activeCategory === cat.id}
              />
            );
          })}
        </aside>

        {/* Centre matrix */}
        <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-auto">
          {filteredApps.length === 0 ? (
            <div
              className="rounded border border-border bg-surface/50 p-4 text-center text-xs text-muted"
              data-testid="matrix-empty"
            >
              {search
                ? `No apps match "${search}" in this category.`
                : "No apps loaded yet. The backend may still be initialising."}
            </div>
          ) : (
            <AppMatrixGrid>
              {filteredApps.map((app) => (
                <AppCard key={app.id} app={app} bridgeBaseUrl={bridgeBaseUrl} onNavigate={onNavigate} />
              ))}
            </AppMatrixGrid>
          )}
        </div>
      </div>

      {/* Footer summary */}
      <footer
        className="grid grid-cols-1 gap-3 rounded border border-border bg-surface/50 p-3 lg:grid-cols-4"
        data-testid="matrix-coverage-footer"
      >
        <div className="flex flex-col gap-1">
          <span className="text-[10px] uppercase text-muted">Coverage Score</span>
          <span className="text-2xl font-bold text-fg" data-testid="matrix-coverage-score">
            {coverageStats.total > 0
              ? `${Math.round((coverageStats.passed / coverageStats.total) * 100)}%`
              : "—"}
          </span>
          <span className="text-[11px] text-muted">
            {coverageStats.passed} / {grandTotal} apps proof-passed
          </span>
          {coverageStats.failed > 0 && (
            <span className="text-[10px] text-rose-300">{coverageStats.failed} blocked by failed proof</span>
          )}
          {coverageStats.unknown > 0 && (
            <span className="text-[10px] text-amber-200">
              {coverageStats.unknown} unknown (no proof_command or never proofed)
            </span>
          )}
        </div>
        <div className="flex flex-col gap-1 lg:col-span-2">
          <span className="text-[10px] uppercase text-muted">Category Coverage</span>
          <div className="grid grid-cols-2 gap-1.5">
            {SOURCE_OS_CATEGORIES.map((cat) => {
              const stats = categoryStats[cat.id] ?? { passed: 0, failed: 0, unknown: 0, total: 0 };
              return (
                <CategoryCoverageBar
                  key={`footer-${cat.id}`}
                  label={cat.label}
                  total={stats.total}
                  passed={stats.passed}
                  failed={stats.failed}
                  unknown={stats.unknown}
                />
              );
            })}
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] uppercase text-muted">License Density</span>
          <ul className="flex flex-col gap-0.5 text-[11px]">
            {Object.entries(licenseDensity)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 6)
              .map(([license, n]) => (
                <li key={license} className="flex items-center justify-between gap-2">
                  <span className="truncate text-fg" title={license}>
                    {license}
                  </span>
                  <span className="font-mono text-muted">{n}</span>
                </li>
              ))}
          </ul>
          <div className="mt-1 inline-flex items-center gap-1 text-[10px] text-muted">
            <Shield className="h-3 w-3" aria-hidden /> Ready = proof_command + last proof passed
          </div>
        </div>
      </footer>
    </section>
  );
}
