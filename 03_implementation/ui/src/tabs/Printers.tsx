import { useEffect, useMemo, useState } from "react";
import { adapters } from "../api/adapters";
import type { Printer } from "../types/printer";
import type { GcodeUploadResult, PrinterLock, TestResult } from "../types/printer-lock";

const PRINTER_ORDER = ["t1-1", "t1-2", "s1", "v400"];
const S1_POLICY_STATUS_OPTIONS: Printer["status"][] = ["online", "active", "offline", "maintenance", "error"];
const OPERATOR_IPS: Record<string, string> = {
  "t1-1": "192.168.0.10",
  "t1-2": "192.168.0.11",
  s1: "192.168.0.12",
  v400: "192.168.0.34",
};

export function PrintersTab() {
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [locks, setLocks] = useState<Record<string, PrinterLock>>({});
  const [testResults, setTestResults] = useState<Record<string, TestResult | null>>({});
  const [gcodePaths, setGcodePaths] = useState<Record<string, string>>({});
  const [jobIds, setJobIds] = useState<Record<string, string>>({});
  const [uploadResults, setUploadResults] = useState<Record<string, GcodeUploadResult | null>>({});
  const [uploadBusy, setUploadBusy] = useState<Record<string, boolean>>({});
  const [statusMessages, setStatusMessages] = useState<Record<string, string | null>>({});
  const orderedPrinters = useMemo(
    () => {
      const fixed = PRINTER_ORDER.map((id) => printers.find((printer) => canonicalPrinterId(printer) === id)).filter(Boolean) as Printer[];
      const fixedIds = new Set(fixed.map((printer) => printer.id));
      const extra = printers.filter((printer) => !fixedIds.has(printer.id) && !PRINTER_ORDER.includes(canonicalPrinterId(printer)));
      return [...fixed, ...extra];
    },
    [printers],
  );

  const refresh = async () => {
    const next = (await adapters.getPrinters()).map(normalizeOperatorPrinter);
    setPrinters(next);
    await Promise.all(next.map(async (printer) => {
      const printerId = canonicalPrinterId(printer);
      if (printerId === "s1") {
        const lock = await adapters.getPrinterLockState("s1");
        setLocks((current) => ({ ...current, [printerId]: lock }));
        await adapters.emitProofEvent("printers.lock.displayed", { printer_id: "s1", lock_reason: lock.reason });
      } else {
        await adapters.emitProofEvent("printers.status.refreshed", { printer_id: printerId });
      }
    }));
  };

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const runTest = async (printer: Printer) => {
    if (isS1(printer)) {
      return;
    }
    const result = await adapters.testPrinter(printer.id);
    setTestResults((current) => ({ ...current, [printer.id]: result }));
    await adapters.emitProofEvent("printers.test.run", { printer_id: printer.id, ok: result.ok });
  };

  const runGcodeUpload = async (printer: Printer, start: boolean) => {
    if (isS1(printer)) {
      return;
    }
    const path = (gcodePaths[printer.id] ?? "").trim();
    if (path === "") {
      setUploadResults((current) => ({
        ...current,
        [printer.id]: {
          printer_id: printer.id,
          accepted: false,
          uploaded: false,
          started: false,
          status: "missing_path",
          reason: "Enter a local .gcode path that the Hermes3D backend can read.",
        },
      }));
      return;
    }
    const jobId = (jobIds[printer.id] ?? "").trim();
    if (start && jobId === "") {
      setUploadResults((current) => ({
        ...current,
        [printer.id]: {
          printer_id: printer.id,
          accepted: false,
          uploaded: false,
          started: false,
          status: "missing_job_id",
          reason: "Upload + Start requires an approved job ID so the backend can verify PRINT_APPROVAL and truth-gate records.",
        },
      }));
      return;
    }
    setUploadBusy((current) => ({ ...current, [printer.id]: true }));
    const result = await adapters.uploadGcode(printer.id, path, start, "hermes3d", "local-operator", start ? jobId : undefined);
    setUploadResults((current) => ({ ...current, [printer.id]: result }));
    setUploadBusy((current) => ({ ...current, [printer.id]: false }));
    await adapters.emitProofEvent("printers.gcode_upload.requested", {
      printer_id: printer.id,
      start,
      accepted: result.accepted,
      uploaded: result.uploaded,
      started: result.started,
      item_path: result.item_path ?? null,
      bounds_passed: result.bounds_passed ?? null,
    });
  };

  const updateStatus = async (printer: Printer, status: Printer["status"]) => {
    try {
      await adapters.updatePrinterStatus(printer.id, status, "local-operator");
      setPrinters((current) => current.map((item) => item.id === printer.id ? { ...item, status } : item));
      setStatusMessages((current) => ({ ...current, [printer.id]: `Status saved: ${status}` }));
      await adapters.emitProofEvent("printers.status.changed", {
        printer_id: printer.id,
        status,
        locked: isS1(printer),
        accepted: true,
      });
    } catch (error) {
      setStatusMessages((current) => ({ ...current, [printer.id]: `Blocked: ${errorMessage(error)}` }));
    }
  };

  return (
    <div data-testid="printers-root" className="flex min-h-[calc(100vh-6.5rem)] flex-col gap-3">
      <header className="flex items-center justify-between rounded border border-border bg-surface p-3">
        <h2 className="text-base font-semibold text-fg">Moonraker Fleet Inventory</h2>
        <button type="button" onClick={() => void refresh()} className="rounded border border-border px-3 py-1 text-sm text-fg">Refresh All</button>
      </header>
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-2 lg:auto-rows-fr">
        {orderedPrinters.length === 0 && (
          <section className="flex h-full items-center justify-center rounded border border-border bg-surface p-4 text-sm text-muted lg:col-span-2">
            No printer inventory returned from the live printer API.
          </section>
        )}
        {orderedPrinters.map((printer) => {
          const printerId = canonicalPrinterId(printer);
          const locked = isS1(printer);
          const result = testResults[printer.id];
          const uploadResult = uploadResults[printer.id];
          const uploadPath = gcodePaths[printer.id] ?? "";
          const jobId = jobIds[printer.id] ?? "";
          const uploadDisabledReason = locked
            ? "S1 is safety locked; upload, print start, test, and movement are blocked by backend policy."
            : printer.write_enabled === false
              ? "This onboarded printer is read-only until guarded writes are enabled after idle/bounds/profile gates."
            : printer.status === "offline" || printer.status === "maintenance"
              ? "Printer must be online before uploading G-code."
              : uploadPath.trim() === ""
                ? "Enter a local .gcode path that the backend can read."
                : null;
          const startDisabledReason = uploadDisabledReason ?? (
            jobId.trim() === ""
              ? "Upload + Start requires an approved job ID for PRINT_APPROVAL and truth-gate verification."
              : null
          );
          const testDisabledReason = locked
            ? "S1 is safety locked; test, movement, upload, and print start are blocked by backend policy."
            : printer.status === "offline" || printer.status === "maintenance"
              ? "Printer must be online before running a Moonraker test."
              : null;
          return (
            <section key={printer.id} className="flex min-h-0 flex-col rounded border border-border bg-surface p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-fg">{printer.name}</h3>
                  <p className="font-mono text-xs text-muted">{printer.ip ?? OPERATOR_IPS[printerId] ?? "no ip"}</p>
                </div>
                <span className={`rounded px-2 py-1 text-xs font-semibold ${locked ? "bg-red-900/50 text-red-300" : result?.ok ? "bg-green-900/40 text-green-300" : "bg-surface2 text-muted"}`}>
                  {locked ? `${printer.status.toUpperCase()} / LOCKED` : result ? (result.ok ? "MOONRAKER READY" : "MOONRAKER FAIL") : "CONFIGURED"}
                </span>
              </div>
              <div className="mt-3 grid gap-1 text-sm text-muted">
                <label className="flex items-center gap-2">
                  <span>{locked ? "S1 policy status:" : "Live status:"}</span>
                  {locked ? (
                    <select
                      className="rounded border border-border bg-bg px-2 py-1 text-fg"
                      value={printer.status}
                      onChange={(event) => {
                        const value = event.currentTarget.value as Printer["status"];
                        void updateStatus(printer, value);
                      }}
                    >
                      {S1_POLICY_STATUS_OPTIONS.map((status) => <option key={status}>{status}</option>)}
                    </select>
                  ) : (
                    <span className="rounded border border-border bg-bg px-2 py-1 font-mono text-fg">
                      {printer.status}
                    </span>
                  )}
                </label>
                <div>Status source: <span className="text-fg">{locked ? "S1 safety policy" : `${printer.data_source} telemetry`}</span></div>
                {printer.onboarded && (
                  <div>Onboarding: <span className="text-fg">{printer.safety_policy ?? "read_only"}</span></div>
                )}
                <div>Health probe: <span className="text-fg">{result ? `${result.ok ? "ready" : "failed"} (${result.latency_ms ?? 0} ms)` : "not run"}</span></div>
                <div>Moonraker: <span className="font-mono text-fg">http://{printer.ip}</span></div>
                {printer.source_refs.official_wiki_url && (
                  <div>
                    Source:{" "}
                    <a href={printer.source_refs.official_wiki_url} target="_blank" rel="noreferrer" className="text-accent-blue hover:underline">
                      official FLSUN wiki
                    </a>
                    {printer.source_refs.profiles_detected && (
                      <span className="ml-2 text-xs text-muted">
                        profiles {Object.values(printer.source_refs.profiles_detected).filter(Boolean).length}/{Object.keys(printer.source_refs.profiles_detected).length}
                      </span>
                    )}
                  </div>
                )}
                {statusMessages[printer.id] && <div className="rounded border border-border bg-bg/40 px-2 py-1 text-xs text-muted">{statusMessages[printer.id]}</div>}
              </div>
              {locked && (
                <div className="mt-4 rounded border border-amber-700/60 bg-amber-950/30 p-3 text-sm text-amber-200">
                  Maintenance lock: do not test or move. Movement may damage the hotend.
                  <div className="mt-1 text-xs text-amber-300">{locks[printerId]?.reason ?? "Safety lock state is enforced by backend for S1."}</div>
                </div>
              )}
              <div className="mt-4 flex items-center gap-2">
                <button
                  type="button"
                  disabled={testDisabledReason != null}
                  title={testDisabledReason ?? "Run live Moonraker/Klipper test"}
                  onClick={() => void runTest(printer)}
                  className="rounded bg-accent-blue px-3 py-1 text-sm font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Test
                </button>
                {result && <span className={`rounded px-2 py-1 text-xs ${result.ok ? "bg-green-900/50 text-green-300" : "bg-red-900/50 text-red-300"}`}>{result.ok ? "OK" : "FAIL"} - {result.message}</span>}
              </div>
              <div className="mt-4 rounded border border-border bg-bg/60 p-3">
                <label className="grid gap-1 text-xs text-muted">
                  <span>Local G-code path for backend upload</span>
                  <input
                    type="text"
                    value={uploadPath}
                    onChange={(event) => {
                      const { value } = event.currentTarget;
                      setGcodePaths((current) => ({ ...current, [printer.id]: value }));
                    }}
                    placeholder="G:\\Github\\...\\part.gcode"
                    disabled={locked}
                    className="rounded border border-border bg-bg px-2 py-1 font-mono text-xs text-fg disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </label>
                <label className="mt-2 grid gap-1 text-xs text-muted">
                  <span>Approved job ID for Upload + Start</span>
                  <input
                    aria-label={`${printer.name} approved job ID`}
                    type="text"
                    value={jobId}
                    onChange={(event) => {
                      const { value } = event.currentTarget;
                      setJobIds((current) => ({ ...current, [printer.id]: value }));
                    }}
                    disabled={locked}
                    className="rounded border border-border bg-bg px-2 py-1 font-mono text-xs text-fg disabled:cursor-not-allowed disabled:opacity-50"
                  />
                </label>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={uploadDisabledReason != null || uploadBusy[printer.id] === true}
                    title={uploadDisabledReason ?? "Run bounds gate and upload to Moonraker without starting"}
                    onClick={() => void runGcodeUpload(printer, false)}
                    className="rounded border border-border px-3 py-1 text-sm font-semibold text-fg disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Upload G-code
                  </button>
                  <button
                    type="button"
                    disabled={startDisabledReason != null || uploadBusy[printer.id] === true}
                    title={startDisabledReason ?? "Run bounds gate, approval/truth gates, upload, and start only if Klipper is idle"}
                    onClick={() => void runGcodeUpload(printer, true)}
                    className="rounded bg-green-500 px-3 py-1 text-sm font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Upload + Start
                  </button>
                </div>
                {uploadResult && (
                  <div className={`mt-2 rounded px-2 py-1 text-xs ${uploadResult.accepted ? "bg-green-900/50 text-green-300" : "bg-red-900/50 text-red-300"}`}>
                    {uploadResult.accepted
                      ? `${uploadResult.started ? "Started" : "Uploaded"} ${uploadResult.item_path ?? uploadResult.gcode_path ?? "G-code"}${uploadResult.bounds_passed ? " after bounds gate" : ""}`
                      : `${uploadResult.status ?? "blocked"}: ${uploadResult.reason ?? "Backend rejected the request."}`}
                  </div>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Backend rejected the printer status update.";
}

function canonicalPrinterId(printer: Printer): string {
  if (printer.id === "flsun_t1_a" || printer.id === "t1-1" || printer.ip === OPERATOR_IPS["t1-1"]) {
    return "t1-1";
  }
  if (printer.id === "flsun_t1_b" || printer.id === "t1-2" || printer.ip === OPERATOR_IPS["t1-2"]) {
    return "t1-2";
  }
  if (printer.id === "flsun-s1" || printer.ip === OPERATOR_IPS.s1 || printer.model === "FLSUN S1") {
    return "s1";
  }
  if (printer.id === "flsun_v400" || printer.id === "v400" || printer.ip === OPERATOR_IPS.v400) {
    return "v400";
  }
  return printer.id;
}

function isS1(printer: Printer): boolean {
  return canonicalPrinterId(printer) === "s1";
}

function normalizeOperatorPrinter(printer: Printer): Printer {
  const printerId = canonicalPrinterId(printer);
  if (printerId === "s1") {
    return {
      ...printer,
      id: "s1",
      name: "FLSUN S1",
      ip: OPERATOR_IPS.s1,
      model: "FLSUN S1",
      maintenance_flag: true,
    };
  }
  return {
    ...printer,
    ip: OPERATOR_IPS[printerId] ?? printer.ip,
  };
}
