export type ProviderStatus = "green" | "amber" | "red" | "idle";

export interface ProviderHealth {
  provider_id: string;
  status: ProviderStatus;
  last_probe_utc: string | null;
  http_status: number | null;
  latency_ms: number | null;
  stale: boolean;
}
