/**
 * W18-A13 — ServiceHealthPage regression: honest-blocked banner.
 *
 * W18-A3 audit finding: when /api/health/services returned 404 (route
 * not on develop) or any non-2xx, the adapter swallowed it as `[]` and
 * the page rendered an empty service grid with no operator signal.
 *
 * This suite mocks the `adapters.getServiceHealthEnvelope` call and
 * asserts:
 *  - `status: "ready"` → no banner, grid renders normally.
 *  - `status: "blocked"` → banner visible with backend reason.
 *  - `status: "unavailable"` → banner visible with `http_404` / network
 *    reason.
 */
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ServiceHealthPage } from "../../src/components/health/ServiceHealthPage";
import { adapters } from "../../src/api/adapters";
import type { ServiceHealthEnvelope } from "../../src/types/serviceHealth";

const realGetServiceHealthEnvelope = adapters.getServiceHealthEnvelope;
const realGetServiceHealth = adapters.getServiceHealth;

function stubEnvelope(envelope: ServiceHealthEnvelope): void {
  (adapters as unknown as {
    getServiceHealthEnvelope: () => Promise<ServiceHealthEnvelope>;
  }).getServiceHealthEnvelope = vi.fn(async () => envelope);
  (adapters as unknown as {
    getServiceHealth: () => Promise<ServiceHealthEnvelope["results"]>;
  }).getServiceHealth = vi.fn(async () => envelope.results);
}

describe("ServiceHealthPage (W18-A13 honest-blocked banner)", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });
  afterEach(() => {
    vi.useRealTimers();
    (adapters as unknown as { getServiceHealthEnvelope: typeof realGetServiceHealthEnvelope }).getServiceHealthEnvelope = realGetServiceHealthEnvelope;
    (adapters as unknown as { getServiceHealth: typeof realGetServiceHealth }).getServiceHealth = realGetServiceHealth;
  });

  it("renders the honest-blocked banner with the backend reason when status=blocked", async () => {
    stubEnvelope({
      status: "blocked",
      accepted: false,
      reason: "no_health_probes_registered",
      results: [],
    });
    render(<ServiceHealthPage />);
    await waitFor(() => {
      expect(screen.getByTestId("service-health-blocked-banner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("service-health-blocked-reason").textContent).toContain(
      "no_health_probes_registered",
    );
  });

  it("renders the banner with the http_404 reason when the bridge has no route", async () => {
    stubEnvelope({
      status: "unavailable",
      accepted: false,
      reason: "http_404",
      results: [],
    });
    render(<ServiceHealthPage />);
    await waitFor(() => {
      expect(screen.getByTestId("service-health-blocked-banner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("service-health-blocked-reason").textContent).toBe(
      "http_404",
    );
  });

  it("does not render the banner when status=ready", async () => {
    stubEnvelope({
      status: "ready",
      accepted: true,
      reason: null,
      results: [
        {
          name: "Some Service",
          category: "mcp",
          host: "127.0.0.1",
          port: 8765,
          status: "online",
          detail: "ok",
          latency_ms: 12.0,
          probed_at: "2026-05-11T10:00:00Z",
        },
      ],
    });
    render(<ServiceHealthPage />);
    await waitFor(() => {
      // Wait for at least one render cycle.
      expect(screen.getByTestId("service-health-root")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("service-health-blocked-banner")).not.toBeInTheDocument();
  });
});
