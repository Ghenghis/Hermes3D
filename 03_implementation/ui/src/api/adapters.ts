import {
  activatePluginLive,
  approveApprovalLive,
  attachEvidenceLive,
  cancelJobLive,
  applyJobRepairLive,
  emitProofEventLive,
  getActiveWorkflowsLive,
  getAgentActionCatalogLive,
  getAgentsLive,
  getApprovalHistoryLive,
  getArtifactsLive,
  getAutopilotGuardrailsLive,
  getAutopilotReadinessLive,
  getAgentHealthLive,
  uploadAgentAttachmentLive,
  getHermesAgentUpdateStatusLive,
  getHermesDesktopUpdateStatusLive,
  getCameraObserverStatusLive,
  getDesignToolchainStatusLive,
  getDimensionalReportsLive,
  getJobDetailLive,
  getJobsLive,
  getLatestProofBundleLive,
  getLearningConfigLive,
  getLearningReportLive,
  getLearningReportsLive,
  getIdleWorkbenchLive,
  getLivePrinters,
  getLogsLive,
  getNotificationsLive,
  getPendingApprovalsLive,
  getPluginsLive,
  getPrinterLockStateLive,
  getProofBundlesLive,
  getProviderHealthLive,
  getRecentJobsLive,
  getRoadmapItemsLive,
  getRoadmapTabCompletionLive,
  getServiceHealthLive,
  getSettingsLive,
  getSourceOSModuleLive,
  getSourceOSModulesLive,
  getModuleRuntimeSetupQueueLive,
  getModuleUpdateReadinessLive,
  getRuntimeReadinessLive,
  getSystemSnapshotLive,
  getVoiceAgentsLive,
  getVoiceCatalogLive,
  planPreviewLive,
  planModuleRuntimeSetupQueueLive,
  onboardPrinterLive,
  probePrinterLive,
  validateCameraUrlLive,
  previewVoiceLive,
  proposeJobRepairLive,
  rollbackHermesAgentLive,
  rollbackJobLive,
  backupHermesDesktopLive,
  downloadHermesDesktopInstallerLive,
  rejectApprovalLive,
  backupHermesAgentLive,
  saveAgentConfigLive,
  saveSettingsLive,
  saveLearningConfigLive,
  createIdleCandidateLive,
  decideIdleCandidateLive,
  requestIdleCandidateReviewLive,
  runIdleCandidateLive,
  runAgentCatalogActionLive,
  saveVoiceAgentLive,
  retryJobLive,
  testPrinterLive,
  updatePrinterStatusLive,
  updateHermesAgentStagedLive,
  uploadGcodeLive,
} from "./adapters.live";
import type { Agent } from "../types/agent";
import type { AgentActionCatalog, AgentActionRunResult } from "../types/agent-actions";
import type { Approval } from "../types/approval";
import type { Artifact, EvidenceForm } from "../types/artifact";
import type { AutopilotCheck, GuardrailPolicy } from "../types/autopilot";
import type { TaskDAG } from "../types/dag";
import type { DimensionalAccuracyReport } from "../types/dimensional";
import type { Job } from "../types/job";
import type { JobDetail, JobTransitionResult } from "../types/job-detail";
import type { IdleCandidateCreateRequest, IdleCandidateMutationResult, IdleWorkbenchState, LearningConfig, ReportMeta } from "../types/learning";
import type { LogEntry } from "../types/log";
import type { Notification } from "../types/notification";
import type { Plugin } from "../types/plugin";
import type { Printer, PrinterOnboardRequest, PrinterOnboardResult } from "../types/printer";
import type { GcodeUploadResult, PrinterLock, TestResult } from "../types/printer-lock";
import type { ProofBundle } from "../types/proof";
import type { ProviderHealth } from "../types/provider";
import type { RoadmapItem, RoadmapTabCompletion } from "../types/roadmap";
import type { ServiceHealthEntry } from "../types/serviceHealth";
import type { AppSettings } from "../types/settings";
import type { SourceModuleRuntimeSetupQueue, SourceModuleUpdateReadiness, SourceOSModule } from "../types/source-os";
import type { RuntimeReadiness, SystemSnapshot } from "../types/system";
import type { ToolchainStatus } from "../types/toolchain";
import type { VoiceAgent, VoiceCatalog, VoicePreviewResult } from "../types/voice";
import type { Workflow } from "../types/workflow";
export type {
  AgentConfigPayload,
  AgentConfigSaveResult,
  AgentAttachmentUpload,
  AgentHealthResult,
  HermesAgentBackup,
  HermesAgentUpdateResult,
  HermesAgentUpdateStatus,
  HermesDesktopBackup,
  HermesDesktopDownload,
  HermesDesktopUpdateStatus,
  LearningReportContent,
  PrinterProbeResult,
  CameraValidateResult,
} from "./adapters.live";
import type {
  AgentConfigPayload,
  AgentConfigSaveResult,
  AgentAttachmentUpload,
  AgentHealthResult,
  HermesAgentBackup,
  HermesAgentUpdateResult,
  HermesAgentUpdateStatus,
  HermesDesktopBackup,
  HermesDesktopDownload,
  HermesDesktopUpdateStatus,
  LearningReportContent,
  PrinterProbeResult,
  CameraValidateResult,
} from "./adapters.live";

export interface AdapterAPI {
  getPrinters(): Promise<Printer[]>;
  getAgents(): Promise<Agent[]>;
  getAgentActionCatalog(): Promise<AgentActionCatalog>;
  runAgentCatalogAction(actionId: string, reason?: string, payload?: Record<string, unknown>): Promise<AgentActionRunResult>;
  getActiveWorkflows(): Promise<Workflow[]>;
  getRecentJobs(): Promise<Job[]>;
  getProofBundles(): Promise<ProofBundle[]>;
  getLatestProofBundle(): Promise<ProofBundle | null>;
  getSystemSnapshot(): Promise<SystemSnapshot | null>;
  getRuntimeReadiness(): Promise<RuntimeReadiness | null>;
  getDimensionalReports(): Promise<DimensionalAccuracyReport[]>;
  getLogs(): Promise<LogEntry[]>;
  getNotifications(): Promise<Notification[]>;
  planPreview(prompt: string): Promise<TaskDAG>;
  getProviderHealth(): Promise<ProviderHealth[]>;
  getServiceHealth(): Promise<ServiceHealthEntry[]>;
  getAutopilotReadiness(): Promise<AutopilotCheck[]>;
  getAutopilotGuardrails(): Promise<GuardrailPolicy[]>;
  getDesignToolchainStatus(): Promise<ToolchainStatus>;
  getJobs(status?: string): Promise<Job[]>;
  getJobDetail(id: string): Promise<JobDetail>;
  cancelJob(id: string): Promise<void>;
  proposeJobRepair(id: string, reason?: string): Promise<JobTransitionResult>;
  applyJobRepair(id: string, notes?: string): Promise<JobTransitionResult>;
  retryJob(id: string, reason?: string): Promise<JobTransitionResult>;
  rollbackJob(id: string, targetArtifactId?: string): Promise<JobTransitionResult>;
  getPrinterLockState(id: string): Promise<PrinterLock>;
  testPrinter(id: string): Promise<TestResult>;
  onboardPrinter(request: PrinterOnboardRequest): Promise<PrinterOnboardResult>;
  probePrinter(ip: string): Promise<PrinterProbeResult>;
  validateCameraUrl(cameraUrl: string): Promise<CameraValidateResult>;
  uploadGcode(id: string, gcodePath: string, start: boolean, remoteSubdir?: string, actor?: string, jobId?: string): Promise<GcodeUploadResult>;
  updatePrinterStatus(id: string, status: Printer["status"], actor?: string): Promise<void>;
  getVoiceAgents(): Promise<VoiceAgent[]>;
  getVoiceCatalog(locale?: string): Promise<VoiceCatalog>;
  saveVoiceAgent(id: string, voice: string): Promise<void>;
  previewVoice(id: string, voice: string, text?: string, rate?: number, pitchPct?: number): Promise<VoicePreviewResult>;
  getPlugins(): Promise<Plugin[]>;
  activatePlugin(id: string): Promise<Plugin>;
  getAgentHealth(): Promise<AgentHealthResult>;
  uploadAgentAttachment(personaId: string, file: File): Promise<AgentAttachmentUpload>;
  saveAgentConfig(config: AgentConfigPayload): Promise<AgentConfigSaveResult>;
  getHermesAgentUpdateStatus(): Promise<HermesAgentUpdateStatus>;
  backupHermesAgent(note?: string): Promise<HermesAgentBackup>;
  updateHermesAgentStaged(maxSteps?: number): Promise<HermesAgentUpdateResult>;
  rollbackHermesAgent(backupId?: string): Promise<HermesAgentUpdateResult>;
  getHermesDesktopUpdateStatus(): Promise<HermesDesktopUpdateStatus>;
  backupHermesDesktop(note?: string): Promise<HermesDesktopBackup>;
  downloadHermesDesktopInstaller(): Promise<HermesDesktopDownload>;
  getLearningConfig(): Promise<LearningConfig>;
  saveLearningConfig(config: Pick<LearningConfig, "enabled" | "idle_minutes">): Promise<LearningConfig>;
  getLearningReports(): Promise<ReportMeta[]>;
  getLearningReport(filename: string): Promise<LearningReportContent>;
  getIdleWorkbench(): Promise<IdleWorkbenchState>;
  createIdleCandidate(request: IdleCandidateCreateRequest): Promise<IdleCandidateMutationResult>;
  requestIdleCandidateReview(candidateId: string): Promise<IdleCandidateMutationResult>;
  runIdleCandidate(candidateId: string): Promise<IdleCandidateMutationResult>;
  decideIdleCandidate(candidateId: string, decision: "keep" | "remove" | "merge", reason?: string): Promise<IdleCandidateMutationResult>;
  getArtifacts(): Promise<Artifact[]>;
  attachEvidence(form: EvidenceForm): Promise<Artifact>;
  getPendingApprovals(): Promise<Approval[]>;
  getApprovalHistory(): Promise<Approval[]>;
  approveApproval(id: string, notes: string): Promise<void>;
  rejectApproval(id: string, reason: string): Promise<void>;
  getRoadmapItems(): Promise<RoadmapItem[]>;
  getRoadmapTabCompletion(): Promise<RoadmapTabCompletion>;
  getSourceOSModules(): Promise<SourceOSModule[]>;
  getSourceOSModule(id: string): Promise<SourceOSModule | null>;
  getModuleUpdateReadiness(deep?: boolean): Promise<SourceModuleUpdateReadiness>;
  getModuleRuntimeSetupQueue(): Promise<SourceModuleRuntimeSetupQueue>;
  planModuleRuntimeSetupQueue(): Promise<SourceModuleRuntimeSetupQueue>;
  getSettings(): Promise<AppSettings>;
  saveSettings(s: Partial<AppSettings>): Promise<void>;
  emitProofEvent(type: string, payload: Record<string, unknown>): Promise<void>;
  getCameraObserverStatus(): Promise<{ status: string; reason: string }>;
}

export const adapters: AdapterAPI = {
  getPrinters: getLivePrinters,
  getAgents: getAgentsLive,
  getAgentActionCatalog: getAgentActionCatalogLive,
  runAgentCatalogAction: runAgentCatalogActionLive,
  getActiveWorkflows: getActiveWorkflowsLive,
  getRecentJobs: getRecentJobsLive,
  getProofBundles: getProofBundlesLive,
  getLatestProofBundle: getLatestProofBundleLive,
  getSystemSnapshot: getSystemSnapshotLive,
  getRuntimeReadiness: getRuntimeReadinessLive,
  getDimensionalReports: getDimensionalReportsLive,
  getLogs: getLogsLive,
  getNotifications: getNotificationsLive,
  planPreview: planPreviewLive,
  getProviderHealth: getProviderHealthLive,
  getServiceHealth: getServiceHealthLive,
  getAutopilotReadiness: getAutopilotReadinessLive,
  getAutopilotGuardrails: getAutopilotGuardrailsLive,
  getDesignToolchainStatus: getDesignToolchainStatusLive,
  getJobs: getJobsLive,
  getJobDetail: getJobDetailLive,
  cancelJob: cancelJobLive,
  proposeJobRepair: proposeJobRepairLive,
  applyJobRepair: applyJobRepairLive,
  retryJob: retryJobLive,
  rollbackJob: rollbackJobLive,
  getPrinterLockState: getPrinterLockStateLive,
  testPrinter: testPrinterLive,
  onboardPrinter: onboardPrinterLive,
  probePrinter: probePrinterLive,
  validateCameraUrl: validateCameraUrlLive,
  uploadGcode: uploadGcodeLive,
  updatePrinterStatus: updatePrinterStatusLive,
  getVoiceAgents: getVoiceAgentsLive,
  getVoiceCatalog: getVoiceCatalogLive,
  saveVoiceAgent: saveVoiceAgentLive,
  previewVoice: previewVoiceLive,
  getPlugins: getPluginsLive,
  activatePlugin: activatePluginLive,
  getAgentHealth: getAgentHealthLive,
  uploadAgentAttachment: uploadAgentAttachmentLive,
  saveAgentConfig: saveAgentConfigLive,
  getHermesAgentUpdateStatus: getHermesAgentUpdateStatusLive,
  backupHermesAgent: backupHermesAgentLive,
  updateHermesAgentStaged: updateHermesAgentStagedLive,
  rollbackHermesAgent: rollbackHermesAgentLive,
  getHermesDesktopUpdateStatus: getHermesDesktopUpdateStatusLive,
  backupHermesDesktop: backupHermesDesktopLive,
  downloadHermesDesktopInstaller: downloadHermesDesktopInstallerLive,
  getLearningConfig: getLearningConfigLive,
  saveLearningConfig: saveLearningConfigLive,
  getLearningReports: getLearningReportsLive,
  getLearningReport: getLearningReportLive,
  getIdleWorkbench: getIdleWorkbenchLive,
  createIdleCandidate: createIdleCandidateLive,
  requestIdleCandidateReview: requestIdleCandidateReviewLive,
  runIdleCandidate: runIdleCandidateLive,
  decideIdleCandidate: decideIdleCandidateLive,
  getArtifacts: getArtifactsLive,
  attachEvidence: attachEvidenceLive,
  getPendingApprovals: getPendingApprovalsLive,
  getApprovalHistory: getApprovalHistoryLive,
  approveApproval: approveApprovalLive,
  rejectApproval: rejectApprovalLive,
  getRoadmapItems: getRoadmapItemsLive,
  getRoadmapTabCompletion: getRoadmapTabCompletionLive,
  getSourceOSModules: getSourceOSModulesLive,
  getSourceOSModule: getSourceOSModuleLive,
  getModuleUpdateReadiness: getModuleUpdateReadinessLive,
  getModuleRuntimeSetupQueue: getModuleRuntimeSetupQueueLive,
  planModuleRuntimeSetupQueue: planModuleRuntimeSetupQueueLive,
  getSettings: getSettingsLive,
  saveSettings: saveSettingsLive,
  emitProofEvent: emitProofEventLive,
  getCameraObserverStatus: getCameraObserverStatusLive,
};
