/**
 * Mock adapter interface for Phase 2.
 *
 * Every method returns mock data via Promise.resolve() — no real network
 * calls, no subprocess, no adapter invocation. Phase 3 swaps the
 * implementation here to call the real Python `hermes3d.adapters` Protocol
 * (over a thin HTTP/IPC bridge or wasm shim — TBD in Phase 3 ADR-009).
 *
 * The interface shape stays stable across the Phase-2 → Phase-3 swap so
 * tab components don't change.
 */
import { MOCK_AGENTS } from "../data/mock/agents";
import { MOCK_DIMENSIONAL_REPORTS } from "../data/mock/dimensional";
import { MOCK_JOBS } from "../data/mock/jobs";
import { MOCK_PRINTERS } from "../data/mock/printers";
import { MOCK_PROOF_BUNDLES, LATEST_BUNDLE } from "../data/mock/proof";
import { MOCK_SYSTEM_SNAPSHOT } from "../data/mock/system";
import { MOCK_WORKFLOWS } from "../data/mock/workflows";
import type { Agent } from "../types/agent";
import type { DimensionalAccuracyReport } from "../types/dimensional";
import type { Job } from "../types/job";
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
}

/**
 * Mock implementation. Phase 3 replaces this with a real client of the
 * Python `hermes3d.adapters` shell, but the AdapterAPI contract remains.
 */
export const adapters: AdapterAPI = {
  getPrinters: async () => MOCK_PRINTERS,
  getAgents: async () => MOCK_AGENTS,
  getActiveWorkflows: async () => MOCK_WORKFLOWS,
  getRecentJobs: async () => MOCK_JOBS,
  getProofBundles: async () => MOCK_PROOF_BUNDLES,
  getLatestProofBundle: async () => LATEST_BUNDLE,
  getSystemSnapshot: async () => MOCK_SYSTEM_SNAPSHOT,
  getDimensionalReports: async () => MOCK_DIMENSIONAL_REPORTS,
};
