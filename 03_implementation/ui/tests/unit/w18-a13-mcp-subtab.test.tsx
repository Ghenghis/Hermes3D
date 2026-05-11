/**
 * W18-A13 — McpSubtab regression: shape mismatch with /api/mcp/locks.
 *
 * W18-A3 audit finding: the McpSubtab fetched `/api/mcp/locks` and read
 * `data.locks` + per-row `file` (singular). The real backend
 * envelope is `{accepted, status, items: [{lock_id, files: [...], ...}]}`.
 * The result was a silently empty grid — the BE had 39 active locks and
 * the FE showed zero rows.
 *
 * This test installs a `global.fetch` mock that returns the real
 * backend envelope and asserts the page renders one row per file
 * (since a single lock can guard multiple files). It also locks the
 * envelope-shape contract: a future BE refactor that renames `items` or
 * `files` breaks this test before it breaks the live UI.
 */
import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { McpSubtab } from "../../src/components/settings/McpSubtab";

function envelope(items: Array<{
  lock_id: string;
  owner: string;
  files: string[];
  role?: string;
  task_id?: string | null;
  acquired_utc?: string | null;
  expires_utc?: string | null;
  is_stale?: boolean;
}>): Response {
  return new Response(
    JSON.stringify({
      accepted: true,
      status: "ready",
      reason: null,
      items,
      total: items.length,
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  );
}

describe("McpSubtab (W18-A13 backend envelope shape)", () => {
  const originalFetch = global.fetch;
  beforeEach(() => {
    global.fetch = vi.fn();
  });
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("reads data.items (not data.locks) and renders rows", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      envelope([
        {
          lock_id: "lock-1",
          owner: "w18-a3",
          files: ["docs/HANDOFF.md"],
          role: "audit",
          task_id: "T-1",
          acquired_utc: "2026-05-11T10:00:00Z",
          expires_utc: new Date(Date.now() + 30 * 60_000).toISOString(),
          is_stale: false,
        },
      ]),
    );
    render(<McpSubtab pollIntervalMs={0} />);
    await waitFor(() => {
      expect(screen.getByTestId("settings-mcp-row-w18-a3")).toBeInTheDocument();
    });
    expect(screen.getByText("docs/HANDOFF.md")).toBeInTheDocument();
  });

  it("expands one lock with multiple files into one row per file", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      envelope([
        {
          lock_id: "lock-2",
          owner: "w18-a13",
          files: ["src/api.ts", "src/util.ts", "src/types.ts"],
        },
      ]),
    );
    render(<McpSubtab pollIntervalMs={0} />);
    await waitFor(() => {
      expect(screen.getByText("src/api.ts")).toBeInTheDocument();
    });
    expect(screen.getByText("src/util.ts")).toBeInTheDocument();
    expect(screen.getByText("src/types.ts")).toBeInTheDocument();
    // Three files for one lock → three rows visible.
    expect(screen.getAllByTestId("settings-mcp-row-w18-a13")).toHaveLength(3);
  });

  it("treats is_stale=true as the legacy stale flag", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      envelope([
        {
          lock_id: "lock-3",
          owner: "stale-owner",
          files: ["x"],
          is_stale: true,
        },
      ]),
    );
    render(<McpSubtab pollIntervalMs={0} />);
    await waitFor(() => {
      expect(screen.getByText("1 stale")).toBeInTheDocument();
    });
  });

  it("falls back to data.locks when the backend uses the legacy key", async () => {
    // Older HermesProof shipped `locks` instead of `items`; the
    // normalizer should still parse it so a stale BE doesn't blank the UI.
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          locks: [
            {
              lock_id: "lock-4",
              owner: "legacy",
              file: "legacy.md",
              role: "agent",
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<McpSubtab pollIntervalMs={0} />);
    await waitFor(() => {
      expect(screen.getByTestId("settings-mcp-row-legacy")).toBeInTheDocument();
    });
    expect(screen.getByText("legacy.md")).toBeInTheDocument();
  });

  it("renders the empty-state when items is empty", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(envelope([]));
    render(<McpSubtab pollIntervalMs={0} />);
    await waitFor(() => {
      expect(screen.getByText("No MCP locks held.")).toBeInTheDocument();
    });
  });
});
