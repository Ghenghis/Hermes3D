import type { Agent, AgentStatus } from "../types/agent";
import type { AgentActionCatalog, AgentActionRunResult } from "../types/agent-actions";
import type { DimensionalAccuracyReport } from "../types/dimensional";
import type { LogEntry } from "../types/log";
import type { Notification } from "../types/notification";
import type { ProofBundle } from "../types/proof";
import type { RuntimeReadiness, SystemSnapshot } from "../types/system";
import type { Workflow } from "../types/workflow";
import type { TaskDAG, TaskEdge, TaskNode } from "../types/dag";
import type { Printer, PrinterAdapter, PrinterDataSource, PrinterOnboardRequest, PrinterOnboardResult, PrinterStatus } from "../types/printer";
import type { ProviderHealth } from "../types/provider";
import type {
  ServiceCategory,
  ServiceHealthEntry,
  ServiceStatus,
} from "../types/serviceHealth";
import type { Approval } from "../types/approval";
import type { Artifact, EvidenceForm } from "../types/artifact";
import type { AutopilotCheck, GuardrailPolicy } from "../types/autopilot";
import type { Job } from "../types/job";
import type { JobDetail, JobTransitionResult, JobTransitionState } from "../types/job-detail";
import type {
  IdleCandidateCreateRequest,
  IdleCandidateMutationResult,
  IdleAutomationCapability,
  IdleAutomationReadiness,
  IdleWorkbenchBlocker,
  IdleWorkbenchCandidate,
  IdleWorkbenchState,
  LearningConfig,
  ReportMeta,
} from "../types/learning";
import type { Plugin } from "../types/plugin";
import type { GcodeUploadResult, PrinterLock, TestResult } from "../types/printer-lock";
import type { RoadmapItem, RoadmapTabCompletion } from "../types/roadmap";
import type { AppSettings } from "../types/settings";
import type { SourceModuleRuntimeSetupQueue, SourceModuleUpdateReadiness, SourceOSModule } from "../types/source-os";
import type { ToolchainStatus } from "../types/toolchain";
import type { AzureVoice, VoiceAgent, VoiceCatalog, VoicePreviewResult } from "../types/voice";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_PRINTERS_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}/api/printers`;
const LIVE_PLAN_PREVIEW_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}/api/plan/preview`;
const LIVE_PROVIDER_HEALTH_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}/api/providers/health`;
const LIVE_SERVICE_HEALTH_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}/api/health/services`;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

export type AgentConfigPayload = Record<string, unknown>;

export interface AgentConfigSaveResult {
  available: boolean;
  saved: boolean;
  status: string;
  reason: string;
  redacted: string[];
  detail?: unknown;
}

export interface AgentAttachmentUpload {
  uploaded: boolean;
  artifact: {
    id: string;
    label: string | null;
    file_path: string;
    file_size: number;
    evidence_type: string;
    agent: string | null;
    stage: string | null;
    notes?: string | null;
    created_at?: string;
  };
}

export interface AgentHealthResult {
  available: boolean;
  healthy: boolean;
  status: string;
  reason: string;
  agents: Record<string, string>;
  setup?: Record<string, unknown>;
  detail?: unknown;
}

export interface HermesAgentUpdateStatus {
  available: boolean;
  repo_url: string;
  checkout_path: string;
  repo_ready: boolean;
  current: {
    repo_ready?: boolean;
    commit?: string;
    exact_tag?: string | null;
    nearest_tag?: string | null;
    branch?: string;
    dirty?: boolean;
    dirty_entries?: string[];
    reason?: string;
  };
  latest_release: {
    tag?: string | null;
    name?: string | null;
    published_at?: string | null;
    html_url?: string | null;
    source?: string;
  };
  outdated: boolean;
  outdated_by: number;
  pending_tags: string[];
  backup_available: boolean;
  latest_backup: HermesAgentBackup | null;
  strategy: string;
  rollback: string;
  reason?: string;
  detail?: unknown;
}

export interface HermesAgentBackup {
  backup_id: string;
  created_at: string;
  note: string;
  checkout_path: string;
  bundle_path: string;
  dirty_zip_path: string | null;
  tag: string | null;
  commit: string;
  dirty: boolean;
  dirty_entries: string[];
}

export interface HermesAgentUpdateResult {
  available: boolean;
  status: string;
  updated?: boolean;
  backup?: HermesAgentBackup | null;
  steps?: Array<{ tag: string; ok: boolean; checks: Array<{ name: string; status: string; output?: string }> }>;
  current?: HermesAgentUpdateStatus["current"];
  latest_release?: HermesAgentUpdateStatus["latest_release"];
  remaining_tags?: string[];
  reason?: string;
  detail?: unknown;
}

export interface HermesDesktopUpdateStatus {
  available: boolean;
  repo_url: string;
  checkout_path: string;
  source_ready: boolean;
  git_ready: boolean;
  current: {
    source_ready?: boolean;
    git_ready?: boolean;
    reason?: string | null;
    package_name?: string | null;
    package_version?: string | null;
    commit?: string | null;
    exact_tag?: string | null;
    nearest_tag?: string | null;
    dirty?: boolean | null;
  };
  latest_release: {
    tag?: string | null;
    name?: string | null;
    published_at?: string | null;
    html_url?: string | null;
    installer_asset?: {
      name?: string | null;
      size?: number | null;
      digest?: string | null;
      browser_download_url?: string | null;
    } | null;
  };
  outdated: boolean;
  strategy: string;
  installer_download_supported: boolean;
  installer_verification_supported?: boolean;
  source_update_supported: boolean;
  backup_available: boolean;
  latest_backup: HermesDesktopBackup | null;
  reason?: string;
  detail?: unknown;
}

export interface HermesDesktopBackup {
  backup_id: string;
  created_at: string;
  note: string;
  checkout_path: string;
  package_version: string | null;
  tag: string | null;
  commit: string | null;
  git_ready: boolean;
  bundle_path: string | null;
  source_zip_path: string | null;
}

export interface HermesDesktopDownload {
  downloaded: boolean;
  asset_name: string;
  path: string;
  size_bytes: number;
  sha256: string;
  expected_sha256?: string | null;
  verification_status?: string;
  next_step: string;
}

export interface LearningReportContent {
  filename: string;
  content: string;
}

const SERVICE_STATUSES = new Set<ServiceStatus>([
  "online",
  "offline",
  "unreachable",
  "auth-required",
  "disabled",
  "unknown",
]);
const SERVICE_CATEGORIES = new Set<ServiceCategory>([
  "mcp",
  "llm",
  "modeling",
  "printer",
  "api",
  "tunnel",
]);

const MODELS = new Set<Printer["model"]>(["FLSUN T1", "FLSUN S1", "FLSUN V400", "Generic"]);
const STATUSES = new Set<PrinterStatus>([
  "online",
  "active",
  "printing",
  "paused",
  "maintenance",
  "offline",
  "error",
]);
const ADAPTERS = new Set<PrinterAdapter>(["moonraker", "octoprint", "printrun", "manual"]);
const DATA_SOURCES = new Set<PrinterDataSource>(["live", "degraded", "error", "policy", "config"]);

export async function getLivePrinters(): Promise<Printer[]> {
  try {
    const response = await fetch(LIVE_PRINTERS_URL, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return [];
    }
    const payload: unknown = await response.json();
    const printers = parsePrinterArray(payload);
    return printers ?? [];
  } catch {
    return [];
  }
}

export async function planPreviewLive(prompt: string): Promise<TaskDAG> {
  try {
    const response = await fetch(LIVE_PLAN_PREVIEW_URL, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`plan preview request failed: ${response.status} ${response.statusText}`);
    }
    const payload: unknown = await response.json();
    const parsed = parseTaskDAG(payload);
    if (!parsed) {
      throw new Error("plan preview API returned an invalid DAG payload");
    }
    return parsed;
  } catch (error) {
    throw new Error(`Plan preview API is unavailable at ${LIVE_PLAN_PREVIEW_URL}: ${errorMessage(error)}`);
  }
}

export async function getProviderHealthLive(): Promise<ProviderHealth[]> {
  try {
    const response = await fetch(LIVE_PROVIDER_HEALTH_URL, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`provider health request failed: ${response.status} ${response.statusText}`);
    }
    const payload: unknown = await response.json();
    const parsed = parseProviderHealthArray(payload);
    if (!parsed) {
      throw new Error("provider health API returned an invalid payload");
    }
    return parsed;
  } catch (error) {
    throw new Error(`Provider health API is unavailable at ${LIVE_PROVIDER_HEALTH_URL}: ${errorMessage(error)}`);
  }
}

export async function getServiceHealthLive(): Promise<ServiceHealthEntry[]> {
  try {
    const response = await fetch(LIVE_SERVICE_HEALTH_URL, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return [];
    }
    const payload: unknown = await response.json();
    return parseServiceHealthArray(payload) ?? [];
  } catch {
    return [];
  }
}

export function getAgentsLive(): Promise<Agent[]> {
  return fetchArray<unknown>("/api/agents").then((agents) => agents.map(parseAgent).filter(isPresent));
}

export function getActiveWorkflowsLive(): Promise<Workflow[]> {
  return fetchArray("/api/workflows");
}

export function getRecentJobsLive(): Promise<Job[]> {
  return getJobsLive();
}

export function getProofBundlesLive(): Promise<ProofBundle[]> {
  return fetchArray("/api/proof/bundles");
}

export async function getLatestProofBundleLive(): Promise<ProofBundle | null> {
  const bundles = await getProofBundlesLive();
  return bundles[0] ?? null;
}

export function getSystemSnapshotLive(): Promise<SystemSnapshot | null> {
  return fetchNullable("/api/system/snapshot");
}

export function getRuntimeReadinessLive(): Promise<RuntimeReadiness | null> {
  return fetchNullable("/api/system/runtime-readiness");
}

export function getDimensionalReportsLive(): Promise<DimensionalAccuracyReport[]> {
  return fetchArray("/api/dimensional-reports");
}

export function getLogsLive(): Promise<LogEntry[]> {
  return fetchArray("/api/logs");
}

export function getNotificationsLive(): Promise<Notification[]> {
  return fetchJson<{ notifications?: unknown[] }>("/api/notifications").then((payload) =>
    (payload?.notifications ?? []).map(parseNotification).filter(isPresent),
  );
}

export function getAutopilotReadinessLive(): Promise<AutopilotCheck[]> {
  return fetchArray<unknown>("/api/autopilot/readiness").then((checks) => checks.map(parseAutopilotCheck).filter(isPresent));
}

export function getAutopilotGuardrailsLive(): Promise<GuardrailPolicy[]> {
  return fetchArray<unknown>("/api/autopilot/guardrails").then((guardrails) => guardrails.map(parseGuardrailPolicy).filter(isPresent));
}

export function getDesignToolchainStatusLive(): Promise<ToolchainStatus> {
  return fetchJson<ToolchainStatus>("/api/design/toolchain/status").then((status) => status ?? {
    overall: "blocked",
    stages: [],
    updated_at: "",
  });
}

export function getJobsLive(status?: string): Promise<Job[]> {
  const queryStatus = status?.split(",").flatMap((item) => item === "printing" ? ["printing", "running"] : [item]).join(",");
  const query = queryStatus ? `?status=${encodeURIComponent(queryStatus)}` : "";
  return fetchArray<unknown>(`/api/jobs${query}`).then((jobs) => jobs.map(parseJob).filter(isPresent));
}

export function getJobDetailLive(id: string): Promise<JobDetail> {
  return fetchJson<unknown>(`/api/jobs/${encodeURIComponent(id)}`).then((job) => parseJobDetail(job) ?? {
    id,
    title: "Unavailable",
    type: "unknown",
    status: "failed",
    dry_run: true,
    printer_id: null,
    created_at: "",
    started_at: null,
    completed_at: null,
    steps: [],
    artifacts: [],
    events: [],
    approvals: [],
    transition_state: null,
  });
}

export function cancelJobLive(id: string): Promise<void> {
  return postVoid(`/api/jobs/${encodeURIComponent(id)}/cancel`);
}

export function proposeJobRepairLive(id: string, reason?: string): Promise<JobTransitionResult> {
  return postJobTransition(`/api/jobs/${encodeURIComponent(id)}/repair/propose`, { actor: "operator", reason: reason ?? "" });
}

export function applyJobRepairLive(id: string, notes?: string): Promise<JobTransitionResult> {
  return postJobTransition(`/api/jobs/${encodeURIComponent(id)}/repair/apply`, { actor: "operator", notes: notes ?? "" });
}

export function retryJobLive(id: string, reason?: string): Promise<JobTransitionResult> {
  return postJobTransition(`/api/jobs/${encodeURIComponent(id)}/retry`, { actor: "operator", reason: reason ?? "" });
}

export function rollbackJobLive(id: string, targetArtifactId?: string): Promise<JobTransitionResult> {
  return postJobTransition(`/api/jobs/${encodeURIComponent(id)}/rollback`, { actor: "operator", target_artifact_id: targetArtifactId ?? null });
}

export function getPrinterLockStateLive(id: string): Promise<PrinterLock> {
  return fetchJson<PrinterLock>(`/api/printers/${encodeURIComponent(id)}/lock`).then((lock) => lock ?? {
    printer_id: id,
    locked: true,
    reason: "Lock state unavailable from local backend.",
    locked_by: null,
    locked_at: null,
  });
}

export function testPrinterLive(id: string): Promise<TestResult> {
  return fetchJson<TestResult>(`/api/printers/${encodeURIComponent(id)}/test`).then((result) => result ?? {
    printer_id: id,
    ok: false,
    message: "Printer test unavailable from local backend.",
    latency_ms: null,
  });
}

export async function onboardPrinterLive(request: PrinterOnboardRequest): Promise<PrinterOnboardResult> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/printers/onboard`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      cache: "no-store",
    });
  } catch (error) {
    return {
      created: false,
      printer: null,
      probe_summary: null,
      status: "unreachable",
      reason: `Printer onboarding endpoint is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`,
      failed_probe: null,
    };
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = isRecord(payload) ? payload.detail : null;
    return {
      created: false,
      printer: null,
      probe_summary: probeSummaryFromDetail(detail),
      status: `HTTP ${response.status}`,
      reason: detailMessage(payload) ?? `Printer onboarding failed with HTTP ${response.status}.`,
      failed_probe: failedProbeFromDetail(detail),
      detail: payload,
    };
  }
  return parsePrinterOnboardResult(payload) ?? {
    created: false,
    printer: null,
    probe_summary: null,
    status: "invalid_response",
    reason: "Printer onboarding response was not in the expected shape.",
    failed_probe: null,
    detail: payload,
  };
}

export async function uploadGcodeLive(
  id: string,
  gcodePath: string,
  start: boolean,
  remoteSubdir = "hermes3d",
  actor = "hermes-agent",
  jobId?: string,
): Promise<GcodeUploadResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/printers/${encodeURIComponent(id)}/upload-gcode`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        gcode_path: gcodePath,
        start,
        job_id: jobId?.trim() || null,
        remote_subdir: remoteSubdir,
        actor,
      }),
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      return {
        printer_id: id,
        accepted: false,
        uploaded: false,
        started: false,
        status: `HTTP ${response.status}`,
        reason: detailMessage(payload) ?? "G-code upload/start rejected by local backend.",
        detail: payload,
      };
    }
    return parseGcodeUploadResult(payload, id) ?? {
      printer_id: id,
      accepted: false,
      uploaded: false,
      started: false,
      status: "invalid_response",
      reason: "G-code upload response was not in the expected shape.",
      detail: payload,
    };
  } catch (error) {
    return {
      printer_id: id,
      accepted: false,
      uploaded: false,
      started: false,
      status: "unreachable",
      reason: error instanceof Error ? error.message : "Local backend unreachable.",
    };
  }
}

export function updatePrinterStatusLive(id: string, status: Printer["status"], actor = "hermes-agent"): Promise<void> {
  return putVoid(`/api/printers/${encodeURIComponent(id)}/status`, { status, actor });
}

export function getVoiceAgentsLive(): Promise<VoiceAgent[]> {
  return fetchArray<unknown>("/api/voice/agents").then((agents) => agents.map(parseVoiceAgent).filter(isPresent));
}

export function getVoiceCatalogLive(locale = "en"): Promise<VoiceCatalog> {
  return fetchJson<unknown>(`/api/voice/voices?locale=${encodeURIComponent(locale)}`).then((payload) => parseVoiceCatalog(payload) ?? {
    provider: "azure",
    configured: false,
    status: "unreachable",
    reason: "Voice catalog API is unavailable from the local backend.",
    count: 0,
    voices: [],
  });
}

export function saveVoiceAgentLive(id: string, voice: string): Promise<void> {
  return putVoid(`/api/voice/agents/${encodeURIComponent(id)}`, { voice });
}

export async function previewVoiceLive(
  id: string,
  voice: string,
  text = "Hello. Hermes3D voice preview is running through the local backend.",
  rate = 1,
  pitchPct = 0,
): Promise<VoicePreviewResult> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/voice/preview`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id, voice, text, rate, pitch_pct: pitchPct }),
      cache: "no-store",
    });
    const payload: unknown = await response.json().catch(() => null);
    return parseVoicePreviewResult(payload, response.ok) ?? {
      accepted: false,
      status: "invalid_response",
      reason: response.statusText || "Voice preview response was not in the expected shape.",
      voice,
    };
  } catch (error) {
    return {
      accepted: false,
      status: "unreachable",
      reason: error instanceof Error ? error.message : "Voice preview API is unreachable.",
      voice,
    };
  }
}

export function getPluginsLive(): Promise<Plugin[]> {
  return fetchArray("/api/plugins");
}

export async function activatePluginLive(id: string): Promise<Plugin> {
  const payload = await postJsonWithResult(`/api/plugins/${encodeURIComponent(id)}/activate`, {});
  if (!isRecord(payload) || !isString(payload.id)) {
    throw new Error("Plugin activation response was not in the expected shape.");
  }
  return payload as unknown as Plugin;
}

export async function getAgentHealthLive(): Promise<AgentHealthResult> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/agents/health`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    return unavailableAgentHealth(`Agent health endpoint is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    return unavailableAgentHealth(httpFailureReason(payload, response, "Agent health endpoint"));
  }

  return parseAgentHealth(payload) ?? unavailableAgentHealth("Agent health response was not in the expected shape.");
}

export async function saveAgentConfigLive(config: AgentConfigPayload): Promise<AgentConfigSaveResult> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/agents/config`, {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
      cache: "no-store",
    });
  } catch (error) {
    return {
      available: false,
      saved: false,
      status: "unreachable",
      reason: `Agent config endpoint is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`,
      redacted: [],
    };
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    return {
      available: false,
      saved: false,
      status: `http_${response.status}`,
      reason: httpFailureReason(payload, response, "Agent config endpoint"),
      redacted: [],
      detail: payload,
    };
  }

  return parseAgentConfigSave(payload) ?? {
    available: true,
    saved: false,
    status: "invalid_response",
    reason: "Agent config response was not in the expected shape.",
    redacted: [],
    detail: payload,
  };
}

export async function getHermesAgentUpdateStatusLive(): Promise<HermesAgentUpdateStatus> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/agents/update/status`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    return unavailableUpdateStatus(`Hermes Agent update status endpoint is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    return unavailableUpdateStatus(httpFailureReason(payload, response, "Hermes Agent update status"));
  }
  return parseHermesAgentUpdateStatus(payload) ?? unavailableUpdateStatus("Hermes Agent update status response was not in the expected shape.");
}

export async function backupHermesAgentLive(note = "manual Hermes Agent pre-update backup"): Promise<HermesAgentBackup> {
  const payload = await postJsonWithResult("/api/agents/update/backup", { note });
  const backup = parseHermesAgentBackup(payload);
  if (!backup) {
    throw new Error("Hermes Agent backup response was not in the expected shape.");
  }
  return backup;
}

export async function updateHermesAgentStagedLive(maxSteps = 1): Promise<HermesAgentUpdateResult> {
  return postUpdateAction("/api/agents/update/staged", {
    max_steps: maxSteps,
    create_backup: true,
    run_checks: true,
    actor: "hermes-agent",
  });
}

export async function rollbackHermesAgentLive(backupId?: string): Promise<HermesAgentUpdateResult> {
  return postUpdateAction("/api/agents/update/rollback", {
    backup_id: backupId,
    actor: "hermes-agent",
  });
}

export function getAgentActionCatalogLive(): Promise<AgentActionCatalog> {
  return fetchJson<AgentActionCatalog>("/api/agents/action-catalog").then((payload) => payload ?? {
    status: "blocked",
    summary: "Hermes Agent action catalog API is unavailable from the local backend.",
    contract_version: "unavailable",
    counts: {},
    total: 0,
    ready_now: [],
    blocked_or_partial: [],
    contracts: [],
  });
}

export async function runAgentCatalogActionLive(actionId: string, reason = "operator requested from Hermes3D UI", payload: Record<string, unknown> = {}): Promise<AgentActionRunResult> {
  const result = await postJsonWithResult(`/api/agents/actions/${encodeURIComponent(actionId)}`, { reason, payload });
  if (!isRecord(result) || !isString(result.action_id) || !isString(result.status)) {
    throw new Error("Hermes Agent action result was not in the expected shape.");
  }
  return result as unknown as AgentActionRunResult;
}

export async function uploadAgentAttachmentLive(personaId: string, file: File): Promise<AgentAttachmentUpload> {
  const body = await file.arrayBuffer();
  const response = await fetch(`${LIVE_BASE_URL}/api/agents/${encodeURIComponent(personaId)}/attachments?filename=${encodeURIComponent(file.name)}`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": file.type || "application/octet-stream",
      "X-Hermes-Filename": file.name,
    },
    body,
    cache: "no-store",
  });
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, "agent attachment upload"));
  }
  const parsed = parseAgentAttachmentUpload(payload);
  if (!parsed) {
    throw new Error("Agent attachment upload response was not in the expected shape.");
  }
  return parsed;
}

export async function getHermesDesktopUpdateStatusLive(): Promise<HermesDesktopUpdateStatus> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/desktop/update/status`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    return unavailableDesktopUpdateStatus(`Hermes Desktop update status endpoint is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    return unavailableDesktopUpdateStatus(httpFailureReason(payload, response, "Hermes Desktop update status"));
  }
  return parseHermesDesktopUpdateStatus(payload) ?? unavailableDesktopUpdateStatus("Hermes Desktop update status response was not in the expected shape.");
}

export async function backupHermesDesktopLive(note = "manual Hermes Desktop pre-update backup"): Promise<HermesDesktopBackup> {
  const payload = await postJsonWithResult("/api/desktop/update/backup", { note });
  const backup = parseHermesDesktopBackup(payload);
  if (!backup) {
    throw new Error("Hermes Desktop backup response was not in the expected shape.");
  }
  return backup;
}

export async function downloadHermesDesktopInstallerLive(): Promise<HermesDesktopDownload> {
  const payload = await postJsonWithResult("/api/desktop/update/download", {});
  const download = parseHermesDesktopDownload(payload);
  if (!download) {
    throw new Error("Hermes Desktop download response was not in the expected shape.");
  }
  return download;
}

export async function getLearningConfigLive(): Promise<LearningConfig> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/learning/config`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(`Learning config API is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, "Learning config request"));
  }
  const config = parseLearningConfig(payload);
  if (config == null) {
    throw new Error("Learning config response was not in the expected shape.");
  }
  return config;
}

export async function getLearningReportsLive(): Promise<ReportMeta[]> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/learning/reports`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(`Learning reports API is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, "Learning reports request"));
  }
  if (!Array.isArray(payload)) {
    throw new Error("Learning reports response was not in the expected shape.");
  }
  return payload.map(parseLearningReport).filter(isPresent);
}

export async function getLearningReportLive(filename: string): Promise<LearningReportContent> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/learning/reports/${encodeURIComponent(filename)}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(`Learning report API is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, "Learning report request"));
  }

  const report = parseLearningReportContent(payload, filename);
  if (report == null) {
    throw new Error("Learning report response was not in the expected shape.");
  }
  return report;
}

export async function saveLearningConfigLive(config: Pick<LearningConfig, "enabled" | "idle_minutes">): Promise<LearningConfig> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/learning/config`, {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        enabled: config.enabled,
        idle_minutes: config.idle_minutes,
      }),
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(`Learning config API is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, "Learning config save"));
  }

  const saved = parseLearningConfig(payload);
  if (saved == null) {
    throw new Error("Learning config response was not in the expected shape.");
  }
  return saved;
}

export async function getIdleWorkbenchLive(): Promise<IdleWorkbenchState> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}/api/learning/idle-workbench`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(`Idle workbench API is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, "Idle workbench request"));
  }
  const state = parseIdleWorkbenchState(payload);
  if (state == null) {
    throw new Error("Idle workbench response was not in the expected shape.");
  }
  return state;
}

export async function createIdleCandidateLive(request: IdleCandidateCreateRequest): Promise<IdleCandidateMutationResult> {
  const payload = await postJsonWithResult("/api/learning/idle-workbench/candidates", request);
  return parseIdleCandidateMutationResult(payload) ?? {
    accepted: false,
    status: "invalid_response",
    reason: "Idle candidate creation response was not in the expected shape.",
    candidate: null,
  };
}

export async function requestIdleCandidateReviewLive(candidateId: string): Promise<IdleCandidateMutationResult> {
  const payload = await postJsonWithResult(`/api/learning/idle-workbench/candidates/${encodeURIComponent(candidateId)}/request-review`, {
    decision: "review",
    actor: "operator",
  });
  return parseIdleCandidateMutationResult(payload) ?? {
    accepted: false,
    status: "invalid_response",
    reason: "Idle candidate review response was not in the expected shape.",
    candidate: null,
  };
}

export async function runIdleCandidateLive(candidateId: string): Promise<IdleCandidateMutationResult> {
  const payload = await postJsonWithResult(`/api/learning/idle-workbench/candidates/${encodeURIComponent(candidateId)}/run`, {
    actor: "operator",
  });
  return parseIdleCandidateMutationResult(payload) ?? {
    accepted: false,
    status: "invalid_response",
    reason: "Idle candidate run response was not in the expected shape.",
    candidate: null,
  };
}

export async function decideIdleCandidateLive(candidateId: string, decision: "keep" | "remove" | "merge", reason?: string): Promise<IdleCandidateMutationResult> {
  const payload = await postJsonWithResult(`/api/learning/idle-workbench/candidates/${encodeURIComponent(candidateId)}/decision`, {
    decision,
    actor: "operator",
    reason,
  });
  return parseIdleCandidateMutationResult(payload) ?? {
    accepted: false,
    status: "invalid_response",
    reason: "Idle candidate decision response was not in the expected shape.",
    candidate: null,
  };
}

export function getArtifactsLive(): Promise<Artifact[]> {
  return fetchJson<unknown>("/api/artifacts?grouped=job").then(parseArtifactsPayload);
}

export function attachEvidenceLive(form: EvidenceForm): Promise<Artifact> {
  if (form.file == null) {
    return Promise.resolve(unavailableArtifact(form, "No file selected."));
  }
  const params = new URLSearchParams({
    job_id: String(form.jobId),
    evidence_type: form.evidenceType,
    stage: form.stage,
    gate: form.gate,
    agent: form.agent,
    label: form.label,
  });
  if (form.notes !== "") {
    params.set("notes", form.notes);
  }
  return postBinary(`/api/artifacts?${params.toString()}`, form.file).then((payload) => {
    const artifact = parseArtifact(payload);
    return artifact ?? unavailableArtifact(form, "Artifact upload response unavailable from local backend.");
  });
}

export function getPendingApprovalsLive(): Promise<Approval[]> {
  return fetchArray("/api/approvals?status=pending");
}

export function getApprovalHistoryLive(): Promise<Approval[]> {
  return fetchArray("/api/approvals?status=approved,rejected");
}

export function approveApprovalLive(id: string, notes: string): Promise<void> {
  return postVoid(`/api/approvals/${encodeURIComponent(id)}/approve`, { notes });
}

export function rejectApprovalLive(id: string, reason: string): Promise<void> {
  return postVoid(`/api/approvals/${encodeURIComponent(id)}/reject`, { reason });
}

export function getRoadmapItemsLive(): Promise<RoadmapItem[]> {
  return fetchArray("/api/roadmap/status");
}

export function getRoadmapTabCompletionLive(): Promise<RoadmapTabCompletion> {
  return fetchJson<RoadmapTabCompletion>("/api/roadmap/tab-completion").then((payload) => payload ?? {
    updated_at: "",
    roadmap_path: "",
    contract: [],
    tabs: [],
    next_packages: [],
    references: [],
  });
}

export function getSourceOSModulesLive(): Promise<SourceOSModule[]> {
  return fetchArray<unknown>("/api/modules").then((modules) => modules.map(parseSourceOSModule).filter(isPresent));
}

export function getSourceOSModuleLive(id: string): Promise<SourceOSModule | null> {
  return fetchJson<unknown>(`/api/modules/${encodeURIComponent(id)}`).then(parseSourceOSModule);
}

export function getModuleUpdateReadinessLive(deep = false): Promise<SourceModuleUpdateReadiness> {
  const query = deep ? "?deep=true" : "";
  return fetchJson<SourceModuleUpdateReadiness>(`/api/modules/update/readiness${query}`).then((payload) => payload ?? {
    status: "unavailable",
    strategy: "Module update readiness API did not return a response.",
    section: null,
    deep,
    count: 0,
    ready_for_update_check: 0,
    blocked: 0,
    outdated_cached: 0,
    dirty: 0,
    records: [],
  });
}

export function getModuleRuntimeSetupQueueLive(): Promise<SourceModuleRuntimeSetupQueue> {
  return fetchJson<unknown>("/api/modules/runtime/setup-queue").then((payload) => parseSourceModuleRuntimeSetupQueue(payload) ?? emptySetupQueue("unavailable"));
}

export async function planModuleRuntimeSetupQueueLive(): Promise<SourceModuleRuntimeSetupQueue> {
  const payload = await postJsonWithResult("/api/modules/runtime/setup-queue", { actor: "operator" });
  const parsed = parseSourceModuleRuntimeSetupQueue(payload);
  if (!parsed) {
    throw new Error("Runtime setup queue API returned an invalid payload.");
  }
  return parsed;
}

export function getSettingsLive(): Promise<AppSettings> {
  return fetchJson<AppSettings>("/api/settings").then((settings) => settings ?? {
    theme: "midnight",
    ports: { bridge: Number(LIVE_BRIDGE_PORT), api: 8000, ui: 5173 },
    printerUrls: {},
    cameraUrls: {},
    serviceUrls: {},
  });
}

export function saveSettingsLive(settings: Partial<AppSettings>): Promise<void> {
  return putVoid("/api/settings", settings);
}

export function emitProofEventLive(type: string, payload: Record<string, unknown>): Promise<void> {
  return postVoid("/api/proof/events", { type, payload });
}

export function getCameraObserverStatusLive(): Promise<{ status: string; reason: string }> {
  return fetchJson<{ state?: string; status?: string; reason?: string | null }>("/api/plugins/camera-observer/status").then((status) => {
    if (!status) {
      return {
        status: "UNAVAILABLE",
        reason: "Camera Observer status unavailable from local backend.",
      };
    }
    const rawStatus = isString(status.state) ? status.state : isString(status.status) ? status.status : "UNAVAILABLE";
    const configured = status.status === "configured" || rawStatus === "ACTIVE";
    return {
      status: configured ? "ACTIVE" : rawStatus,
      reason: isString(status.reason) && status.reason.length > 0
        ? status.reason
        : configured
          ? "Camera endpoints are configured from live printer camera URLs."
          : "Camera Observer is not configured.",
    };
  });
}

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function fetchArray<T>(path: string): Promise<T[]> {
  const payload = await fetchJson<unknown>(path);
  return Array.isArray(payload) ? payload as T[] : [];
}

async function fetchNullable<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

async function postBinary(path: string, body: Blob): Promise<unknown | null> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}${path}`, {
      method: "POST",
      headers: { Accept: "application/json" },
      body,
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return await response.json();
  } catch {
    return null;
  }
}

async function postJsonWithResult(path: string, body: unknown): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(`${path} is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, path));
  }
  return payload;
}

async function postJobTransition(path: string, body: unknown): Promise<JobTransitionResult> {
  const payload = await postJsonWithResult(path, body);
  const parsed = parseJobTransitionResult(payload);
  if (!parsed) {
    throw new Error(`${path} returned an invalid job transition payload.`);
  }
  return parsed;
}

async function postVoid(path: string, body?: unknown): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}${path}`, {
      method: "POST",
      headers: body === undefined ? { Accept: "application/json" } : {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(`${path} is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, path));
  }
}

async function putVoid(path: string, body: unknown): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${LIVE_BASE_URL}${path}`, {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch (error) {
    throw new Error(`${path} is unreachable at ${LIVE_BASE_URL}: ${errorMessage(error)}`);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(httpFailureReason(payload, response, path));
  }
}

function parseAutopilotCheck(value: unknown): AutopilotCheck | null {
  if (!isRecord(value) || !isString(value.id) || !isString(value.name)) {
    return null;
  }
  const ready = typeof value.ready === "boolean" ? value.ready : value.status === "ready";
  return {
    id: value.id,
    name: value.name,
    status: ready ? "ready" : "needs_setup",
    detail: isString(value.detail) ? value.detail : isString(value.message) && value.message.length > 0 ? value.message : null,
    fix_target: isNullableString(value.fix_target) ? value.fix_target : inferAutopilotFixTarget(value.id),
  };
}

function inferAutopilotFixTarget(id: string): string {
  if (id.includes("printer") || id.includes("movement") || id.includes("temp") || id.includes("mesh")) {
    return "printers";
  }
  if (id.includes("slicer") || id.includes("comfy") || id.includes("llm")) {
    return "source-os";
  }
  if (id.includes("approval")) {
    return "approvals";
  }
  if (id.includes("proof") || id.includes("evidence")) {
    return "artifacts";
  }
  return "settings";
}

function parseGuardrailPolicy(value: unknown): GuardrailPolicy | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  const description = isString(value.description) ? value.description : isString(value.rule) ? value.rule : "";
  return {
    id: value.id,
    name: isString(value.name) ? value.name : value.id.replaceAll("_", " "),
    enabled: typeof value.enabled === "boolean" ? value.enabled : value.enforced === true,
    severity: value.severity === "info" || value.severity === "warn" || value.severity === "block" ? value.severity : "block",
    description,
  };
}

function parseJob(value: unknown): Job | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  const rawStatus = isString(value.status) ? value.status : "queued";
  return {
    id: value.id,
    name: isString(value.name) ? value.name : value.id,
    status: normalizeJobStatus(rawStatus),
    printer_id: isNullableString(value.printer_id) ? value.printer_id : null,
    started_utc: isString(value.started_utc) ? value.started_utc : isString(value.created_at) ? value.created_at : "",
    eta_utc: isNullableString(value.eta_utc) ? value.eta_utc : null,
    progress: isNumber(value.progress) ? value.progress : rawStatus === "completed" ? 100 : 0,
    proof_ref: isNullableString(value.proof_ref) ? value.proof_ref : null,
  };
}

function normalizeJobStatus(value: string): Job["status"] {
  if (value === "printing" || value === "running" || value === "active") {
    return "printing";
  }
  if (value === "completed" || value === "complete" || value === "done") {
    return "completed";
  }
  if (value === "failed" || value === "error") {
    return "failed";
  }
  if (value === "cancelled" || value === "canceled") {
    return "cancelled";
  }
  if (value === "rolled_back") {
    return "rolled_back";
  }
  return "queued";
}

function parseJobDetail(value: unknown): JobDetail | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  const rawStatus = isString(value.status) ? value.status : "queued";
  return {
    id: value.id,
    title: isString(value.title) ? value.title : isString(value.name) ? value.name : value.id,
    type: isString(value.type) ? value.type : isString(value.job_type) ? value.job_type : "unknown",
    status: normalizeJobDetailStatus(rawStatus),
    dry_run: value.dry_run === true || value.dry_run === 1,
    printer_id: isNullableString(value.printer_id) ? value.printer_id : null,
    created_at: isString(value.created_at) ? value.created_at : "",
    started_at: isNullableString(value.started_at) ? value.started_at : null,
    completed_at: isNullableString(value.completed_at) ? value.completed_at : null,
    steps: Array.isArray(value.steps) ? value.steps.map(parseJobStep).filter(isPresent) : [],
    artifacts: Array.isArray(value.artifacts) ? value.artifacts.map(parseJobArtifact).filter(isPresent) : [],
    events: Array.isArray(value.events) ? value.events.map(parseJobEvent).filter(isPresent) : [],
    approvals: Array.isArray(value.approvals) ? value.approvals.map(parseJobApprovalSummary).filter(isPresent) : [],
    transition_state: parseJobTransitionState(value.transition_state),
  };
}

function parseJobStep(value: unknown): JobDetail["steps"][number] | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  return {
    id: value.id,
    description: isString(value.description) ? value.description : isString(value.name) ? value.name : value.id,
    status: value.status === "running" || value.status === "done" || value.status === "failed" || value.status === "pending" ? value.status : "pending",
    started_at: isNullableString(value.started_at) ? value.started_at : null,
    completed_at: isNullableString(value.completed_at) ? value.completed_at : isNullableString(value.ended_at) ? value.ended_at : null,
    error: isNullableString(value.error) ? value.error : null,
  };
}

function normalizeJobDetailStatus(value: string): JobDetail["status"] {
  if (value === "running" || value === "waiting_approval" || value === "done") {
    return value;
  }
  return normalizeJobStatus(value);
}

function parseJobArtifact(value: unknown): JobDetail["artifacts"][number] | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  const filePath = isString(value.file_path) ? value.file_path : isString(value.path) ? value.path : "";
  return {
    id: value.id,
    name: isString(value.name) ? value.name : isString(value.label) ? value.label : filePath.split(/[\\/]/).at(-1) ?? value.id,
    kind: normalizeJobArtifactKind(isString(value.kind) ? value.kind : isString(value.evidence_type) ? value.evidence_type : "proof"),
    url: isString(value.url) ? value.url : `${LIVE_BASE_URL}/api/artifacts/${encodeURIComponent(value.id)}/download`,
  };
}

function normalizeJobArtifactKind(value: string): JobDetail["artifacts"][number]["kind"] {
  if (value.includes("gcode") || value.includes("g-code")) return "gcode";
  if (value.includes("log")) return "log";
  if (value.includes("report")) return "report";
  if (value.includes("model") || value.includes("mesh")) return "model";
  return "proof";
}

function parseJobEvent(value: unknown): JobDetail["events"][number] | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  return {
    id: value.id,
    type: isString(value.type) ? value.type : isString(value.event_type) ? value.event_type : "event",
    description: isString(value.description) ? value.description : isString(value.message) ? value.message : "",
    timestamp: isString(value.timestamp) ? value.timestamp : isString(value.created_at) ? value.created_at : "",
  };
}

function parseJobApprovalSummary(value: unknown): JobDetail["approvals"][number] | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  return {
    id: value.id,
    approval_type: isString(value.approval_type) ? value.approval_type : "",
    status: value.status === "approved" || value.status === "rejected" ? value.status : "pending",
    requested_at: isString(value.requested_at) ? value.requested_at : "",
    decided_at: isNullableString(value.decided_at) ? value.decided_at : null,
  };
}

function parseJobTransitionState(value: unknown): JobDetail["transition_state"] {
  if (!isRecord(value)) {
    return null;
  }
  const blocker = isRecord(value.blocker) ? value.blocker : {};
  return {
    failed_step_id: isNullableString(value.failed_step_id) ? value.failed_step_id : null,
    failed_step: parseFailedStep(value.failed_step),
    pending_repair_approval_id: isNullableString(value.pending_repair_approval_id) ? value.pending_repair_approval_id : null,
    approved_repair_approval_id: isNullableString(value.approved_repair_approval_id) ? value.approved_repair_approval_id : null,
    rollback_targets: Array.isArray(value.rollback_targets) ? value.rollback_targets.map(parseRollbackTarget).filter(isPresent) : [],
    can_request_repair: value.can_request_repair === true,
    can_apply_repair: value.can_apply_repair === true,
    can_retry: value.can_retry === true,
    can_rollback: value.can_rollback === true,
    blocker: {
      gate: isString(blocker.gate) ? blocker.gate : "UNKNOWN",
      reason: isString(blocker.reason) ? blocker.reason : "Transition state unavailable from backend.",
    },
  };
}

function parseFailedStep(value: unknown): JobTransitionState["failed_step"] {
  if (!isRecord(value)) {
    return null;
  }
  return {
    id: isNullableString(value.id) ? value.id : null,
    name: isNullableString(value.name) ? value.name : null,
    status: isNullableString(value.status) ? value.status : null,
    error: isNullableString(value.error) ? value.error : null,
  };
}

function parseRollbackTarget(value: unknown): JobTransitionState["rollback_targets"][number] | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  return {
    id: value.id,
    label: isNullableString(value.label) ? value.label : null,
    file_path: isNullableString(value.file_path) ? value.file_path : null,
    evidence_type: isNullableString(value.evidence_type) ? value.evidence_type : null,
    gate: isNullableString(value.gate) ? value.gate : null,
  };
}

function parseJobTransitionResult(value: unknown): JobTransitionResult | null {
  if (!isRecord(value) || !isString(value.job_id) || !isString(value.status)) {
    return null;
  }
  return {
    job_id: value.job_id,
    status: value.status,
    proof_event_id: isString(value.proof_event_id) ? value.proof_event_id : undefined,
    approval_id: isString(value.approval_id) ? value.approval_id : undefined,
    target_artifact_id: isString(value.target_artifact_id) ? value.target_artifact_id : undefined,
    created: typeof value.created === "boolean" ? value.created : undefined,
    repair: isRecord(value.repair) ? {
      outcome: isString(value.repair.outcome) ? value.repair.outcome : "",
      strategy_used: isString(value.repair.strategy_used) ? value.repair.strategy_used : "",
      notes: isString(value.repair.notes) ? value.repair.notes : "",
      suggested_action: isRecord(value.repair.suggested_action) ? value.repair.suggested_action : undefined,
    } : undefined,
    detail: value,
  };
}

function parseVoiceAgent(value: unknown): VoiceAgent | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = isString(value.id) ? value.id : isString(value.agent_id) ? value.agent_id : "";
  if (id === "") {
    return null;
  }
  return {
    id,
    name: isString(value.name) ? value.name : isString(value.agent_name) ? value.agent_name : id,
    voice: isString(value.voice) ? value.voice : isString(value.voice_name) ? value.voice_name : "",
    provider: isString(value.provider) ? value.provider : "azure",
  };
}

function parseVoiceCatalog(value: unknown): VoiceCatalog | null {
  if (!isRecord(value)) {
    return null;
  }
  const voices = Array.isArray(value.voices) ? value.voices.map(parseAzureVoice).filter(isPresent) : [];
  const status = normalizeVoiceCatalogStatus(value.status);
  return {
    provider: "azure",
    configured: value.configured === true,
    status,
    region: isNullableString(value.region) ? value.region : null,
    reason: isString(value.reason) ? value.reason : undefined,
    count: isNumber(value.count) ? value.count : voices.length,
    voices,
  };
}

function parseAzureVoice(value: unknown): AzureVoice | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = isString(value.id) ? value.id : isString(value.short_name) ? value.short_name : "";
  const locale = isString(value.locale) ? value.locale : "";
  if (id === "" || locale === "") {
    return null;
  }
  return {
    id,
    shortName: isString(value.shortName) ? value.shortName : isString(value.short_name) ? value.short_name : id,
    displayName: isString(value.displayName) ? value.displayName : isString(value.display_name) ? value.display_name : id,
    localName: isString(value.localName) ? value.localName : isString(value.local_name) ? value.local_name : "",
    locale,
    gender: isString(value.gender) ? value.gender : "",
    styles: isStringArray(value.styles) ? value.styles : [],
  };
}

function parseVoicePreviewResult(value: unknown, responseOk: boolean): VoicePreviewResult | null {
  if (!isRecord(value)) {
    return null;
  }
  const status = normalizeVoicePreviewStatus(value.status);
  return {
    accepted: responseOk && status === "ready" && isString(value.audio_base64),
    status,
    reason: isString(value.reason) ? value.reason : undefined,
    voice: isString(value.voice) ? value.voice : undefined,
    mimeType: isString(value.mime_type) ? value.mime_type : undefined,
    audioBase64: isString(value.audio_base64) ? value.audio_base64 : undefined,
    bytes: isNumber(value.bytes) ? value.bytes : undefined,
    proofEventId: isString(value.proof_event_id) ? value.proof_event_id : undefined,
  };
}

function normalizeVoiceCatalogStatus(value: unknown): VoiceCatalog["status"] {
  if (value === "ready" || value === "not_configured" || value === "unreachable" || value === "azure_error") {
    return value;
  }
  return "unreachable";
}

function normalizeVoicePreviewStatus(value: unknown): VoicePreviewResult["status"] {
  if (
    value === "ready" ||
    value === "not_configured" ||
    value === "not_installed" ||
    value === "unreachable" ||
    value === "azure_error" ||
    value === "invalid_response"
  ) {
    return value;
  }
  return "invalid_response";
}

function parseAgentHealth(value: unknown): AgentHealthResult | null {
  if (!isRecord(value)) {
    return null;
  }
  const healthy = typeof value.healthy === "boolean" ? value.healthy : value.status === "ready";
  const status = isString(value.status) ? value.status : healthy ? "ready" : "unknown";
  const setup = isRecord(value.setup) ? value.setup : undefined;
  return {
    available: true,
    healthy,
    status,
    reason: detailMessage(value) ?? agentHealthReason(status, healthy, setup),
    agents: parseStringRecord(value.agents),
    setup,
    detail: value,
  };
}

function parseAgentConfigSave(value: unknown): AgentConfigSaveResult | null {
  if (!isRecord(value)) {
    return null;
  }
  const saved = value.saved === true;
  const status = saved ? "saved" : isString(value.status) ? value.status : "blocked";
  return {
    available: true,
    saved,
    status,
    reason: detailMessage(value) ?? (saved ? "Agent policy saved to /api/agents/config." : `Agent config status: ${status}.`),
    redacted: isStringArray(value.redacted) ? value.redacted : [],
    detail: value,
  };
}

function unavailableAgentHealth(reason: string): AgentHealthResult {
  return {
    available: false,
    healthy: false,
    status: "unavailable",
    reason,
    agents: {},
  };
}

function unavailableUpdateStatus(reason: string): HermesAgentUpdateStatus {
  return {
    available: false,
    repo_url: "https://github.com/NousResearch/hermes-agent",
    checkout_path: "",
    repo_ready: false,
    current: { repo_ready: false, reason },
    latest_release: {},
    outdated: false,
    outdated_by: 0,
    pending_tags: [],
    backup_available: false,
    latest_backup: null,
    strategy: "unavailable",
    rollback: "unavailable",
    reason,
  };
}

function unavailableDesktopUpdateStatus(reason: string): HermesDesktopUpdateStatus {
  return {
    available: false,
    repo_url: "https://github.com/fathah/hermes-desktop",
    checkout_path: "",
    source_ready: false,
    git_ready: false,
    current: { source_ready: false, git_ready: false, reason },
    latest_release: {},
    outdated: false,
    strategy: "unavailable",
    installer_download_supported: false,
    installer_verification_supported: false,
    source_update_supported: false,
    backup_available: false,
    latest_backup: null,
    reason,
  };
}

async function postUpdateAction(path: string, body: unknown): Promise<HermesAgentUpdateResult> {
  try {
    const payload = await postJsonWithResult(path, body);
    return parseHermesAgentUpdateResult(payload) ?? {
      available: true,
      status: "invalid_response",
      reason: "Hermes Agent update response was not in the expected shape.",
      detail: payload,
    };
  } catch (error) {
    return {
      available: false,
      status: "unreachable",
      reason: errorMessage(error),
    };
  }
}

function parseHermesDesktopUpdateStatus(value: unknown): HermesDesktopUpdateStatus | null {
  if (!isRecord(value) || !isString(value.repo_url) || !isString(value.checkout_path)) {
    return null;
  }
  const current = isRecord(value.current) ? value.current : {};
  const latest = isRecord(value.latest_release) ? value.latest_release : {};
  const installer = isRecord(latest.installer_asset) ? latest.installer_asset : null;
  return {
    available: true,
    repo_url: value.repo_url,
    checkout_path: value.checkout_path,
    source_ready: value.source_ready === true,
    git_ready: value.git_ready === true,
    current: {
      source_ready: typeof current.source_ready === "boolean" ? current.source_ready : undefined,
      git_ready: typeof current.git_ready === "boolean" ? current.git_ready : undefined,
      reason: isNullableString(current.reason) ? current.reason : null,
      package_name: isNullableString(current.package_name) ? current.package_name : null,
      package_version: isNullableString(current.package_version) ? current.package_version : null,
      commit: isNullableString(current.commit) ? current.commit : null,
      exact_tag: isNullableString(current.exact_tag) ? current.exact_tag : null,
      nearest_tag: isNullableString(current.nearest_tag) ? current.nearest_tag : null,
      dirty: typeof current.dirty === "boolean" ? current.dirty : null,
    },
    latest_release: {
      tag: isNullableString(latest.tag) ? latest.tag : null,
      name: isNullableString(latest.name) ? latest.name : null,
      published_at: isNullableString(latest.published_at) ? latest.published_at : null,
      html_url: isNullableString(latest.html_url) ? latest.html_url : null,
      installer_asset: installer ? {
        name: isNullableString(installer.name) ? installer.name : null,
        size: isNumber(installer.size) ? installer.size : null,
        digest: isNullableString(installer.digest) ? installer.digest : null,
        browser_download_url: isNullableString(installer.browser_download_url) ? installer.browser_download_url : null,
      } : null,
    },
    outdated: value.outdated === true,
    strategy: isString(value.strategy) ? value.strategy : "",
    installer_download_supported: value.installer_download_supported === true,
    installer_verification_supported: value.installer_verification_supported === true,
    source_update_supported: value.source_update_supported === true,
    backup_available: value.backup_available === true,
    latest_backup: parseHermesDesktopBackup(value.latest_backup),
    reason: isString(value.reason) ? value.reason : undefined,
    detail: value,
  };
}

function parseHermesDesktopBackup(value: unknown): HermesDesktopBackup | null {
  if (!isRecord(value) || !isString(value.backup_id)) {
    return null;
  }
  return {
    backup_id: value.backup_id,
    created_at: isString(value.created_at) ? value.created_at : "",
    note: isString(value.note) ? value.note : "",
    checkout_path: isString(value.checkout_path) ? value.checkout_path : "",
    package_version: isNullableString(value.package_version) ? value.package_version : null,
    tag: isNullableString(value.tag) ? value.tag : null,
    commit: isNullableString(value.commit) ? value.commit : null,
    git_ready: value.git_ready === true,
    bundle_path: isNullableString(value.bundle_path) ? value.bundle_path : null,
    source_zip_path: isNullableString(value.source_zip_path) ? value.source_zip_path : null,
  };
}

function parseHermesDesktopDownload(value: unknown): HermesDesktopDownload | null {
  if (!isRecord(value) || !isString(value.asset_name) || !isString(value.path) || !isString(value.sha256)) {
    return null;
  }
  return {
    downloaded: value.downloaded === true,
    asset_name: value.asset_name,
    path: value.path,
    size_bytes: isNumber(value.size_bytes) ? value.size_bytes : 0,
    sha256: value.sha256,
    expected_sha256: isNullableString(value.expected_sha256) ? value.expected_sha256 : null,
    verification_status: isString(value.verification_status) ? value.verification_status : "",
    next_step: isString(value.next_step) ? value.next_step : "",
  };
}

function parseAgentAttachmentUpload(value: unknown): AgentAttachmentUpload | null {
  if (!isRecord(value) || value.uploaded !== true || !isRecord(value.artifact)) {
    return null;
  }
  const artifact = value.artifact;
  if (!isString(artifact.id) || !isString(artifact.file_path) || !isString(artifact.evidence_type)) {
    return null;
  }
  return {
    uploaded: true,
    artifact: {
      id: artifact.id,
      label: isNullableString(artifact.label) ? artifact.label : null,
      file_path: artifact.file_path,
      file_size: isNumber(artifact.file_size) ? artifact.file_size : 0,
      evidence_type: artifact.evidence_type,
      agent: isNullableString(artifact.agent) ? artifact.agent : null,
      stage: isNullableString(artifact.stage) ? artifact.stage : null,
      notes: isNullableString(artifact.notes) ? artifact.notes : null,
      created_at: isString(artifact.created_at) ? artifact.created_at : undefined,
    },
  };
}

function parseHermesAgentUpdateStatus(value: unknown): HermesAgentUpdateStatus | null {
  if (!isRecord(value) || !isString(value.repo_url) || !isString(value.checkout_path)) {
    return null;
  }
  const current = isRecord(value.current) ? value.current : {};
  const latest = isRecord(value.latest_release) ? value.latest_release : {};
  return {
    available: true,
    repo_url: value.repo_url,
    checkout_path: value.checkout_path,
    repo_ready: value.repo_ready === true,
    current: {
      repo_ready: typeof current.repo_ready === "boolean" ? current.repo_ready : undefined,
      commit: isString(current.commit) ? current.commit : undefined,
      exact_tag: isNullableString(current.exact_tag) ? current.exact_tag : null,
      nearest_tag: isNullableString(current.nearest_tag) ? current.nearest_tag : null,
      branch: isString(current.branch) ? current.branch : undefined,
      dirty: typeof current.dirty === "boolean" ? current.dirty : undefined,
      dirty_entries: isStringArray(current.dirty_entries) ? current.dirty_entries : [],
      reason: isString(current.reason) ? current.reason : undefined,
    },
    latest_release: {
      tag: isNullableString(latest.tag) ? latest.tag : null,
      name: isNullableString(latest.name) ? latest.name : null,
      published_at: isNullableString(latest.published_at) ? latest.published_at : null,
      html_url: isNullableString(latest.html_url) ? latest.html_url : null,
      source: isString(latest.source) ? latest.source : undefined,
    },
    outdated: value.outdated === true,
    outdated_by: isNumber(value.outdated_by) ? value.outdated_by : 0,
    pending_tags: isStringArray(value.pending_tags) ? value.pending_tags : [],
    backup_available: value.backup_available === true,
    latest_backup: parseHermesAgentBackup(value.latest_backup),
    strategy: isString(value.strategy) ? value.strategy : "",
    rollback: isString(value.rollback) ? value.rollback : "",
    reason: isString(value.reason) ? value.reason : undefined,
    detail: value,
  };
}

function parseHermesAgentBackup(value: unknown): HermesAgentBackup | null {
  if (!isRecord(value) || !isString(value.backup_id) || !isString(value.commit)) {
    return null;
  }
  return {
    backup_id: value.backup_id,
    created_at: isString(value.created_at) ? value.created_at : "",
    note: isString(value.note) ? value.note : "",
    checkout_path: isString(value.checkout_path) ? value.checkout_path : "",
    bundle_path: isString(value.bundle_path) ? value.bundle_path : "",
    dirty_zip_path: isNullableString(value.dirty_zip_path) ? value.dirty_zip_path : null,
    tag: isNullableString(value.tag) ? value.tag : null,
    commit: value.commit,
    dirty: value.dirty === true,
    dirty_entries: isStringArray(value.dirty_entries) ? value.dirty_entries : [],
  };
}

function parseHermesAgentUpdateResult(value: unknown): HermesAgentUpdateResult | null {
  if (!isRecord(value)) {
    return null;
  }
  return {
    available: true,
    status: isString(value.status) ? value.status : value.updated === true ? "updated" : "unknown",
    updated: typeof value.updated === "boolean" ? value.updated : undefined,
    backup: parseHermesAgentBackup(value.backup),
    steps: Array.isArray(value.steps) ? value.steps.map(parseUpdateStep).filter(isPresent) : [],
    current: isRecord(value.current) ? parseHermesAgentUpdateStatus({ repo_url: "", checkout_path: "", repo_ready: true, current: value.current, latest_release: {}, outdated: false, outdated_by: 0, pending_tags: [], backup_available: false, latest_backup: null, strategy: "", rollback: "" })?.current : undefined,
    latest_release: isRecord(value.latest_release) ? parseHermesAgentUpdateStatus({ repo_url: "", checkout_path: "", repo_ready: true, current: {}, latest_release: value.latest_release, outdated: false, outdated_by: 0, pending_tags: [], backup_available: false, latest_backup: null, strategy: "", rollback: "" })?.latest_release : undefined,
    remaining_tags: isStringArray(value.remaining_tags) ? value.remaining_tags : [],
    reason: detailMessage(value) ?? (isString(value.reason) ? value.reason : undefined),
    detail: value,
  };
}

function parseUpdateStep(value: unknown): { tag: string; ok: boolean; checks: Array<{ name: string; status: string; output?: string }> } | null {
  if (!isRecord(value) || !isString(value.tag)) {
    return null;
  }
  return {
    tag: value.tag,
    ok: value.ok === true,
    checks: Array.isArray(value.checks) ? value.checks.map(parseUpdateCheck).filter(isPresent) : [],
  };
}

function parseUpdateCheck(value: unknown): { name: string; status: string; output?: string } | null {
  if (!isRecord(value) || !isString(value.name) || !isString(value.status)) {
    return null;
  }
  return {
    name: value.name,
    status: value.status,
    output: isString(value.output) ? value.output : undefined,
  };
}

function agentHealthReason(status: string, healthy: boolean, setup?: Record<string, unknown>): string {
  if (healthy) {
    return "Agent runtime is ready.";
  }
  const env = setup && isString(setup.env) ? setup.env : null;
  if (status === "not_configured" && env) {
    return `Agent runtime is not configured; set ${env}.`;
  }
  return `Agent runtime status: ${status}.`;
}

function parseStringRecord(value: unknown): Record<string, string> {
  if (!isRecord(value)) {
    return {};
  }
  return Object.fromEntries(Object.entries(value).filter(([, entry]) => isString(entry))) as Record<string, string>;
}

function httpFailureReason(value: unknown, response: Response, label: string): string {
  return detailMessage(value) ?? `${label} failed with HTTP ${response.status}${response.statusText ? ` ${response.statusText}` : ""}.`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown network error.";
}

function parseLearningConfig(value: unknown): LearningConfig | null {
  if (!isRecord(value)) {
    return null;
  }
  const enabled = value.enabled === true;
  const active = value.active === true;
  const idleMinutes = isNumber(value.idle_minutes) ? value.idle_minutes : 30;
  return {
    enabled,
    active,
    mode: active ? "active" : enabled ? "idle-research-reporting" : "disabled",
    idle_minutes: idleMinutes,
    reports_directory: isString(value.reports_directory) ? value.reports_directory : "var/hermes3d.db/learning/reports",
    next_topic: isNullableString(value.next_topic) ? value.next_topic : null,
    runner_status: isString(value.runner_status) ? value.runner_status : undefined,
    reason: isNullableString(value.reason) ? value.reason : null,
  };
}

function parseLearningReport(value: unknown): ReportMeta | null {
  if (!isRecord(value) || !isString(value.filename)) {
    return null;
  }
  return {
    id: isString(value.id) ? value.id : value.filename,
    filename: value.filename,
    title: isString(value.title) ? value.title : value.filename.replace(/\.md$/i, ""),
    created_at: isString(value.created_at) ? value.created_at : "",
    size_bytes: isNumber(value.size_bytes) ? value.size_bytes : 0,
    preview_url: isString(value.preview_url) ? value.preview_url : `${LIVE_BASE_URL}/api/learning/reports/${encodeURIComponent(value.filename)}`,
  };
}

function parseLearningReportContent(value: unknown, fallbackFilename: string): LearningReportContent | null {
  if (!isRecord(value) || !isString(value.content)) {
    return null;
  }
  return {
    filename: isString(value.filename) ? value.filename : fallbackFilename,
    content: value.content,
  };
}

function parseIdleWorkbenchState(value: unknown): IdleWorkbenchState | null {
  if (!isRecord(value) || !Array.isArray(value.blockers) || !Array.isArray(value.candidates) || !isString(value.review_policy)) {
    return null;
  }
  const blockers = value.blockers.map(parseIdleWorkbenchBlocker).filter(isPresent);
  const candidates = value.candidates.map(parseIdleWorkbenchCandidate).filter(isPresent);
  const dailyPrompt = isRecord(value.daily_prompt) ? value.daily_prompt : {};
  return {
    status: isString(value.status) ? value.status : "ready",
    review_policy: value.review_policy,
    blockers,
    candidates,
    automation: parseIdleAutomationReadiness(value.automation) ?? undefined,
    daily_prompt: {
      question: isString(dailyPrompt.question) ? dailyPrompt.question : "What should Hermes3D improve while idle?",
      last_candidate_at: isNullableString(dailyPrompt.last_candidate_at) ? dailyPrompt.last_candidate_at : null,
      suggested_kinds: isStringArray(dailyPrompt.suggested_kinds) ? dailyPrompt.suggested_kinds : [],
    },
  };
}

function parseIdleAutomationReadiness(value: unknown): IdleAutomationReadiness | null {
  if (!isRecord(value) || !Array.isArray(value.capabilities)) {
    return null;
  }
  return {
    runner_status: isString(value.runner_status) ? value.runner_status : "not_configured",
    runner_reason: isNullableString(value.runner_reason) ? value.runner_reason : null,
    agent_runtime_status: isString(value.agent_runtime_status) ? value.agent_runtime_status : "not_configured",
    agent_runtime_reason: isNullableString(value.agent_runtime_reason) ? value.agent_runtime_reason : null,
    capabilities: value.capabilities.map(parseIdleAutomationCapability).filter(isPresent),
  };
}

function parseIdleAutomationCapability(value: unknown): IdleAutomationCapability | null {
  if (!isRecord(value) || !isString(value.kind) || !isString(value.label)) {
    return null;
  }
  return {
    kind: value.kind,
    label: value.label,
    agent_id: isString(value.agent_id) ? value.agent_id : "research-agent",
    queue_enabled: value.queue_enabled === true,
    execution_status: isString(value.execution_status) ? value.execution_status : "blocked",
    missing: isStringArray(value.missing) ? value.missing : [],
    proof_required: value.proof_required === true,
    safety_scope: isString(value.safety_scope) ? value.safety_scope : "queue-only until proof gates pass",
  };
}

function parseIdleWorkbenchBlocker(value: unknown): IdleWorkbenchBlocker | null {
  if (!isRecord(value) || !isString(value.type) || !isString(value.reason)) {
    return null;
  }
  return {
    type: value.type,
    id: isNullableString(value.id) ? value.id : null,
    label: isString(value.label) ? value.label : value.type,
    status: isString(value.status) ? value.status : "unknown",
    reason: value.reason,
  };
}

function parseIdleWorkbenchCandidate(value: unknown): IdleWorkbenchCandidate | null {
  if (!isRecord(value) || !isString(value.id) || !isString(value.title) || !isString(value.summary)) {
    return null;
  }
  return {
    id: value.id,
    title: value.title,
    kind: isString(value.kind) ? value.kind : "research",
    agent_id: isString(value.agent_id) ? value.agent_id : "research-agent",
    status: isIdleCandidateStatus(value.status) ? value.status : "queued",
    risk_level: isString(value.risk_level) ? value.risk_level : "low",
    summary: value.summary,
    source: isString(value.source) ? value.source : "operator",
    source_url: isNullableString(value.source_url) ? value.source_url : null,
    target_tab: isNullableString(value.target_tab) ? value.target_tab : null,
    target_files: isStringArray(value.target_files) ? value.target_files : [],
    branch_ref: isNullableString(value.branch_ref) ? value.branch_ref : null,
    gate_status: isRecord(value.gate_status) ? value.gate_status : {},
    proof_event_ids: isStringArray(value.proof_event_ids) ? value.proof_event_ids : [],
    approval_id: isNullableString(value.approval_id) ? value.approval_id : null,
    blocked_reason: isNullableString(value.blocked_reason) ? value.blocked_reason : null,
    created_by: isString(value.created_by) ? value.created_by : "operator",
    created_at: isString(value.created_at) ? value.created_at : "",
    updated_at: isString(value.updated_at) ? value.updated_at : "",
  };
}

function parseIdleCandidateMutationResult(value: unknown): IdleCandidateMutationResult | null {
  if (!isRecord(value) || !isString(value.status)) {
    return null;
  }
  const report = isRecord(value.report) &&
    isString(value.report.filename) &&
    isString(value.report.path) &&
    isNumber(value.report.size_bytes) &&
    isString(value.report.sha256)
    ? {
      filename: value.report.filename,
      path: value.report.path,
      size_bytes: value.report.size_bytes,
      sha256: value.report.sha256,
    }
    : null;
  return {
    accepted: value.accepted === true,
    status: value.status,
    reason: isNullableString(value.reason) ? value.reason : null,
    decision: isString(value.decision) ? value.decision : undefined,
    approval_id: isNullableString(value.approval_id) ? value.approval_id : undefined,
    proof_event_id: isNullableString(value.proof_event_id) ? value.proof_event_id : undefined,
    candidate: parseIdleWorkbenchCandidate(value.candidate),
    blockers: Array.isArray(value.blockers) ? value.blockers.map(parseIdleWorkbenchBlocker).filter(isPresent) : undefined,
    report,
    artifact_id: isNullableString(value.artifact_id) ? value.artifact_id : undefined,
  };
}

function parseServiceHealthArray(payload: unknown): ServiceHealthEntry[] | null {
  if (!isRecord(payload) || !Array.isArray(payload.results)) {
    return null;
  }
  const parsed = payload.results.map(parseServiceHealthEntry);
  if (parsed.some((entry) => entry == null)) {
    return null;
  }
  return parsed as ServiceHealthEntry[];
}

function parseServiceHealthEntry(value: unknown): ServiceHealthEntry | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.name) ||
    !isServiceCategory(value.category) ||
    !isString(value.host) ||
    !isNumber(value.port) ||
    !isServiceStatus(value.status) ||
    !isString(value.detail) ||
    !isNumber(value.latency_ms) ||
    !isString(value.probed_at)
  ) {
    return null;
  }
  return {
    name: value.name,
    category: value.category,
    host: value.host,
    port: value.port,
    status: value.status,
    detail: value.detail,
    latency_ms: value.latency_ms,
    probed_at: value.probed_at,
  };
}

function isServiceStatus(value: unknown): value is ServiceStatus {
  return typeof value === "string" && SERVICE_STATUSES.has(value as ServiceStatus);
}

function isServiceCategory(value: unknown): value is ServiceCategory {
  return typeof value === "string" && SERVICE_CATEGORIES.has(value as ServiceCategory);
}

function parsePrinterArray(payload: unknown): Printer[] | null {
  if (!Array.isArray(payload)) {
    return null;
  }
  const printers = payload.map(parsePrinter);
  if (printers.some((printer) => printer == null)) {
    return null;
  }
  return printers as Printer[];
}

function parsePrinter(value: unknown): Printer | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.id) ||
    !isString(value.name) ||
    !isModel(value.model) ||
    !isNullableString(value.ip) ||
    !isStatus(value.status) ||
    !isAdapter(value.adapter) ||
    !isDataSource(value.data_source) ||
    !isNullableNumber(value.temp_hot) ||
    !isNullableNumber(value.temp_bed) ||
    !isNullableNumber(value.progress) ||
    !isNullableString(value.current_job) ||
    typeof value.maintenance_flag !== "boolean" ||
    !isNullableString(value.camera_url)
  ) {
    return null;
  }
  return {
    id: value.id,
    name: value.name,
    model: value.model,
    ip: value.ip,
    status: value.status,
    adapter: value.adapter,
    data_source: value.data_source,
    temp_hot: value.temp_hot,
    temp_bed: value.temp_bed,
    progress: value.progress,
    current_job: value.current_job,
    maintenance_flag: value.maintenance_flag,
    camera_url: value.camera_url,
    moonraker_url: isNullableString(value.moonraker_url) ? value.moonraker_url : undefined,
    safety_policy: isString(value.safety_policy) ? value.safety_policy : undefined,
    write_enabled: typeof value.write_enabled === "boolean" ? value.write_enabled : undefined,
    onboarded: typeof value.onboarded === "boolean" ? value.onboarded : undefined,
    status_source: isString(value.status_source) ? value.status_source : undefined,
    source_refs: parsePrinterSourceRefs(value.source_refs),
  };
}

function parsePrinterOnboardResult(value: unknown): PrinterOnboardResult | null {
  if (!isRecord(value) || value.created !== true) {
    return null;
  }
  const printer = parsePrinter(value.printer);
  if (!printer) {
    return null;
  }
  return {
    created: true,
    printer,
    probe_summary: probeSummaryFromDetail(value.probe_summary),
    proof_event_id: isString(value.proof_event_id) ? value.proof_event_id : null,
  };
}

function probeSummaryFromDetail(value: unknown): PrinterOnboardResult["probe_summary"] {
  if (!isRecord(value)) {
    return null;
  }
  return {
    ok: typeof value.ok === "boolean" ? value.ok : undefined,
    required_probes: isStringArray(value.required_probes) ? value.required_probes : undefined,
    probes: Array.isArray(value.probes) ? value.probes.filter(isRecord).map((probe) => ({
      name: isString(probe.name) ? probe.name : "unknown",
      ok: probe.ok === true,
      required: typeof probe.required === "boolean" ? probe.required : undefined,
      http_status: isNullableNumber(probe.http_status) ? probe.http_status : undefined,
      reason: isString(probe.reason) ? probe.reason : undefined,
      klippy_connected: typeof probe.klippy_connected === "boolean" ? probe.klippy_connected : undefined,
      klippy_state: isString(probe.klippy_state) ? probe.klippy_state : undefined,
      moonraker_version: isString(probe.moonraker_version) ? probe.moonraker_version : undefined,
      api_version: isString(probe.api_version) ? probe.api_version : undefined,
      print_state: isString(probe.print_state) ? probe.print_state : undefined,
      filename: isNullableString(probe.filename) ? probe.filename : undefined,
      progress: isNumber(probe.progress) ? probe.progress : undefined,
    })) : undefined,
  };
}

function failedProbeFromDetail(value: unknown): string | null {
  if (isRecord(value) && isString(value.failed_probe)) {
    return value.failed_probe;
  }
  return null;
}

function parsePrinterSourceRefs(value: unknown): Printer["source_refs"] {
  if (!isRecord(value)) {
    return {};
  }
  const profiles = isRecord(value.profiles_detected)
    ? Object.fromEntries(Object.entries(value.profiles_detected).filter(([, detected]) => typeof detected === "boolean")) as Record<string, boolean>
    : undefined;
  const installed = isRecord(value.installed_profiles)
    ? Object.fromEntries(Object.entries(value.installed_profiles).filter(([, path]) => typeof path === "string")) as Record<string, string>
    : undefined;
  return {
    official_wiki_url: isString(value.official_wiki_url) ? value.official_wiki_url : undefined,
    official_setup_topics: isStringArray(value.official_setup_topics) ? value.official_setup_topics : undefined,
    flsun_slicer_install: isString(value.flsun_slicer_install) ? value.flsun_slicer_install : undefined,
    source_profile_ini: isString(value.source_profile_ini) ? value.source_profile_ini : undefined,
    source_profile_ini_detected: typeof value.source_profile_ini_detected === "boolean" ? value.source_profile_ini_detected : undefined,
    profiles_detected: profiles,
    installed_profiles: installed,
    safety: isString(value.safety) ? value.safety : undefined,
  };
}

function parseGcodeUploadResult(value: unknown, fallbackId: string): GcodeUploadResult | null {
  if (!isRecord(value)) {
    return null;
  }
  if (typeof value.accepted !== "boolean" || typeof value.uploaded !== "boolean" || typeof value.started !== "boolean") {
    return null;
  }
  return {
    printer_id: isString(value.printer_id) ? value.printer_id : fallbackId,
    accepted: value.accepted,
    uploaded: value.uploaded,
    started: value.started,
    status: isString(value.status) ? value.status : undefined,
    reason: isString(value.reason) ? value.reason : undefined,
    detail: value.detail,
    moonraker_url: isString(value.moonraker_url) ? value.moonraker_url : undefined,
    item_path: isString(value.item_path) ? value.item_path : undefined,
    gcode_path: isString(value.gcode_path) ? value.gcode_path : undefined,
    gcode_sha256: isString(value.gcode_sha256) ? value.gcode_sha256 : undefined,
    gcode_bytes: isNumber(value.gcode_bytes) ? value.gcode_bytes : undefined,
    bounds_passed: typeof value.bounds_passed === "boolean" ? value.bounds_passed : undefined,
    used_fallback_bounds: typeof value.used_fallback_bounds === "boolean" ? value.used_fallback_bounds : undefined,
    klippy_state: isString(value.klippy_state) ? value.klippy_state : undefined,
  };
}

function detailMessage(value: unknown): string | null {
  if (!isRecord(value) || value.detail == null) {
    return null;
  }
  if (typeof value.detail === "string") {
    return value.detail;
  }
  if (isRecord(value.detail)) {
    if (typeof value.detail.reason === "string") {
      return value.detail.reason;
    }
    if (typeof value.detail.error === "string") {
      return value.detail.error;
    }
  }
  return JSON.stringify(value.detail);
}

function parseTaskDAG(value: unknown): TaskDAG | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.dag_id) ||
    !isString(value.run_id) ||
    !Array.isArray(value.nodes) ||
    !Array.isArray(value.edges) ||
    !isNumber(value.max_depth) ||
    !isNumber(value.max_fanout) ||
    !isRecord(value.metadata)
  ) {
    return null;
  }
  const nodes = value.nodes.map(parseTaskNode);
  const edges = value.edges.map(parseTaskEdge);
  if (nodes.some((node) => node == null) || edges.some((edge) => edge == null)) {
    return null;
  }
  return {
    dag_id: value.dag_id,
    run_id: value.run_id,
    nodes: nodes as TaskNode[],
    edges: edges as TaskEdge[],
    max_depth: value.max_depth,
    max_fanout: value.max_fanout,
    metadata: value.metadata,
  };
}

function parseTaskNode(value: unknown): TaskNode | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.node_id) ||
    !isString(value.tool) ||
    !isString(value.kind) ||
    !isRecord(value.inputs) ||
    !isNumber(value.retry_budget) ||
    !isStringArray(value.gate_set) ||
    !isStringArray(value.depends_on)
  ) {
    return null;
  }
  return {
    node_id: value.node_id,
    tool: value.tool,
    kind: value.kind,
    inputs: value.inputs,
    retry_budget: value.retry_budget,
    gate_set: value.gate_set,
    depends_on: value.depends_on,
  };
}

function parseTaskEdge(value: unknown): TaskEdge | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.from_node) ||
    !isString(value.to_node) ||
    !isString(value.condition)
  ) {
    return null;
  }
  return {
    from_node: value.from_node,
    to_node: value.to_node,
    condition: value.condition,
  };
}

function parseProviderHealthArray(payload: unknown): ProviderHealth[] | null {
  if (!isRecord(payload) || !Array.isArray(payload.providers)) {
    return null;
  }
  const providers = payload.providers.map(parseProviderHealth);
  if (providers.some((provider) => provider == null)) {
    return null;
  }
  return providers as ProviderHealth[];
}

function parseProviderHealth(value: unknown): ProviderHealth | null {
  if (!isRecord(value)) {
    return null;
  }
  const status = value.status;
  if (status !== "green" && status !== "amber" && status !== "red" && status !== "idle") {
    return null;
  }
  if (!isString(value.provider_id) || typeof value.stale !== "boolean") {
    return null;
  }
  if (!isNullableString(value.last_probe_utc)) {
    return null;
  }
  if (!isNullableNumber(value.http_status) || !isNullableNumber(value.latency_ms)) {
    return null;
  }
  return {
    provider_id: value.provider_id,
    status,
    last_probe_utc: value.last_probe_utc,
    http_status: value.http_status,
    latency_ms: value.latency_ms,
    stale: value.stale,
  };
}

function parseAgent(value: unknown): Agent | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  return {
    id: value.id,
    role: isString(value.name) ? value.name : value.id,
    status: isAgentStatus(value.status) ? value.status : "idle",
    task_count: isNumber(value.task_count) ? value.task_count : 0,
    last_activity_utc: isString(value.last_activity_utc) ? value.last_activity_utc : "",
    model_provider: isString(value.model_provider) ? value.model_provider : "",
  };
}

function parseNotification(value: unknown): Notification | null {
  if (!isRecord(value) || !isString(value.id) || !isString(value.title)) {
    return null;
  }
  const message = isString(value.body) ? value.body : isString(value.message) ? value.message : "";
  const tsUtc = isString(value.created_at) ? value.created_at : isString(value.ts_utc) ? value.ts_utc : "";
  return {
    id: value.id,
    ts_utc: tsUtc,
    severity: notificationSeverity(value.type, value.priority),
    title: value.title,
    message,
    read: value.read_at != null,
    type: isNotificationType(value.type) ? value.type : undefined,
    priority: isNotificationPriority(value.priority) ? value.priority : undefined,
    body: isString(value.body) ? value.body : undefined,
    source_agent_id: isNullableString(value.source_agent_id) ? value.source_agent_id : null,
    source_tab: isNullableString(value.source_tab) ? value.source_tab : null,
    action_url: isNullableString(value.action_url) ? value.action_url : null,
    action_label: isNullableString(value.action_label) ? value.action_label : null,
    created_at: isString(value.created_at) ? value.created_at : undefined,
    read_at: isNullableString(value.read_at) ? value.read_at : null,
    dismissed_at: isNullableString(value.dismissed_at) ? value.dismissed_at : null,
  };
}

function parseArtifactsPayload(payload: unknown): Artifact[] {
  if (Array.isArray(payload)) {
    return payload.map((item) => parseArtifact(item)).filter(isPresent);
  }
  if (!isRecord(payload)) {
    return [];
  }
  return Object.entries(payload).flatMap(([jobTitle, rows]) => {
    if (!Array.isArray(rows)) {
      return [];
    }
    return rows.map((row) => parseArtifact(row, jobTitle)).filter(isPresent);
  });
}

function parseArtifact(value: unknown, groupedJobTitle?: string): Artifact | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  const evidenceType = value.type ?? value.evidence_type;
  const jobId = value.jobId ?? value.job_id ?? (evidenceType === "agent_attachment" ? `agent:${String(value.agent ?? "chat")}` : null);
  const filePath = value.path ?? value.file_path;
  const stage = value.stage;
  if (
    !(isString(jobId) || isNumber(jobId)) ||
    !isArtifactType(evidenceType) ||
    !isString(filePath) ||
    !isArtifactStage(stage)
  ) {
    return null;
  }
  const fileName = isString(value.name) ? value.name : filePath.split(/[\\/]/).at(-1) ?? value.id;
  return {
    id: value.id,
    jobId,
    jobTitle: isString(value.jobTitle) ? value.jobTitle : groupedJobTitle ?? String(jobId),
    type: evidenceType,
    name: fileName,
    path: filePath,
    stage,
    gate: isArtifactGate(value.gate) ? value.gate : null,
    agent: isNullableString(value.agent) ? value.agent : null,
    label: isNullableString(value.label) ? value.label : null,
    notes: isNullableString(value.notes) ? value.notes : null,
    sizeBytes: isNumber(value.sizeBytes) ? value.sizeBytes : isNumber(value.file_size) ? value.file_size : 0,
    createdAt: isString(value.createdAt) ? value.createdAt : isString(value.created_at) ? value.created_at : "",
    downloadUrl: isString(value.downloadUrl) ? value.downloadUrl : `${LIVE_BASE_URL}/api/artifacts/${encodeURIComponent(value.id)}/download`,
  };
}

function unavailableArtifact(form: EvidenceForm, notes: string): Artifact {
  return {
    id: "unavailable",
    jobId: form.jobId,
    jobTitle: "Unavailable",
    type: form.evidenceType,
    name: form.label,
    path: "",
    stage: form.stage,
    gate: form.gate,
    agent: form.agent,
    label: form.label,
    notes,
    sizeBytes: 0,
    createdAt: "",
    downloadUrl: "",
  };
}

function parseSourceModuleRuntimeSetupQueue(value: unknown): SourceModuleRuntimeSetupQueue | null {
  if (!isRecord(value) || !isRecord(value.counts) || !Array.isArray(value.records)) {
    return null;
  }
  return {
    accepted: value.accepted === true,
    status: isString(value.status) ? value.status : "blocked",
    section: isNullableString(value.section) ? value.section : null,
    count: isNumber(value.count) ? value.count : value.records.length,
    counts: {
      runtime_ready: isNumber(value.counts.runtime_ready) ? value.counts.runtime_ready : 0,
      source_ready: isNumber(value.counts.source_ready) ? value.counts.source_ready : 0,
      runner_not_registered: isNumber(value.counts.runner_not_registered) ? value.counts.runner_not_registered : 0,
      source_install_available: isNumber(value.counts.source_install_available) ? value.counts.source_install_available : 0,
      runtime_repair_required: isNumber(value.counts.runtime_repair_required) ? value.counts.runtime_repair_required : 0,
      blocked: isNumber(value.counts.blocked) ? value.counts.blocked : 0,
    },
    execution_mode: isString(value.execution_mode) ? value.execution_mode : "unknown",
    agent_gate: isString(value.agent_gate) ? value.agent_gate : "Runtime setup execution is blocked until the backend reports a safe runner.",
    records: value.records.map(parseSourceModuleRuntimeSetupRecord).filter(isPresent),
    proof_event_id: isNullableString(value.proof_event_id) ? value.proof_event_id : null,
  };
}

function parseSourceModuleRuntimeSetupRecord(value: unknown): SourceModuleRuntimeSetupQueue["records"][number] | null {
  if (!isRecord(value) || !isString(value.module_id)) {
    return null;
  }
  return {
    module_id: value.module_id,
    display: isNullableString(value.display) ? value.display : null,
    section: isNullableString(value.section) ? value.section : null,
    repo: isNullableString(value.repo) ? value.repo : null,
    local_path: isNullableString(value.local_path) ? value.local_path : null,
    launch_kind: isNullableString(value.launch_kind) ? value.launch_kind : null,
    install_state: isNullableString(value.install_state) ? value.install_state : null,
    runtime_status: isString(value.runtime_status) ? value.runtime_status : "blocked",
    runtime_label: isNullableString(value.runtime_label) ? value.runtime_label : null,
    verifier: isNullableString(value.verifier) ? value.verifier : null,
    runner_status: isString(value.runner_status) ? value.runner_status : "blocked",
    next_action: isString(value.next_action) ? value.next_action : "fix source registry before setup",
    source_install_supported: value.source_install_supported === true,
    runtime_ready: value.runtime_ready === true,
    agent_can_execute_setup_now: value.agent_can_execute_setup_now === true,
    agent_setup_gate: isString(value.agent_setup_gate) ? value.agent_setup_gate : "No setup runner is registered.",
    setup_steps: isStringArray(value.setup_steps) ? value.setup_steps : [],
    reason: isNullableString(value.reason) ? value.reason : null,
    proof_source: isNullableString(value.proof_source) ? value.proof_source : null,
  };
}

function emptySetupQueue(status: string): SourceModuleRuntimeSetupQueue {
  return {
    accepted: false,
    status,
    section: null,
    count: 0,
    counts: {
      runtime_ready: 0,
      source_ready: 0,
      runner_not_registered: 0,
      source_install_available: 0,
      runtime_repair_required: 0,
      blocked: 0,
    },
    execution_mode: "unavailable",
    agent_gate: "Runtime setup queue API is unavailable from the local backend.",
    records: [],
    proof_event_id: null,
  };
}

function parseSourceOSModule(value: unknown): SourceOSModule | null {
  if (!isRecord(value) || !isString(value.id)) {
    return null;
  }
  const installState = value.installState ?? value.install_state;
  const launchKind = value.launchKind ?? value.launch_kind;
  const resolvedInstallState = isInstallState(installState) ? installState : "unavailable";
  const resolvedLaunchKind = isLaunchKind(launchKind) ? launchKind : null;
  const localPath = isNullableString(value.localPath) ? value.localPath : isNullableString(value.local_path) ? value.local_path : null;
  return {
    id: value.id,
    display: isString(value.display) ? value.display : isString(value.display_name) ? value.display_name : value.id,
    priority: isString(value.priority) ? value.priority : "",
    license: isString(value.license) ? value.license : "",
    section: isString(value.section) ? value.section : "",
    repo: isNullableString(value.repo) ? value.repo : null,
    localPath,
    installState: resolvedInstallState,
    installProgress: isNumber(value.installProgress) ? value.installProgress : isNumber(value.install_progress) ? value.install_progress : 0,
    detectedVersion: isNullableString(value.detectedVersion) ? value.detectedVersion : isNullableString(value.detected_version) ? value.detected_version : null,
    health: isModuleHealth(value.health) ? value.health : "unknown",
    launchKind: resolvedLaunchKind,
    bridgeTasks: Array.isArray(value.bridgeTasks) ? value.bridgeTasks as SourceOSModule["bridgeTasks"] : [],
    proofs: Array.isArray(value.proofs) ? value.proofs as ProofBundle[] : [],
    dispatchGates: Array.isArray(value.dispatchGates) ? value.dispatchGates as SourceOSModule["dispatchGates"] : [],
    providers: Array.isArray(value.providers) ? value.providers.map(parseSourceOSProvider).filter(isPresent) : [],
    activeProvider: isNullableString(value.activeProvider) ? value.activeProvider : null,
    runtime: parseSourceModuleRuntime(value.runtime, resolvedInstallState, localPath, resolvedLaunchKind),
  };
}

function parseSourceModuleRuntime(
  value: unknown,
  installState: SourceOSModule["installState"],
  localPath: string | null,
  launchKind: SourceOSModule["launchKind"],
): SourceOSModule["runtime"] {
  if (isRecord(value)) {
    return {
      status: isString(value.status) ? value.status : "blocked",
      label: isString(value.label) ? value.label : "Runtime blocked",
      kind: isNullableString(value.kind) ? value.kind : null,
      verifier: isNullableString(value.verifier) ? value.verifier : null,
      path: isNullableString(value.path) ? value.path : null,
      detected: value.detected === true,
      executed: value.executed === true,
      return_code: isNullableNumber(value.return_code) ? value.return_code : null,
      capabilities: isStringArray(value.capabilities) ? value.capabilities : [],
      reason: isNullableString(value.reason) ? value.reason : null,
      setup_steps: isStringArray(value.setup_steps) ? value.setup_steps : [],
      proof_source: isNullableString(value.proof_source) ? value.proof_source : null,
      output_head: isStringArray(value.output_head) ? value.output_head : [],
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

function parseSourceOSProvider(value: unknown): SourceOSModule["providers"][number] | null {
  if (!isRecord(value) || !isString(value.id) || !isString(value.display)) {
    return null;
  }
  return {
    id: value.id,
    moduleId: isString(value.moduleId) ? value.moduleId : "",
    display: value.display,
    kind: isString(value.kind) ? value.kind : "",
    repo: isNullableString(value.repo) ? value.repo : null,
    installCommand: isNullableString(value.installCommand) ? value.installCommand : null,
    verifyCommands: isStringArray(value.verifyCommands) ? value.verifyCommands : [],
    capabilities: isStringArray(value.capabilities) ? value.capabilities : [],
    license: isNullableString(value.license) ? value.license : null,
    state: isString(value.state) ? value.state : "unknown",
    notes: isNullableString(value.notes) ? value.notes : null,
  };
}

function isPresent<T>(value: T | null | undefined): value is T {
  return value != null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isModel(value: unknown): value is Printer["model"] {
  return typeof value === "string" && MODELS.has(value as Printer["model"]);
}

function isStatus(value: unknown): value is PrinterStatus {
  return typeof value === "string" && STATUSES.has(value as PrinterStatus);
}

function isAdapter(value: unknown): value is PrinterAdapter {
  return typeof value === "string" && ADAPTERS.has(value as PrinterAdapter);
}

function isDataSource(value: unknown): value is PrinterDataSource {
  return typeof value === "string" && DATA_SOURCES.has(value as PrinterDataSource);
}

function isArtifactType(value: unknown): value is Artifact["type"] {
  return (
    value === "model_evidence" ||
    value === "agent_plan" ||
    value === "gcode" ||
    value === "screenshot" ||
    value === "report" ||
    value === "photo" ||
    value === "mesh" ||
    value === "g-code" ||
    value === "log" ||
    value === "agent_attachment" ||
    value === "other"
  );
}

function isArtifactStage(value: unknown): value is Artifact["stage"] {
  return (
    value === "INTAKE" ||
    value === "MODELING" ||
    value === "SLICING" ||
    value === "AGENT_CHAT" ||
    value === "PRINT_APPROVAL" ||
    value === "PRINT_RUN" ||
    value === "COMPLETE"
  );
}

function isArtifactGate(value: unknown): value is NonNullable<Artifact["gate"]> {
  return value === "MODEL_APPROVAL" || value === "PRINT_APPROVAL" || (typeof value === "string" && /^GATE_([1-9]|10|11)$/.test(value));
}

function isAgentStatus(value: unknown): value is AgentStatus {
  return value === "idle" || value === "active" || value === "paused" || value === "error";
}

function isIdleCandidateStatus(value: unknown): value is IdleWorkbenchCandidate["status"] {
  return value === "queued" || value === "blocked" || value === "ready_for_review" || value === "approved" || value === "rejected" || value === "completed";
}

function isNotificationType(value: unknown): value is Notification["type"] {
  return (
    value === "INFO" ||
    value === "SUCCESS" ||
    value === "WARNING" ||
    value === "ACTION_REQUIRED" ||
    value === "ANOMALY_DETECTED" ||
    value === "PRINT_COMPLETE" ||
    value === "AGENT_BLOCKED" ||
    value === "WHILE_AWAY_ESCALATION"
  );
}

function isNotificationPriority(value: unknown): value is Notification["priority"] {
  return value === "low" || value === "medium" || value === "high" || value === "critical";
}

function isInstallState(value: unknown): value is SourceOSModule["installState"] {
  return (
    value === "unavailable" ||
    value === "source_available" ||
    value === "downloading" ||
    value === "installing" ||
    value === "installed" ||
    value === "detected" ||
    value === "healthy" ||
    value === "degraded" ||
    value === "failed" ||
    value === "rollback_available"
  );
}

function isLaunchKind(value: unknown): value is NonNullable<SourceOSModule["launchKind"]> {
  return (
    value === "catalog_reference" ||
    value === "desktop_app" ||
    value === "desktop_or_cli" ||
    value === "service" ||
    value === "service_reference" ||
    value === "source_reference" ||
    value === "cli_worker" ||
    value === "cli_or_python_worker" ||
    value === "firmware_source" ||
    value === "hardware_reference" ||
    value === "python_worker" ||
    value === "gpu_worker" ||
    value === "web_app" ||
    value === "web_app_reference" ||
    value === "npm_package" ||
    value === "rust_library" ||
    value === "reference" ||
    value === "rust_library_reference" ||
    value === "touch_ui_reference" ||
    value === "unknown"
  );
}

function isModuleHealth(value: unknown): value is SourceOSModule["health"] {
  return value === "unknown" || value === "healthy" || value === "degraded" || value === "failed";
}

function notificationSeverity(type: unknown, priority: unknown): Notification["severity"] {
  if (priority === "critical" || priority === "high" || type === "SYSTEM_ERROR") {
    return "error";
  }
  if (priority === "medium" || type === "WARNING" || type === "ACTION_REQUIRED") {
    return "warn";
  }
  if (type === "SUCCESS" || type === "PRINT_COMPLETE") {
    return "success";
  }
  return "info";
}
