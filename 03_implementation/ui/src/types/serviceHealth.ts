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

/**
 * Honest-blocked envelope wrapping a `GET /api/health/services` result.
 *
 * Added in W18-A13 (PR addressing W18-A3 audit). The Service Health page
 * previously swallowed non-2xx + network errors with an empty array,
 * silently rendering an empty service grid. The envelope lets the page
 * differentiate three cases:
 *
 * - `status === "ready"` + `results.length > 0`: live probe results.
 * - `status === "ready"` + `results.length === 0`: backend confirmed
 *   no probes are configured (rare; honest empty state, no banner).
 * - `status === "blocked"` or `"unavailable"`: render an honest-blocked
 *   banner with `reason` so the operator sees the actual cause
 *   (e.g. `mcp_server_unreachable`, `http_404`, `network_error`).
 */
export interface ServiceHealthEnvelope {
  status: "ready" | "blocked" | "unavailable";
  accepted: boolean;
  reason: string | null;
  results: ServiceHealthEntry[];
}
