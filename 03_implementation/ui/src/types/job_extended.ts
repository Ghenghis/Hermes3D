export interface JobStep {
  id: string;
  description: string;
  status: "pending" | "running" | "done" | "failed";
  startedAt: string | null;
  completedAt: string | null;
}

export interface JobEvent {
  id: string;
  type: string;
  description: string;
  timestamp: string;
}

export interface JobDetail {
  id: number;
  title: string;
  type: string;
  status: "queued" | "running" | "done" | "failed" | "cancelled" | "waiting_approval";
  dryRun: boolean;
  printerId: string | null;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  steps: JobStep[];
  artifacts: string[];
  events: JobEvent[];
}
