import type { InstallState, SourceModuleCliSurfaceRecord, SourceOSModule } from "../../types/source-os";

type RunnerContract = {
  module_id: string;
  runner_status: string;
  required_verifier_family: string;
  safe_actions: string[];
  acceptance_gate: string;
  blocked_reason: string | null;
};
import { ResizablePane } from "../layout/ResizablePane";

const INSTALL_BADGE_CLASS: Record<InstallState, string> = {
  unavailable: "bg-surface2 text-muted",
  source_available: "bg-blue-900/50 text-blue-300",
  downloading: "bg-blue-700/60 text-blue-200 animate-pulse",
  installing: "bg-yellow-700/60 text-yellow-200 animate-pulse",
  installed: "bg-green-900/50 text-green-400",
  detected: "bg-green-700/60 text-green-300",
  healthy: "bg-green-600/60 text-green-200",
  degraded: "bg-amber-700/60 text-amber-200",
  failed: "bg-red-800/60 text-red-300",
  rollback_available: "bg-orange-800/60 text-orange-300",
};

const HEALTH_BADGE_CLASS: Record<SourceOSModule["health"], string> = {
  unknown: "bg-surface2 text-muted",
  healthy: "bg-green-600/60 text-green-200",
  degraded: "bg-amber-700/60 text-amber-200",
  failed: "bg-red-800/60 text-red-300",
};

const RUNTIME_BADGE_CLASS: Record<string, string> = {
  ready: "bg-green-600/60 text-green-200",
  source_ready: "bg-cyan-900/60 text-cyan-200",
  setup_required: "bg-amber-800/60 text-amber-200",
  not_installed: "bg-blue-900/50 text-blue-300",
  blocked: "bg-red-900/50 text-red-300",
};

// Runner family badge styles — keyed on runner_status from /api/modules/runtime/runner-contracts
const RUNNER_STATUS_BADGE_CLASS: Record<string, string> = {
  agent_cli_ready: "bg-green-900/80 text-green-200",
  readonly_api_ready: "bg-cyan-900/70 text-cyan-200",
  metadata_ready_needs_runner: "bg-blue-900/60 text-blue-300",
  launcher_metadata_only: "bg-blue-900/50 text-blue-300",
  runtime_repair_required: "bg-amber-900/70 text-amber-200",
  npm_package_runner_gap: "bg-amber-900/60 text-amber-300",
  desktop_app_runner_gap: "bg-surface2 text-muted",
  gpu_worker_runner_gap: "bg-purple-950/70 text-purple-300",
  source_reference_only: "bg-surface2 text-muted",
  blocked: "bg-red-950/60 text-red-400",
  metadata_only: "bg-surface2 text-muted",
};

const RUNNER_STATUS_LABEL: Record<string, string> = {
  agent_cli_ready: "Agent CLI",
  readonly_api_ready: "Read-only API",
  metadata_ready_needs_runner: "Needs Runner",
  launcher_metadata_only: "Launcher Only",
  runtime_repair_required: "Repair Needed",
  npm_package_runner_gap: "npm Gap",
  desktop_app_runner_gap: "Desktop Gap",
  gpu_worker_runner_gap: "GPU Gap",
  source_reference_only: "Source Ref",
  blocked: "Blocked",
  metadata_only: "Metadata Only",
};

const CLI_BADGE_CLASS: Record<string, string> = {
  enabled_agent_cli: "bg-green-950/80 text-green-200",
  cli_candidate_needs_verifier: "bg-cyan-950/80 text-cyan-200",
  documentation_cli_signal_needs_verifier: "bg-cyan-950/80 text-cyan-200",
  service_or_setup_candidate_needs_verifier: "bg-cyan-950/80 text-cyan-200",
  launcher_only_not_cli: "bg-surface2 text-muted",
  no_local_cli_signal: "bg-amber-950/70 text-amber-200",
};

export function ModuleList({
  modules,
  selectedId,
  onSelect,
  cliSurfaceByModule,
  runnerContractsByModule,
}: {
  modules: SourceOSModule[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  cliSurfaceByModule?: Record<string, SourceModuleCliSurfaceRecord>;
  runnerContractsByModule?: Record<string, RunnerContract>;
}) {
  const sections = modules.reduce<Record<string, SourceOSModule[]>>((acc, module) => {
    acc[module.section] = [...(acc[module.section] ?? []), module];
    return acc;
  }, {});

  return (
    <ResizablePane
      storageKey="h3d.sourceOs.moduleRail.width"
      defaultWidth={330}
      minWidth={220}
      maxWidth={620}
      label="Source OS project list"
      role="complementary"
      ariaLabel="Source OS project list"
      dataTestId="source-module-rail"
      className="max-h-64 w-full shrink-0 overflow-auto border-b border-border bg-surface/70 md:max-h-none md:w-[var(--pane-width)] md:border-b-0 md:border-r"
    >
      <aside aria-label="Source OS modules">
        {Object.entries(sections).map(([section, sectionModules]) => (
          <div key={section} className="border-b border-border/50">
            <div className="sticky top-0 z-10 bg-surface px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-muted">
              {section}
            </div>
            <ul className="flex flex-col gap-0.5 p-1.5">
              {sectionModules.map((module) => {
                const selected = module.id === selectedId;
                const cliSurface = cliSurfaceByModule?.[module.id] ?? null;
                const runnerContract = runnerContractsByModule?.[module.id] ?? null;
                return (
                  <li key={module.id}>
                    <button
                      type="button"
                      onClick={() => onSelect(module.id)}
                      className={[
                        "grid w-full grid-cols-[minmax(0,1fr)] gap-1 rounded border-l-2 px-2 py-1.5 text-left text-xs",
                        selected
                          ? "bg-accent-blue/20 border-accent-blue"
                          : "border-transparent hover:bg-surface2/50",
                      ].join(" ")}
                    >
                      <span className="min-w-0 truncate text-fg">{module.display}</span>
                      <span className="flex min-w-0 flex-wrap items-center gap-1">
                        {cliSurface && <Badge label={cliBadgeLabel(cliSurface)} className={cliBadgeClass(cliSurface)} />}
                        <Badge label={module.installState} className={INSTALL_BADGE_CLASS[module.installState]} />
                        <Badge label={runtimeBadgeLabel(module.runtime.status)} className={RUNTIME_BADGE_CLASS[module.runtime.status] ?? HEALTH_BADGE_CLASS[module.health]} />
                        {runnerContract && (
                          <Badge
                            label={RUNNER_STATUS_LABEL[runnerContract.runner_status] ?? runnerContract.runner_status}
                            className={RUNNER_STATUS_BADGE_CLASS[runnerContract.runner_status] ?? "bg-surface2 text-muted"}
                          />
                        )}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </aside>
    </ResizablePane>
  );
}

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span className={`rounded px-1.5 py-0.5 text-[9px] font-medium uppercase ${className}`}>
      {label.replaceAll("_", " ")}
    </span>
  );
}

function runtimeBadgeLabel(status: string): string {
  if (status === "source_ready") return "source";
  if (status === "setup_required") return "setup";
  if (status === "not_installed") return "install";
  return status;
}

function cliBadgeLabel(record: SourceModuleCliSurfaceRecord): string {
  if (record.agent_enabled) return "Agent CLI";
  if (record.cli_surface_status.includes("candidate") || record.cli_surface_status.includes("signal")) return "CLI signal";
  if (record.cli_surface_status === "launcher_only_not_cli") return "Launcher";
  if (record.cli_surface_status === "no_local_cli_signal") return "No CLI";
  if (record.agent_execution_tier === "package_or_import_ready") return "Pkg/API";
  if (record.agent_execution_tier === "service_api_ready") return "API";
  return "Source";
}

function cliBadgeClass(record: SourceModuleCliSurfaceRecord): string {
  if (record.agent_execution_tier === "package_or_import_ready" || record.agent_execution_tier === "service_api_ready") {
    return "bg-blue-950/70 text-blue-200";
  }
  if (record.cli_surface_status.endsWith("_not_cli")) {
    return "bg-surface2 text-muted";
  }
  return CLI_BADGE_CLASS[record.cli_surface_status] ?? "bg-surface2 text-muted";
}
