import { useEffect, useMemo, useState } from "react";
import { adapters } from "../api/adapters";
import { AppDetailPanel } from "../components/source-os/AppDetailPanel";
import { DockModeControls, type SourceOSDockMode } from "../components/source-os/DockModeControls";
import { ModuleList } from "../components/source-os/ModuleList";
import { SecondaryNav } from "../components/source-os/SecondaryNav";
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

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

export function SourceOSTab() {
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
    void loadModules();
    void loadUpdateReadiness(false);
    void loadVerifierSummary();
    void loadCliSurfaceSummary();
  }, []);

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
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface px-3 py-2">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold text-fg">Hermes3D OS</h1>
          <p className="truncate text-xs text-muted">
            {modules.length} source-backed modules from the local API module registry.
          </p>
        </div>
        <DockModeControls mode={dockMode} onChange={setDockMode} />
      </div>
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
            />
            <AppDetailPanel
              module={selectedModule}
              updateRecord={selectedUpdateRecord}
              cliSurfaceRecord={selectedCliSurfaceRecord}
              onRefresh={() => {
                void loadModules({ showLoading: false });
                void loadUpdateReadiness(updateReadiness?.deep ?? false);
                void loadCliSurfaceSummary();
              }}
            />
          </>
        )}
      </div>
    </div>
  );
}

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

function Metric({ label, value, tone = "muted" }: { label: string; value: number; tone?: "green" | "amber" | "cyan" | "muted" }) {
  const toneClass = {
    green: "bg-green-950/70 text-green-300",
    amber: "bg-amber-950/70 text-amber-200",
    cyan: "bg-cyan-950/70 text-cyan-200",
    muted: "bg-surface2 text-muted",
  }[tone];
  return <span className={`rounded px-2 py-1 text-[10px] uppercase ${toneClass}`}>{value} {label}</span>;
}

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
