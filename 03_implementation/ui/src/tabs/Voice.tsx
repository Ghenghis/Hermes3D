import { Play, RefreshCw, Save, Settings, Volume2 } from "lucide-react";
import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { adapters } from "../api/adapters";
import { ResizablePane } from "../components/layout/ResizablePane";
import type { AzureVoice, VoiceAgent, VoiceCatalog, VoiceProvider } from "../types/voice";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const VOICE_LOCALES = [
  { value: "en", label: "All English" },
  { value: "en-US", label: "US" },
  { value: "en-GB", label: "UK" },
  { value: "en-AU", label: "Australia" },
  { value: "en-CA", label: "Canada" },
  { value: "en-IN", label: "India" },
  { value: "en-IE", label: "Ireland" },
  { value: "en-NZ", label: "New Zealand" },
  { value: "en-SG", label: "Singapore" },
  { value: "en-ZA", label: "South Africa" },
] as const;

const DEFAULT_SAMPLE = "Hello. I'm your Hermes3D coding and print assistant. How can I help today?";

export function VoiceTab() {
  const [agents, setAgents] = useState<VoiceAgent[]>([]);
  const [providers, setProviders] = useState<VoiceProvider[]>([]);
  const [catalog, setCatalog] = useState<VoiceCatalog | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>("");
  const [locale, setLocale] = useState("en");
  const [query, setQuery] = useState("");
  const [previewText, setPreviewText] = useState(DEFAULT_SAMPLE);
  const [rate, setRate] = useState(1);
  const [pitch, setPitch] = useState(0);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadAgents(setAgents, setSelectedAgentId, setSelectedVoiceId);
    void loadProviders(setProviders, setMessage);
  }, []);

  useEffect(() => {
    void loadCatalog(locale, setCatalog, setSelectedVoiceId, setMessage);
  }, [locale]);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? agents[0] ?? null;
  const voices = catalog?.voices ?? [];
  const selectedVoice = voices.find((voice) => voice.id === selectedVoiceId) ?? null;
  const provider = providers.find((item) => item.id === "azure") ?? null;
  const providerReady = catalog?.status === "ready" && catalog.configured;
  const visibleVoices = useMemo(() => filterVoices(voices, query), [voices, query]);

  const selectAgent = (agent: VoiceAgent) => {
    setSelectedAgentId(agent.id);
    setSelectedVoiceId(agent.voice);
  };

  const saveAssignment = async () => {
    if (!selectedAgent || selectedVoiceId === "") {
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await adapters.saveVoiceAgent(selectedAgent.id, selectedVoiceId);
      setAgents((current) => current.map((agent) => agent.id === selectedAgent.id ? { ...agent, voice: selectedVoiceId } : agent));
      await adapters.emitProofEvent("voice.agent.voice_saved", {
        agent_id: selectedAgent.id,
        voice: selectedVoiceId,
        provider: "azure",
        accepted: true,
      });
      setMessage(`Saved ${selectedVoiceId} for ${selectedAgent.name}.`);
    } catch (error) {
      setMessage(`Blocked: ${errorMessage(error)}`);
    } finally {
      setSaving(false);
    }
  };

  const previewVoice = async (voiceOverride?: string) => {
    const voice = voiceOverride ?? selectedVoiceId;
    if (!selectedAgent || voice === "") {
      return;
    }
    setPreviewing(true);
    setMessage(null);
    try {
      const result = await adapters.previewVoice(selectedAgent.id, voice, previewText, rate, pitch);
      if (result.accepted && result.audioBase64 && result.mimeType) {
        const audio = new Audio(`data:${result.mimeType};base64,${result.audioBase64}`);
        await audio.play().catch(() => undefined);
        setMessage(`Playing Azure preview for ${voice} (${result.bytes ?? 0} bytes).`);
      } else {
        setMessage(`Blocked: ${result.reason ?? result.status}.`);
      }
      await adapters.emitProofEvent("voice.agent.preview.triggered", {
        agent_id: selectedAgent.id,
        voice,
        accepted: result.accepted,
        status: result.status,
      });
    } catch (error) {
      setMessage(`Blocked: ${errorMessage(error)}`);
    } finally {
      setPreviewing(false);
    }
  };

  return (
    <div data-testid="voice-root" className="flex h-[calc(100vh-5rem)] min-h-0 min-w-0 flex-col gap-2.5 lg:flex-row">
      <ResizablePane
        storageKey="h3d.voice.agentRail.width"
        defaultWidth={350}
        minWidth={240}
        maxWidth={560}
        label="Voice agent list"
        dataTestId="voice-side-rail"
        className="flex min-h-0 w-full shrink-0 flex-col rounded-card border border-border bg-surface lg:w-[var(--pane-width)]"
      >
        <header className="flex h-10 items-center justify-between border-b border-border px-3">
          <div className="min-w-0">
            <h2 className="truncate text-[13px] font-semibold text-fg">Hermes Voice Layer</h2>
            <p className="truncate text-[10px] text-muted">Azure Speech via backend runtime env only</p>
          </div>
          <button
            type="button"
            title="Refresh Azure provider and voice catalog"
            onClick={() => {
              void loadProviders(setProviders, setMessage);
              void loadCatalog(locale, setCatalog, setSelectedVoiceId, setMessage);
            }}
            className="rounded border border-border p-1.5 text-muted hover:text-fg"
          >
            <RefreshCw size={14} />
          </button>
        </header>
        <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)_auto] gap-2 p-3">
          <ProviderStatus provider={provider} catalog={catalog} />
          <div className="min-h-0 overflow-auto rounded border border-border bg-bg/40">
            {agents.map((agent) => (
              <button
                type="button"
                key={agent.id}
                onClick={() => selectAgent(agent)}
                className={[
                  "flex w-full flex-col gap-1 border-b border-border/60 px-3 py-2 text-left text-xs last:border-0 hover:bg-surface2/60",
                  agent.id === selectedAgentId ? "bg-accent-cyan/10 text-fg" : "text-muted",
                ].join(" ")}
              >
                <span className="font-semibold text-fg">{agent.name}</span>
                <span className="truncate font-mono text-[10px]">{agent.voice}</span>
              </button>
            ))}
          </div>
          <div className="rounded border border-border bg-bg/40 p-2 text-[11px] text-muted">
            {selectedAgent ? (
              <>
                <div className="font-semibold text-fg">{selectedAgent.name}</div>
                <div className="truncate">Selected voice: {selectedVoiceId || selectedAgent.voice}</div>
              </>
            ) : (
              "No voice agents returned by the backend."
            )}
          </div>
        </div>
      </ResizablePane>

      <section className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_minmax(0,1fr)_auto] rounded-card border border-border bg-surface">
        <header className="grid gap-2 border-b border-border p-3 lg:grid-cols-[1fr_auto]">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-[13px] font-semibold text-fg">Voice Browser & Fine-Tuning</h2>
              <span className="rounded-chip border border-border bg-bg px-2 py-0.5 text-[10px] text-muted">
                {catalog ? `${catalog.count} live voices` : "loading voices"}
              </span>
              {selectedVoice && (
                <span className="rounded-chip border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-0.5 text-[10px] text-accent-cyan">
                  {selectedVoice.displayName} · {selectedVoice.locale}
                </span>
              )}
            </div>
            <p className="mt-1 text-[11px] text-muted">
              Catalog rows come from Azure Speech through the Python backend. The frontend never receives the Speech key.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              className="rounded border border-border bg-bg px-2 py-1 text-xs text-fg"
              value={locale}
              onChange={(event) => setLocale(event.target.value)}
            >
              {VOICE_LOCALES.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
            <input
              className="w-44 rounded border border-border bg-bg px-2 py-1 text-xs text-fg"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search voices"
            />
          </div>
        </header>

        <div className="grid min-h-0 gap-2 p-3 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div className="min-h-0 overflow-auto rounded border border-border bg-bg/40">
            {visibleVoices.length > 0 ? (
              visibleVoices.map((voice) => (
                <VoiceRow
                  key={voice.id}
                  voice={voice}
                  selected={voice.id === selectedVoiceId}
                  onSelect={() => setSelectedVoiceId(voice.id)}
                  onPreview={() => {
                    setSelectedVoiceId(voice.id);
                    void previewVoice(voice.id);
                  }}
                  previewEnabled={providerReady}
                />
              ))
            ) : (
              <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-1 p-4 text-center text-xs text-muted">
                <Volume2 size={22} />
                <div className="font-semibold text-fg">{catalog?.reason ?? "No Azure voices returned for this filter."}</div>
                <div>Set `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` in `G:\\private\\.env` to load the live Azure catalog.</div>
              </div>
            )}
          </div>

          <div className="flex min-h-0 flex-col gap-2 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
            <div className="flex items-center gap-2 font-semibold text-fg">
              <Settings size={14} className="text-accent-cyan" />
              Fine-Tuning
            </div>
            <label className="grid gap-1">
              <span className="text-muted">Sample text</span>
              <textarea
                className="min-h-24 rounded border border-border bg-bg p-2 text-fg"
                value={previewText}
                onChange={(event) => setPreviewText(event.target.value)}
              />
            </label>
            <RangeControl label={`Rate: ${rate.toFixed(1)}x`} min={0.5} max={2} step={0.1} value={rate} onChange={setRate} />
            <RangeControl label={`Pitch: ${pitch}%`} min={-50} max={50} step={1} value={pitch} onChange={setPitch} />
            <div className="mt-auto grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={!selectedAgent || selectedVoiceId === "" || saving}
                onClick={() => void saveAssignment()}
                className="inline-flex items-center justify-center gap-1 rounded border border-border px-2 py-1.5 text-fg hover:border-accent-blue disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Save size={13} />
                {saving ? "Saving" : "Save"}
              </button>
              <button
                type="button"
                disabled={!providerReady || !selectedAgent || selectedVoiceId === "" || previewing}
                title={providerReady ? "Play real Azure TTS preview" : catalog?.reason ?? "Azure Speech is not configured."}
                onClick={() => void previewVoice()}
                className="inline-flex items-center justify-center gap-1 rounded bg-accent-cyan px-2 py-1.5 font-semibold text-bg disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Play size={13} />
                {previewing ? "Loading" : "Preview"}
              </button>
            </div>
            {message && <div className="rounded border border-border bg-surface p-2 text-[11px] text-muted">{message}</div>}
          </div>
        </div>
      </section>
    </div>
  );
}

async function loadAgents(
  setAgents: (agents: VoiceAgent[]) => void,
  setSelectedAgentId: (id: string) => void,
  setSelectedVoiceId: (id: string) => void,
) {
  const next = await adapters.getVoiceAgents();
  setAgents(next);
  if (next[0]) {
    setSelectedAgentId(next[0].id);
    setSelectedVoiceId(next[0].voice);
  }
}

async function loadProviders(setProviders: (providers: VoiceProvider[]) => void, setMessage: (message: string | null) => void) {
  try {
    const response = await fetchProviderRows();
    setProviders(response);
  } catch {
    setMessage("Blocked: voice provider API is unreachable from the local backend.");
  }
}

async function fetchProviderRows(): Promise<VoiceProvider[]> {
  const response = await fetch(`${LIVE_BASE_URL}/api/voice/providers`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const payload: unknown = await response.json().catch(() => []);
  return Array.isArray(payload) ? payload.filter(isVoiceProvider) : [];
}

async function loadCatalog(
  locale: string,
  setCatalog: (catalog: VoiceCatalog) => void,
  setSelectedVoiceId: Dispatch<SetStateAction<string>>,
  setMessage: (message: string | null) => void,
) {
  const next = await adapters.getVoiceCatalog(locale);
  setCatalog(next);
  if (next.status !== "ready") {
    setMessage(next.reason ?? "Azure voice catalog is not ready.");
    return;
  }
  setMessage(null);
  if (next.voices[0]) {
    setSelectedVoiceId((current) => current || next.voices[0].id);
  }
}

function ProviderStatus({ provider, catalog }: { provider: VoiceProvider | null; catalog: VoiceCatalog | null }) {
  const ready = catalog?.status === "ready" && catalog.configured;
  return (
    <div className="rounded border border-border bg-bg/50 p-2 text-[11px]">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-fg">{provider?.name ?? "Azure Speech"}</span>
        <span className={ready ? "text-accent-green" : "text-accent-amber"}>{ready ? "READY" : catalog?.status ?? "LOADING"}</span>
      </div>
      <div className="mt-1 text-muted">
        {ready ? `Region: ${catalog?.region ?? provider?.region ?? "configured"}` : catalog?.reason ?? "Waiting for provider status."}
      </div>
      <div className="mt-1 text-[10px] text-muted">
        TTS preview and chat mic STT both route through the backend; Speech keys stay out of the frontend bundle.
      </div>
    </div>
  );
}

function VoiceRow({
  voice,
  selected,
  onSelect,
  onPreview,
  previewEnabled,
}: {
  voice: AzureVoice;
  selected: boolean;
  onSelect: () => void;
  onPreview: () => void;
  previewEnabled: boolean;
}) {
  return (
    <div className={["grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 border-b border-border/60 p-2 last:border-0", selected ? "bg-accent-cyan/10" : ""].join(" ")}>
      <button type="button" onClick={onSelect} className="min-w-0 text-left">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-fg">{voice.displayName}</span>
          <span className="text-[11px] text-muted">{voice.gender} · {voice.locale}</span>
          <span className="font-mono text-[10px] text-muted">{voice.shortName}</span>
        </div>
        <div className="mt-0.5 truncate text-[11px] text-muted">
          {voice.styles.length > 0 ? `Styles: ${voice.styles.join(", ")}` : "Standard neural voice"}
        </div>
      </button>
      <button
        type="button"
        disabled={!previewEnabled}
        title={previewEnabled ? `Preview ${voice.shortName}` : "Azure Speech is not configured."}
        onClick={onPreview}
        className="rounded border border-border p-1.5 text-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Play size={13} />
      </button>
    </div>
  );
}

function RangeControl({
  label,
  min,
  max,
  step,
  value,
  onChange,
}: {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="grid gap-1">
      <span className="text-muted">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-cyan-400"
      />
    </label>
  );
}

function filterVoices(voices: AzureVoice[], query: string): AzureVoice[] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return voices;
  }
  return voices.filter((voice) => (
    voice.displayName.toLowerCase().includes(needle) ||
    voice.shortName.toLowerCase().includes(needle) ||
    voice.locale.toLowerCase().includes(needle) ||
    voice.styles.some((style) => style.toLowerCase().includes(needle))
  ));
}

function isVoiceProvider(value: unknown): value is VoiceProvider {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  const row = value as Record<string, unknown>;
  return typeof row.id === "string" && typeof row.name === "string" && typeof row.configured === "boolean";
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
