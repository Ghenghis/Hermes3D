/**
 * Vitest suite for the Task Monitor drawer.
 *
 * Covers:
 *   - Pure backoff math (nextBackoffMs, classifyError).
 *   - Render of the drawer header / row / state badges.
 *   - Polling-mocked expansion of a run row to its event timeline.
 *   - Clear-completed local filter behaviour.
 *
 * Run with: npx vitest run tests/unit/TaskMonitorDrawer.test.tsx
 *
 * NOTE: This file lives in tests/unit/ (NOT under src/) so that tsc, which is
 * scoped to `include: ["src"]` in tsconfig.json, will not type-check it as part
 * of `npm run build`. Vitest is configured separately via vitest.config.ts.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import {
  classifyError,
  nextBackoffMs,
  useRecoveryRunsPoll,
} from "../../src/components/TaskMonitor/useRecoveryRunsPoll";
import {
  RecoveryRunsFetchError,
  type RecoveryRun,
  type RecoveryRunsResponse,
} from "../../src/api/recoveryRuns";
import { TaskMonitorDrawer } from "../../src/components/TaskMonitor/TaskMonitorDrawer";

afterEach(cleanup);

const sampleRun = (
  overrides: Partial<RecoveryRun> & Pick<RecoveryRun, "attempt_id" | "task_id" | "state">,
): RecoveryRun => ({
  attempt_id: overrides.attempt_id,
  task_id: overrides.task_id,
  state: overrides.state,
  branch: overrides.branch ?? "propose_review_apply_rerun",
  failure_class: overrides.failure_class ?? "gate_fail",
  failed_step_type: overrides.failed_step_type ?? "ci",
  failure_fingerprint: overrides.failure_fingerprint ?? "fp-aaa",
  retry_count: overrides.retry_count ?? 0,
  retry_budget_max: overrides.retry_budget_max ?? 3,
  actor: overrides.actor ?? "user",
  confirm: overrides.confirm ?? false,
  started_utc: overrides.started_utc ?? "2026-05-09T10:00:00Z",
  last_event_utc: overrides.last_event_utc ?? "2026-05-09T10:01:00Z",
  last_event_summary: overrides.last_event_summary ?? "step 1",
  proposal_id: overrides.proposal_id ?? null,
  review_evidence_id: overrides.review_evidence_id ?? null,
  apply_evidence_id: overrides.apply_evidence_id ?? null,
  retry_gate_id: overrides.retry_gate_id ?? null,
  terminal_status: overrides.terminal_status ?? null,
  cancelled_reason: overrides.cancelled_reason ?? null,
  is_terminal: overrides.is_terminal ?? false,
  is_cancellable: overrides.is_cancellable ?? true,
  history: overrides.history,
  locked_files: overrides.locked_files,
  pre_snapshot_ids: overrides.pre_snapshot_ids,
  freeze_event_utc: overrides.freeze_event_utc,
  next_action: overrides.next_action,
});

const sampleResponse = (runs: RecoveryRun[]): RecoveryRunsResponse => ({
  count: runs.length,
  by_state: runs.reduce<Partial<Record<RecoveryRun["state"], number>>>((acc, r) => {
    acc[r.state] = (acc[r.state] ?? 0) + 1;
    return acc;
  }, {}),
  runs,
  task_id_filter: null,
});

describe("nextBackoffMs", () => {
  it("returns the base interval at step 0", () => {
    expect(nextBackoffMs(0, 5_000)).toBe(5_000);
  });

  it("doubles each step", () => {
    expect(nextBackoffMs(1, 5_000)).toBe(10_000);
    expect(nextBackoffMs(2, 5_000)).toBe(20_000);
    expect(nextBackoffMs(3, 5_000)).toBe(40_000);
  });

  it("caps at MAX_BACKOFF_MS (60s)", () => {
    expect(nextBackoffMs(10, 5_000)).toBe(60_000);
  });
});

describe("classifyError", () => {
  it("classifies 5xx as retry", () => {
    expect(classifyError(new RecoveryRunsFetchError(503, "boom"))).toBe("retry");
    expect(classifyError(new RecoveryRunsFetchError(0, "no network"))).toBe("retry");
  });
  it("classifies 4xx as fatal", () => {
    expect(classifyError(new RecoveryRunsFetchError(403, "forbidden"))).toBe("fatal");
  });
  it("classifies AbortError as retry (silent)", () => {
    const err = new DOMException("aborted", "AbortError");
    expect(classifyError(err)).toBe("retry");
  });
});

describe("<TaskMonitorDrawer /> static-data render", () => {
  it("shows empty state when no runs are present", () => {
    render(
      <TaskMonitorDrawer open onClose={() => {}} staticData={sampleResponse([])} />,
    );
    expect(screen.getByTestId("task-monitor-drawer")).toHaveAttribute("data-open", "true");
    expect(screen.getByTestId("task-monitor-list")).toHaveTextContent(
      /No active recovery runs/,
    );
  });

  it("renders one row per run with the right state badge", () => {
    const runs = [
      sampleRun({ attempt_id: "a1aaaa1aaaaaaaaa", task_id: "T-1", state: "proposing" }),
      sampleRun({ attempt_id: "a2bbbb2bbbbbbbbb", task_id: "T-2", state: "applying" }),
      sampleRun({ attempt_id: "a3cccc3cccccccccc", task_id: "T-3", state: "escalated", terminal_status: "escalated", is_terminal: true, is_cancellable: false }),
    ];
    render(
      <TaskMonitorDrawer open onClose={() => {}} staticData={sampleResponse(runs)} />,
    );
    const rows = screen.getAllByTestId("task-monitor-row");
    expect(rows).toHaveLength(3);
    const badges = screen.getAllByTestId("task-monitor-state-badge");
    const states = badges.map((badge) => badge.getAttribute("data-state"));
    expect(states).toEqual(["proposing", "applying", "escalated"]);
    expect(screen.getByTestId("task-monitor-count")).toHaveTextContent("3");
  });

  it("expands a row to show its event timeline", () => {
    const run = sampleRun({
      attempt_id: "a1aaaa1aaaaaaaaa",
      task_id: "T-1",
      state: "applying",
      history: [
        { ts_utc: "2026-05-09T10:00:00Z", from: "created", to: "proposing", note: "step 1" },
        { ts_utc: "2026-05-09T10:00:30Z", from: "proposing", to: "reviewing", note: "step 2" },
        { ts_utc: "2026-05-09T10:01:00Z", from: "reviewing", to: "applying", note: "step 3" },
      ],
    });
    render(<TaskMonitorDrawer open onClose={() => {}} staticData={sampleResponse([run])} />);
    expect(screen.queryByTestId("task-monitor-timeline")).not.toBeInTheDocument();
    const row = screen.getByTestId("task-monitor-row");
    fireEvent.click(within(row).getByRole("button"));
    const timeline = screen.getByTestId("task-monitor-timeline");
    expect(timeline).toBeInTheDocument();
    // Sorted ascending by ts_utc — checked by reading the rendered <li> order.
    const events = within(timeline).getAllByRole("listitem");
    expect(events.map((li) => li.textContent)).toEqual([
      expect.stringContaining("step 1"),
      expect.stringContaining("step 2"),
      expect.stringContaining("step 3"),
    ]);
  });

  it("hides terminal runs when 'Clear completed' is toggled", () => {
    const runs = [
      sampleRun({ attempt_id: "11", task_id: "T-1", state: "proposing" }),
      sampleRun({ attempt_id: "22", task_id: "T-2", state: "recovered", is_terminal: true, terminal_status: "recovered", is_cancellable: false }),
      sampleRun({ attempt_id: "33", task_id: "T-3", state: "cancelled", is_terminal: true, terminal_status: "cancelled", is_cancellable: false }),
    ];
    render(
      <TaskMonitorDrawer open onClose={() => {}} staticData={sampleResponse(runs)} />,
    );
    expect(screen.getAllByTestId("task-monitor-row")).toHaveLength(3);
    fireEvent.click(screen.getByTestId("task-monitor-clear-completed"));
    expect(screen.getAllByTestId("task-monitor-row")).toHaveLength(1);
    fireEvent.click(screen.getByTestId("task-monitor-clear-completed"));
    expect(screen.getAllByTestId("task-monitor-row")).toHaveLength(3);
  });
});

describe("<TaskMonitorDrawer /> with mocked polling", () => {
  it("uses the injected fetcher and renders the response", async () => {
    const fetchRunsImpl = vi.fn().mockResolvedValue(
      sampleResponse([sampleRun({ attempt_id: "abcd", task_id: "T-poll", state: "reviewing" })]),
    );
    render(
      <TaskMonitorDrawer
        open
        onClose={() => {}}
        pollOptions={{ fetchRunsImpl, intervalMs: 60_000 }}
      />,
    );
    await waitFor(() => {
      expect(fetchRunsImpl).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByTestId("task-monitor-row")).toHaveAttribute("data-state", "reviewing");
    });
  });

  it("does not poll when closed", async () => {
    const fetchRunsImpl = vi.fn().mockResolvedValue(sampleResponse([]));
    render(
      <TaskMonitorDrawer
        open={false}
        onClose={() => {}}
        pollOptions={{ fetchRunsImpl, intervalMs: 60_000 }}
      />,
    );
    // Give React a microtask to settle; polling should be disabled when open=false.
    await new Promise((r) => setTimeout(r, 20));
    expect(fetchRunsImpl).not.toHaveBeenCalled();
  });
});

describe("useRecoveryRunsPoll backoff smoke", () => {
  /** Minimal harness so we can introspect backoffStep without mounting the drawer. */
  function HookHarness({ fetcher }: { fetcher: typeof import("../../src/api/recoveryRuns").fetchRecoveryRuns }) {
    const result = useRecoveryRunsPoll({ enabled: true, intervalMs: 60_000, fetchRunsImpl: fetcher });
    return <div data-testid="harness" data-backoff-step={result.backoffStep} data-error={result.error ?? ""} data-success={result.successCount} />;
  }

  it("increments backoff step on retryable error", async () => {
    const fetcher = vi.fn().mockRejectedValue(new RecoveryRunsFetchError(503, "boom"));
    render(<HookHarness fetcher={fetcher as never} />);
    await waitFor(() => {
      const harness = screen.getByTestId("harness");
      expect(harness.getAttribute("data-backoff-step")).toBe("1");
    });
  });

  it("surfaces fatal errors", async () => {
    const fetcher = vi.fn().mockRejectedValue(new RecoveryRunsFetchError(403, "forbidden"));
    render(<HookHarness fetcher={fetcher as never} />);
    await waitFor(() => {
      const harness = screen.getByTestId("harness");
      expect(harness.getAttribute("data-error")).toBe("forbidden");
    });
  });
});
