/**
 * Adapter interface for Phase 2 mock mode and Phase 3.1 local live reads.
 *
 * Default mode returns deterministic mock data. Live mode only reads the
 * local bridge `GET /api/printers`; all other methods remain mock-backed.
 *
 * The interface shape stays stable across the Phase-2 → Phase-3 swap so
 * tab components don't change.
 */
import { getLivePrinters, planPreviewLive } from "./adapters.live";
import { MOCK_AGENTS } from "../data/mock/agents";
import { MOCK_PLAN_DAG } from "../data/mock/dag";
import { MOCK_DIMENSIONAL_REPORTS } from "../data/mock/dimensional";
import { MOCK_JOBS } from "../data/mock/jobs";
import { MOCK_LOGS } from "../data/mock/logs";
import { MOCK_NOTIFICATIONS } from "../data/mock/notifications";
import { MOCK_PRINTERS } from "../data/mock/printers";
import { MOCK_PROOF_BUNDLES, LATEST_BUNDLE } from "../data/mock/proof";
import { MOCK_SYSTEM_SNAPSHOT } from "../data/mock/system";
import { MOCK_WORKFLOWS } from "../data/mock/workflows";
import type { Agent } from "../types/agent";
import type { DimensionalAccuracyReport } from "../types/dimensional";
import type { TaskDAG } from "../types/dag";
import type { Job } from "../types/job";
import type { LogEntry } from "../types/log";
import type { Notification } from "../types/notification";
import type { Printer } from "../types/printer";
import type { ProofBundle } from "../types/proof";
import type { SystemSnapshot } from "../types/system";
import type { Workflow } from "../types/workflow";

export interface AdapterAPI {
  getPrinters(): Promise<Printer[]>;
  getAgents(): Promise<Agent[]>;
  getActiveWorkflows(): Promise<Workflow[]>;
  getRecentJobs(): Promise<Job[]>;
  getProofBundles(): Promise<ProofBundle[]>;
  getLatestProofBundle(): Promise<ProofBundle>;
  getSystemSnapshot(): Promise<SystemSnapshot>;
  getDimensionalReports(): Promise<DimensionalAccuracyReport[]>;
  getLogs(): Promise<LogEntry[]>;
  getNotifications(): Promise<Notification[]>;
  planPreview(prompt: string): Promise<TaskDAG>;
}

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_ADAPTER?: string;
  };
};

const mockAdapters: AdapterAPI = {
  getPrinters: async () => MOCK_PRINTERS,
  getAgents: async () => MOCK_AGENTS,
  getActiveWorkflows: async () => MOCK_WORKFLOWS,
  getRecentJobs: async () => MOCK_JOBS,
  getProofBundles: async () => MOCK_PROOF_BUNDLES,
  getLatestProofBundle: async () => LATEST_BUNDLE,
  getSystemSnapshot: async () => MOCK_SYSTEM_SNAPSHOT,
  getDimensionalReports: async () => MOCK_DIMENSIONAL_REPORTS,
  getLogs: async () => MOCK_LOGS,
  getNotifications: async () => MOCK_NOTIFICATIONS,
  planPreview: async () => MOCK_PLAN_DAG,
};

const liveAdapters: AdapterAPI = {
  ...mockAdapters,
  getPrinters: getLivePrinters,
  planPreview: planPreviewLive,
};

function adapterMode(): "mock" | "live" {
  const env = (import.meta as HermesImportMeta).env;
  if (env.VITE_HERMES3D_ADAPTER === "live") {
    return "live";
  }
  if (typeof window !== "undefined") {
    return new URLSearchParams(window.location.search).get("adapter") === "live" ? "live" : "mock";
  }
  return "mock";
}

export const adapters: AdapterAPI = adapterMode() === "live" ? liveAdapters : mockAdapters;
