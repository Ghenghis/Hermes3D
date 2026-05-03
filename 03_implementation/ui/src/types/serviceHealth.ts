/**
 * Wire shape returned by `GET /api/health/services`.
 *
 * Mirrors the FastAPI serialiser in
 * `03_implementation/src/hermes3d/api/health.py`. Keep the two in lock-step:
 * the Service Health page is the only consumer.
 */

export type ServiceStatus =
  | "online"
  | "offline"
  | "unreachable"
  | "auth-required"
  | "disabled"
  | "unknown";

export type ServiceCategory =
  | "mcp"
  | "llm"
  | "modeling"
  | "printer"
  | "api"
  | "tunnel";

export interface ServiceHealthEntry {
  name: string;
  category: ServiceCategory;
  host: string;
  port: number;
  status: ServiceStatus;
  detail: string;
  latency_ms: number;
  probed_at: string;
}

export interface ServiceHealthResponse {
  results: ServiceHealthEntry[];
}
