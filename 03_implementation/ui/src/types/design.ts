export type DesignStatus = "draft" | "submitted" | "modeling" | "slicing" | "approval" | "complete";
export type TargetPrinterId = "t1-a" | "t1-b" | "v400";

export interface DesignSpec {
  id: string;
  title: string;
  description: string;
  targetPrinterId: TargetPrinterId;
  dimensionsXMm: number | null;
  dimensionsYMm: number | null;
  dimensionsZMm: number | null;
  tolerances: string | null;
  material: string | null;
  constraints: string | null;
  createdAt: string;
  status: DesignStatus;
}

export interface ToolchainStep {
  id: string;
  name: string;
  description: string;
  status: "ready" | "pending" | "active" | "blocked";
}
