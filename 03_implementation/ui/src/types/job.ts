/** Recent-jobs list shape per visual contract Dashboard's "Recent Jobs" panel. */

export type JobStatus =
  | "queued"
  | "printing"
  | "completed"
  | "failed"
  | "cancelled";

export interface Job {
  id: string;
  name: string;
  status: JobStatus;
  printer_id: string | null;
  started_utc: string;
  /** ETA timestamp ISO 8601, or null if completed/failed. */
  eta_utc: string | null;
  /** 0-100. */
  progress: number;
  /** Reference to a ProofBundle, or null until proof is generated. */
  proof_ref: string | null;
}
