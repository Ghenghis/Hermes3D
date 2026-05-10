import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { McpSubtab, type McpLockEntry } from "../../src/components/settings/McpSubtab";

describe("McpSubtab", () => {
  it("renders a row per active lock", async () => {
    const locks: McpLockEntry[] = [
      {
        file: "src/foo.ts",
        owner: "claude-w8-2",
        role: "agent",
        taskId: "T-1",
        acquiredAt: "2026-05-09T10:00:00Z",
        expiresAt: new Date(Date.now() + 30 * 60_000).toISOString(),
        stale: false,
      },
      {
        file: "src/bar.ts",
        owner: "codex-impl-01",
        role: "agent",
        taskId: null,
        acquiredAt: null,
        expiresAt: null,
        stale: true,
      },
    ];
    render(<McpSubtab fetcher={async () => locks} pollIntervalMs={0} />);
    await waitFor(() => {
      expect(screen.getByTestId("settings-mcp-row-claude-w8-2")).toBeInTheDocument();
      expect(screen.getByTestId("settings-mcp-row-codex-impl-01")).toBeInTheDocument();
    });
    expect(screen.getByText("1 stale")).toBeInTheDocument();
  });

  it("shows an honest blocked state when the locks API errors", async () => {
    const fetcher = vi.fn(async (): Promise<McpLockEntry[]> => {
      throw new Error("ECONNREFUSED");
    });
    render(<McpSubtab fetcher={fetcher} pollIntervalMs={0} />);
    await waitFor(() => {
      expect(screen.getByTestId("settings-mcp-error")).toHaveTextContent("ECONNREFUSED");
    });
  });

  it("shows an empty-state message when the API returns no locks", async () => {
    render(<McpSubtab fetcher={async () => []} pollIntervalMs={0} />);
    await waitFor(() => {
      expect(screen.getByText("No MCP locks held.")).toBeInTheDocument();
    });
  });
});
