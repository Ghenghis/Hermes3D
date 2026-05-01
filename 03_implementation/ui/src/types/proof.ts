/** Proof bundle + gate matrix shapes for the Proof & Reports tab + Dashboard chip. */

export type GateVerdict = "pass" | "fail" | "skip" | "pending";
export type ProofVerdict = "verified" | "pending" | "failed";

export interface GateResult {
  layer: string; // e.g. "Layer A", "Layer B (ubuntu × py3.11)", "Layer T"
  verdict: GateVerdict;
  duration_s: number | null;
}

export interface ProofBundle {
  id: string;
  sha256: string;
  branch: string;
  commit: string;
  ts_utc: string;
  files_count: number;
  size_bytes: number;
  verdict: ProofVerdict;
  /** Per-layer gate results. */
  gates: GateResult[];
}
