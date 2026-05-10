import type { LaunchKind as SourceLaunchKind } from "./source-os";

export type InstallState =
  | "unavailable"
  | "source_available"
  | "downloading"
  | "installing"
  | "installed"
  | "detected"
  | "healthy"
  | "degraded"
  | "failed"
  | "rollback_available";

export type ModulePriority =
  | "primary"
  | "secondary"
  | "core-runtime"
  | "profile-first"
  | "fast-preview"
  | "reference"
  | "research"
  | "catalog"
  | "candidate"
  | "future";

export type ModuleCategory =
  | "slicers"
  | "modelers"
  | "print_farm"
  | "firmware"
  | "three_d_generation"
  | "agents"
  | "library"
  | "materials"
  | "hardware"
  | "utilities"
  | "research";

export type LaunchKind = Exclude<SourceLaunchKind, "rust_library_reference" | "touch_ui_reference">;

export interface BridgeTask {
  id: string;
  name: string;
  status: "pending" | "running" | "pass" | "fail" | "skipped";
  lastRunAt: string | null;
  lastRunLog: string | null;
  durationMs: number | null;
}

export interface Module {
  id: string;
  display: string;
  category: ModuleCategory;
  section: string;
  priority: ModulePriority;
  license: string;
  repoUrl: string | null;
  repoPolicy: string | null;
  localPath: string | null;
  installState: InstallState;
  healthState: "unknown" | "healthy" | "degraded" | "failed";
  versionDetected: string | null;
  exePath: string | null;
  launchKind: LaunchKind;
  safety: string | null;
  bridgeTasks: BridgeTask[];
  settingsSchemaPath: string | null;
  checkpointPath: string | null;
}

export interface BridgeTaskResult {
  taskId: string;
  status: "pass" | "fail";
  log: string;
  durationMs: number;
  proofEventId: string;
}

export interface DetectResult {
  detected: boolean;
  version: string | null;
  exePath: string | null;
  healthState: "healthy" | "degraded" | "failed";
}

export interface InstallStep {
  id: string;
  description: string;
  command: string | null;
  status: "pending" | "running" | "done" | "failed";
}

export interface InstallPlan {
  moduleId: string;
  steps: InstallStep[];
  diskMb: number;
  estimatedMinutes: number;
  requiresRestart: boolean;
  platform: "windows" | "linux" | "macos";
}

export interface LaunchResult {
  pid: number | null;
  port: number | null;
  url: string | null;
  launched: boolean;
}
