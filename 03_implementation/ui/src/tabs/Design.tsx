import { useEffect, useMemo, useRef, useState } from "react";
import { adapters } from "../api/adapters";
import type { Printer } from "../types/printer";
import type { ToolchainEvidence, ToolchainStage, ToolchainStatus } from "../types/toolchain";
import {
  gcodeDownloadUrl,
  getSlice,
  pollSliceUntilTerminal,
  startSlice,
  type SliceState,
} from "../api/slicer";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const DEFAULT_TOOLCHAIN: ToolchainStatus = {
  overall: "degraded",
  updated_at: new Date(0).toISOString(),
  stages: [],
};

// ---------------------------------------------------------------------------
// Types for real provider health + template data from backend
// ---------------------------------------------------------------------------

interface CadProvider {
  id: string;
  name: string;
  kind: string;
  status: "ready" | "detected" | "not_installed";
  detected: boolean;
  path: string | null;
  version: string | null;
  version_detail: string | null;
  capabilities: string[];
  docs_url: string;
  detail: string;
  probed_at: string;
}

interface CadTemplate {
  id: string;
  name: string;
  description?: string;
  executor_module?: string;
  executor_available?: boolean;
  executor_detail?: string;
  outputs?: string[];
  parameters?: string[];
  requires?: string[];
  missing_deps?: string[];
  deps_ok?: boolean;
  preview_available?: boolean;
  preview_note?: string;
}

export function DesignTab() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState("desk_organizer");
  const [widthMm, setWidthMm] = useState(180);
  const [depthMm, setDepthMm] = useState(100);
  const [heightMm, setHeightMm] = useState(55);
  const [trayCount, setTrayCount] = useState(3);
  const [penCount, setPenCount] = useState(4);
  const [phoneSlot, setPhoneSlot] = useState(true);
  const [cablePassthrough, setCablePassthrough] = useState(true);
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [targetPrinterId, setTargetPrinterId] = useState("");
  const [toolchain, setToolchain] = useState<ToolchainStatus>(DEFAULT_TOOLCHAIN);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);
  const [logsMessage, setLogsMessage] = useState<string | null>(null);
  const [cadProviders, setCadProviders] = useState<CadProvider[]>([]);
  const [cadTemplates, setCadTemplates] = useState<CadTemplate[]>([]);
  const [providersLoading, setProvidersLoading] = useState(true);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  // W18-A12 — STL artifacts produced by recent design-intake calls and the
  // current state of the slicer job spawned via "Slice this STL".
  const [producedStls, setProducedStls] = useState<ProducedStl[]>([]);
  const [sliceState, setSliceState] = useState<SliceState | null>(null);
  const [sliceMessage, setSliceMessage] = useState<string | null>(null);
  const [slicing, setSlicing] = useState(false);
  const sliceAbortRef = useRef<AbortController | null>(null);
  const unlockedPrinters = useMemo(
    () => printers.filter((printer) => !printer.maintenance_flag && printer.status !== "maintenance"),
    [printers],
  );
  const toolchainReady = toolchain.overall === "ready" && toolchain.execution_ready !== false;
  const toolchainReason = designBlockReason(toolchain);
  const canSubmit = title.trim().length > 0 && description.trim().length > 0 && targetPrinterId.length > 0 && toolchainReady;
  const localTools = toolchain.tools ?? [];
  const sourceTools = toolchain.sources ?? [];

  useEffect(() => {
    let mounted = true;
    void adapters.getPrinters().then((next) => {
      if (!mounted) {
        return;
      }
      setPrinters(next);
      setTargetPrinterId(next.find((printer) => !printer.maintenance_flag && printer.status !== "maintenance")?.id ?? "");
    });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    const load = () => {
      void adapters.getDesignToolchainStatus().then((next) => {
        if (mounted) {
          setToolchain(next);
        }
      });
    };
    load();
    const timer = window.setInterval(load, 15_000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  // Fetch real CAD provider health from backend
  useEffect(() => {
    let mounted = true;
    const load = () => {
      setProvidersLoading(true);
      fetch(`${LIVE_BASE_URL}/api/design/providers`, { cache: "no-store" })
        .then((r) => r.json())
        .then((data: unknown) => {
          if (mounted && Array.isArray(data)) {
            setCadProviders(data as CadProvider[]);
          }
        })
        .catch(() => { /* backend unreachable — providers stay empty */ })
        .finally(() => { if (mounted) setProvidersLoading(false); });
    };
    load();
    const timer = window.setInterval(load, 30_000);
    return () => { mounted = false; window.clearInterval(timer); };
  }, []);

  // Fetch real CAD template list from backend
  useEffect(() => {
    let mounted = true;
    setTemplatesLoading(true);
    fetch(`${LIVE_BASE_URL}/api/design/templates`, { cache: "no-store" })
      .then((r) => r.json())
      .then((data: unknown) => {
        if (mounted && Array.isArray(data)) {
          setCadTemplates(data as CadTemplate[]);
          // Keep the select pre-populated with the first available template
          const first = (data as CadTemplate[]).find((t) => t.executor_available !== false);
          if (first && mounted) setTemplate(first.id);
        }
      })
      .catch(() => { /* backend unreachable — templates stay empty */ })
      .finally(() => { if (mounted) setTemplatesLoading(false); });
    return () => { mounted = false; };
  }, []);

  const submit = async () => {
    if (!canSubmit) {
      setSubmitMessage(toolchainReady ? "Blocked: complete the design name, intent, and target printer first." : `Blocked: ${toolchainReason}`);
      return;
    }
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/design/intake`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: `${title.trim()}\n\n${description.trim()}`,
          constraints: {
            template,
            target_printer_id: targetPrinterId,
            width_mm: widthMm,
            depth_mm: depthMm,
            height_mm: heightMm,
            tray_count: trayCount,
            pen_count: penCount,
            phone_slot: phoneSlot,
            cable_passthrough: cablePassthrough,
          },
        }),
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      const accepted = actionAccepted(response.ok, payload);
      setSubmitMessage(accepted ? `Design intake accepted: ${designSummary(payload, response.statusText)}` : `Blocked: ${designSummary(payload, response.statusText)}`);
      if (accepted) {
        const stl = extractStlArtifact(payload);
        if (stl) {
          setProducedStls((prev) => [stl, ...prev.filter((s) => s.file_path !== stl.file_path)].slice(0, 5));
        }
      }
      await adapters.emitProofEvent("design.intake.submitted", { title, target_printer_id: targetPrinterId, accepted, response: payload });
    } catch {
      setSubmitMessage(`Design intake failed: backend API is unreachable at ${LIVE_BASE_URL}.`);
      await adapters.emitProofEvent("design.intake.submitted", { title, target_printer_id: targetPrinterId, accepted: false });
    }
  };

  const sliceStl = async (stl: ProducedStl) => {
    setSliceMessage(`Starting slice of ${stl.label}…`);
    setSliceState(null);
    setSlicing(true);
    sliceAbortRef.current?.abort("new-slice");
    const controller = new AbortController();
    sliceAbortRef.current = controller;
    try {
      const accepted = await startSlice(
        { stl_path: stl.file_path },
        { signal: controller.signal, timeoutMs: 30_000 },
      );
      setSliceMessage(`Slice job ${accepted.job_id.slice(0, 12)} accepted; polling…`);
      const terminal = await pollSliceUntilTerminal(accepted.job_id, {
        intervalMs: 2000,
        maxMs: 25 * 60_000,
        signal: controller.signal,
        onProgress: (s) => setSliceState(s),
      });
      setSliceState(terminal);
      if (terminal.status === "completed") {
        const layers = terminal.layer_count ?? "?";
        const motion = terminal.motion_lines ?? "?";
        setSliceMessage(`Slice complete — ${layers} layers, ${motion} motion lines, sha256 ${(terminal.sha256 ?? "").slice(0, 12)}…`);
      } else {
        setSliceMessage(`Slice ${terminal.status}: ${terminal.error ?? "see backend logs"}`);
      }
      await adapters.emitProofEvent("design.slice.completed", {
        job_id: terminal.job_id,
        status: terminal.status,
        gcode_path: terminal.gcode_path,
        sha256: terminal.sha256,
        layer_count: terminal.layer_count,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setSliceMessage(`Slice failed: ${message}`);
      await adapters.emitProofEvent("design.slice.failed", { stl_path: stl.file_path, error: message });
    } finally {
      setSlicing(false);
    }
  };

  const refreshSlice = async () => {
    if (!sliceState?.job_id) return;
    const fresh = await getSlice(sliceState.job_id).catch(() => null);
    if (fresh) setSliceState(fresh);
  };

  const viewLogs = async (stageId: string) => {
    const logs = await adapters.getLogs();
    const recent = logs
      .filter((entry) => entry.message.toLowerCase().includes(stageId.toLowerCase()) || entry.source?.toLowerCase().includes("design"))
      .slice(0, 5);
    setLogsMessage(recent.length > 0
      ? recent.map((entry) => `${entry.ts_utc} ${entry.level}: ${entry.message}`).join("\n")
      : `No matching design logs returned by /api/logs for ${stageId}.`);
    await adapters.emitProofEvent("design.logs.viewed", { stage_id: stageId, rows: recent.length });
  };

  return (
    <div data-testid="design-root" className="grid min-h-[calc(100vh-6.5rem)] gap-3 lg:grid-cols-12">
      <section id="design.intake" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4 lg:col-span-5">
        <h2 className="text-base font-semibold text-fg">Design Intake</h2>
        <div className="mt-3 grid min-h-0 flex-1 gap-3">
          <select
            className="rounded border border-border bg-bg px-3 py-2 text-sm text-fg"
            aria-label="Design template"
            value={template}
            onChange={(event) => setTemplate(event.target.value)}
          >
            {templatesLoading && <option value="">Loading templates…</option>}
            {!templatesLoading && cadTemplates.length === 0 && (
              <option value="desk_organizer">Parametric Desk Organizer</option>
            )}
            {cadTemplates.map((item) => (
              <option key={item.id} value={item.id} disabled={item.executor_available === false}>
                {item.name}{item.executor_available === false ? " (unavailable)" : ""}
              </option>
            ))}
          </select>
          <input className="rounded border border-border bg-bg px-3 py-2 text-sm text-fg" required aria-label="Design name" value={title} onChange={(event) => setTitle(event.target.value)} />
          <textarea className="min-h-32 rounded border border-border bg-bg px-3 py-2 text-sm text-fg" required aria-label="Design intent, constraints, notes" value={description} onChange={(event) => setDescription(event.target.value)} />
          <div className="grid grid-cols-3 gap-2">
            <NumberField label="Width mm" value={widthMm} min={60} max={240} onChange={setWidthMm} />
            <NumberField label="Depth mm" value={depthMm} min={50} max={180} onChange={setDepthMm} />
            <NumberField label="Height mm" value={heightMm} min={25} max={120} onChange={setHeightMm} />
            <NumberField label="Trays" value={trayCount} min={1} max={8} onChange={setTrayCount} />
            <NumberField label="Pens" value={penCount} min={0} max={12} onChange={setPenCount} />
            <label className="flex min-h-[58px] items-center gap-2 rounded border border-border bg-bg px-3 py-2 text-xs text-muted">
              <input type="checkbox" checked={phoneSlot} onChange={(event) => setPhoneSlot(event.target.checked)} />
              Phone slot
            </label>
          </div>
          <label className="flex items-center gap-2 rounded border border-border bg-bg px-3 py-2 text-xs text-muted">
            <input type="checkbox" checked={cablePassthrough} onChange={(event) => setCablePassthrough(event.target.checked)} />
            Cable pass-through
          </label>
          <select className="rounded border border-border bg-bg px-3 py-2 text-sm text-fg" required value={targetPrinterId} onChange={(event) => setTargetPrinterId(event.target.value)}>
            {unlockedPrinters.map((printer) => (
              <option key={printer.id} value={printer.id}>{printer.name}</option>
            ))}
          </select>
          <button
            type="button"
            disabled={!canSubmit}
            title={canSubmit ? "Create a real parametric design artifact and proof." : toolchainReady ? "Complete the required design fields." : toolchainReason}
            onClick={submit}
            className="rounded bg-accent-blue px-3 py-2 text-sm font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-50"
          >
            Start Design
          </button>
          {!toolchainReady && <div className="rounded border border-amber-700/60 bg-amber-950/30 p-2 text-xs text-amber-200">{toolchainReason}</div>}
          {submitMessage && <div className="rounded border border-border bg-bg/40 p-2 text-xs text-muted">{submitMessage}</div>}
        </div>
      </section>

      <section id="design.toolchain" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4 lg:col-span-7">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-fg">DESIGN TOOLCHAIN</h2>
            <p className="text-xs text-muted">Source checkouts and local executables from live backend proof.</p>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => { window.location.hash = "#sources"; }} className="rounded border border-border px-2 py-1 text-xs text-fg">
              Open Source OS
            </button>
            <span className={["rounded px-2 py-1 text-xs uppercase", statusTone(toolchain.overall)].join(" ")}>{formatStatus(toolchain.overall)}</span>
          </div>
        </div>
        {toolchain.blockers && toolchain.blockers.length > 0 && (
          <div className="mt-3 rounded border border-amber-700/60 bg-amber-950/30 p-3 text-xs text-amber-100">
            <div className="font-semibold uppercase tracking-wide">Execution blocked</div>
            <ul className="mt-2 list-disc space-y-1 pl-4">
              {toolchain.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}
            </ul>
          </div>
        )}
        <div className="mt-4 grid min-h-0 flex-1 content-start gap-3 overflow-auto">
          <div className="grid gap-3 xl:grid-cols-2">
            {toolchain.stages.map((stage) => (
              <ToolchainStageCard key={stage.id} stage={stage} onViewLogs={() => void viewLogs(stage.id)} />
            ))}
          </div>

          <EvidenceSection
            title="Local Executables"
            detail="Detected from backend audit; paths stay server-side and are displayed as proof."
            items={localTools}
            empty="No local executable proof was returned."
          />

          <EvidenceSection
            title="Source Checkouts"
            detail="Installed source-backed modules available to Design and agent workflows."
            items={sourceTools}
            empty="No source checkout proof was returned."
          />

          <div className="rounded border border-border bg-bg/40 p-3 text-xs">
            <div className="font-semibold uppercase tracking-wide text-fg">Proof Sources</div>
            <div className="mt-2 grid gap-1 font-mono text-[11px] text-muted">
              {Object.entries(toolchain.proof_sources ?? {}).map(([key, value]) => (
                <div key={key} className="truncate"><span className="text-accent-cyan">{key}</span>: {value ?? "not recorded"}</div>
              ))}
              {Object.keys(toolchain.proof_sources ?? {}).length === 0 && <div>No proof source paths returned.</div>}
            </div>
          </div>
        </div>
        {logsMessage && <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap rounded border border-border bg-bg/60 p-2 text-xs text-muted">{logsMessage}</pre>}
      </section>

      {/* CAD Provider Health — real probes from backend, no fake stubs */}
      <section id="design.providers" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4 lg:col-span-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-fg">CAD Provider Health</h2>
            <p className="text-xs text-muted">Live probe results — shutil.which + importlib. No cached stubs.</p>
          </div>
          {providersLoading && <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">Probing…</span>}
          {!providersLoading && <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">{cadProviders.length} providers</span>}
        </div>
        <div className="mt-4 grid min-h-0 flex-1 content-start gap-2 overflow-auto">
          {cadProviders.length === 0 && !providersLoading && (
            <div className="rounded border border-border bg-bg/40 p-3 text-xs text-muted">
              Backend provider probe endpoint unreachable. Start the Hermes3D backend to see real provider status.
            </div>
          )}
          {cadProviders.map((provider) => (
            <ProviderCard key={provider.id} provider={provider} />
          ))}
        </div>
      </section>

      {/* CAD Template Gallery — from backend, with preview-not-available when no renderer */}
      <section id="design.templates" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4 lg:col-span-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-fg">Template Gallery</h2>
            <p className="text-xs text-muted">Real executor modules discovered from the backend at runtime.</p>
          </div>
          {templatesLoading && <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">Loading…</span>}
          {!templatesLoading && <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">{cadTemplates.length} templates</span>}
        </div>
        <div className="mt-4 grid min-h-0 flex-1 content-start gap-3 overflow-auto">
          {cadTemplates.length === 0 && !templatesLoading && (
            <div className="rounded border border-border bg-bg/40 p-3 text-xs text-muted">
              Backend template list endpoint unreachable. Start the Hermes3D backend to see available templates.
            </div>
          )}
          {cadTemplates.map((tmpl) => (
            <TemplateCard key={tmpl.id} tmpl={tmpl} selected={template === tmpl.id} onSelect={() => setTemplate(tmpl.id)} />
          ))}
        </div>
      </section>

      {/* W18-A12 — Slicer wire-up. Lists STLs produced by recent design intakes
          and exposes "Slice this STL" -> POST /api/slice -> poll -> show
          gcode_path + size + sha256 + layer_count + download link. The slicer
          NEVER dispatches G-code to a printer (operator freeze 2026-05-11). */}
      <section
        id="design.slicer"
        data-testid="design-slicer-root"
        className="flex min-h-0 flex-col rounded border border-border bg-surface p-4 lg:col-span-12"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-fg">Slicer</h2>
            <p className="text-xs text-muted">
              Run PrusaSlicer/OrcaSlicer CLI on a produced STL. The result is a real G-code file on disk; nothing is sent to a printer.
            </p>
          </div>
          <span
            data-testid="design-slicer-freeze-badge"
            className="rounded bg-surface2 px-2 py-1 text-[11px] uppercase tracking-wide text-muted"
            title="Operator freeze 2026-05-11 — slicer does not dispatch G-code"
          >
            no-printer-writes
          </span>
        </div>

        <div className="mt-4 grid min-h-0 flex-1 content-start gap-3 lg:grid-cols-2">
          {/* Left column: list of STLs available to slice. */}
          <div className="rounded border border-border bg-bg/40 p-3">
            <div className="text-sm font-semibold uppercase tracking-wide text-fg">
              Produced STLs
            </div>
            <p className="text-xs text-muted">
              STLs returned by recent design-intake calls in this session.
            </p>
            <div className="mt-3 grid gap-2" data-testid="design-slicer-stl-list">
              {producedStls.length === 0 && (
                <div className="rounded border border-border bg-bg/30 p-3 text-xs text-muted">
                  No STLs yet. Submit a Design Intake first and a "Slice this STL" button will appear here.
                </div>
              )}
              {producedStls.map((stl) => (
                <div
                  key={stl.file_path}
                  className="grid grid-cols-[1fr_auto] items-start gap-2 rounded border border-border bg-bg/50 p-3 text-xs"
                  data-testid="design-slicer-stl-row"
                >
                  <div className="min-w-0">
                    <div className="truncate font-semibold text-fg">{stl.label}</div>
                    <div className="mt-0.5 truncate font-mono text-[11px] text-muted">{stl.file_path}</div>
                    <div className="mt-0.5 text-[11px] text-muted">{stl.file_size?.toLocaleString() ?? "?"} bytes — sha256 {(stl.sha256 ?? "").slice(0, 16) || "?"}…</div>
                  </div>
                  <button
                    type="button"
                    data-testid={`design-slicer-slice-button-${stl.label}`}
                    aria-label={`Slice ${stl.label}`}
                    disabled={slicing}
                    onClick={() => void sliceStl(stl)}
                    className="shrink-0 rounded bg-accent-blue px-3 py-1.5 text-xs font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Slice this STL
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Right column: current slice-job state. */}
          <div
            className="rounded border border-border bg-bg/40 p-3"
            data-testid="design-slicer-state-panel"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-semibold uppercase tracking-wide text-fg">Slice Job</div>
              {slicing && (
                <span
                  data-testid="design-slicer-spinner"
                  className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-accent-blue border-t-transparent"
                />
              )}
              {!slicing && sliceState && (
                <button
                  type="button"
                  data-testid="design-slicer-refresh"
                  onClick={() => void refreshSlice()}
                  className="rounded border border-border px-2 py-1 text-[11px] text-fg"
                >
                  Refresh
                </button>
              )}
            </div>
            {!sliceState && !slicing && (
              <div className="mt-3 rounded border border-border bg-bg/30 p-3 text-xs text-muted">
                Click "Slice this STL" on the left to start a job.
              </div>
            )}
            {sliceState && (
              <div className="mt-3 grid gap-2 text-xs">
                <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                  <span className="text-muted">job_id</span>
                  <span className="truncate font-mono text-fg" data-testid="design-slicer-job-id">{sliceState.job_id}</span>
                  <span className="text-muted">status</span>
                  <span data-testid="design-slicer-status">
                    <span className={["rounded px-2 py-0.5 text-[11px] uppercase", statusTone(sliceState.status)].join(" ")}>{sliceState.status}</span>
                  </span>
                  {sliceState.gcode_path && (
                    <>
                      <span className="text-muted">gcode_path</span>
                      <span className="truncate font-mono text-fg" data-testid="design-slicer-gcode-path" title={sliceState.gcode_path}>{sliceState.gcode_path}</span>
                    </>
                  )}
                  {typeof sliceState.size_bytes === "number" && (
                    <>
                      <span className="text-muted">size_bytes</span>
                      <span className="font-mono text-fg" data-testid="design-slicer-size">{sliceState.size_bytes.toLocaleString()}</span>
                    </>
                  )}
                  {sliceState.sha256 && (
                    <>
                      <span className="text-muted">sha256</span>
                      <span className="truncate font-mono text-fg" data-testid="design-slicer-sha256">{sliceState.sha256}</span>
                    </>
                  )}
                  {typeof sliceState.layer_count === "number" && (
                    <>
                      <span className="text-muted">layer_count</span>
                      <span className="font-mono text-fg" data-testid="design-slicer-layer-count">{sliceState.layer_count}</span>
                    </>
                  )}
                  {typeof sliceState.motion_lines === "number" && (
                    <>
                      <span className="text-muted">motion_lines</span>
                      <span className="font-mono text-fg" data-testid="design-slicer-motion-lines">{sliceState.motion_lines}</span>
                    </>
                  )}
                  {typeof sliceState.estimated_print_time_min === "number" && (
                    <>
                      <span className="text-muted">est. print time</span>
                      <span className="font-mono text-fg">{sliceState.estimated_print_time_min} min</span>
                    </>
                  )}
                  {sliceState.proof_event_id && (
                    <>
                      <span className="text-muted">proof_event_id</span>
                      <span className="truncate font-mono text-fg" data-testid="design-slicer-proof-event">{sliceState.proof_event_id}</span>
                    </>
                  )}
                </div>
                {sliceState.status === "completed" && gcodeDownloadUrl(sliceState) && (
                  <a
                    href={gcodeDownloadUrl(sliceState) ?? "#"}
                    data-testid="design-slicer-download"
                    className="mt-1 inline-block w-fit rounded border border-accent-green/40 bg-accent-green/10 px-3 py-1.5 text-xs font-semibold text-accent-green"
                    download
                  >
                    Download G-code
                  </a>
                )}
                {sliceState.status === "failed" && (
                  <div className="rounded border border-accent-red/40 bg-accent-red/10 p-2 text-xs text-accent-red" data-testid="design-slicer-error">
                    {sliceState.error ?? "Slice failed (no error message returned)."}
                  </div>
                )}
              </div>
            )}
            {sliceMessage && (
              <div className="mt-3 rounded border border-border bg-bg/40 p-2 text-[11px] text-muted" data-testid="design-slicer-message">
                {sliceMessage}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

interface ProducedStl {
  file_path: string;
  label: string;
  file_size: number | null;
  sha256: string | null;
  job_id: string | null;
}

function extractStlArtifact(payload: unknown): ProducedStl | null {
  if (!isRecord(payload)) return null;
  const artifact = payload.artifact;
  if (!isRecord(artifact)) return null;
  const file_path = typeof artifact.file_path === "string" ? artifact.file_path : null;
  if (!file_path) return null;
  return {
    file_path,
    label: typeof artifact.label === "string" ? artifact.label : file_path.split(/[\\/]/).pop() || file_path,
    file_size: typeof artifact.file_size === "number" ? artifact.file_size : null,
    sha256: typeof artifact.sha256 === "string" ? artifact.sha256 : null,
    job_id: typeof payload.job_id === "string" ? payload.job_id : null,
  };
}

// ---------------------------------------------------------------------------
// Provider health card — shows real probed status
// ---------------------------------------------------------------------------

function ProviderCard({ provider }: { provider: CadProvider }) {
  const tone = provider.status === "ready"
    ? "bg-accent-green/15 text-accent-green"
    : provider.status === "detected"
    ? "bg-accent-cyan/15 text-accent-cyan"
    : "bg-surface2 text-muted";
  return (
    <div className="grid grid-cols-[1fr_auto] items-start gap-2 rounded border border-border bg-bg/50 p-3 text-xs">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-fg">{provider.name}</span>
          <span className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted">{provider.kind}</span>
        </div>
        <div className="mt-1 truncate font-mono text-[11px] text-muted">{provider.path ?? "not on PATH"}</div>
        {provider.version_detail && (
          <div className="mt-0.5 truncate text-[11px] text-muted">{provider.version_detail}</div>
        )}
        <div className="mt-1.5 line-clamp-2 text-muted">{provider.detail}</div>
        {provider.capabilities.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {provider.capabilities.slice(0, 5).map((cap) => (
              <span key={cap} className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted">{cap}</span>
            ))}
          </div>
        )}
      </div>
      <span className={["shrink-0 rounded px-2 py-1 text-[11px] uppercase", tone].join(" ")}>
        {provider.status.replace(/_/g, " ")}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Template card — shows real executor status, never fake preview
// ---------------------------------------------------------------------------

function TemplateCard({ tmpl, selected, onSelect }: { tmpl: CadTemplate; selected: boolean; onSelect: () => void }) {
  const available = tmpl.executor_available !== false;
  return (
    <div
      className={[
        "rounded border p-3 text-xs transition-colors",
        selected ? "border-accent-blue bg-accent-blue/10" : "border-border bg-bg/50",
        available ? "cursor-pointer" : "cursor-not-allowed opacity-60",
      ].join(" ")}
      role="button"
      tabIndex={available ? 0 : -1}
      aria-disabled={!available}
      onClick={available ? onSelect : undefined}
      onKeyDown={(e) => { if (available && (e.key === "Enter" || e.key === " ")) onSelect(); }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-semibold text-fg">{tmpl.name}</div>
          {tmpl.description && <div className="mt-0.5 line-clamp-2 text-muted">{tmpl.description}</div>}
        </div>
        <span className={[
          "shrink-0 rounded px-2 py-1 text-[11px] uppercase",
          available ? "bg-accent-green/15 text-accent-green" : "bg-surface2 text-muted",
        ].join(" ")}>
          {available ? "ready" : "unavailable"}
        </span>
      </div>
      {tmpl.executor_detail && (
        <div className="mt-2 text-[11px] text-muted">{tmpl.executor_detail}</div>
      )}
      {/* Preview: always show preview-not-available when no renderer is detected */}
      <div className="mt-2 rounded border border-border bg-surface/50 p-2 text-[11px] text-muted">
        {tmpl.preview_available
          ? "Preview available."
          : tmpl.preview_note ?? "Preview not available — no 3D renderer detected."}
      </div>
      {(tmpl.missing_deps ?? []).length > 0 && (
        <div className="mt-1.5 rounded border border-amber-700/50 bg-amber-950/20 p-1.5 text-[11px] text-amber-200">
          Missing deps: {(tmpl.missing_deps ?? []).join(", ")}
        </div>
      )}
      {tmpl.outputs && tmpl.outputs.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {tmpl.outputs.map((out) => (
            <span key={out} className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted">{out}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function designBlockReason(toolchain: ToolchainStatus): string {
  if (toolchain.overall === "ready") {
    return "Design toolchain is ready.";
  }
  if (toolchain.blockers && toolchain.blockers.length > 0) {
    return toolchain.blockers[0];
  }
  const blocked = toolchain.stages.find((stage) => stage.status !== "ready");
  const stageName = stageTitle(blocked);
  const detail = blocked?.detail ?? "";
  return stageName ? `${stageName} is ${blocked?.status}${detail ? `: ${detail}` : ""}.` : "Design CAD/modeling toolchain is not ready.";
}

function NumberField({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void }) {
  return (
    <label className="grid gap-1 rounded border border-border bg-bg px-2 py-1.5 text-[11px] text-muted">
      {label}
      <input
        className="min-w-0 bg-transparent text-sm font-semibold text-fg outline-none"
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-label={label}
      />
    </label>
  );
}

function ToolchainStageCard({ stage, onViewLogs }: { stage: ToolchainStage; onViewLogs: () => void }) {
  return (
    <div className="grid min-h-[116px] grid-rows-[auto_1fr_auto] gap-2 rounded border border-border bg-bg/50 p-3 text-sm">
      <div className="flex min-w-0 items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium text-fg">{stageTitle(stage)}</div>
          <div className="mt-0.5 truncate text-[11px] uppercase tracking-wide text-muted">{stage.source ?? "backend"}</div>
        </div>
        <span className={["shrink-0 rounded px-2 py-1 text-[11px] uppercase", statusTone(stage.status)].join(" ")}>{formatStatus(stage.status)}</span>
      </div>
      <div className="line-clamp-3 text-xs leading-5 text-muted">{stage.detail ?? "No recent detail."}</div>
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 truncate font-mono text-[11px] text-muted">{stage.path ?? stage.proof_path ?? stage.repo_url ?? stage.module_id ?? stage.id}</div>
        <button type="button" className="shrink-0 rounded border border-border px-2 py-1 text-xs text-fg" onClick={onViewLogs}>
          View Logs
        </button>
      </div>
    </div>
  );
}

function EvidenceSection({ title, detail, items, empty }: { title: string; detail: string; items: ToolchainEvidence[]; empty: string }) {
  return (
    <section className="rounded border border-border bg-bg/30 p-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-fg">{title}</h3>
          <p className="text-xs text-muted">{detail}</p>
        </div>
        <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">{items.length} records</span>
      </div>
      <div className="mt-3 grid gap-2 xl:grid-cols-2">
        {items.map((item) => (
          <div key={item.id} className="rounded border border-border bg-surface/60 p-3 text-xs">
            <div className="flex min-w-0 items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate font-semibold text-fg">{item.name}</div>
                <div className="mt-0.5 truncate font-mono text-[11px] text-muted">{item.path ?? item.repo_url ?? item.module_id ?? item.id}</div>
              </div>
              <span className={["shrink-0 rounded px-2 py-1 text-[11px] uppercase", statusTone(item.status)].join(" ")}>{formatStatus(item.status)}</span>
            </div>
            <div className="mt-2 line-clamp-2 text-muted">{item.detail ?? "No detail returned."}</div>
            {item.capabilities && item.capabilities.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {item.capabilities.slice(0, 6).map((capability) => (
                  <span key={capability} className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted">{capability}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {items.length === 0 && <div className="mt-3 rounded border border-border bg-surface/50 p-3 text-xs text-muted">{empty}</div>}
    </section>
  );
}

function stageTitle(stage: ToolchainStage | undefined): string | undefined {
  return stage?.name ?? stage?.label ?? stage?.id;
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ");
}

function statusTone(status: string): string {
  if (status === "ready" || status === "pass") {
    return "bg-accent-green/15 text-accent-green";
  }
  if (status === "blocked" || status === "fail" || status === "error") {
    return "bg-accent-red/15 text-accent-red";
  }
  if (status === "detected" || status === "active") {
    return "bg-accent-cyan/15 text-accent-cyan";
  }
  if (status === "warning") {
    return "bg-amber-500/15 text-amber-300";
  }
  return "bg-surface2 text-muted";
}

function designSummary(payload: unknown, fallback: string): string {
  if (!isRecord(payload)) {
    return fallback || "No response body.";
  }
  const detail = payload.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (isRecord(detail)) {
    return String(detail.reason ?? detail.error ?? detail.status ?? fallback);
  }
  if (isRecord(payload.artifact) && typeof payload.artifact.label === "string") {
    const proofId = isRecord(payload.proof) && typeof payload.proof.event_id === "string" ? `; proof ${payload.proof.event_id}` : "";
    return `${payload.artifact.label}${proofId}`;
  }
  return String(payload.reason ?? payload.message ?? payload.status ?? payload.job_id ?? payload.id ?? fallback);
}

function actionAccepted(httpOk: boolean, payload: unknown): boolean {
  if (!httpOk) {
    return false;
  }
  if (!isRecord(payload)) {
    return true;
  }
  if (payload.accepted === false || payload.created === false || payload.queued === false || payload.success === false) {
    return false;
  }
  const status = typeof payload.status === "string" ? payload.status.toLowerCase() : "";
  return !["blocked", "failed", "error", "not_configured", "unreachable", "rejected"].includes(status);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
