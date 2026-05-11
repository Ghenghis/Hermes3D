/**
 * W18-A13 — Wiring unit tests for the bounded-fetch helper and the
 * Autopilot honest-blocked envelope detection.
 *
 * These exercise the adapter-level fixes from W18-A3 audit:
 *  - The action-catalog fetch must abort after 8s (FAIL_BROKEN cause).
 *  - The service-health envelope must surface http_<code> on non-2xx
 *    (FAIL_NOT_WIRED cause: page silently rendered empty).
 *  - The sourceOsClient.updateReadiness now points at the canonical
 *    /api/modules/update/readiness path (FAIL_BACKEND_MISSING cause).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  AGENT_ACTION_CATALOG_TIMEOUT_MS,
  getServiceHealthEnvelopeLive,
  getAgentActionCatalogLive,
} from "../../src/api/adapters.live";
import { appsClient as sourceOsClientNamespace } from "../../src/api/hermes3dClient";

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("W18-A13 action-catalog bounded fetch", () => {
  it("aborts after AGENT_ACTION_CATALOG_TIMEOUT_MS and returns honest-blocked envelope", async () => {
    // The constant must exist and be a sensible value.
    expect(typeof AGENT_ACTION_CATALOG_TIMEOUT_MS).toBe("number");
    expect(AGENT_ACTION_CATALOG_TIMEOUT_MS).toBeGreaterThan(0);
    expect(AGENT_ACTION_CATALOG_TIMEOUT_MS).toBeLessThanOrEqual(30_000);

    vi.useFakeTimers({ shouldAdvanceTime: true });
    let abortObserved = false;
    global.fetch = vi.fn((_url: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        // Never resolve; only reject if aborted, so the timeout path is exercised.
        const signal = init?.signal;
        if (signal) {
          if (signal.aborted) {
            abortObserved = true;
            reject(new DOMException("aborted", "AbortError"));
            return;
          }
          signal.addEventListener("abort", () => {
            abortObserved = true;
            reject(new DOMException("aborted", "AbortError"));
          });
        }
      }),
    ) as unknown as typeof fetch;

    const promise = getAgentActionCatalogLive();
    // Advance past the timeout.
    await vi.advanceTimersByTimeAsync(AGENT_ACTION_CATALOG_TIMEOUT_MS + 100);
    const result = await promise;
    // Honest-blocked envelope is returned when the call times out.
    expect(result.status).toBe("blocked");
    expect(result.summary).toMatch(/unavailable|action catalog/i);
    expect(abortObserved).toBe(true);
  });
});

describe("W18-A13 getServiceHealthEnvelopeLive", () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  it("returns status=unavailable with http_<code> when the BE 404s", async () => {
    global.fetch = vi.fn(async () =>
      new Response("not found", { status: 404 }),
    ) as unknown as typeof fetch;
    const envelope = await getServiceHealthEnvelopeLive();
    expect(envelope.status).toBe("unavailable");
    expect(envelope.accepted).toBe(false);
    expect(envelope.reason).toBe("http_404");
    expect(envelope.results).toEqual([]);
  });

  it("returns status=unavailable with network_error when fetch throws", async () => {
    global.fetch = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    }) as unknown as typeof fetch;
    const envelope = await getServiceHealthEnvelopeLive();
    expect(envelope.status).toBe("unavailable");
    expect(envelope.reason).toMatch(/network_error/);
  });

  it("returns status=ready with results when the backend is up", async () => {
    global.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          accepted: true,
          status: "ready",
          reason: null,
          results: [
            {
              name: "Hermes Locks",
              category: "mcp",
              host: "127.0.0.1",
              port: 8910,
              status: "online",
              detail: "ok",
              latency_ms: 5.2,
              probed_at: "2026-05-11T10:00:00Z",
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    ) as unknown as typeof fetch;
    const envelope = await getServiceHealthEnvelopeLive();
    expect(envelope.status).toBe("ready");
    expect(envelope.results).toHaveLength(1);
    expect(envelope.results[0].name).toBe("Hermes Locks");
  });

  it("returns status=blocked when the backend reports accepted=false", async () => {
    global.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({
          accepted: false,
          status: "blocked",
          reason: "no_health_probes_registered",
          results: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    ) as unknown as typeof fetch;
    const envelope = await getServiceHealthEnvelopeLive();
    expect(envelope.status).toBe("blocked");
    expect(envelope.reason).toBe("no_health_probes_registered");
  });
});

describe("W18-A13 sourceOsClient.updateReadiness canonical path", () => {
  // Re-read the file at runtime — the export carries the path via the
  // safeGetJson closure; we assert by spying on the underlying fetch.
  it("requests /api/modules/update/readiness, not /api/source-os/modules/update-readiness", async () => {
    const calls: string[] = [];
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      calls.push(url);
      return new Response(JSON.stringify({ ready: true }), { status: 200 });
    }) as unknown as typeof fetch;
    await sourceOsClientNamespace.updateReadiness();
    expect(calls.length).toBeGreaterThan(0);
    const requested = calls[calls.length - 1];
    expect(requested).toContain("/api/modules/update/readiness");
    expect(requested).not.toContain("/api/source-os/modules/update-readiness");
  });
});
