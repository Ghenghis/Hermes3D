export type ApprovalType = "MODEL_APPROVAL" | "PRINT_APPROVAL" | "REPAIR_APPROVAL";
export type ApprovalStatus = "pending" | "approved" | "rejected";
export type ApprovalDecision = "approved" | "rejected";

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
}
