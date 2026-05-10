export type GenerationEngine = "trellis2" | "hunyuan3d21" | "triposr";
export type TruthGateStatus = "pending" | "running" | "pass" | "fail" | "skipped";

export interface TruthGateResult {
  gateNumber: number;
  gateName: string;
  status: TruthGateStatus;
  proofData: Record<string, unknown>;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface GenerationServices {
  primaryEngine: { id: string; url: string; status: "connected" | "timeout" | "missing" };
  comparisonEngine: { id: string; url: string; status: string };
  fastPreview: { id: string; url: string; status: string };
  comfyui: { url: string; status: string };
  trellis2: { url: string; status: string };
}
