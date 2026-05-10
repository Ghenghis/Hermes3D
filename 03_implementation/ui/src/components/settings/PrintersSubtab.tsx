import { useEffect, useState } from "react";
import { Camera, Plus, Printer as PrinterIcon, RefreshCcw, Save } from "lucide-react";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";
import { adapters } from "../../api/adapters";
import type { Printer, PrinterOnboardResult, PrinterStatus } from "../../types/printer";

type HealthState = "loading" | "live" | "unavailable";

const PRINTER_TONE: Record<PrinterStatus, StatusTone> = {
  online: "green",
  active: "green",
  printing: "cyan",
  paused: "amber",
  maintenance: "amber",
  offline: "muted",
  error: "red",
};

export function PrintersSubtab() {
  const [printers, setPrinters] = useState<Printer[]>([]);
  const [cameraDrafts, setCameraDrafts] = useState<Record<string, string>>({});
  const [savingCamera, setSavingCamera] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [state, setState] = useState<HealthState>("loading");
  const [onboardDraft, setOnboardDraft] = useState({
    id: "",
    name: "",
    model: "Generic" as Printer["model"],
    moonraker_url: "",
    camera_url: "",
    write_enabled: false,
  });
  const [onboarding, setOnboarding] = useState(false);
  const [onboardResult, setOnboardResult] = useState<PrinterOnboardResult | null>(null);

  const loadPrinters = async () => {
    setState("loading");
    const [next, settings] = await Promise.all([adapters.getPrinters(), adapters.getSettings()]);
    setPrinters(next);
    setCameraDrafts(Object.fromEntries(next.map((printer) => [
      printer.id,
      settings.cameraUrls[printer.id] ?? printer.camera_url ?? "",
    ])));
    setState("live");
  };

  useEffect(() => {
    let cancelled = false;
    void loadPrinters()
      .then(() => {
        if (cancelled) return;
      })
      .catch(() => {
        if (cancelled) return;
        setPrinters([]);
        setState("unavailable");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const groups = Array.from(new Set(printers.map((p) => p.model)));
  const canOnboard = onboardDraft.name.trim().length > 0 && onboardDraft.moonraker_url.trim().length > 0 && !onboarding;

  const submitOnboarding = async () => {
    if (!canOnboard) return;
    setOnboarding(true);
    setOnboardResult(null);
    try {
      const result = await adapters.onboardPrinter({
        id: onboardDraft.id.trim() || undefined,
        name: onboardDraft.name.trim(),
        model: onboardDraft.model,
        moonraker_url: onboardDraft.moonraker_url.trim(),
        camera_url: onboardDraft.camera_url.trim() || undefined,
        write_enabled: onboardDraft.write_enabled,
        actor: "local-operator",
      });
      setOnboardResult(result);
      if (result.created) {
        await loadPrinters();
        setOnboardDraft({
          id: "",
          name: "",
          model: "Generic",
          moonraker_url: "",
          camera_url: "",
          write_enabled: false,
        });
      }
    } catch (error) {
      setOnboardResult({
        created: false,
        printer: null,
        probe_summary: null,
        status: "unreachable",
        reason: error instanceof Error ? error.message : "Printer onboarding failed.",
        failed_probe: null,
      });
    } finally {
      setOnboarding(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="settings-printers">
      <header className="flex items-center gap-2 text-muted">
        <PrinterIcon size={14} />
        <span className="text-fg font-medium">Printer fleet</span>
        <span className="text-[10px]">·</span>
        <span className="text-[10px]">{printers.length} units from the backend</span>
        <span className="ml-auto inline-flex items-center gap-1.5">
          <RefreshCcw size={11} className="text-muted" />
          <HealthStateBadge state={state} />
        </span>
      </header>

      <section className="rounded border border-border bg-surface2/30 p-2.5" data-testid="printer-onboarding-form">
        <div className="mb-2 flex items-center gap-2">
          <Plus size={13} className="text-accent-cyan" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-fg">Add Moonraker Printer</h3>
          <span className="ml-auto text-[10px] text-muted">live probe required before save</span>
        </div>
        <div className="grid gap-2 lg:grid-cols-[1fr_0.8fr_1.3fr_1.3fr_auto]">
          <label className="grid gap-1">
            <span className="text-[10px] text-muted">Name</span>
            <input
              aria-label="New printer name"
              value={onboardDraft.name}
              onChange={(event) => {
                const { value } = event.currentTarget;
                setOnboardDraft((current) => ({ ...current, name: value }));
              }}
              className="rounded border border-border bg-bg px-2 py-1 text-[11px] text-fg outline-none focus:border-accent-cyan"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-[10px] text-muted">Model</span>
            <select
              aria-label="New printer model"
              value={onboardDraft.model}
              onChange={(event) => {
                const value = event.currentTarget.value as Printer["model"];
                setOnboardDraft((current) => ({ ...current, model: value }));
              }}
              className="rounded border border-border bg-bg px-2 py-1 text-[11px] text-fg outline-none focus:border-accent-cyan"
            >
              <option>Generic</option>
              <option>FLSUN T1</option>
              <option>FLSUN V400</option>
            </select>
          </label>
          <label className="grid gap-1">
            <span className="text-[10px] text-muted">Moonraker URL</span>
            <input
              aria-label="New printer Moonraker URL"
              value={onboardDraft.moonraker_url}
              onChange={(event) => {
                const { value } = event.currentTarget;
                setOnboardDraft((current) => ({ ...current, moonraker_url: value }));
              }}
              className="rounded border border-border bg-bg px-2 py-1 font-mono text-[10px] text-fg outline-none focus:border-accent-cyan"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-[10px] text-muted">Camera URL</span>
            <input
              aria-label="New printer camera URL"
              value={onboardDraft.camera_url}
              onChange={(event) => {
                const { value } = event.currentTarget;
                setOnboardDraft((current) => ({ ...current, camera_url: value }));
              }}
              className="rounded border border-border bg-bg px-2 py-1 font-mono text-[10px] text-fg outline-none focus:border-accent-cyan"
            />
          </label>
          <div className="flex flex-col justify-end gap-1">
            <label className="flex items-center gap-1.5 text-[10px] text-muted">
              <input
                type="checkbox"
                checked={onboardDraft.write_enabled}
                onChange={(event) => {
                  const { checked } = event.currentTarget;
                  setOnboardDraft((current) => ({ ...current, write_enabled: checked }));
                }}
              />
              guarded writes
            </label>
            <button
              type="button"
              disabled={!canOnboard}
              onClick={() => void submitOnboarding()}
              className="rounded bg-accent-blue px-3 py-1 text-[11px] font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-50"
            >
              {onboarding ? "Probing" : "Add"}
            </button>
          </div>
        </div>
        {onboardResult && (
          <div className={`mt-2 rounded border px-2 py-1.5 text-[11px] ${onboardResult.created ? "border-green-700/60 bg-green-950/30 text-green-200" : "border-red-800/60 bg-red-950/30 text-red-200"}`}>
            {onboardResult.created
              ? `${onboardResult.printer?.name ?? "Printer"} onboarded. Proof event ${onboardResult.proof_event_id ?? "recorded"}.`
              : `Onboarding blocked${onboardResult.failed_probe ? ` at ${onboardResult.failed_probe}` : ""}: ${onboardResult.reason ?? "backend rejected the request."}`}
          </div>
        )}
      </section>

      {groups.map((group) => (
        <section
          key={group}
          className="flex flex-col gap-1"
          data-testid={`settings-printers-group-${group.replace(/\s+/g, "-").toLowerCase()}`}
        >
          <h3 className="text-fg text-[11px] uppercase tracking-wide">{group}</h3>
          <ul className="flex flex-col gap-1">
            {printers.filter((p) => p.model === group).map((p) => {
              return (
                <li
                  key={p.id}
                  data-testid={`settings-printers-row-${p.id}`}
                  className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border"
                >
                  <span className="text-fg text-[11px] font-medium w-44 shrink-0 truncate">
                    {p.name}
                  </span>
                  <span className="text-muted font-mono text-[10px] hidden md:inline truncate">
                    {p.id}
                  </span>
                  <span className="text-fg font-mono text-[10px] flex-1 truncate">
                    {p.ip ?? "no IP returned"}
                  </span>
                  <label className="hidden min-w-0 flex-[1.5] items-center gap-1.5 lg:flex">
                    <Camera size={11} className="shrink-0 text-accent-cyan" />
                    <input
                      aria-label={`${p.name} camera URL`}
                      value={cameraDrafts[p.id] ?? ""}
                      onChange={(event) => {
                        const { value } = event.currentTarget;
                        setCameraDrafts((current) => ({ ...current, [p.id]: value }));
                      }}
                      className="min-w-0 flex-1 rounded border border-border bg-bg px-2 py-1 font-mono text-[10px] text-fg outline-none focus:border-accent-cyan"
                    />
                    <button
                      type="button"
                      disabled={savingCamera === p.id}
                      onClick={() => void saveCameraUrl(p.id, cameraDrafts[p.id] ?? "", setSavingCamera, setMessage)}
                      className="rounded border border-border p-1 text-fg disabled:cursor-not-allowed disabled:opacity-50"
                      title={`Save ${p.name} camera URL`}
                    >
                      <Save size={11} />
                    </button>
                  </label>
                  {p.source_refs.official_wiki_url && (
                    <a
                      href={p.source_refs.official_wiki_url}
                      target="_blank"
                      rel="noreferrer"
                      className="hidden max-w-32 truncate text-[10px] text-accent-blue hover:underline lg:inline"
                      title={p.source_refs.official_wiki_url}
                    >
                      FLSUN wiki
                    </a>
                  )}
                  {p.source_refs.profiles_detected && (
                    <span className="hidden text-[10px] text-muted xl:inline">
                      profiles {Object.values(p.source_refs.profiles_detected).filter(Boolean).length}/{Object.keys(p.source_refs.profiles_detected).length}
                    </span>
                  )}
                  <StatusBadge tone={PRINTER_TONE[p.status]} label={p.status} />
                </li>
              );
            })}
          </ul>
        </section>
      ))}
      {printers.length === 0 && (
        <div className="rounded border border-border bg-surface2/30 px-3 py-2 text-muted">
          {state === "loading" && "Loading printers from the backend."}
          {state === "live" && "No printers returned by the backend."}
          {state === "unavailable" && "Printer endpoint is unavailable."}
        </div>
      )}
      {message && <div className="rounded border border-border bg-surface2/30 px-3 py-2 text-[11px] text-muted">{message}</div>}

      <footer className="text-muted text-[10px] pt-2 border-t border-border">
        Fleet rows are fetched from <span className="font-mono">/api/printers</span>; camera URLs save to <span className="font-mono">/api/settings</span>; S1 remains operator-editable but locked for test/upload/move.
      </footer>
    </div>
  );
}

async function saveCameraUrl(
  printerId: string,
  value: string,
  setSaving: (printerId: string | null) => void,
  setMessage: (message: string) => void,
) {
  setSaving(printerId);
  try {
    await adapters.saveSettings({ cameraUrls: { [printerId]: value.trim() } });
    setMessage(`${printerId}: camera URL saved. Observe will use this feed on refresh.`);
    await adapters.emitProofEvent("settings.printer_camera_url.saved", {
      printer_id: printerId,
      configured: value.trim().length > 0,
    });
  } catch {
    setMessage(`${printerId}: camera URL save failed because the settings API is unreachable.`);
  } finally {
    setSaving(null);
  }
}

function HealthStateBadge({ state }: { state: HealthState }) {
  if (state === "live") return <StatusBadge tone="green" label="live" />;
  if (state === "loading") return <StatusBadge tone="cyan" label="loading" />;
  return <StatusBadge tone="muted" label="config-only" />;
}
