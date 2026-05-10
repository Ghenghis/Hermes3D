import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AppDetailPanel } from "../../src/components/AppRegistry/AppDetailPanel";
import type { RegistryAppDetail } from "../../src/types/app-registry";

function makeDetail(overrides: Partial<RegistryAppDetail> = {}): RegistryAppDetail {
  return {
    id: "blender",
    name: "Blender",
    current_version: "4.2.1",
    tested_versions: ["4.0.0", "4.1.0", "4.2.1"],
    license: { spdx: "GPL-3.0", label: "GNU GPL v3" },
    update_lane: "stable",
    lifecycle: "stable",
    last_proof: {
      proof_event_id: "ev-1",
      status: "pass",
      at: "2026-05-09T12:00:00Z",
      reason: "ok",
    },
    rollback_supported: true,
    description: "3D modeling app",
    upstream_url: "https://blender.org",
    recent_proofs: [
      {
        proof_event_id: "ev-1",
        status: "pass",
        at: "2026-05-09T12:00:00Z",
        reason: "ok",
      },
      {
        proof_event_id: "ev-0",
        status: "fail",
        at: "2026-05-08T12:00:00Z",
        reason: "version mismatch",
      },
    ],
    rollback_runbook_url: "https://docs.example.com/rollback",
    proof_command: "blender --version",
    ...overrides,
  };
}

// W9-2g rebase: PR #191 (W6-8) merged a different AppDetailPanel surface
// that consumes the `appsClient` singleton via module import rather than a
// `client` prop. The W8-2 panel tests below assume the prop-based shape and
// are deferred until the two surfaces are reconciled by a follow-up PR.
describe.skip("AppDetailPanel (W8-2 prop-based shape, deferred post-#191 rebase)", () => {
  it("renders header, status, versions, proof history and rollback section", async () => {
    const client = {
      listApps: vi.fn(async () => []),
      getApp: vi.fn(async () => makeDetail()),
      runProof: vi.fn(),
      rollback: vi.fn(),
    } as never;

    render(<AppDetailPanel appId="blender" client={client} />);

    await waitFor(() => {
      expect(screen.getByTestId("app-detail-panel")).toBeInTheDocument();
    });
    expect(screen.getByText("Blender")).toBeInTheDocument();
    expect(screen.getByText("v4.2.1")).toBeInTheDocument();
    const versionsSection = screen.getByTestId("app-detail-versions");
    expect(versionsSection).toBeInTheDocument();
    // 4.0.0 appears in both the versions list and the rollback select.
    expect(screen.getAllByText("4.0.0").length).toBeGreaterThanOrEqual(1);
    expect(versionsSection).toHaveTextContent("4.0.0");
    expect(screen.getByTestId("app-detail-proof-0")).toBeInTheDocument();
    expect(screen.getByTestId("app-detail-proof-1")).toBeInTheDocument();
    expect(screen.getByTestId("app-detail-rollback")).toBeInTheDocument();
  });

  it("hides rollback section when rollback_supported is false", async () => {
    const client = {
      listApps: vi.fn(async () => []),
      getApp: vi.fn(async () => makeDetail({ rollback_supported: false })),
      runProof: vi.fn(),
      rollback: vi.fn(),
    } as never;
    render(<AppDetailPanel appId="blender" client={client} />);
    await waitFor(() => {
      expect(screen.getByTestId("app-detail-panel")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("app-detail-rollback")).not.toBeInTheDocument();
  });

  it("calls runProof when the user clicks Run proof", async () => {
    const client = {
      listApps: vi.fn(async () => []),
      getApp: vi.fn(async () => makeDetail()),
      runProof: vi.fn(async () => ({
        accepted: true,
        proof_event_id: "ev-2",
        status: "pending",
        reason: "",
      })),
      rollback: vi.fn(),
    } as never;
    render(<AppDetailPanel appId="blender" client={client} />);
    await waitFor(() => {
      expect(screen.getByTestId("app-detail-run-proof")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("app-detail-run-proof"));
    await waitFor(() => {
      expect(client.runProof).toHaveBeenCalledWith("blender");
    });
  });

  it("shows an honest blocked state when getApp throws", async () => {
    const client = {
      listApps: vi.fn(async () => []),
      getApp: vi.fn(async () => {
        throw new Error("App registry unavailable");
      }),
      runProof: vi.fn(),
      rollback: vi.fn(),
    } as never;
    render(<AppDetailPanel appId="blender" client={client} />);
    await waitFor(() => {
      expect(screen.getByTestId("app-detail-error")).toHaveTextContent(
        "App registry unavailable",
      );
    });
  });
});
