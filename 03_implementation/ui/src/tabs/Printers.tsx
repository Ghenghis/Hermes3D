import { useEffect, useMemo, useState } from "react";
import { adapters } from "../api/adapters";
import type { CameraValidateResult, PrinterProbeResult } from "../api/adapters";
import type { Printer, PrinterOnboardRequest } from "../types/printer";
import type { GcodeUploadResult, PrinterLock, TestResult } from "../types/printer-lock";
import { usePrinters } from "../hooks/usePrinters";

const PRINTER_ORDER = ["t1-1", "t1-2", "s1", "v400"];
const S1_POLICY_STATUS_OPTIONS: Printer["status"][] = ["online", "active", "offline", "maintenance", "error"];
const OPERATOR_IPS: Record<string, string> = {
  "t1-1": "192.168.0.10",
  "t1-2": "192.168.0.11",
  s1: "192.168.0.12",
  v400: "192.168.0.34",
};

/** S1 camera-only IP — must never be added as a print target (matches backend CAMERA_ONLY_IPS). */
const CAMERA_ONLY_IPS = new Set(["192.168.0.12"]);

// ---------------------------------------------------------------------------
// Onboarding wizard types
// ---------------------------------------------------------------------------

type WizardStep = "ip" | "probe" | "camera" | "confirm" | "done";

interface WizardState {
  ip: string;
  printerType: "moonraker" | "octoprint" | "direct";
  probeResult: PrinterProbeResult | null;
  cameraUrl: string;
  cameraResult: CameraValidateResult | null;
  name: string;
  model: Printer["model"];
  writeEnabled: boolean;
  // Camera-only block
  isCameraOnly: boolean;
}

const WIZARD_DEFAULTS: WizardState = {
  ip: "",
  printerType: "moonraker",
  probeResult: null,
  cameraUrl: "",
  cameraResult: null,
  name: "",
  model: "Generic",
  writeEnabled: false,
  isCameraOnly: false,
};

// ---------------------------------------------------------------------------
// PrinterOnboardingWizard component
// ---------------------------------------------------------------------------

function PrinterOnboardingWizard({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [step, setStep] = useState<WizardStep>("ip");
  const [wizard, setWizard] = useState<WizardState>(WIZARD_DEFAULTS);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateWizard = (patch: Partial<WizardState>) => setWizard((prev) => ({ ...prev, ...patch }));

  // Step 1: Enter printer IP + type
  const handleProbeStep = async () => {
    setError(null);
    const ipTrimmed = wizard.ip.trim();
    if (!ipTrimmed) {
      setError("Enter the printer IP address.");
      return;
    }
    // S1 / camera-only safety block — frontend check before hitting backend.
    if (CAMERA_ONLY_IPS.has(ipTrimmed)) {
      updateWizard({ isCameraOnly: true });
      setStep("probe");
      return;
    }
    setBusy(true);
    setStep("probe");
    try {
      const result = await adapters.probePrinter(ipTrimmed);
      updateWizard({
        probeResult: result,
        cameraUrl: result.ok ? `http://${ipTrimmed}/webcam/?action=stream` : "",
        name: result.ok ? `Printer @ ${ipTrimmed}` : "",
        isCameraOnly: false,
      });
      await adapters.emitProofEvent("printers.wizard.probe", {
        ip: ipTrimmed,
        ok: result.ok,
        klippy_state: result.klippy_state,
        moonraker_version: result.moonraker_version ?? null,
      });
    } catch {
      setError("Probe failed — check the IP and try again.");
    } finally {
      setBusy(false);
    }
  };

  // Step 3: Validate camera URL
  const handleCameraStep = async () => {
    setError(null);
    const urlTrimmed = wizard.cameraUrl.trim();
    if (!urlTrimmed) {
      setStep("confirm");
      return;
    }
    setBusy(true);
    try {
      const result = await adapters.validateCameraUrl(urlTrimmed);
      updateWizard({ cameraResult: result });
      await adapters.emitProofEvent("printers.wizard.camera_validate", {
        camera_url: urlTrimmed,
        ok: result.ok,
        is_mjpeg: result.is_mjpeg ?? false,
      });
      setStep("confirm");
    } catch {
      setError("Camera validation failed.");
    } finally {
      setBusy(false);
    }
  };

  // Step 4: Confirm + save
  const handleConfirm = async () => {
    setError(null);
    setBusy(true);
    try {
      const moonraker_url =
        wizard.printerType === "moonraker"
          ? `http://${wizard.ip.trim()}:7125`
          : `http://${wizard.ip.trim()}`;
      const request: PrinterOnboardRequest = {
        id: undefined,
        name: wizard.name.trim() || `Printer @ ${wizard.ip.trim()}`,
        model: wizard.model,
        moonraker_url,
        camera_url: wizard.cameraUrl.trim() || undefined,
        actor: "hermes3d-wizard",
        write_enabled: wizard.writeEnabled,
      };
      const result = await adapters.onboardPrinter(request);
      await adapters.emitProofEvent("printers.wizard.onboarded", {
        ok: result.created,
        printer_id: result.printer?.id ?? null,
        name: request.name,
        moonraker_url,
        write_enabled: wizard.writeEnabled,
      });
      if (result.created) {
        setStep("done");
      } else {
        setError(result.reason ?? "Onboarding failed — check the printer is reachable and Klipper is ready.");
      }
    } catch {
      setError("Onboarding request failed — backend may be unreachable.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" data-testid="printer-wizard-overlay">
      <div className="relative w-full max-w-md rounded-lg border border-border bg-surface p-6 shadow-xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-3 top-3 rounded px-2 py-1 text-xs text-muted hover:text-fg"
          aria-label="Close wizard"
        >
          ✕
        </button>

        <h2 className="mb-4 text-base font-semibold text-fg">Add Printer — Onboarding Wizard</h2>

        {/* Step indicators */}
        <div className="mb-5 flex items-center gap-2 text-xs text-muted">
          {(["ip", "probe", "camera", "confirm", "done"] as WizardStep[]).map((s, idx) => (
            <span
              key={s}
              className={`rounded px-2 py-0.5 ${step === s ? "bg-accent-blue text-bg font-semibold" : "bg-surface2"}`}
            >
              {idx + 1}
            </span>
          ))}
          <span className="ml-1 text-muted">{stepLabel(step)}</span>
        </div>

        {/* Step 1: IP + type */}
        {step === "ip" && (
          <div className="grid gap-4">
            <label className="grid gap-1 text-sm text-muted">
              Printer IP address
              <input
                type="text"
                value={wizard.ip}
                onChange={(e) => updateWizard({ ip: e.currentTarget.value })}
                placeholder="192.168.0.x"
                className="rounded border border-border bg-bg px-2 py-1.5 font-mono text-sm text-fg"
                data-testid="wizard-ip-input"
              />
            </label>
            <label className="grid gap-1 text-sm text-muted">
              Connection type
              <select
                value={wizard.printerType}
                onChange={(e) => updateWizard({ printerType: e.currentTarget.value as WizardState["printerType"] })}
                className="rounded border border-border bg-bg px-2 py-1.5 text-sm text-fg"
              >
                <option value="moonraker">Moonraker / Klipper</option>
                <option value="octoprint">OctoPrint</option>
                <option value="direct">Direct (raw)</option>
              </select>
            </label>
            {error && <p className="text-xs text-red-400" data-testid="wizard-error">{error}</p>}
            <button
              type="button"
              onClick={() => void handleProbeStep()}
              disabled={busy}
              className="rounded bg-accent-blue px-4 py-2 text-sm font-semibold text-bg disabled:opacity-50"
            >
              {busy ? "Probing…" : "Next — Probe Printer"}
            </button>
          </div>
        )}

        {/* Step 2: Probe result */}
        {step === "probe" && (
          <div className="grid gap-4">
            {wizard.isCameraOnly ? (
              <div
                className="rounded border border-red-700/60 bg-red-950/30 p-4 text-sm text-red-200"
                data-testid="wizard-camera-only-block"
              >
                <strong>Camera only — cannot add as print target.</strong>
                <p className="mt-1 text-xs text-red-300">
                  IP {wizard.ip} is reserved for camera/read-only access (FLSUN S1 policy). It
                  cannot be onboarded as a printable printer.
                </p>
              </div>
            ) : busy ? (
              <p className="text-sm text-muted">Probing {wizard.ip}…</p>
            ) : wizard.probeResult ? (
              <div className="grid gap-2 text-sm">
                <div className={`rounded px-3 py-2 text-xs font-semibold ${wizard.probeResult.ok ? "bg-green-900/40 text-green-300" : "bg-red-900/40 text-red-300"}`}>
                  {wizard.probeResult.ok ? "Moonraker reachable" : "Probe failed"}
                </div>
                {wizard.probeResult.ok && (
                  <>
                    <div className="grid gap-1 text-xs text-muted">
                      <div>Klippy: <span className="text-fg">{wizard.probeResult.klippy_state}</span></div>
                      {wizard.probeResult.moonraker_version && (
                        <div>Moonraker: <span className="font-mono text-fg">{wizard.probeResult.moonraker_version}</span></div>
                      )}
                      {wizard.probeResult.bed_kind && (
                        <div>
                          Bed:{" "}
                          <span className="text-fg">
                            {wizard.probeResult.bed_kind === "circular"
                              ? `circular Ø${wizard.probeResult.bed_diameter_mm ?? "?"}mm`
                              : `${wizard.probeResult.bed_x_mm ?? "?"}×${wizard.probeResult.bed_y_mm ?? "?"}mm`}
                            {wizard.probeResult.z_height_mm != null ? `, H ${wizard.probeResult.z_height_mm}mm` : ""}
                          </span>
                        </div>
                      )}
                    </div>
                    <label className="grid gap-1 text-xs text-muted">
                      Printer name
                      <input
                        type="text"
                        value={wizard.name}
                        onChange={(e) => updateWizard({ name: e.currentTarget.value })}
                        className="rounded border border-border bg-bg px-2 py-1 text-sm text-fg"
                      />
                    </label>
                    <label className="grid gap-1 text-xs text-muted">
                      Model
                      <select
                        value={wizard.model}
                        onChange={(e) => updateWizard({ model: e.currentTarget.value as Printer["model"] })}
                        className="rounded border border-border bg-bg px-2 py-1 text-sm text-fg"
                      >
                        <option value="Generic">Generic</option>
                        <option value="FLSUN T1">FLSUN T1</option>
                        <option value="FLSUN V400">FLSUN V400</option>
                      </select>
                    </label>
                  </>
                )}
                {wizard.probeResult.reason && (
                  <p className="text-xs text-red-400">{wizard.probeResult.reason}</p>
                )}
              </div>
            ) : (
              <p className="text-xs text-red-400">{error ?? "Probe failed."}</p>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => { setStep("ip"); setError(null); }}
                className="rounded border border-border px-3 py-1.5 text-sm text-fg"
              >
                Back
              </button>
              {!wizard.isCameraOnly && wizard.probeResult?.ok && (
                <button
                  type="button"
                  onClick={() => setStep("camera")}
                  className="rounded bg-accent-blue px-4 py-1.5 text-sm font-semibold text-bg"
                >
                  Next — Camera URL
                </button>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Camera URL */}
        {step === "camera" && (
          <div className="grid gap-4">
            <p className="text-sm text-muted">Set a camera URL (MJPEG stream). Leave blank to skip.</p>
            <label className="grid gap-1 text-sm text-muted">
              Camera URL
              <input
                type="text"
                value={wizard.cameraUrl}
                onChange={(e) => updateWizard({ cameraUrl: e.currentTarget.value })}
                placeholder={`http://${wizard.ip}/webcam/?action=stream`}
                className="rounded border border-border bg-bg px-2 py-1.5 font-mono text-sm text-fg"
                data-testid="wizard-camera-url-input"
              />
            </label>
            {wizard.cameraResult && (
              <div className={`rounded px-3 py-2 text-xs ${wizard.cameraResult.ok ? "bg-green-900/40 text-green-300" : "bg-amber-900/40 text-amber-300"}`}>
                {wizard.cameraResult.ok
                  ? `Camera OK${wizard.cameraResult.is_mjpeg ? " (MJPEG stream detected)" : ""}`
                  : wizard.cameraResult.reason ?? "Camera did not return MJPEG stream."}
              </div>
            )}
            {error && <p className="text-xs text-red-400">{error}</p>}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => { setStep("probe"); setError(null); }}
                className="rounded border border-border px-3 py-1.5 text-sm text-fg"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => void handleCameraStep()}
                disabled={busy}
                className="rounded border border-border px-3 py-1.5 text-sm text-fg disabled:opacity-50"
              >
                {busy ? "Validating…" : "Validate Camera"}
              </button>
              <button
                type="button"
                onClick={() => setStep("confirm")}
                className="rounded bg-accent-blue px-4 py-1.5 text-sm font-semibold text-bg"
              >
                Next — Confirm
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Confirm + save */}
        {step === "confirm" && (
          <div className="grid gap-4">
            <div className="rounded border border-border bg-bg/60 p-3 text-xs text-muted grid gap-1">
              <div>IP: <span className="font-mono text-fg">{wizard.ip}</span></div>
              <div>Name: <span className="text-fg">{wizard.name || `Printer @ ${wizard.ip}`}</span></div>
              <div>Model: <span className="text-fg">{wizard.model}</span></div>
              <div>Type: <span className="text-fg">{wizard.printerType}</span></div>
              <div>Moonraker URL: <span className="font-mono text-fg">
                {wizard.printerType === "moonraker" ? `http://${wizard.ip}:7125` : `http://${wizard.ip}`}
              </span></div>
              <div>Camera URL: <span className="font-mono text-fg">{wizard.cameraUrl || "none"}</span></div>
              <div>Write enabled: <span className="text-fg">{wizard.writeEnabled ? "yes" : "no (read-only)"}</span></div>
            </div>
            <label className="flex items-center gap-2 text-sm text-muted cursor-pointer">
              <input
                type="checkbox"
                checked={wizard.writeEnabled}
                onChange={(e) => updateWizard({ writeEnabled: e.currentTarget.checked })}
                className="rounded"
              />
              Enable write (upload / print start) after idle + bounds gate
            </label>
            {error && <p className="text-xs text-red-400" data-testid="wizard-error">{error}</p>}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => { setStep("camera"); setError(null); }}
                className="rounded border border-border px-3 py-1.5 text-sm text-fg"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => void handleConfirm()}
                disabled={busy}
                className="rounded bg-green-500 px-4 py-1.5 text-sm font-semibold text-bg disabled:opacity-50"
              >
                {busy ? "Saving…" : "Confirm + Save Profile"}
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Done */}
        {step === "done" && (
          <div className="grid gap-4">
            <div className="rounded border border-green-700/60 bg-green-950/30 p-4 text-sm text-green-200">
              Printer onboarded successfully.
            </div>
            <button
              type="button"
              onClick={() => { onSuccess(); onClose(); }}
              className="rounded bg-accent-blue px-4 py-2 text-sm font-semibold text-bg"
            >
              Close and Refresh
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function stepLabel(step: WizardStep): string {
  switch (step) {
    case "ip": return "Enter IP";
    case "probe": return "Probe";
    case "camera": return "Camera URL";
    case "confirm": return "Confirm";
    case "done": return "Done";
  }
}

// ---------------------------------------------------------------------------
// PrintersTab
// ---------------------------------------------------------------------------

export function PrintersTab() {
  // W17-FIX-PRINTERS-API: switched from `adapters.getPrinters()` (which
  // swallowed all errors and returned `[]`) to `usePrinters`, which exposes
  // the error so the operator can see why the list is empty. The local
  // `printers` state is now derived from the hook's `data` after applying
  // the operator-canonical normalization (S1 lock + IP overrides). Saving
  // a printer status is still optimistic via `setPrinters`.
  const printersQuery = usePrinters();
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [locks, setLocks] = useState<Record<string, PrinterLock>>({});
  const [testResults, setTestResults] = useState<Record<string, TestResult | null>>({});
  const [gcodePaths, setGcodePaths] = useState<Record<string, string>>({});
  const [jobIds, setJobIds] = useState<Record<string, string>>({});
  const [uploadResults, setUploadResults] = useState<Record<string, GcodeUploadResult | null>>({});
  const [uploadBusy, setUploadBusy] = useState<Record<string, boolean>>({});
  const [statusMessages, setStatusMessages] = useState<Record<string, string | null>>({});
  const [showWizard, setShowWizard] = useState(false);

  const orderedPrinters = useMemo(
    () => {
      const fixed = PRINTER_ORDER.map((id) => printers.find((printer) => canonicalPrinterId(printer) === id)).filter(Boolean) as Printer[];
      const fixedIds = new Set(fixed.map((printer) => printer.id));
      const extra = printers.filter((printer) => !fixedIds.has(printer.id) && !PRINTER_ORDER.includes(canonicalPrinterId(printer)));
      return [...fixed, ...extra];
    },
    [printers],
  );

  // Sync the locally-mutable printer state with the hook's latest snapshot
  // after applying operator normalization. We keep a local `printers` state
  // so `updateStatus` can optimistically patch a row before the next poll.
  useEffect(() => {
    if (!printersQuery.data) return;
    const normalized = printersQuery.data.map(normalizeOperatorPrinter);
    setPrinters(normalized);
    // Side-effects that previously lived in refresh(): fetch S1 lock state
    // and emit refresh proof events. Run as fire-and-forget; failures here
    // do NOT clear the printer list.
    void Promise.all(
      normalized.map(async (printer) => {
        const printerId = canonicalPrinterId(printer);
        if (printerId === "s1") {
          try {
            const lock = await adapters.getPrinterLockState("s1");
            setLocks((current) => ({ ...current, [printerId]: lock }));
            await adapters.emitProofEvent("printers.lock.displayed", {
              printer_id: "s1",
              lock_reason: lock.reason,
            });
          } catch {
            // Lock state is supplementary; keep the printer card visible.
          }
        } else {
          await adapters.emitProofEvent("printers.status.refreshed", { printer_id: printerId }).catch(() => undefined);
        }
      }),
    );
  }, [printersQuery.data]);

  const refresh = async () => {
    await printersQuery.refetch();
  };

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
      {showWizard && (
        <PrinterOnboardingWizard
          onClose={() => setShowWizard(false)}
          onSuccess={() => { void refresh(); }}
        />
      )}
      <header className="flex items-center justify-between rounded border border-border bg-surface p-3">
        <h2 className="text-base font-semibold text-fg">Moonraker Fleet Inventory</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowWizard(true)}
            className="rounded bg-accent-blue px-3 py-1 text-sm font-semibold text-bg"
            data-testid="add-printer-btn"
          >
            + Add Printer
          </button>
          <button type="button" onClick={() => void refresh()} className="rounded border border-border px-3 py-1 text-sm text-fg">Refresh All</button>
        </div>
      </header>
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-2 lg:auto-rows-fr">
        {/* W17-FIX-PRINTERS-API: distinguish loading / error / empty so the
            operator can see what's actually wrong instead of a generic
            "no inventory" message. */}
        {orderedPrinters.length === 0 && printersQuery.isLoading && (
          <section
            data-testid="printers-loading"
            className="flex h-full items-center justify-center rounded border border-border bg-surface p-4 text-sm text-muted lg:col-span-2"
          >
            Loading printer inventory from the live printer API.
          </section>
        )}
        {orderedPrinters.length === 0 && !printersQuery.isLoading && printersQuery.error && (
          <section
            data-testid="printers-error"
            className="flex h-full items-center justify-center rounded border border-red-700/60 bg-red-950/30 p-4 text-sm text-red-200 lg:col-span-2"
          >
            Printer API error: {printersQuery.error.message}
          </section>
        )}
        {orderedPrinters.length === 0 && !printersQuery.isLoading && !printersQuery.error && (
          <section
            data-testid="printers-empty"
            className="flex h-full items-center justify-center rounded border border-border bg-surface p-4 text-sm text-muted lg:col-span-2"
          >
            No printers configured. Use Add Printer to onboard a Moonraker/Klipper target.
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
          const safety = printerSafetyState(printer);
          return (
            <section key={printer.id} className="flex min-h-0 flex-col rounded border border-border bg-surface p-4" data-testid={`printer-card-${printerId}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-base font-semibold text-fg">{printer.name}</h3>
                  <p className="font-mono text-xs text-muted">{printer.ip ?? OPERATOR_IPS[printerId] ?? "no ip"}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className={`rounded px-2 py-1 text-xs font-semibold ${locked ? "bg-red-900/50 text-red-300" : result?.ok ? "bg-green-900/40 text-green-300" : "bg-surface2 text-muted"}`}>
                    {locked ? `${printer.status.toUpperCase()} / LOCKED` : result ? (result.ok ? "MOONRAKER READY" : "MOONRAKER FAIL") : "CONFIGURED"}
                  </span>
                  {/* W6-9 safety-state badge — distinct from connection status; always shown so operators see write/lock posture. */}
                  <span
                    data-testid={`printer-safety-state-${printerId}`}
                    data-safety-state={safety.kind}
                    aria-label={`Safety state: ${safety.label}`}
                    title={safety.title}
                    className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${safety.className}`}
                  >
                    {safety.label}
                  </span>
                </div>
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

/**
 * Distill backend printer state into a single safety badge.
 *
 * Order of precedence (matches backend gating):
 *   1. S1 / maintenance flag      -> SAFETY LOCKED (red)
 *   2. Onboarded read-only        -> READ-ONLY (amber)
 *   3. Onboarded write-enabled    -> WRITE ENABLED (green)
 *   4. Anything else              -> POLICY UNKNOWN (muted)
 *
 * The badge is rendered alongside the connection-status badge so operators
 * see lock posture even when the printer is offline (W6-9 requirement).
 */
type PrinterSafetyState = {
  kind: "locked" | "read_only" | "write_enabled" | "policy_unknown";
  label: string;
  title: string;
  className: string;
};

function printerSafetyState(printer: Printer): PrinterSafetyState {
  if (isS1(printer) || printer.maintenance_flag) {
    return {
      kind: "locked",
      label: "Safety locked",
      title: "Maintenance / camera-only safety lock enforced by backend.",
      className: "bg-red-900/60 text-red-200 border border-red-700/60",
    };
  }
  const policy = printer.safety_policy;
  if (printer.write_enabled === true || policy === "write_enabled") {
    return {
      kind: "write_enabled",
      label: "Write enabled",
      title: "Backend allows guarded upload/start after idle + bounds + approval gates.",
      className: "bg-green-900/40 text-green-300 border border-green-700/60",
    };
  }
  if (policy === "locked") {
    return {
      kind: "locked",
      label: "Safety locked",
      title: "Backend lock policy: control disabled.",
      className: "bg-red-900/60 text-red-200 border border-red-700/60",
    };
  }
  if (policy === "read_only" || printer.onboarded === true || printer.write_enabled === false) {
    return {
      kind: "read_only",
      label: "Read-only",
      title: "Onboarded read-only — writes blocked until policy approves them.",
      className: "bg-amber-900/40 text-amber-200 border border-amber-700/60",
    };
  }
  return {
    kind: "policy_unknown",
    label: "Policy unknown",
    title: "No safety_policy returned by backend; treating as read-only by default.",
    className: "bg-surface2 text-muted border border-border",
  };
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
