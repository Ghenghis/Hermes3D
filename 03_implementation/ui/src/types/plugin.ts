export type PluginState = "ACTIVE" | "READY" | "PLANNED";

export interface Plugin {
  id: string;
  display: string;
  description: string;
  state: PluginState;
  dependencies: string[];
  configSchema: Record<string, unknown> | null;
  healthUrl: string | null;
  installVia: "source_os_module" | "npm" | "pip" | "none";
  sourceOsModuleId: string | null;
  configured: boolean;
  status?: string;
  reason?: string | null;
}
