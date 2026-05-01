/**
 * Dimensional Truth Engine UI-standards types.
 *
 * Phase 2 reserves these shapes per the addendum in PHASE2_PLAN.md so Phase
 * 4-6 can populate them without renegotiating the visual contract. Phase 2
 * ships placeholders only — no real measurement logic, no CAD libraries.
 */

export type Unit = "mm" | "in";

export interface ScaleConfirmation {
  unit: Unit;
  scale_factor: number;
  /** Mock: "operator" | null — Phase 6 wires the operator-confirmation flow. */
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
