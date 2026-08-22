export type ApprovalType = "MODEL_APPROVAL" | "PRINT_APPROVAL" | "REPAIR_APPROVAL" | "IDLE_CANDIDATE_REVIEW";
export type ApprovalStatus = "pending" | "approved" | "rejected" | "deferred";
export type ApprovalDecision = "approved" | "rejected" | "deferred";

export interface Approval {
  id: string;
  jobId: number;
  jobTitle: string;
  approvalType: ApprovalType;
  status: ApprovalStatus;
  createdAt: string;
  decidedAt: string | null;
  decidedBy: "operator" | "auto" | null;
  evidence: {
    gateResultsUrl: string | null;
    artifactUrls: string[];
  };
  /**
   * Optional list of repository-relative file paths affected by the request.
   * Surfaced from `hermes_request_handoff` payloads. Empty when the
   * approval covers a non-file action (e.g. job repair).
   */
  fileScope?: string[];
  /**
   * Optional name of the agent/operator that requested this approval.
   * Mirrors the `requester` field on `hermes_request_handoff` payloads.
   */
  requester?: string | null;
}
