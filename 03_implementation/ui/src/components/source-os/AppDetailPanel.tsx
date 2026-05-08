import { Copy, ExternalLink, RotateCcw, Settings, Terminal, Wrench } from "lucide-react";
import { useState } from "react";
import { BridgeTasks } from "./BridgeTasks";
import { CompilerProofSection } from "./CompilerProofSection";
import { DispatchGateSection } from "./DispatchGateSection";
import type { InstallState, SourceModuleCliSurfaceRecord, SourceModuleUpdateRecord, SourceOSModule } from "../../types/source-os";

type RunnerContract = {
  module_id: string;
  runner_status: string;
  required_verifier_family: string;
  safe_actions: string[];
  acceptance_gate: string;
  blocked_reason: string | null;
};

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const INSTALLED_STATES: InstallState[] = ["installed", "healthy", "detected"];

const ACTIONS = [
  "Install",
  "Verify",
  "Backup",
  "Check Update",
  "Update",
  "Launch",
  "Stop",
  "Setup",
  "Start Runner",
  "Bridge",
  "Repo",
  "Settings",
  "Logs",
  "Proof",
  "Rollback",
] as const;

export function AppDetailPanel({
  module,
  updateRecord,
  cliSurfaceRecord,
  runnerContract,
  onRefresh,
}: {
  module: SourceOSModule | null;
  updateRecord?: SourceModuleUpdateRecord | null;
  cliSurfaceRecord?: SourceModuleCliSurfaceRecord | null;
  runnerContract?: RunnerContract | null;
  onRefresh?: () => void;
}) {
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  if (!module) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-muted">
        Select a module
      </div>
    );
  }

  const dispatchDisabled = module.dispatchGates.length > 0 && !INSTALLED_STATES.includes(module.installState);
  const installLog = actionMessage ? [actionMessage] : [];
  const activeProvider = module.providers.find((provider) => provider.id === module.activeProvider) ?? module.providers[0] ?? null;

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-auto bg-bg">
      <header className="border-b border-border bg-surface p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-fg">{module.display}</h2>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Pill label={module.priority} tone="blue" />
              <Pill label={module.license} tone="muted" />
              <Pill label={module.installState} tone={module.installState === "unavailable" ? "muted" : "green"} />
              <Pill label={module.detectedVersion ?? "-"} tone="cyan" />
              <Pill label={runtimeLabel(module.runtime.status)} tone={runtimeTone(module.runtime.status)} />
              {runnerContract && (
                <Pill
                  label={`runner: ${runnerContract.runner_status.replaceAll("_", " ")}`}
                  tone={runnerContractTone(runnerContract.runner_status)}
                />
              )}
            </div>
          </div>
          <div className="flex flex-wrap justify-end gap-1.5">
            {ACTIONS.map((action) => (
              <ActionButton key={action} action={action} module={module} updateRecord={updateRecord ?? null} onResult={setActionMessage} onRefresh={onRefresh} />
            ))}
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-3 p-4 xl:grid-cols-2">
        <InfoBox title="Source">
          <Field label="Repository" value={module.repo ?? "verification required"} mono action={<CopyButton value={module.repo ?? ""} />} />
          <Field label="Launch Kind" value={module.launchKind ?? "not configured"} />
          <Field label="Local Checkout" value={module.localPath ?? "not installed"} mono />
          <Field label="Detected Version" value={module.detectedVersion ?? "not detected"} />
          <Field label="Registry Section" value={module.section} />
        </InfoBox>

        <InfoBox title="Install">
          <Field label="Install State" value={module.installState.replaceAll("_", " ")} />
          <Field label="Runtime" value={module.runtime.label} />
          <Field label="Verifier" value={module.runtime.verifier ?? "not registered"} />
          <Field label="Runtime Path" value={module.runtime.path ?? "not configured"} mono />
          <Field label="Proof Source" value={module.runtime.proof_source ?? "verify to record proof"} mono />
          <Field label="API Source" value={`${LIVE_BASE_URL}/api/modules/${module.id}`} mono />
          <div>
            <div className="mb-1 flex justify-between text-[10px] uppercase tracking-wide text-muted">
              <span>Progress</span>
              <span>{module.installProgress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface2">
              <div className="h-full rounded-full bg-accent-blue" style={{ width: `${module.installProgress}%` }} />
            </div>
          </div>
          <div className="rounded bg-bg/60 p-2 font-mono text-[10px] text-muted">
            {(installLog.length > 0 ? installLog : ["No install log endpoint is exposed; only action responses are shown here."]).map((line) => (
              <div key={line}>{line}</div>
            ))}
          </div>
          {module.runtime.setup_steps.length > 0 && (
            <div className="rounded border border-border/70 bg-bg/40 p-2 text-[11px] leading-relaxed text-muted">
              {module.runtime.setup_steps.slice(0, 4).map((step) => (
                <div key={step}>- {step}</div>
              ))}
            </div>
          )}
        </InfoBox>

        <InfoBox title="Update Readiness">
          {updateRecord ? (
            <>
              <Field label="Check State" value={updateRecord.source_update_supported ? "ready" : "blocked"} />
              <Field label="Deep Check" value={updateRecord.deep_checked ? "complete" : "not run"} />
              <Field label="Action" value={updateRecord.update_action.replaceAll("_", " ")} />
              <Field label="Current Ref" value={updateRecord.current.exact_tag ?? updateRecord.current.branch ?? updateRecord.current.commit ?? "run deep check"} mono />
              <Field label="Behind" value={updateRecord.cached_behind_count == null ? "not checked" : String(updateRecord.cached_behind_count)} />
              <Field label="Backup" value={updateRecord.latest_backup?.backup_id ?? "none recorded"} mono />
              <Field label="Remote Check" value={updateRecord.latest_check ? `${updateRecord.latest_check.status} · ${shortHash(updateRecord.latest_check.remote_commit)}` : "not run"} mono />
              <div className="text-[11px] leading-relaxed text-muted">{updateRecord.reason ?? updateRecord.safety}</div>
            </>
          ) : (
            <div className="text-[11px] leading-relaxed text-muted">
              Update readiness has not loaded for this source module yet.
            </div>
          )}
        </InfoBox>

        <InfoBox title="Hermes Agent CLI">
          {cliSurfaceRecord ? (
            <>
              <Field label="Agent Use" value={cliSurfaceRecord.agent_enabled ? "enabled by verified CLI" : "detected; verifier required"} />
              <Field label="CLI Surface" value={cliSurfaceLabel(cliSurfaceRecord)} />
              <Field label="Exec Tier" value={cliSurfaceRecord.agent_execution_tier.replaceAll("_", " ")} />
              <Field label="Verifier" value={cliSurfaceRecord.verifier ?? "not registered"} />
              <Field label="Proof Gate" value={cliSurfaceRecord.proof_gate_version ?? "candidate only"} mono />
              <Field label="Runner Path" value={cliSurfaceRecord.path ?? "not configured"} mono />
              <div className="rounded border border-border/70 bg-bg/40 p-2 text-[11px] leading-relaxed text-muted">
                {cliSurfaceRecord.source_signals.length > 0 ? (
                  cliSurfaceRecord.source_signals.slice(0, 4).map((signal) => (
                    <div key={`${signal.kind}-${signal.name}-${signal.command}`} className="truncate" title={`${signal.source}: ${signal.command}`}>
                      - {signal.kind.replaceAll("_", " ")} · {signal.name}: {signal.command}
                    </div>
                  ))
                ) : (
                  <div>No local CLI/service command signal was found in the shallow source audit.</div>
                )}
              </div>
              <div className="text-[11px] leading-relaxed text-muted">{cliSurfaceRecord.next_action}</div>
            </>
          ) : (
            <div className="text-[11px] leading-relaxed text-muted">
              CLI surface proof has not loaded yet. The backend endpoint is {LIVE_BASE_URL}/api/modules/runtime/cli-surface.
            </div>
          )}
        </InfoBox>

        {runnerContract && (
          <InfoBox title="Runner Contract">
            <Field label="Runner Status" value={runnerContract.runner_status.replaceAll("_", " ")} />
            <Field label="Verifier Family" value={runnerContract.required_verifier_family.replaceAll("_", " ")} />
            <Field label="Safe Actions" value={runnerContract.safe_actions.join(", ") || "none"} />
            {runnerContract.blocked_reason && (
              <div className="text-[11px] leading-relaxed text-amber-300">{runnerContract.blocked_reason}</div>
            )}
            <div className="rounded border border-border/70 bg-bg/40 p-2 text-[11px] leading-relaxed text-muted">
              {runnerContract.acceptance_gate}
            </div>
          </InfoBox>
        )}

        {module.providers.length > 0 && (
          <InfoBox title="Provider">
            <ProviderSelector module={module} activeProvider={activeProvider} onResult={setActionMessage} onRefresh={onRefresh} />
            {activeProvider && (
              <>
                <Field label="Active" value={activeProvider.display} />
                <Field label="State" value={activeProvider.state} />
                <Field label="Install" value={activeProvider.installCommand ?? "manual validation required"} mono />
                <Field label="Repo" value={activeProvider.repo ?? "no repository URL"} mono />
                <div className="text-[11px] leading-relaxed text-muted">{activeProvider.notes ?? "No provider notes returned."}</div>
                <div className="flex flex-wrap gap-1">
                  {activeProvider.capabilities.map((capability) => (
                    <Pill key={capability} label={capability} tone="muted" />
                  ))}
                </div>
              </>
            )}
          </InfoBox>
        )}

        <BridgeTasks tasks={module.bridgeTasks} moduleId={module.id} onRun={(taskId) => runBridgeTask(module.id, taskId, setActionMessage)} />
        <CompilerProofSection proofs={module.proofs} />
        <div className="xl:col-span-2">
          <DispatchGateSection gates={module.dispatchGates} disabled={dispatchDisabled} />
        </div>
      </div>
    </section>
  );
}

function ProviderSelector({
  module,
  activeProvider,
  onResult,
  onRefresh,
}: {
  module: SourceOSModule;
  activeProvider: SourceOSModule["providers"][number] | null;
  onResult: (message: string) => void;
  onRefresh?: () => void;
}) {
  return (
    <div className="grid grid-cols-[110px_1fr_auto] items-center gap-2 text-xs">
      <span className="text-[10px] uppercase tracking-wide text-muted">Switch</span>
      <select
        value={activeProvider?.id ?? ""}
        onChange={(event) => void switchProvider(module.id, event.target.value, onResult, onRefresh)}
        className="min-w-0 rounded border border-border bg-bg px-2 py-1 text-fg"
      >
        {module.providers.map((provider) => (
          <option key={provider.id} value={provider.id}>{provider.display}</option>
        ))}
      </select>
      <button
        type="button"
        disabled={!activeProvider}
        onClick={() => activeProvider && void validateProvider(module.id, activeProvider.id, onResult)}
        className="rounded border border-border px-2 py-1 text-[11px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
      >
        Validate
      </button>
    </div>
  );
}

async function switchProvider(
  moduleId: string,
  providerId: string,
  onResult: (message: string) => void,
  onRefresh?: () => void,
) {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/modules/${encodeURIComponent(moduleId)}/provider`, {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ provider_id: providerId }),
      cache: "no-store",
    });
    const text = await response.text();
    const payload = parseActionPayload(text);
    const accepted = response.ok && actionAccepted(payload);
    onResult(`Provider ${accepted ? "selected" : "blocked"}: ${actionSummary(payload, text || response.statusText)}`);
    onRefresh?.();
  } catch {
    onResult(`Provider switch failed: backend API is unreachable at ${LIVE_BASE_URL}.`);
  }
}

async function validateProvider(moduleId: string, providerId: string, onResult: (message: string) => void) {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/modules/${encodeURIComponent(moduleId)}/providers/${encodeURIComponent(providerId)}/validate`, {
      method: "POST",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const text = await response.text();
    const payload = parseActionPayload(text);
    const accepted = response.ok && actionAccepted(payload);
    onResult(`Provider validation ${accepted ? "accepted" : "blocked"}: ${actionSummary(payload, text || response.statusText)}`);
  } catch {
    onResult(`Provider validation failed: backend API is unreachable at ${LIVE_BASE_URL}.`);
  }
}

function ActionButton({
  action,
  module,
  updateRecord,
  onResult,
  onRefresh,
}: {
  action: (typeof ACTIONS)[number];
  module: SourceOSModule;
  updateRecord: SourceModuleUpdateRecord | null;
  onResult: (message: string) => void;
  onRefresh?: () => void;
}) {
  const installed = INSTALLED_STATES.includes(module.installState);
  const disabledReason = getDisabledReason(action, module, installed, updateRecord);
  const label = actionLabel(action);
  const Icon = action === "Repo"
    ? ExternalLink
    : action === "Settings"
      ? Settings
      : action === "Logs"
        ? Terminal
        : action === "Rollback"
          ? RotateCcw
          : Wrench;

  return (
    <button
      type="button"
      disabled={disabledReason != null}
      title={disabledReason ?? `${label} ${module.display}`}
      onClick={() => runAction(action, module, onResult, onRefresh)}
      className="inline-flex items-center gap-1.5 rounded border border-border bg-surface2/70 px-2.5 py-1 text-[11px] text-fg hover:border-accent-blue/40 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <Icon size={12} />
      {label}
    </button>
  );
}

function actionLabel(action: (typeof ACTIONS)[number]): string {
  return action === "Setup" ? "Setup Plan" : action;
}

function getDisabledReason(
  action: (typeof ACTIONS)[number],
  module: SourceOSModule,
  installed: boolean,
  updateRecord: SourceModuleUpdateRecord | null,
): string | null {
  if (module.installState === "unavailable" && action !== "Repo" && action !== "Proof") {
    return "Source reference is unavailable for direct install";
  }
  if (action === "Install" && module.installState !== "source_available") {
    return "Install is only available from source available state";
  }
  if (action === "Verify" && module.installState === "unavailable") {
    return "A verified source or runtime path is required before verification.";
  }
  if ((action === "Launch" || action === "Stop" || action === "Update") && !installed) {
    return "Install first to launch";
  }
  if (action === "Start Runner" && !installed) {
    return "Install or source-ready checkout is required before starting a service runner.";
  }
  if (action === "Start Runner" && !moduleHasServiceRunner(module)) {
    return "No supervised local service runner is registered for this module.";
  }
  if (action === "Launch" && !moduleHasLaunchBridge(module)) {
    return "No real launch/stop bridge is configured for this module";
  }
  if (action === "Stop" && !moduleHasLaunchBridge(module) && !moduleHasServiceRunner(module)) {
    return "No real launch/stop bridge is configured for this module";
  }
  if (action === "Backup") {
    if (!updateRecord?.git_ready) {
      return updateRecord?.reason ?? "Backup requires a local git source checkout.";
    }
  }
  if (action === "Check Update") {
    if (!updateRecord?.source_update_supported) {
      return updateRecord?.reason ?? "Update check requires a clean local git source checkout.";
    }
  }
  if (action === "Update") {
    if (!updateRecord) {
      return "Update readiness is not loaded yet.";
    }
    if (!updateRecord.source_update_supported) {
      return updateRecord.reason ?? "This source checkout is not ready for update checks.";
    }
    if (updateRecord.update_action === "deep_check_required") {
      return "Run Deep Check before planning an update.";
    }
    if (!updateRecord.backup_available) {
      return "Create a backup before applying an update.";
    }
  }
  if (action === "Settings") {
    return "No module settings endpoint is exposed by the backend API";
  }
  if (action === "Logs") {
    return "No module logs endpoint is exposed by the backend API";
  }
  if (action === "Bridge") {
    return "Bridge task runs are exposed per task in the Bridge Tasks section";
  }
  if (action === "Proof") {
    return "No module proof endpoint is exposed by the backend API";
  }
  if (action === "Rollback") {
    if (!updateRecord) {
      return "Update readiness is not loaded yet.";
    }
    return updateRecord.backup_available ? null : "No recorded source backup available";
  }
  if (action === "Repo" && module.repo == null) {
    return "Repository must be verified before opening";
  }
  return null;
}

function moduleHasLaunchBridge(module: SourceOSModule): boolean {
  return module.id === "printrun";
}

function moduleHasServiceRunner(module: SourceOSModule): boolean {
  return module.runtime.kind === "local_http_health" || module.launchKind === "service" || module.launchKind === "web_app";
}

async function runAction(
  action: (typeof ACTIONS)[number],
  module: SourceOSModule,
  onResult: (message: string) => void,
  onRefresh?: () => void,
) {
  if (action === "Repo" && module.repo) {
    window.open(module.repo, "_blank", "noopener,noreferrer");
    onResult(`Opened repository for ${module.display}.`);
    return;
  }

  const endpoint = actionEndpoint(action, module);
  if (!endpoint) {
    onResult(`${action} is unavailable; no backend endpoint is exposed.`);
    return;
  }

  try {
    const response = await fetch(endpoint.url, {
      method: endpoint.method,
      headers: { Accept: "application/json", ...(endpoint.body ? { "Content-Type": "application/json" } : {}) },
      body: endpoint.body ? JSON.stringify(endpoint.body) : undefined,
      cache: "no-store",
    });
    const text = await response.text();
    const payload = parseActionPayload(text);
    const accepted = response.ok && actionAccepted(payload);
    onResult(`${actionLabel(action)} ${accepted ? "accepted" : "blocked"}: ${actionSummary(payload, text || response.statusText)}`);
    onRefresh?.();
  } catch {
    onResult(`${actionLabel(action)} failed: backend API is unreachable at ${LIVE_BASE_URL}.`);
  }
}

function actionEndpoint(action: (typeof ACTIONS)[number], module: SourceOSModule): { method: "GET" | "POST"; url: string; body?: Record<string, unknown> } | null {
  const moduleId = module.id;
  const encoded = encodeURIComponent(moduleId);
  if (action === "Install") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/install` };
  if (action === "Verify") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/runtime/verify`, body: { actor: "operator" } };
  if (action === "Backup") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/update/backup`, body: { actor: "operator", note: "manual source app backup from Source OS" } };
  if (action === "Check Update") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/update/check`, body: { actor: "operator", reason: "manual source app update check from Source OS" } };
  if (action === "Update") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/update/apply`, body: { actor: "operator", reason: "manual source app update from Source OS" } };
  if (action === "Launch") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/launch` };
  if (action === "Stop") {
    return moduleHasServiceRunner(module)
      ? { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/runtime/stop-runner`, body: { actor: "operator" } }
      : { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/stop` };
  }
  if (action === "Setup") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/runtime/setup-plan`, body: { actor: "operator" } };
  if (action === "Start Runner") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/runtime/start-runner`, body: { actor: "operator", execute: true } };
  if (action === "Rollback") return { method: "POST", url: `${LIVE_BASE_URL}/api/modules/${encoded}/rollback`, body: { actor: "operator", reason: "manual source app rollback from Source OS" } };
  return null;
}

async function runBridgeTask(moduleId: string, taskId: string, onResult: (message: string) => void) {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/modules/${encodeURIComponent(moduleId)}/bridge-tasks/${encodeURIComponent(taskId)}/run`, {
      method: "POST",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const text = await response.text();
    const payload = parseActionPayload(text);
    const accepted = response.ok && actionAccepted(payload);
    onResult(`Bridge task ${accepted ? "accepted" : "blocked"}: ${actionSummary(payload, text || response.statusText)}`);
  } catch {
    onResult(`Bridge task failed: backend API is unreachable at ${LIVE_BASE_URL}.`);
  }
}

function parseActionPayload(text: string): unknown {
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function actionAccepted(payload: unknown): boolean {
  return actionPayloadRecords(payload).every((record) => !recordBlocksAction(record));
}

function actionSummary(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) {
    return formatActionText(fallback);
  }
  const detail = payload.detail;
  if (isRecord(detail)) {
    return summaryFromRecord(detail, fallback);
  }
  if (typeof detail === "string" && detail.length > 0) {
    return formatActionText(detail);
  }
  return summaryFromRecord(payload, fallback);
}

function actionPayloadRecords(payload: unknown): Record<string, unknown>[] {
  if (!isRecord(payload)) {
    return [];
  }
  const records = [payload];
  if (isRecord(payload.detail)) {
    records.push(payload.detail);
  }
  return records;
}

function recordBlocksAction(record: Record<string, unknown>): boolean {
  if (record.accepted === false || record.success === false || record.stopped === false || record.rollback_started === false) {
    return true;
  }
  if (record.not_configured === true) {
    return true;
  }
  return blockedStatusValue(record.status)
    || blockedStatusValue(record.state)
    || blockedStatusValue(record.result)
    || blockedStatusValue(record.outcome);
}

function blockedStatusValue(value: unknown): boolean {
  return value === "not_configured" || value === "blocked" || value === "failed";
}

function summaryFromRecord(record: Record<string, unknown>, fallback: string): string {
  if (isRecord(record.start_result)) {
    const status = record.start_result.status;
    const runtimeReady = record.start_result.runtime_ready === true ? "runtime ready" : "health proof pending";
    const reason = record.start_result.blocked_reason;
    const proof = record.proof_event_id;
    return formatActionText(`${String(status ?? fallback)} · ${runtimeReady}${typeof reason === "string" ? ` · ${reason}` : ""}${typeof proof === "string" ? ` · proof ${proof}` : ""}`);
  }
  if (isRecord(record.stop_result)) {
    const status = record.stop_result.status;
    const reason = record.stop_result.reason;
    const proof = record.proof_event_id;
    return formatActionText(`${String(status ?? fallback)}${typeof reason === "string" ? ` · ${reason}` : ""}${typeof proof === "string" ? ` · proof ${proof}` : ""}`);
  }
  if (isRecord(record.record)) {
    const runner = record.record.runner_status;
    const nextAction = record.record.next_action;
    const proof = record.proof_event_id;
    if (typeof runner === "string") {
      return formatActionText(`${runner}${typeof nextAction === "string" ? ` · ${nextAction}` : ""}${typeof proof === "string" ? ` · proof ${proof}` : ""}`);
    }
  }
  if (Array.isArray(record.steps)) {
    const proof = record.proof_event_id;
    return formatActionText(`${record.steps.length} setup steps${typeof proof === "string" ? ` · proof ${proof}` : ""}`);
  }
  const summary = record.reason ?? record.notes ?? record.message ?? record.status ?? record.state ?? fallback;
  const proof = record.proof_event_id;
  return formatActionText(`${String(summary)}${typeof proof === "string" ? ` · proof ${proof}` : ""}`);
}

function formatActionText(value: string): string {
  return value.replaceAll("_", " ");
}

function shortHash(value: string | null | undefined): string {
  return value ? value.slice(0, 12) : "unknown";
}

function runtimeLabel(status: string): string {
  if (status === "source_ready") return "source ready";
  if (status === "setup_required") return "setup needed";
  if (status === "not_installed") return "install ready";
  return status;
}

function runnerContractTone(runnerStatus: string): "blue" | "cyan" | "green" | "red" | "muted" {
  if (runnerStatus === "agent_cli_ready") return "green";
  if (runnerStatus === "readonly_api_ready") return "cyan";
  if (runnerStatus === "metadata_ready_needs_runner" || runnerStatus === "launcher_metadata_only") return "blue";
  if (runnerStatus === "blocked") return "red";
  return "muted";
}

function runtimeTone(status: string): "blue" | "cyan" | "green" | "red" | "muted" {
  if (status === "ready") return "green";
  if (status === "source_ready") return "cyan";
  if (status === "setup_required" || status === "not_installed") return "blue";
  if (status === "blocked") return "red";
  return "muted";
}

function cliSurfaceLabel(record: SourceModuleCliSurfaceRecord): string {
  if (record.agent_enabled) return "Agent CLI ready";
  if (record.cli_surface_status === "launcher_only_not_cli") return "desktop launcher only";
  if (record.cli_surface_status === "no_local_cli_signal") return "no local CLI signal";
  if (record.cli_surface_status.includes("candidate") || record.cli_surface_status.includes("signal")) return "CLI/service signal";
  if (record.agent_execution_tier === "package_or_import_ready") return "package/import proof only";
  if (record.agent_execution_tier === "service_api_ready") return "read-only service API proof";
  if (record.agent_execution_tier === "source_reference_ready") return "source/reference proof only";
  return record.cli_surface_status.replaceAll("_", " ");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function InfoBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded border border-border bg-surface2/30 p-3">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
        {title}
      </h3>
      <div className="flex flex-col gap-2">{children}</div>
    </section>
  );
}

function Field({
  label,
  value,
  mono = false,
  action,
}: {
  label: string;
  value: string;
  mono?: boolean;
  action?: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[110px_1fr_auto] items-center gap-2 text-xs">
      <span className="text-[10px] uppercase tracking-wide text-muted">{label}</span>
      <span className={`min-w-0 truncate text-fg ${mono ? "font-mono" : ""}`}>{value}</span>
      {action ?? <span />}
    </div>
  );
}

function CopyButton({ value }: { value: string }) {
  return (
    <button
      type="button"
      disabled={value.length === 0}
      title={value.length === 0 ? "No repository URL to copy" : "Copy repository URL"}
      onClick={() => void navigator.clipboard.writeText(value)}
      className="rounded p-1 text-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-50"
    >
      <Copy size={12} />
    </button>
  );
}

function Pill({ label, tone }: { label: string; tone: "blue" | "cyan" | "green" | "red" | "muted" }) {
  const toneClass = {
    blue: "bg-accent-blue/10 text-accent-blue",
    cyan: "bg-accent-cyan/10 text-accent-cyan",
    green: "bg-accent-green/10 text-accent-green",
    red: "bg-accent-red/10 text-accent-red",
    muted: "bg-surface2 text-muted",
  }[tone];
  return (
    <span className={`rounded px-2 py-0.5 text-[10px] font-medium uppercase ${toneClass}`}>
      {label.replaceAll("_", " ")}
    </span>
  );
}
