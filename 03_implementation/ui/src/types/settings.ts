export type ThemeName = "midnight" | "alloy" | "ember" | "forest";

export interface RuntimePorts {
  bridge: number;
  api: number;
  ui: number;
  [service: string]: number;
}

export interface AppSettings {
  theme: ThemeName;
  ports: RuntimePorts;
  printerUrls: Record<string, string>;
  cameraUrls: Record<string, string>;
  serviceUrls: Record<string, string>;
}
