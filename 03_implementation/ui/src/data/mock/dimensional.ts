/**
 * Dimensional Truth Engine mock data — Phase 2 placeholder per the addendum
 * in PHASE2_PLAN.md. All entries default to `pending` / null / phase4_pending
 * so the UI placeholders render in their "Phase 6 will populate" state.
 */
import type { DimensionalAccuracyReport } from "../../types/dimensional";

export const MOCK_DIMENSIONAL_REPORTS: DimensionalAccuracyReport[] = [
  {
    job_id: "job-100",
    scale: { unit: "mm", scale_factor: 1.0, confirmed_by: null, confirmed_at_utc: null },
    changes: [
      {
        axis: "diameter",
        from_mm: 24.0,
        to_mm: 24.2,
        reason: "operator-requested clearance bump for press fit",
        status: "requested",
      },
    ],
    before_after: null,
    fidelity: { score: 0, method: "phase4_pending", notes: "Phase 6 will populate after print + scan." },
    printability: "pending",
    mesh_repair: { applied: false, notes: "Phase 6 will run trimesh repair pipeline." },
    proof_bundle_ref: null,
  },
  {
    job_id: "job-097",
    scale: { unit: "mm", scale_factor: 1.0, confirmed_by: "operator", confirmed_at_utc: "2026-05-01T08:15:00Z" },
    changes: [],
    before_after: null,
    fidelity: { score: 0, method: "phase4_pending", notes: "Phase 6 will populate after print + scan." },
    printability: "pending",
    mesh_repair: { applied: false, notes: "Phase 6 will run trimesh repair pipeline." },
    proof_bundle_ref: "bundle-a3b9",
  },
];
