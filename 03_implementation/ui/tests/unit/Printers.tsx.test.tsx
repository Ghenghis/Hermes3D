/**
 * Printers tab — W17-FIX-PRINTERS-API regression test.
 *
 * Asserts that when `/api/printers` returns the live 4-printer payload,
 * the Printers tab actually mounts per-printer cards. The bug we're guarding
 * against is the previous behavior where `adapters.getPrinters()` swallowed
 * errors and returned `[]`, leaving the operator staring at
 * "No printer inventory returned from the live printer API" while the
 * backend was returning 4 valid records.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

// Adapter mock — Printers.tsx still calls adapters for proof-event/lock-state
// side effects after the hook resolves. Keep these as no-ops so the test
// focuses on the wire-up between the live API and the per-printer cards.
const adaptersMock = vi.hoisted(() => ({
  getPrinterLockState: vi.fn(async (id: string) => ({
    printer_id: id,
    locked: true,
    reason: "S1 maintenance lock",
  })),
  emitProofEvent: vi.fn(async () => undefined),
  testPrinter: vi.fn(async () => ({ printer_id: "x", ok: true, message: "ok", latency_ms: 1 })),
  uploadGcode: vi.fn(async () => ({ printer_id: "x", accepted: false, uploaded: false, started: false })),
  updatePrinterStatus: vi.fn(async () => undefined),
  // Legacy path — should NOT be the source of truth anymore, but Dashboard
  // and other call sites still use it. The fix makes the Printers tab
  // independent of this mock.
  getPrinters: vi.fn(async () => []),
  probePrinter: vi.fn(),
  validateCameraUrl: vi.fn(),
  onboardPrinter: vi.fn(),
}));

vi.mock("../../src/api/adapters", () => ({
  adapters: adaptersMock,
}));

import { PrintersTab } from "../../src/tabs/Printers";

function livePrinter(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: "flsun_t1_a",
    name: "T1 #1",
    model: "FLSUN T1",
    ip: "192.168.0.10",
    status: "online",
    adapter: "moonraker",
    data_source: "live",
    temp_hot: 33.2,
    temp_bed: 60.0,
    progress: 100.0,
    current_job: "hermes3d/test.gcode",
    maintenance_flag: false,
    camera_url: "http://192.168.0.10/webcam/?action=stream",
    moonraker_url: "http://192.168.0.10",
    source_refs: { official_wiki_url: "https://wiki.flsun3d.com/en/FlsunT1" },
    status_source: "live",
    safety_policy: "write_enabled",
    write_enabled: true,
    onboarded: false,
    ...overrides,
  };
}

const FOUR_LIVE_PRINTERS = [
  livePrinter(),
  livePrinter({ id: "flsun_t1_b", name: "T1 #2", ip: "192.168.0.11" }),
  livePrinter({
    id: "flsun_s1",
    name: "FLSUN S1",
    model: "FLSUN S1",
    ip: "192.168.0.12",
    status: "offline",
    data_source: "policy",
    temp_hot: null,
    temp_bed: null,
    progress: null,
    current_job: null,
    maintenance_flag: true,
    safety_policy: "locked",
    write_enabled: false,
    camera_url: "http://192.168.0.12/webcam/?action=stream",
    moonraker_url: "http://192.168.0.12",
  }),
  livePrinter({
    id: "flsun_v400",
    name: "FLSUN V400",
    model: "FLSUN V400",
    ip: "192.168.0.34",
    temp_hot: 26.7,
    temp_bed: 26.9,
    progress: 0.0,
    current_job: null,
    camera_url: "http://192.168.0.34/webcam/?action=stream",
    moonraker_url: "http://192.168.0.34",
  }),
];

function mockFetchOnce(body: unknown, init: { status?: number; ok?: boolean } = {}): void {
  const ok = init.ok ?? true;
  const status = init.status ?? 200;
  globalThis.fetch = vi.fn(async () => {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }) as unknown as typeof fetch;
  // `ok` is derived from status by the Response constructor — no override
  // needed; we just keep the helper signature explicit.
  void ok;
}

beforeEach(() => {
  Object.values(adaptersMock).forEach((fn) => {
    if (typeof fn === "function" && "mockReset" in fn) {
      (fn as { mockReset: () => void }).mockReset();
    }
  });
  adaptersMock.getPrinterLockState.mockResolvedValue({
    printer_id: "s1",
    locked: true,
    reason: "S1 maintenance lock",
  });
  adaptersMock.emitProofEvent.mockResolvedValue(undefined);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("PrintersTab — W17-FIX-PRINTERS-API wiring", () => {
  it("mounts a per-printer card for every printer returned by /api/printers", async () => {
    mockFetchOnce(FOUR_LIVE_PRINTERS);
    render(<PrintersTab />);

    // The four operator-canonical IDs that the tab orders to.
    await waitFor(() => {
      expect(screen.getByTestId("printer-card-t1-1")).toBeInTheDocument();
    });
    expect(screen.getByTestId("printer-card-t1-2")).toBeInTheDocument();
    expect(screen.getByTestId("printer-card-s1")).toBeInTheDocument();
    expect(screen.getByTestId("printer-card-v400")).toBeInTheDocument();
    expect(screen.queryByTestId("printers-empty")).not.toBeInTheDocument();
    expect(screen.queryByTestId("printers-error")).not.toBeInTheDocument();
  });

  it("renders a W6-9 / W15-A15 safety-state badge on every printer card", async () => {
    mockFetchOnce(FOUR_LIVE_PRINTERS);
    render(<PrintersTab />);

    await waitFor(() => {
      expect(screen.getByTestId("printer-safety-state-t1-1")).toHaveAttribute(
        "data-safety-state",
        "write_enabled",
      );
    });
    expect(screen.getByTestId("printer-safety-state-t1-2")).toHaveAttribute(
      "data-safety-state",
      "write_enabled",
    );
    // S1 is always safety-locked per backend policy.
    expect(screen.getByTestId("printer-safety-state-s1")).toHaveAttribute(
      "data-safety-state",
      "locked",
    );
    expect(screen.getByTestId("printer-safety-state-v400")).toHaveAttribute(
      "data-safety-state",
      "write_enabled",
    );
  });

  it("surfaces a Printer API error message when the live fetch fails", async () => {
    // 503 — the kind of failure the legacy `getLivePrinters` would have
    // silently swallowed, producing "No printer inventory returned…".
    globalThis.fetch = vi.fn(async () => new Response("backend offline", { status: 503 })) as unknown as typeof fetch;
    render(<PrintersTab />);

    await waitFor(() => {
      expect(screen.getByTestId("printers-error")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("printer-card-t1-1")).not.toBeInTheDocument();
    expect(screen.getByTestId("printers-error").textContent).toMatch(/HTTP 503/);
  });

  it("renders the 'no printers configured' empty state when the API returns []", async () => {
    mockFetchOnce([]);
    render(<PrintersTab />);

    await waitFor(() => {
      expect(screen.getByTestId("printers-empty")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("printers-error")).not.toBeInTheDocument();
    expect(screen.queryByTestId("printer-card-t1-1")).not.toBeInTheDocument();
  });
});
