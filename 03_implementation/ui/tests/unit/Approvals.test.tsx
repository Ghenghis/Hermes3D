import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Approval } from "../../src/types/approval";

const adaptersMock = vi.hoisted(() => ({
  getPendingApprovals: vi.fn<[], Promise<Approval[]>>(),
  getApprovalHistory: vi.fn<[], Promise<Approval[]>>(),
  approveApproval: vi.fn<[string, string], Promise<void>>(),
  rejectApproval: vi.fn<[string, string], Promise<void>>(),
  deferApproval: vi.fn<[string, string], Promise<void>>(),
  emitProofEvent: vi.fn(async () => {}),
}));

vi.mock("../../src/api/adapters", () => ({
  adapters: adaptersMock,
}));

import { ApprovalsTab } from "../../src/tabs/Approvals";

function makePending(overrides: Partial<Approval> = {}): Approval {
  return {
    id: "a-1",
    jobId: 42,
    jobTitle: "Print large object",
    approvalType: "PRINT_APPROVAL",
    status: "pending",
    createdAt: "2026-05-09T12:00:00Z",
    decidedAt: null,
    decidedBy: null,
    evidence: { gateResultsUrl: null, artifactUrls: [] },
    fileScope: ["src/foo.ts", "src/bar.ts"],
    requester: "claude-w8-2",
    ...overrides,
  };
}

beforeEach(() => {
  Object.values(adaptersMock).forEach((fn) => {
    if (typeof fn === "function" && "mockReset" in fn) {
      (fn as { mockReset: () => void }).mockReset();
    }
  });
  adaptersMock.emitProofEvent.mockResolvedValue(undefined);
  // Default: 0 polling so tests don't keep timers alive
  if (typeof window !== "undefined") {
    window.__HERMES_APPROVALS_POLL_MS__ = 0;
  }
});

afterEach(() => {
  if (typeof window !== "undefined") {
    delete window.__HERMES_APPROVALS_POLL_MS__;
  }
});

describe("ApprovalsTab", () => {
  it("shows pending approvals with file scope and three action buttons", async () => {
    adaptersMock.getPendingApprovals.mockResolvedValue([makePending()]);
    adaptersMock.getApprovalHistory.mockResolvedValue([]);
    render(<ApprovalsTab />);
    await waitFor(() => {
      expect(screen.getByTestId("approvals-pending-a-1")).toBeInTheDocument();
    });
    expect(screen.getByTestId("approvals-action-approve-a-1")).toBeInTheDocument();
    expect(screen.getByTestId("approvals-action-deny-a-1")).toBeInTheDocument();
    expect(screen.getByTestId("approvals-action-defer-a-1")).toBeInTheDocument();
    expect(screen.getByTestId("approvals-file-scope-a-1")).toBeInTheDocument();
    expect(screen.getByText("claude-w8-2")).toBeInTheDocument();
  });

  it("calls deferApproval when Defer flow is confirmed with a reason", async () => {
    adaptersMock.getPendingApprovals.mockResolvedValue([makePending()]);
    adaptersMock.getApprovalHistory.mockResolvedValue([]);
    adaptersMock.deferApproval.mockResolvedValue(undefined);
    render(<ApprovalsTab />);
    await waitFor(() => screen.getByTestId("approvals-action-defer-a-1"));
    fireEvent.click(screen.getByTestId("approvals-action-defer-a-1"));
    const input = await screen.findByTestId("approvals-input-a-1");
    fireEvent.change(input, { target: { value: "needs more review" } });
    fireEvent.click(screen.getByTestId("approvals-submit-a-1"));
    await waitFor(() => {
      expect(adaptersMock.deferApproval).toHaveBeenCalledWith("a-1", "needs more review");
    });
  });

  it("renders an empty state when no pending approvals", async () => {
    adaptersMock.getPendingApprovals.mockResolvedValue([]);
    adaptersMock.getApprovalHistory.mockResolvedValue([]);
    render(<ApprovalsTab />);
    await waitFor(() => {
      expect(screen.getByTestId("approvals-pending-empty")).toBeInTheDocument();
    });
  });
});
