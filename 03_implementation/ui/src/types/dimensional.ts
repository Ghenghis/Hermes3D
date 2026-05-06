/**
 * Dimensional Truth Engine UI-standards types.
 *
 * Live dimensional reports returned by the local backend. Empty arrays mean
 * no report has been written yet.
 */

export type Unit = "mm" | "in";

export interface ScaleConfirmation {
  unit: Unit;
  scale_factor: number;
  /** Actor that confirmed the scale, or null if it is not confirmed yet. */
  confirmed_by: string | null;
  confirmed_at_utc: string | null;
}

export interface MeasurementChangeRequest {
  axis: "x" | "y" | "z" | "diameter" | "length";
  from_mm: number;
  to_mm: number;
  reason: string;
  status: "requested" | "applied" | "rejected";
}

export interface BeforeAfterDimensions {
  before_mm: { x: number; y: number; z: number };
  after_mm: { x: number; y: number; z: number };
  delta_mm: { x: number; y: number; z: number };
}

export interface VisualFidelityScore {
  /** 0-100. */
  score: number;
  method: "ssim" | "human_eyeball" | "phase4_pending";
  notes: string;
}

export interface DimensionalAccuracyReport {
  job_id: string;
  scale: ScaleConfirmation;
  changes: MeasurementChangeRequest[];
  /** null until print + scan complete (Phase 6). */
  before_after: BeforeAfterDimensions | null;
  fidelity: VisualFidelityScore | null;
  printability: "pass" | "fail" | "pending";
  mesh_repair: { applied: boolean; notes: string };
  proof_bundle_ref: string | null;
}
