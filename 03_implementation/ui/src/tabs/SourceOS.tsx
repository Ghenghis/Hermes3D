import { useEffect, useMemo, useState } from "react";
import { adapters } from "../api/adapters";
import { AppDetailPanel } from "../components/source-os/AppDetailPanel";
import { DockModeControls, type SourceOSDockMode } from "../components/source-os/DockModeControls";
import { ModuleList } from "../components/source-os/ModuleList";
import { SecondaryNav } from "../components/source-os/SecondaryNav";
import { SixtyAppCoverageMatrix } from "../components/source-os/SixtyAppCoverageMatrix";
import type { GateResult, GateVerdict, ProofBundle, ProofVerdict } from "../types/proof";
import type { BridgeTask, DispatchGateStatus, InstallState, LaunchKind, SourceModuleCliSurfaceAudit, SourceModuleCliSurfaceRecord, SourceModuleRuntime, SourceModuleUpdateReadiness, SourceOSModule, SourceOSProvider } from "../types/source-os";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

type RawModule = Record<string, unknown>;
type RuntimeCounts = {
  ready: number;
  agent_cli: number;
  source_ready: number;
  setup_required: number;
  not_installed: number;
  blocked: number;
};

// Runner contract record from /api/modules/runtime/runner-contracts
type RunnerContract = {
  module_id: string;
  runner_status: string;
  required_verifier_family: string;
  safe_actions: string[];
  acceptance_gate: string;
  blocked_reason: string | null;
};

type RunnerContractsPayload = {
  count: number;
  contracts: RunnerContract[];
};
type RuntimeVerifierSummary = {
  count: number;
  enabled_count: number;
  total_modules: number;
  runner_gap: number;
  blocked: number;
  registered_ids: string[];
};
type CliSurfaceSummary = {
  agent_enabled_cli: number;
  candidate_needs_verifier: number;
  no_local_cli_signal: number;
};

// --- Source OS readiness types (from /api/sources/readiness) ---
type ToolReadinessStatus = "verified" | "detected" | "source_ready" | "not_installed" | "unavailable";

type KeyToolDetail = {
  module_id: string;
  display: string;
  status: ToolReadinessStatus;
  runtime_status: string;
  agent_execution_tier: string;
  path: string | null;
  verifier: string | null;
  return_code: number | null;
  executed: boolean;
  cli_surface_status: string | null;
  next_action: string | null;
};

type CategoryReadiness = {
  id: string;
  label: string;
  section: string;
  total: number;
  status_counts: Record<string, number>;
  key_tools: KeyToolDetail[];
};

type SourcesReadinessPayload = {
  generated_at_utc: string;
  proof_files: Record<string, string>;
  summary: {
    verified_agent_cli: number;
    runner_gaps: number;
    agent_enabled_cli: number;
    candidate_needs_verifier: number;
  };
  categories: Record<string, CategoryReadiness>;
  artifacts_url: string;
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

// ─────────────────────────────────────────────────────────────────────────────
// Tool status badge helpers
// ─────────────────────────────────────────────────────────────────────────────

const TOOL_STATUS_BADGE: Record<ToolReadinessStatus, string> = {
  verified: "bg-green-900/70 text-green-300 border border-green-700/40",
  detected: "bg-cyan-900/60 text-cyan-200 border border-cyan-700/40",
  source_ready: "bg-blue-900/50 text-blue-300 border border-blue-700/40",
  not_installed: "bg-surface2 text-muted border border-border",
  unavailable: "bg-red-950/50 text-red-400 border border-red-800/40",
};

const TOOL_STATUS_LABEL: Record<ToolReadinessStatus, string> = {
  verified: "Verified CLI",
  detected: "Detected",
  source_ready: "Source Ready",
  not_installed: "Not Installed",
  unavailable: "Unavailable",
};

// ─────────────────────────────────────────────────────────────────────────────
// SourceOSTab (main export)
// ─────────────────────────────────────────────────────────────────────────────

type SourceOSView = "matrix" | "registry";

const VIEW_STORAGE_KEY = "h3d.sourceOs.view";

function readInitialView(): SourceOSView {
  // Default to the legacy "registry" view so the existing live-gui E2E
  // contract (which expects the source-backed-modules subtitle and the
  // runtime readiness bar on first open) keeps passing. Operators who
  // prefer the 60-app matrix can switch via the ViewSwitch and the
  // selection is persisted in localStorage below.
  if (typeof window === "undefined") return "registry";
  try {
    const raw = window.localStorage.getItem(VIEW_STORAGE_KEY);
    if (raw === "registry") return "registry";
    if (raw === "matrix") return "matrix";
  } catch {
    // localStorage unavailable (private mode / SSR snapshot) — fall through.
  }
  return "registry";
}

function navigateToAppDetail(id: string) {
  if (typeof window === "undefined") return;
  window.location.hash = `apps/${encodeURIComponent(id)}`;
}

export function SourceOSTab() {
  const [view, setView] = useState<SourceOSView>(() => readInitialView());
  const [activeSection, setActiveSection] = useState("source_backed");
  const [dockMode, setDockMode] = useState<SourceOSDockMode>("dock");
  const [modules, setModules] = useState<SourceOSModule[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [updateReadiness, setUpdateReadiness] = useState<SourceModuleUpdateReadiness | null>(null);
  const [updateBusy, setUpdateBusy] = useState(false);
  const [runtimeVerifyBusy, setRuntimeVerifyBusy] = useState(false);
  const [runtimeVerifyMessage, setRuntimeVerifyMessage] = useState<string | null>(null);
  const [setupQueueBusy, setSetupQueueBusy] = useState(false);
  const [setupQueueMessage, setSetupQueueMessage] = useState<string | null>(null);
  const [verifierSummary, setVerifierSummary] = useState<RuntimeVerifierSummary | null>(null);
  const [cliSurfaceSummary, setCliSurfaceSummary] = useState<CliSurfaceSummary | null>(null);
  const [cliSurfaceRecords, setCliSurfaceRecords] = useState<SourceModuleCliSurfaceRecord[]>([]);
  const [runnerContracts, setRunnerContracts] = useState<Record<string, RunnerContract>>({});
  // CLI readiness panel state
  const [sourcesReadiness, setSourcesReadiness] = useState<SourcesReadinessPayload | null>(null);
  const [sourcesReadinessLoading, setSourcesReadinessLoading] = useState(false);
  const [cliPanelExpanded, setCliPanelExpanded] = useState(true);
  const [proofPanelExpanded, setProofPanelExpanded] = useState(false);

  const loadModules = async ({ showLoading = true }: { showLoading?: boolean } = {}) => {
    if (showLoading) {
      setLoadState("loading");
    }
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/modules`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) {
        setModules([]);
        setLoadState("unavailable");
        return;
      }
      const payload: unknown = await response.json();
      const next = Array.isArray(payload) ? payload.map(normalizeModule).filter((module): module is SourceOSModule => module != null) : [];
      setModules(next);
      setSelectedId((current) => current ?? next[0]?.id ?? null);
      setLoadState("ready");
    } catch {
      setModules([]);
      setLoadState("unavailable");
    }
  };

  useEffect(() => {
    // The legacy registry view fetches /api/modules + 4 sibling endpoints
    // which can hang on some environments. Defer them until the user opens
    // the Module Registry view so the 60-App Matrix never trips on them.
    if (view !== "registry") return;
    void loadModules();
    void loadUpdateReadiness(false);
    void loadVerifierSummary();
    void loadCliSurfaceSummary();
    void loadSourcesReadiness();
    void loadRunnerContracts();
  }, [view]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(VIEW_STORAGE_KEY, view);
    } catch {
      // Persistence is best-effort; never crash the UI over a storage write.
    }
  }, [view]);

  const loadVerifierSummary = async () => {
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/modules/runtime/verifiers`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) {
        setVerifierSummary(null);
        return;
      }
      setVerifierSummary(normalizeVerifierSummary(await response.json()));
    } catch {
      setVerifierSummary(null);
    }
  };

  const loadCliSurfaceSummary = async () => {
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/modules/runtime/cli-surface`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) {
        setCliSurfaceSummary(null);
        setCliSurfaceRecords([]);
        return;
      }
      const payload = await response.json();
      setCliSurfaceSummary(normalizeCliSurfaceSummary(payload));
      setCliSurfaceRecords(normalizeCliSurfaceRecords(payload));
    } catch {
      setCliSurfaceSummary(null);
      setCliSurfaceRecords([]);
    }
  };

  const loadRunnerContracts = async () => {
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/modules/runtime/runner-contracts`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) {
        setRunnerContracts({});
        return;
      }
      const payload = await response.json() as RunnerContractsPayload;
      const byModuleId: Record<string, RunnerContract> = {};
      if (Array.isArray(payload.contracts)) {
        for (const contract of payload.contracts) {
          if (typeof contract.module_id === "string" && contract.module_id.length > 0) {
            byModuleId[contract.module_id] = contract;
          }
        }
      }
      setRunnerContracts(byModuleId);
    } catch {
      setRunnerContracts({});
    }
  };

  const loadSourcesReadiness = async () => {
    setSourcesReadinessLoading(true);
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/sources/readiness`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) {
        setSourcesReadiness(null);
        return;
      }
      const payload = await response.json() as SourcesReadinessPayload;
      setSourcesReadiness(payload);
    } catch {
      setSourcesReadiness(null);
    } finally {
      setSourcesReadinessLoading(false);
    }
  };

  const loadUpdateReadiness = async (deep: boolean) => {
    setUpdateBusy(true);
    try {
      setUpdateReadiness(await adapters.getModuleUpdateReadiness(deep));
    } finally {
      setUpdateBusy(false);
    }
  };

  const verifyAllRuntimes = async () => {
    setRuntimeVerifyBusy(true);
    setRuntimeVerifyMessage(null);
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/modules/runtime/verify-all`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ actor: "operator" }),
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      setRuntimeVerifyMessage(`${response.ok && batchAccepted(payload) ? "Verify All accepted" : "Verify All blocked"}: ${runtimeBatchSummary(payload, response.statusText)}`);
      await loadModules({ showLoading: false });
      await loadVerifierSummary();
      await loadCliSurfaceSummary();
      await loadRunnerContracts();
    } catch {
      setRuntimeVerifyMessage(`Verify All failed: backend API is unreachable at ${LIVE_BASE_URL}.`);
    } finally {
      setRuntimeVerifyBusy(false);
    }
  };

  const planSetupQueue = async () => {
    setSetupQueueBusy(true);
    setSetupQueueMessage(null);
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/modules/runtime/setup-queue`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ actor: "operator" }),
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      setSetupQueueMessage(`${response.ok && batchAccepted(payload) ? "Setup Queue accepted" : "Setup Queue blocked"}: ${setupQueueSummary(payload, response.statusText)}`);
      await loadModules({ showLoading: false });
      await loadVerifierSummary();
      await loadCliSurfaceSummary();
      await loadRunnerContracts();
    } catch {
      setSetupQueueMessage(`Setup Queue failed: backend API is unreachable at ${LIVE_BASE_URL}.`);
    } finally {
      setSetupQueueBusy(false);
    }
  };

  const visibleModules = useMemo(() => {
    if (activeSection === "home" || activeSection === "source_backed") {
      return modules;
    }
    return modules.filter((module) => module.section === activeSection);
  }, [activeSection, modules]);

  const selectedModule = useMemo(() => {
    const selected = modules.find((module) => module.id === selectedId) ?? null;
    if (selected && (activeSection === "home" || activeSection === "source_backed" || selected.section === activeSection)) {
      return selected;
    }
    return visibleModules[0] ?? null;
  }, [activeSection, selectedId, visibleModules, modules]);

  const selectedUpdateRecord = useMemo(() => {
    return updateReadiness?.records.find((record) => record.module_id === selectedModule?.id) ?? null;
  }, [selectedModule?.id, updateReadiness]);

  const cliSurfaceByModule = useMemo(() => {
    return cliSurfaceRecords.reduce<Record<string, SourceModuleCliSurfaceRecord>>((acc, record) => {
      acc[record.module_id] = record;
      return acc;
    }, {});
  }, [cliSurfaceRecords]);

  const selectedCliSurfaceRecord = selectedModule ? cliSurfaceByModule[selectedModule.id] ?? null : null;

  const handleSectionSelect = (section: string) => {
    setActiveSection(section);
    const firstModule = section === "home" || section === "source_backed"
      ? modules[0]
      : modules.find((module) => module.section === section);
    setSelectedId(firstModule?.id ?? null);
  };

  const counts = useMemo(() => {
    return modules.reduce<Record<string, number>>((acc, module) => {
      acc[module.section] = (acc[module.section] ?? 0) + 1;
      return acc;
    }, {});
  }, [modules]);

  const runtimeCounts = useMemo(() => runtimeCountsFor(modules), [modules]);
  const unclassifiedLaunchKinds = useMemo(() => modules.filter((module) => !module.launchKind || module.launchKind === "unknown").length, [modules]);

  return (
    <div data-testid="source-os-root" className="source-os-shell flex h-full min-h-0 flex-col overflow-hidden rounded border border-border bg-bg">
      {/* ── Header ── */}
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface px-3 py-2">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold text-fg">Hermes3D OS</h1>
          <p className="truncate text-xs text-muted">
            {view === "matrix"
              ? "60-app coverage matrix — backend-driven, no fabricated readiness."
              : `${modules.length} source-backed modules from the local API module registry.`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ViewSwitch view={view} onChange={setView} />
          <DockModeControls mode={dockMode} onChange={setDockMode} />
        </div>
      </div>

      {view === "matrix" ? (
        <div
          data-testid="source-os-matrix-view"
          className={[
            "flex min-h-0 flex-1 flex-col overflow-auto",
            dockMode === "full" ? "h-full" : "",
          ].join(" ")}
        >
          <SixtyAppCoverageMatrix bridgeBaseUrl={LIVE_BASE_URL} onNavigate={navigateToAppDetail} />
        </div>
      ) : (
        <>
          {/* ── Status bars ── */}
          <UpdateReadinessBar readiness={updateReadiness} busy={updateBusy} onDeepCheck={() => void loadUpdateReadiness(true)} />
          <RuntimeReadinessBar
            counts={runtimeCounts}
            total={modules.length}
            verifyBusy={runtimeVerifyBusy}
            setupBusy={setupQueueBusy}
            message={setupQueueMessage ?? runtimeVerifyMessage}
            onVerifyAll={() => void verifyAllRuntimes()}
            onPlanSetupQueue={() => void planSetupQueue()}
            verifierSummary={verifierSummary}
            cliSurfaceSummary={cliSurfaceSummary}
            unclassifiedLaunchKinds={unclassifiedLaunchKinds}
          />

          {/* ── CLI Readiness Panel ── */}
          <CliReadinessPanel
            readiness={sourcesReadiness}
            loading={sourcesReadinessLoading}
            expanded={cliPanelExpanded}
            onToggle={() => setCliPanelExpanded((v) => !v)}
            onRefresh={() => void loadSourcesReadiness()}
            baseUrl={LIVE_BASE_URL}
          />

          {/* ── Proof & Artifact Panel ── */}
          <ProofArtifactPanel
            readiness={sourcesReadiness}
            expanded={proofPanelExpanded}
            onToggle={() => setProofPanelExpanded((v) => !v)}
            baseUrl={LIVE_BASE_URL}
          />

          {/* ── Module registry browser ── */}
          <SecondaryNav activeSection={activeSection} counts={counts} onSelect={handleSectionSelect} />
          <div
            className={[
              "flex min-h-0 flex-1 flex-col overflow-hidden md:flex-row",
              dockMode === "full" ? "h-full" : "",
            ].join(" ")}
          >
            {loadState === "loading" ? (
              <div className="flex flex-1 items-center justify-center text-sm text-muted">Loading Source OS modules from API.</div>
            ) : modules.length === 0 ? (
              <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted">
                Source OS module registry is unavailable from {LIVE_BASE_URL}/api/modules.
              </div>
            ) : (
              <>
                <ModuleList
                  modules={visibleModules}
                  selectedId={selectedModule?.id ?? null}
                  onSelect={setSelectedId}
                  cliSurfaceByModule={cliSurfaceByModule}
                  runnerContractsByModule={runnerContracts}
                />
                <AppDetailPanel
                  module={selectedModule}
                  updateRecord={selectedUpdateRecord}
                  cliSurfaceRecord={selectedCliSurfaceRecord}
                  runnerContract={selectedModule ? (runnerContracts[selectedModule.id] ?? null) : null}
                  onRefresh={() => {
                    void loadModules({ showLoading: false });
                    void loadUpdateReadiness(updateReadiness?.deep ?? false);
                    void loadCliSurfaceSummary();
                    void loadRunnerContracts();
                  }}
                />
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ViewSwitch — toggle between the 60-app matrix and the legacy registry view.
// ─────────────────────────────────────────────────────────────────────────────

function ViewSwitch({ view, onChange }: { view: SourceOSView; onChange: (next: SourceOSView) => void }) {
  return (
    <div
      role="tablist"
      aria-label="Source OS view"
      data-testid="source-os-view-switch"
      className="inline-flex overflow-hidden rounded border border-border bg-bg/40"
    >
      <button
        type="button"
        role="tab"
        aria-selected={view === "matrix"}
        data-testid="source-os-view-matrix"
        onClick={() => onChange("matrix")}
        className={[
          "px-2.5 py-1 text-[11px] transition-colors",
          view === "matrix" ? "bg-accent-blue/20 text-fg" : "text-muted hover:text-fg",
        ].join(" ")}
      >
        60-App Matrix
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={view === "registry"}
        data-testid="source-os-view-registry"
        onClick={() => onChange("registry")}
        className={[
          "px-2.5 py-1 text-[11px] transition-colors",
          view === "registry" ? "bg-accent-blue/20 text-fg" : "text-muted hover:text-fg",
        ].join(" ")}
      >
        Module Registry
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CLI Readiness Panel
// ─────────────────────────────────────────────────────────────────────────────

const CATEGORY_ORDER = ["slicers", "modelers", "print_farm", "firmware", "gen3d"] as const;

function CliReadinessPanel({
  readiness,
  loading,
  expanded,
  onToggle,
  onRefresh,
  baseUrl,
}: {
  readiness: SourcesReadinessPayload | null;
  loading: boolean;
  expanded: boolean;
  onToggle: () => void;
  onRefresh: () => void;
  baseUrl: string;
}) {
  const summary = readiness?.summary;
  return (
    <div className="border-b border-border bg-bg" data-testid="source-cli-readiness-panel">
      {/* Collapsed header row */}
      <div className="flex w-full items-center justify-between gap-2 px-3 py-2 text-xs hover:bg-surface/60">
        <button
          type="button"
          onClick={onToggle}
          className="flex min-w-0 flex-1 flex-wrap items-center gap-2 text-left"
          aria-expanded={expanded}
        >
          <span className="font-semibold text-fg">CLI Readiness</span>
          {summary && (
            <>
              <Metric label="verified CLI" value={summary.verified_agent_cli} tone="green" />
              <Metric label="runner gaps" value={summary.runner_gaps} tone={summary.runner_gaps > 0 ? "amber" : "muted"} />
              <Metric label="candidates" value={summary.candidate_needs_verifier} tone={summary.candidate_needs_verifier > 0 ? "cyan" : "muted"} />
            </>
          )}
          {loading && <span className="text-[11px] text-muted italic">refreshing…</span>}
          {!readiness && !loading && (
            <span className="text-[11px] text-amber-400">backend unavailable — {baseUrl}/api/sources/readiness</span>
          )}
        </button>
        <div className="flex items-center gap-2">
          {readiness?.generated_at_utc && (
            <span className="text-[10px] text-muted" title={readiness.generated_at_utc}>
              proof {readiness.generated_at_utc.slice(0, 10)}
            </span>
          )}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onRefresh(); }}
            disabled={loading}
            className="rounded border border-border px-2 py-0.5 text-[11px] text-fg hover:border-accent-blue/40 disabled:opacity-50"
          >
            {loading ? "Loading" : "Refresh"}
          </button>
          <button
            type="button"
            onClick={onToggle}
            className="rounded border border-transparent px-1 text-[11px] text-muted hover:border-border hover:text-fg"
            aria-label={expanded ? "Collapse CLI readiness panel" : "Expand CLI readiness panel"}
            aria-expanded={expanded}
          >
            {expanded ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {/* Expanded body */}
      {expanded && readiness && (
        <div className="overflow-y-auto px-3 pb-3 pt-1" style={{ maxHeight: "420px" }}>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {CATEGORY_ORDER.map((catId) => {
              const cat = readiness.categories[catId];
              if (!cat) return null;
              return <CategoryCard key={catId} category={cat} />;
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryCard({ category }: { category: CategoryReadiness }) {
  const { verified = 0, detected = 0, source_ready = 0, not_installed = 0, unavailable = 0 } = category.status_counts;
  const allReady = verified + detected;

  return (
    <div className="flex flex-col gap-2 rounded border border-border bg-surface/50 p-2">
      <div className="flex items-center justify-between gap-1">
        <span className="text-[11px] font-semibold text-fg">{category.label}</span>
        <span className="text-[10px] text-muted">{category.total} total</span>
      </div>

      {/* Status mini-bar */}
      <div className="flex flex-wrap gap-1">
        {verified > 0 && <span className="rounded bg-green-900/60 px-1.5 py-0.5 text-[10px] text-green-300">{verified} verified</span>}
        {detected > 0 && <span className="rounded bg-cyan-900/60 px-1.5 py-0.5 text-[10px] text-cyan-200">{detected} detected</span>}
        {source_ready > 0 && <span className="rounded bg-blue-900/50 px-1.5 py-0.5 text-[10px] text-blue-300">{source_ready} src ready</span>}
        {not_installed > 0 && <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] text-muted">{not_installed} not installed</span>}
        {unavailable > 0 && <span className="rounded bg-red-950/50 px-1.5 py-0.5 text-[10px] text-red-400">{unavailable} unavailable</span>}
        {allReady === 0 && <span className="text-[10px] text-amber-400">no verified tools</span>}
      </div>

      {/* Key tools */}
      <div className="flex flex-col gap-1">
        {category.key_tools.map((tool) => (
          <KeyToolRow key={tool.module_id} tool={tool} />
        ))}
      </div>
    </div>
  );
}

function KeyToolRow({ tool }: { tool: KeyToolDetail }) {
  const badgeClass = TOOL_STATUS_BADGE[tool.status] ?? TOOL_STATUS_BADGE.unavailable;
  const label = TOOL_STATUS_LABEL[tool.status] ?? tool.status;
  return (
    <div
      className="flex items-center justify-between gap-1 rounded bg-bg/60 px-1.5 py-1"
      title={tool.next_action ?? tool.path ?? tool.module_id}
    >
      <span className="min-w-0 flex-1 truncate text-[11px] text-fg">{tool.display}</span>
      <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${badgeClass}`}>{label}</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Proof Artifact Panel
// ─────────────────────────────────────────────────────────────────────────────

function ProofArtifactPanel({
  readiness,
  expanded,
  onToggle,
  baseUrl,
}: {
  readiness: SourcesReadinessPayload | null;
  expanded: boolean;
  onToggle: () => void;
  baseUrl: string;
}) {
  return (
    <div className="border-b border-border bg-bg" data-testid="source-proof-panel">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs hover:bg-surface/60"
        aria-expanded={expanded}
      >
        <span className="font-semibold text-fg">Proof Artifacts</span>
        <span className="text-[11px] text-muted">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="overflow-y-auto px-3 pb-3 pt-1" style={{ maxHeight: "320px" }}>
          {/* Artifact browser link */}
          <div className="mb-2 flex flex-wrap gap-2">
            <a
              href={`${baseUrl}/api/artifacts`}
              target="_blank"
              rel="noreferrer"
              className="rounded border border-border px-2 py-1 text-[11px] text-accent-blue hover:border-accent-blue/60 hover:underline"
            >
              Browse all proof artifacts →
            </a>
            <a
              href={`${baseUrl}/api/artifacts?grouped=job`}
              target="_blank"
              rel="noreferrer"
              className="rounded border border-border px-2 py-1 text-[11px] text-accent-blue hover:border-accent-blue/60 hover:underline"
            >
              Grouped by job →
            </a>
          </div>

          {/* Per-category proof file listing */}
          {readiness ? (
            <div className="flex flex-col gap-2">
              <p className="text-[11px] text-muted">Proof files read by /api/sources/readiness:</p>
              {Object.entries(readiness.proof_files).map(([key, path]) => (
                <div key={key} className="flex flex-col gap-0.5 rounded border border-border bg-surface/40 px-2 py-1.5">
                  <span className="text-[11px] font-medium text-fg capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="truncate text-[10px] text-muted font-mono" title={path}>{path}</span>
                </div>
              ))}
              {readiness.generated_at_utc && (
                <p className="text-[10px] text-muted">Generated: {readiness.generated_at_utc}</p>
              )}
              {/* Per-category artifact links */}
              <p className="mt-1 text-[11px] text-muted">Category artifact queries:</p>
              {CATEGORY_ORDER.map((catId) => {
                const cat = readiness.categories[catId];
                if (!cat) return null;
                return (
                  <a
                    key={catId}
                    href={`${baseUrl}/api/artifacts?grouped=job`}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded border border-border px-2 py-1 text-[11px] text-accent-blue hover:border-accent-blue/60 hover:underline"
                  >
                    {cat.label} artifacts →
                  </a>
                );
              })}
            </div>
          ) : (
            <p className="text-[11px] text-muted">
              Proof data unavailable. Backend at {baseUrl} may be offline.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Runtime counts helper
// ─────────────────────────────────────────────────────────────────────────────

function runtimeCountsFor(modules: SourceOSModule[]): RuntimeCounts {
  return modules.reduce<RuntimeCounts>((acc, module) => {
    if (module.runtime.status === "ready") {
      acc.ready += 1;
      if ((module.runtime.kind === "cli" || module.runtime.kind === "python_module_cli") && module.runtime.executed) {
        acc.agent_cli += 1;
      }
    } else if (module.runtime.status === "source_ready") {
      acc.source_ready += 1;
    } else if (module.runtime.status === "setup_required") {
      acc.setup_required += 1;
    } else if (module.runtime.status === "not_installed") {
      acc.not_installed += 1;
    } else {
      acc.blocked += 1;
    }
    return acc;
  }, {
    ready: 0,
    agent_cli: 0,
    source_ready: 0,
    setup_required: 0,
    not_installed: 0,
    blocked: 0,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// RuntimeReadinessBar (unchanged)
// ─────────────────────────────────────────────────────────────────────────────

function RuntimeReadinessBar({
  counts,
  total,
  verifyBusy,
  setupBusy,
  message,
  onVerifyAll,
  onPlanSetupQueue,
  verifierSummary,
  cliSurfaceSummary,
  unclassifiedLaunchKinds,
}: {
  counts: RuntimeCounts;
  total: number;
  verifyBusy: boolean;
  setupBusy: boolean;
  message: string | null;
  onVerifyAll: () => void;
  onPlanSetupQueue: () => void;
  verifierSummary: RuntimeVerifierSummary | null;
  cliSurfaceSummary: CliSurfaceSummary | null;
  unclassifiedLaunchKinds: number;
}) {
  const busy = verifyBusy || setupBusy;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-surface/70 px-3 py-2 text-xs" data-testid="source-runtime-readiness">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-fg">Runtime Readiness</span>
        <Metric label="apps" value={total} />
        <Metric label="runtime ready" value={counts.ready} tone="green" />
        <Metric label="agent CLI" value={counts.agent_cli} tone={counts.agent_cli ? "green" : "muted"} />
        <Metric label="CLI signals" value={cliSurfaceSummary?.candidate_needs_verifier ?? 0} tone={cliSurfaceSummary?.candidate_needs_verifier ? "cyan" : "muted"} />
        <Metric label="no CLI signal" value={cliSurfaceSummary?.no_local_cli_signal ?? 0} tone={cliSurfaceSummary?.no_local_cli_signal ? "amber" : "muted"} />
        <Metric label="source ready" value={counts.source_ready} tone="cyan" />
        <Metric label="setup needed" value={counts.setup_required} tone={counts.setup_required ? "amber" : "muted"} />
        <Metric label="install ready" value={counts.not_installed} tone={counts.not_installed ? "cyan" : "muted"} />
        <Metric label="blocked" value={counts.blocked} tone={counts.blocked ? "amber" : "muted"} />
        <Metric label="verifiers" value={verifierSummary?.enabled_count ?? 0} tone={verifierSummary?.enabled_count ? "green" : "muted"} />
        <Metric label="unclassified" value={unclassifiedLaunchKinds} tone={unclassifiedLaunchKinds ? "amber" : "muted"} />
      </div>
      <div className="flex min-w-0 flex-wrap items-center justify-end gap-2">
        {message && <span className="max-w-[34rem] truncate text-[11px] text-muted" title={message}>{message}</span>}
        <button
          type="button"
          disabled={busy || total === 0}
          onClick={onPlanSetupQueue}
          className="rounded border border-border px-2 py-1 text-[11px] text-fg hover:border-accent-blue/40 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {setupBusy ? "Planning" : "Setup Queue"}
        </button>
        <button
          type="button"
          disabled={busy || total === 0}
          onClick={onVerifyAll}
          className="rounded border border-border px-2 py-1 text-[11px] text-fg hover:border-accent-blue/40 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {verifyBusy ? "Verifying" : "Verify All"}
        </button>
        <span className="text-[11px] text-muted">proof-gated</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Normalizers (unchanged from original)
// ─────────────────────────────────────────────────────────────────────────────

function normalizeVerifierSummary(payload: unknown): RuntimeVerifierSummary | null {
  if (!isRecord(payload)) {
    return null;
  }
  return {
    count: numberValue(payload.count),
    enabled_count: numberValue(payload.enabled_count),
    total_modules: numberValue(payload.total_modules),
    runner_gap: numberValue(payload.runner_gap),
    blocked: numberValue(payload.blocked),
    registered_ids: stringArrayValue(payload.registered_ids),
  };
}

function normalizeCliSurfaceSummary(payload: unknown): CliSurfaceSummary | null {
  if (!isCliSurfaceAudit(payload)) {
    return null;
  }
  return {
    agent_enabled_cli: numberValue(payload.summary.agent_enabled_cli),
    candidate_needs_verifier: numberValue(payload.summary.candidate_needs_verifier),
    no_local_cli_signal: numberValue(payload.summary.no_local_cli_signal),
  };
}

function normalizeCliSurfaceRecords(payload: unknown): SourceModuleCliSurfaceRecord[] {
  if (!isCliSurfaceAudit(payload)) {
    return [];
  }
  return payload.records.filter((record) => record.module_id.length > 0);
}

function isCliSurfaceAudit(value: unknown): value is SourceModuleCliSurfaceAudit {
  return isRecord(value) && isRecord(value.summary) && Array.isArray(value.records);
}

function batchAccepted(payload: unknown): boolean {
  return isRecord(payload) && payload.accepted !== false && payload.status !== "blocked";
}

function runtimeBatchSummary(payload: unknown, fallback: string): string {
  if (!isRecord(payload) || !isRecord(payload.counts)) {
    return fallback || "runtime verifier did not return a usable summary";
  }
  const ready = numberValue(payload.counts.ready);
  const sourceReady = numberValue(payload.counts.source_ready);
  const setupNeeded = numberValue(payload.counts.setup_required);
  const installReady = numberValue(payload.counts.not_installed);
  const blocked = numberValue(payload.counts.blocked);
  const proof = stringValue(payload.proof_event_id);
  return `${ready} runtime ready / ${sourceReady} source ready / ${setupNeeded} setup needed / ${installReady} install ready / ${blocked} blocked${proof ? ` · proof ${proof}` : ""}`;
}

function setupQueueSummary(payload: unknown, fallback: string): string {
  if (!isRecord(payload) || !isRecord(payload.counts)) {
    return fallback || "setup planner did not return a usable summary";
  }
  const runtimeReady = numberValue(payload.counts.runtime_ready);
  const sourceReady = numberValue(payload.counts.source_ready);
  const runnerMissing = numberValue(payload.counts.runner_not_registered);
  const installAvailable = numberValue(payload.counts.source_install_available);
  const repairRequired = numberValue(payload.counts.runtime_repair_required);
  const blocked = numberValue(payload.counts.blocked);
  const proof = stringValue(payload.proof_event_id);
  return `${runtimeReady} runtime ready / ${sourceReady} source ready / ${runnerMissing} need runners / ${installAvailable} install ready / ${repairRequired} repair / ${blocked} blocked${proof ? ` · proof ${proof}` : ""}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// UpdateReadinessBar (unchanged)
// ─────────────────────────────────────────────────────────────────────────────

function UpdateReadinessBar({
  readiness,
  busy,
  onDeepCheck,
}: {
  readiness: SourceModuleUpdateReadiness | null;
  busy: boolean;
  onDeepCheck: () => void;
}) {
  const loaded = readiness != null && readiness.status !== "unavailable";
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-bg px-3 py-2 text-xs" data-testid="source-update-readiness">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-fg">App Update Readiness</span>
        <Metric label="apps" value={loaded ? readiness.count : 0} />
        <Metric label="ready" value={loaded ? readiness.ready_for_update_check : 0} tone="green" />
        <Metric label="blocked" value={loaded ? readiness.blocked : 0} tone={readiness?.blocked ? "amber" : "muted"} />
        <Metric label="dirty" value={loaded ? readiness.dirty : 0} tone={readiness?.dirty ? "amber" : "muted"} />
        <Metric label="cached behind" value={loaded ? readiness.outdated_cached : 0} tone={readiness?.outdated_cached ? "cyan" : "muted"} />
      </div>
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
        <span>{readiness?.deep ? "deep check complete" : "lightweight check"}</span>
        <button
          type="button"
          disabled={busy}
          onClick={onDeepCheck}
          className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Checking" : "Deep Check"}
        </button>
        <span className="max-w-[34rem] truncate" title={readiness?.strategy ?? "Readiness has not loaded yet."}>
          updates require backup + proof + rollback
        </span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Metric badge (unchanged)
// ─────────────────────────────────────────────────────────────────────────────

function Metric({ label, value, tone = "muted" }: { label: string; value: number; tone?: "green" | "amber" | "cyan" | "muted" }) {
  const toneClass = {
    green: "bg-green-950/70 text-green-300",
    amber: "bg-amber-950/70 text-amber-200",
    cyan: "bg-cyan-950/70 text-cyan-200",
    muted: "bg-surface2 text-muted",
  }[tone];
  return <span className={`rounded px-2 py-1 text-[10px] uppercase ${toneClass}`}>{value} {label}</span>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Module normalizers (unchanged from original)
// ─────────────────────────────────────────────────────────────────────────────

function normalizeModule(raw: RawModule): SourceOSModule | null {
  const id = stringValue(raw.id);
  const display = stringValue(raw.display ?? raw.display_name);
  const section = stringValue(raw.section);
  if (!id || !display || !section) {
    return null;
  }

  const installState = installStateValue(raw.installState ?? raw.install_state);
  return {
    id,
    display,
    priority: stringValue(raw.priority) || "unknown",
    license: stringValue(raw.license) || "unknown",
    section,
    repo: nullableString(raw.repo ?? raw.repo_url),
    localPath: nullableString(raw.localPath ?? raw.local_path),
    installState,
    installProgress: numberValue(raw.installProgress ?? raw.install_progress),
    detectedVersion: nullableString(raw.detectedVersion ?? raw.detected_version),
    health: healthValue(raw.health),
    launchKind: launchKindValue(raw.launchKind ?? raw.launch_kind),
    bridgeTasks: bridgeTasksValue(raw.bridgeTasks ?? raw.bridge_tasks, id),
    proofs: proofBundlesValue(raw.proofs),
    dispatchGates: dispatchGatesValue(raw.dispatchGates ?? raw.dispatch_gates),
    providers: providersValue(raw.providers),
    activeProvider: nullableString(raw.activeProvider ?? raw.active_provider),
    runtime: runtimeValue(raw.runtime, installState, nullableString(raw.localPath ?? raw.local_path), launchKindValue(raw.launchKind ?? raw.launch_kind)),
  };
}

function runtimeValue(value: unknown, installState: InstallState, localPath: string | null, launchKind: LaunchKind | null): SourceModuleRuntime {
  if (isRecord(value)) {
    return {
      status: stringValue(value.status) || "blocked",
      label: stringValue(value.label) || "Runtime blocked",
      kind: nullableString(value.kind),
      verifier: nullableString(value.verifier),
      path: nullableString(value.path),
      detected: Boolean(value.detected),
      executed: Boolean(value.executed),
      return_code: typeof value.return_code === "number" ? value.return_code : null,
      capabilities: stringArrayValue(value.capabilities),
      reason: nullableString(value.reason),
      setup_steps: stringArrayValue(value.setup_steps),
      proof_source: nullableString(value.proof_source),
      output_head: stringArrayValue(value.output_head),
    };
  }
  const installed = installState === "installed" || installState === "detected" || installState === "healthy";
  return {
    status: installed ? "source_ready" : installState === "source_available" ? "not_installed" : "blocked",
    label: installed ? "Source ready" : installState === "source_available" ? "Install ready" : "Source blocked",
    kind: launchKind,
    verifier: "source checkout",
    path: localPath,
    detected: installed,
    executed: false,
    return_code: null,
    capabilities: [],
    reason: installed ? "Source checkout is present; runtime verifier has not been registered yet." : null,
    setup_steps: [],
    proof_source: null,
    output_head: [],
  };
}

function proofBundlesValue(value: unknown): ProofBundle[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => {
    if (!isRecord(item)) {
      return null;
    }
    const id = stringValue(item.id);
    const sha256 = stringValue(item.sha256);
    const branch = stringValue(item.branch);
    const commit = stringValue(item.commit);
    const ts_utc = stringValue(item.ts_utc);
    const verdict = proofVerdictValue(item.verdict);
    if (!id || !sha256 || !branch || !commit || !ts_utc || !verdict) {
      return null;
    }
    return {
      id,
      sha256,
      branch,
      commit,
      ts_utc,
      files_count: numberValue(item.files_count),
      size_bytes: numberValue(item.size_bytes),
      verdict,
      gates: gateResultsValue(item.gates),
    } satisfies ProofBundle;
  }).filter((proof): proof is ProofBundle => proof != null);
}

function gateResultsValue(value: unknown): GateResult[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => {
    if (!isRecord(item)) {
      return null;
    }
    const layer = stringValue(item.layer);
    const verdict = gateVerdictValue(item.verdict);
    if (!layer || !verdict) {
      return null;
    }
    return {
      layer,
      verdict,
      duration_s: typeof item.duration_s === "number" ? item.duration_s : null,
    } satisfies GateResult;
  }).filter((gate): gate is GateResult => gate != null);
}

function providersValue(value: unknown): SourceOSProvider[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => {
    if (!isRecord(item)) {
      return null;
    }
    const id = stringValue(item.id);
    const display = stringValue(item.display ?? item.display_name);
    if (!id || !display) {
      return null;
    }
    return {
      id,
      moduleId: stringValue(item.moduleId ?? item.module_id),
      display,
      kind: stringValue(item.kind ?? item.provider_kind),
      repo: nullableString(item.repo ?? item.repo_url),
      installCommand: nullableString(item.installCommand ?? item.install_command),
      verifyCommands: stringArrayValue(item.verifyCommands ?? item.verify_commands),
      capabilities: stringArrayValue(item.capabilities),
      license: nullableString(item.license),
      state: stringValue(item.state) || "unknown",
      notes: nullableString(item.notes),
    };
  }).filter((provider): provider is SourceOSProvider => provider != null);
}

function dispatchGatesValue(value: unknown): SourceOSModule["dispatchGates"] {
  const parsed = typeof value === "string" ? parseJson(value) : value;
  if (!Array.isArray(parsed)) {
    return [];
  }
  return parsed.map((item) => {
    if (!isRecord(item)) {
      return null;
    }
    const id = stringValue(item.id);
    if (!id) {
      return null;
    }
    return {
      id,
      required_approvals: typeof item.required_approvals === "number" ? item.required_approvals : 0,
      current_approver: nullableString(item.current_approver),
      status: dispatchGateStatusValue(item.status),
    };
  }).filter((gate): gate is SourceOSModule["dispatchGates"][number] => gate != null);
}

function bridgeTasksValue(value: unknown, moduleId: string): BridgeTask[] {
  const parsed = typeof value === "string" ? parseJson(value) : value;
  const items = Array.isArray(parsed) ? parsed : [];
  return items.map((item, index) => {
    if (typeof item === "string") {
      return { id: `${moduleId}::${item}`, name: item, status: "pending", last_run_at: null, last_run_log: null, duration_ms: null } satisfies BridgeTask;
    }
    if (isRecord(item)) {
      const name = stringValue(item.name) || `Task ${index + 1}`;
      return {
        id: stringValue(item.id) || `${moduleId}::${name}`,
        name,
        status: bridgeStatusValue(item.status),
        last_run_at: nullableString(item.last_run_at),
        last_run_log: nullableString(item.last_result ?? item.last_run_log),
        duration_ms: typeof item.duration_ms === "number" ? item.duration_ms : null,
      } satisfies BridgeTask;
    }
    return null;
  }).filter((task): task is BridgeTask => task != null);
}

function parseJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return [];
  }
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function nullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function stringArrayValue(value: unknown): string[] {
  const parsed = typeof value === "string" ? parseJson(value) : value;
  return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [];
}

function installStateValue(value: unknown): InstallState {
  const states: InstallState[] = ["unavailable", "source_available", "downloading", "installing", "installed", "detected", "healthy", "degraded", "failed", "rollback_available"];
  return typeof value === "string" && states.includes(value as InstallState) ? value as InstallState : "unavailable";
}

function healthValue(value: unknown): SourceOSModule["health"] {
  return value === "healthy" || value === "degraded" || value === "failed" ? value : "unknown";
}

function launchKindValue(value: unknown): LaunchKind | null {
  return typeof value === "string" && value.length > 0 ? value as LaunchKind : null;
}

function bridgeStatusValue(value: unknown): BridgeTask["status"] {
  return value === "running" || value === "pass" || value === "fail" || value === "skipped" ? value : "pending";
}

function dispatchGateStatusValue(value: unknown): DispatchGateStatus {
  const statuses: DispatchGateStatus[] = ["locked", "pending", "approved", "rejected", "unknown", "not_configured"];
  return typeof value === "string" && statuses.includes(value as DispatchGateStatus) ? value as DispatchGateStatus : "unknown";
}

function proofVerdictValue(value: unknown): ProofVerdict | null {
  const verdicts: ProofVerdict[] = ["verified", "pending", "failed"];
  return typeof value === "string" && verdicts.includes(value as ProofVerdict) ? value as ProofVerdict : null;
}

function gateVerdictValue(value: unknown): GateVerdict | null {
  const verdicts: GateVerdict[] = ["pass", "fail", "skip", "pending"];
  return typeof value === "string" && verdicts.includes(value as GateVerdict) ? value as GateVerdict : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
