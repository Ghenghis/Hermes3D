/**
 * Types for the 60-app registry exposed via /api/apps.
 *
 * Backend contract is owned by W6-7 (Recovery Controller / proof gates).
 * The shape here mirrors the documented payload from
 * `03_implementation/docs/handoffs` for the registry data layer.
 *
 * No-fake contract: every optional field is treated as "unknown" rather
 * than fabricated; the GUI must surface gaps honestly (em-dash placeholder
 * or explicit "—" with aria-label).
 */

export type AppLifecycleStatus = "stable" | "canary" | "frozen" | "unknown";
export type AppUpdateLane = "core" | "stable" | "canary" | "frozen" | "experimental" | "unknown";
export type ProofStatus = "pass" | "fail" | "pending" | "unknown";
export type TruthfulStatus =
  | "INSTALLED_PROVEN"
  | "INSTALLED_UNPROVEN"
  | "FAILED_PROOF"
  | "NO_PROOF_COMMAND"
  | "NOT_INSTALLED"
  | "SOURCE_AVAILABLE"
  | "CONFIG_REQUIRED"
  | "UNKNOWN";

export interface AppLicense {
  /** SPDX expression where known, e.g. "MIT", "Apache-2.0", or "Unknown". */
  spdx: string;
  /** Optional friendly label rendered in the badge. */
  label?: string;
  /** Optional URL to the license file or upstream license page. */
  url?: string | null;
}

export interface AppProofResult {
  /** Proof event id; missing means the row has never been proofed. */
  proof_event_id: string | null;
  /** Last proof status (pass/fail/pending). */
  status: ProofStatus;
  /** ISO 8601 timestamp of last proof completion. */
  at: string | null;
  /** Short reason / failure summary; never includes raw shell output. */
  reason?: string | null;
}

/** A single registry row as returned by GET /api/apps. */
export interface RegistryApp {
  /** Stable identifier, e.g. "hermes-agent". */
  id: string;
  /** Human-readable display name. */
  name: string;
  /** Version that the local install resolved to (semver-ish). */
  current_version: string | null;
  /** Versions that have a passing proof on record. */
  tested_versions: string[];
  /** License metadata. */
  license: AppLicense;
  /** Lifecycle / update lane bucket. */
  update_lane: AppUpdateLane;
  /** Lifecycle status. */
  lifecycle: AppLifecycleStatus;
  /** Last proof result. May be null if never proofed. */
  last_proof: AppProofResult | null;
  /** Whether the backend supports rollback for this app. */
  rollback_supported: boolean;
  /** Optional human description shown in the detail page. */
  description?: string | null;
  /** Optional source repo / docs URL. */
  upstream_url?: string | null;
  /** Honest install status derived from proof evidence (W19-7). */
  truthful_status?: TruthfulStatus | null;
  /** Idempotent shell command to verify install (null = no proof available). */
  proof_command?: string | null;
}

/** Wrapper for GET /api/apps. */
export interface RegistryAppListResponse {
  apps: RegistryApp[];
  /** Backend wall-clock at the time of the response. */
  generated_at?: string;
}

/** Detail payload from GET /api/apps/{id}. */
export interface RegistryAppDetail extends RegistryApp {
  /** Last 5 proof results (newest first). */
  recent_proofs: AppProofResult[];
  /** Pointer to the rollback runbook (relative or absolute URL). */
  rollback_runbook_url?: string | null;
  /** Optional canonical command to re-run the proof for this app (W8-2). */
  proof_command?: string | null;
  /** Optional metadata block (free-form, must be string-keyed scalars). */
  metadata?: Record<string, string | number | boolean | null>;
}

/** Response to POST /api/apps/{id}/run-proof. */
export interface RegistryRunProofResponse {
  /** Whether the backend accepted the proof request. */
  accepted: boolean;
  /** Proof event id, if the backend assigned one synchronously. */
  proof_event_id: string | null;
  /** Updated proof status; may be "pending" if dispatched async. */
  status: ProofStatus;
  /** Free-text human reason. */
  reason?: string | null;
}
