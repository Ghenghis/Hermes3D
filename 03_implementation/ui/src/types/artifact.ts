export type ArtifactType =
  | "model_evidence"
  | "agent_plan"
  | "gcode"
  | "screenshot"
  | "report"
  | "photo"
  | "mesh"
  | "g-code"
  | "log"
  | "agent_attachment"
  | "other";
export type ArtifactStage =
  | "INTAKE"
  | "MODELING"
  | "SLICING"
  | "AGENT_CHAT"
  | "PRINT_APPROVAL"
  | "PRINT_RUN"
  | "COMPLETE";
export type ArtifactGate = "MODEL_APPROVAL" | "PRINT_APPROVAL" | `GATE_${1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11}`;
export type EvidenceType = ArtifactType;

export interface Artifact {
  id: string;
  jobId: string | number;
  jobTitle: string;
  type: ArtifactType;
  name: string;
  path: string;
  stage: ArtifactStage;
  gate: ArtifactGate | null;
  agent: string | null;
  label: string | null;
  notes: string | null;
  sizeBytes: number;
  createdAt: string;
  downloadUrl: string;
}

export interface AttachEvidenceForm {
  jobId: string | number;
  evidenceType: ArtifactType;
  agent: string;
  stage: ArtifactStage;
  gate: ArtifactGate;
  label: string;
  file: File | null;
  notes: string;
}

export type EvidenceForm = AttachEvidenceForm;
