import type { ServiceHealthEntry } from "../../types/serviceHealth";

/**
 * Deterministic mock-mode data for the Service Health page. Keeps the
 * UI inspectable in Phase 2 without a running FastAPI backend; live mode
 * fetches `/api/health/services` directly.
 */
export const MOCK_SERVICE_HEALTH: ServiceHealthEntry[] = [
  {
    name: "HermesProof MCP",
    category: "mcp",
    host: "127.0.0.1",
    port: 0,
    status: "disabled",
    detail: "service disabled by config",
    latency_ms: 0,
    probed_at: "2026-05-03T12:00:00+00:00",
  },
  {
    name: "LM Studio",
    category: "llm",
    host: "127.0.0.1",
    port: 1234,
    status: "online",
    detail: "TCP 127.0.0.1:1234 accepted",
    latency_ms: 4.2,
    probed_at: "2026-05-03T12:00:00+00:00",
  },
  {
    name: "Ollama",
    category: "llm",
    host: "127.0.0.1",
    port: 11434,
    status: "online",
    detail: "TCP 127.0.0.1:11434 accepted",
    latency_ms: 6.1,
    probed_at: "2026-05-03T12:00:00+00:00",
  },
  {
    name: "Blender MCP",
    category: "modeling",
    host: "127.0.0.1",
    port: 9876,
    status: "offline",
    detail: "TCP 127.0.0.1:9876 refused (errno=10061)",
    latency_ms: 1.4,
    probed_at: "2026-05-03T12:00:00+00:00",
  },
  {
    name: "ComfyUI",
    category: "modeling",
    host: "127.0.0.1",
    port: 8188,
    status: "offline",
    detail: "TCP 127.0.0.1:8188 refused (errno=10061)",
    latency_ms: 1.2,
    probed_at: "2026-05-03T12:00:00+00:00",
  },
  {
    name: "FastAPI server",
    category: "api",
    host: "127.0.0.1",
    port: 8000,
    status: "online",
    detail: "TCP 127.0.0.1:8000 accepted",
    latency_ms: 2.3,
    probed_at: "2026-05-03T12:00:00+00:00",
  },
  {
    name: "Gradio launcher",
    category: "api",
    host: "127.0.0.1",
    port: 7860,
    status: "online",
    detail: "TCP 127.0.0.1:7860 accepted",
    latency_ms: 3.8,
    probed_at: "2026-05-03T12:00:00+00:00",
  },
  {
    name: "Moonraker — flsun_t1_a",
    category: "printer",
    host: "flsun-t1-a.local",
    port: 7125,
    status: "unreachable",
    detail: "DNS/host error",
    latency_ms: 0,
    probed_at: "2026-05-03T12:00:00+00:00",
  },
];
