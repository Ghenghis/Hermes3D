/**
 * Unit test for the W17-NEW-A5 fix: the Print Queue tab now has a
 * "Submit Job" button that opens `SubmitJobDialog` which calls
 * `jobsClient.enqueue` (POST `/api/jobs`).
 *
 * Coverage:
 *   1. The new Submit button is visible in the Print Queue header.
 *   2. Clicking it mounts the dialog with file/printer pickers
 *      (job-type select acts as the file/template picker — the W17 brief
 *      explicitly allows substituting the type picker if a separate
 *      files endpoint is not yet wired by W17-FIX-BACKEND-GAPS).
 *   3. Submitting the form calls `jobsClient.enqueue` with the typed
 *      payload and refreshes the queue from the returned row.
 *   4. Backend error strings (e.g. policy 423 / 503) propagate to the
 *      operator instead of a generic toast.
 *
 * The test mocks the `adapters` module (for queue refresh) and the
 * `hermes3dClient` module (for the enqueue call) independently so the
 * collaborating W17-FIX-PRINTERS-API lane can keep editing
 * `adapters.live.ts` without affecting this lane's surface.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Job } from "../../src/types/job";
import type { Printer } from "../../src/types/printer";
import type { JobsEnqueueResult } from "../../src/api/hermes3dClient";

const adaptersMock = vi.hoisted(() => ({
  getJobs: vi.fn<[status?: string], Promise<Job[]>>(),
  getPrinters: vi.fn<[], Promise<Printer[]>>(),
}));

const jobsClientMock = vi.hoisted(() => ({
  enqueue: vi.fn<[Record<string, unknown>], Promise<JobsEnqueueResult>>(),
}));

vi.mock("../../src/api/adapters", () => ({
  adapters: adaptersMock,
}));

vi.mock("../../src/api/hermes3dClient", async () => {
  const actual = await vi.importActual<
    typeof import("../../src/api/hermes3dClient")
  >("../../src/api/hermes3dClient");
  return {
    ...actual,
    jobsClient: jobsClientMock,
  };
});

import { PrintQueueTab } from "../../src/tabs/PrintQueue";

function makeEnqueueResult(
  overrides: Partial<JobsEnqueueResult> = {},
): JobsEnqueueResult {
  return {
    id: "job-new",
    name: "regression-test",
    job_type: "print",
    status: "queued",
    printer_id: "flsun_t1_a",
    dry_run: 1,
    created_at: "2026-05-11T12:00:00Z",
    updated_at: "2026-05-11T12:00:00Z",
    ...overrides,
  };
}

function makePrinter(overrides: Partial<Printer> = {}): Printer {
  return {
    id: "flsun_t1_a",
    name: "FLSun T1 A",
    model: "FLSUN T1",
    ip: "192.168.0.10",
    status: "online",
    adapter: "moonraker",
    data_source: "live",
    temp_hot: null,
    temp_bed: null,
    progress: null,
    current_job: null,
    maintenance_flag: false,
    camera_url: null,
    source_refs: {},
    ...overrides,
  };
}

beforeEach(() => {
  Object.values(adaptersMock).forEach((fn) => {
    if (typeof fn === "function" && "mockReset" in fn) {
      (fn as { mockReset: () => void }).mockReset();
    }
  });
  jobsClientMock.enqueue.mockReset();
  adaptersMock.getJobs.mockResolvedValue([]);
  adaptersMock.getPrinters.mockResolvedValue([makePrinter()]);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("PrintQueueTab — Submit Job control (W17-NEW-A5 fix)", () => {
  it("renders the Submit Job button alongside Refresh and Pause", async () => {
    render(<PrintQueueTab />);
    await waitFor(() => {
      expect(screen.getByTestId("print-queue-submit")).toBeInTheDocument();
    });
    expect(screen.getByTestId("print-queue-refresh")).toBeInTheDocument();
    expect(screen.getByTestId("print-queue-pause")).toBeInTheDocument();
  });

  it("clicking Submit Job mounts the dialog with file (job-type) and printer pickers", async () => {
    render(<PrintQueueTab />);
    await waitFor(() => screen.getByTestId("print-queue-submit"));
    await waitFor(() => {
      expect(adaptersMock.getPrinters).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByTestId("print-queue-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("submit-job-dialog")).toBeInTheDocument();
    });
    expect(screen.getByTestId("submit-job-dialog-type")).toBeInTheDocument();
    expect(screen.getByTestId("submit-job-dialog-printer")).toBeInTheDocument();
    expect(screen.getByTestId("submit-job-dialog-name")).toBeInTheDocument();
    expect(screen.getByTestId("submit-job-dialog-dry-run")).toBeInTheDocument();
    expect(screen.getByTestId("submit-job-dialog-submit")).toBeInTheDocument();
  });

  it("submits the typed payload to jobsClient.enqueue and refreshes on success", async () => {
    jobsClientMock.enqueue.mockResolvedValue(makeEnqueueResult());

    render(<PrintQueueTab />);
    await waitFor(() => screen.getByTestId("print-queue-submit"));
    await waitFor(() => {
      expect(adaptersMock.getPrinters).toHaveBeenCalled();
    });
    fireEvent.click(screen.getByTestId("print-queue-submit"));
    await waitFor(() => screen.getByTestId("submit-job-dialog"));

    fireEvent.change(screen.getByTestId("submit-job-dialog-name"), {
      target: { value: "regression-test" },
    });
    fireEvent.change(screen.getByTestId("submit-job-dialog-printer"), {
      target: { value: "flsun_t1_a" },
    });
    fireEvent.click(screen.getByTestId("submit-job-dialog-submit"));

    await waitFor(() => {
      expect(jobsClientMock.enqueue).toHaveBeenCalledWith({
        name: "regression-test",
        job_type: "print",
        printer_id: "flsun_t1_a",
        dry_run: true,
      });
    });
    // Dialog closes after success and the queue refresh re-fires getJobs.
    await waitFor(() => {
      expect(screen.queryByTestId("submit-job-dialog")).not.toBeInTheDocument();
    });
    expect(adaptersMock.getJobs.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("surfaces the backend error string verbatim when the policy gate rejects the request", async () => {
    jobsClientMock.enqueue.mockRejectedValue(
      new Error("/api/jobs failed (423): PRINTER_WRITE_DENIED"),
    );

    render(<PrintQueueTab />);
    await waitFor(() => screen.getByTestId("print-queue-submit"));
    fireEvent.click(screen.getByTestId("print-queue-submit"));
    await waitFor(() => screen.getByTestId("submit-job-dialog"));
    fireEvent.click(screen.getByTestId("submit-job-dialog-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("submit-job-dialog-error")).toHaveTextContent(
        /PRINTER_WRITE_DENIED/,
      );
    });
    // Dialog stays open so the operator can adjust the request.
    expect(screen.getByTestId("submit-job-dialog")).toBeInTheDocument();
  });
});
