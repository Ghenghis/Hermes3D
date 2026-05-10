import { ChevronRight, Clock, Mic, MicOff, Pause, Play, RefreshCw, Save, Settings, Shield, Square, Volume2, VolumeX } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { adapters } from "../api/adapters";
import { ResizablePane } from "../components/layout/ResizablePane";
import type { AzureVoice, VoiceAgent, VoiceCatalog, VoiceProofEvent, VoiceProvider, VoiceTranscript } from "../types/voice";

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

type TabName = "browser" | "transcripts" | "proof";

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
  const [muted, setMuted] = useState(false);
  const [activeTab, setActiveTab] = useState<TabName>("browser");

  // Transcript history state
  const [transcripts, setTranscripts] = useState<VoiceTranscript[]>([]);
  const [transcriptsLoading, setTranscriptsLoading] = useState(false);
  const [transcriptsError, setTranscriptsError] = useState<string | null>(null);
  const [selectedTranscript, setSelectedTranscript] = useState<VoiceTranscript | null>(null);

  // Playback state (backend-proxied audio only)
  const [playbackState, setPlaybackState] = useState<"idle" | "loading" | "playing" | "paused">("idle");
  const [playbackRecordingId, setPlaybackRecordingId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Proof review state
  const [proofEvents, setProofEvents] = useState<VoiceProofEvent[]>([]);
  const [proofLoading, setProofLoading] = useState(false);
  const [proofError, setProofError] = useState<string | null>(null);
  const [expandedProofId, setExpandedProofId] = useState<string | null>(null);

  useEffect(() => {
    void loadAgents(setAgents, setSelectedAgentId, setSelectedVoiceId);
    void loadProviders(setProviders, setMessage);
  }, []);

  useEffect(() => {
    void loadCatalog(locale, setCatalog, setSelectedVoiceId, setMessage);
  }, [locale]);

  useEffect(() => {
    if (activeTab === "transcripts") {
      void loadTranscripts();
    } else if (activeTab === "proof") {
      void loadProofEvents();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

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
        // Text transcript always set (mute cannot suppress the text display)
        const textSummary = `Azure TTS preview: "${previewText.slice(0, 80)}${previewText.length > 80 ? "…" : ""}" — voice ${voice} (${result.bytes ?? 0} bytes)`;
        if (muted) {
          setMessage(`Muted — audio suppressed. ${textSummary}`);
        } else {
          const audio = new Audio(`data:${result.mimeType};base64,${result.audioBase64}`);
          await audio.play().catch(() => undefined);
          setMessage(`Playing Azure preview for ${voice} (${result.bytes ?? 0} bytes).`);
        }
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

  const loadTranscripts = async () => {
    setTranscriptsLoading(true);
    setTranscriptsError(null);
    try {
      const items = await adapters.getVoiceTranscripts(50);
      setTranscripts(items);
    } catch (error) {
      setTranscriptsError(errorMessage(error));
    } finally {
      setTranscriptsLoading(false);
    }
  };

  const loadProofEvents = async () => {
    setProofLoading(true);
    setProofError(null);
    try {
      const items = await adapters.getVoiceProofEvents(100);
      setProofEvents(items);
    } catch (error) {
      setProofError(errorMessage(error));
    } finally {
      setProofLoading(false);
    }
  };

  const playRecording = (recordingId: string) => {
    if (playbackRecordingId === recordingId && playbackState === "playing") {
      // pause current
      audioRef.current?.pause();
      setPlaybackState("paused");
      return;
    }
    if (playbackRecordingId === recordingId && playbackState === "paused") {
      // resume
      void audioRef.current?.play().catch(() => undefined);
      setPlaybackState("playing");
      return;
    }
    // stop any existing
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    setPlaybackRecordingId(recordingId);
    setPlaybackState("loading");
    const url = adapters.getVoiceRecordingUrl(recordingId);
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.oncanplaythrough = () => {
      setPlaybackState("playing");
      void audio.play().catch(() => {
        setPlaybackState("idle");
      });
    };
    audio.onended = () => {
      setPlaybackState("idle");
      setPlaybackRecordingId(null);
    };
    audio.onerror = () => {
      setPlaybackState("idle");
      setPlaybackRecordingId(null);
    };
  };

  const stopPlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    setPlaybackState("idle");
    setPlaybackRecordingId(null);
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

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5">
        {/* Tab bar */}
        <nav className="flex gap-1 rounded-card border border-border bg-surface px-2 py-1.5">
          {(
            [
              { id: "browser", label: "Voice Browser", icon: <Volume2 size={13} /> },
              { id: "transcripts", label: "Transcript History", icon: <Mic size={13} /> },
              { id: "proof", label: "Proof Review", icon: <Shield size={13} /> },
            ] as { id: TabName; label: string; icon: React.ReactNode }[]
          ).map(({ id, label, icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              className={[
                "inline-flex items-center gap-1.5 rounded px-3 py-1 text-xs font-medium transition-colors",
                activeTab === id
                  ? "bg-accent-cyan/20 text-accent-cyan"
                  : "text-muted hover:text-fg",
              ].join(" ")}
            >
              {icon}
              {label}
            </button>
          ))}
        </nav>

        {/* Voice Browser tab */}
        {activeTab === "browser" && (
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
                <div className="mt-auto grid grid-cols-[1fr_1fr_auto] gap-2">
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
                  <button
                    type="button"
                    onClick={() => setMuted((current) => !current)}
                    title={muted ? "Audio muted — click to unmute. Text is always shown." : "Click to mute audio. Text transcript is always visible."}
                    className={[
                      "inline-flex items-center justify-center rounded border px-2 py-1.5",
                      muted ? "border-accent-amber/60 bg-accent-amber/10 text-accent-amber" : "border-border text-muted hover:text-fg",
                    ].join(" ")}
                  >
                    {muted ? <VolumeX size={13} /> : <Volume2 size={13} />}
                  </button>
                </div>
                {message && <div className="rounded border border-border bg-surface p-2 text-[11px] text-muted">{message}</div>}
              </div>
            </div>
          </section>
        )}

        {/* Transcript History tab */}
        {activeTab === "transcripts" && (
          <section
            data-testid="voice-transcript-history"
            className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_minmax(0,1fr)] rounded-card border border-border bg-surface"
          >
            <header className="flex items-center justify-between border-b border-border p-3">
              <div>
                <h2 className="text-[13px] font-semibold text-fg">Transcript History</h2>
                <p className="mt-0.5 text-[11px] text-muted">
                  STT interactions stored by the backend, newest first. No audio device access from the frontend.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {/* Playback controls — audio served from backend only */}
                {playbackState !== "idle" && (
                  <div className="flex items-center gap-1 rounded border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-1">
                    <span className="text-[10px] font-mono text-accent-cyan truncate max-w-24">
                      {playbackState === "loading" ? "buffering…" : playbackState}
                    </span>
                    <button
                      type="button"
                      title={playbackState === "playing" ? "Pause" : "Resume"}
                      onClick={() => playbackRecordingId && playRecording(playbackRecordingId)}
                      className="text-accent-cyan hover:text-fg"
                    >
                      {playbackState === "playing" ? <Pause size={13} /> : <Play size={13} />}
                    </button>
                    <button
                      type="button"
                      title="Stop playback"
                      onClick={stopPlayback}
                      className="text-accent-amber hover:text-fg"
                    >
                      <Square size={13} />
                    </button>
                  </div>
                )}
                <button
                  type="button"
                  title="Refresh transcript history"
                  onClick={() => void loadTranscripts()}
                  disabled={transcriptsLoading}
                  className="rounded border border-border p-1.5 text-muted hover:text-fg disabled:opacity-50"
                >
                  <RefreshCw size={14} className={transcriptsLoading ? "animate-spin" : ""} />
                </button>
              </div>
            </header>

            <div className="grid min-h-0 gap-2 p-3 lg:grid-cols-[minmax(0,1fr)_22rem]">
              {/* Left: transcript list */}
              <div className="min-h-0 overflow-auto rounded border border-border bg-bg/40">
                {transcriptsError && (
                  <div className="flex h-20 items-center justify-center p-4 text-center text-xs text-accent-red">
                    <MicOff size={14} className="mr-2 shrink-0" />
                    {transcriptsError}
                  </div>
                )}
                {!transcriptsError && transcripts.length === 0 && !transcriptsLoading && (
                  <div className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 p-4 text-center text-xs text-muted">
                    <Clock size={22} />
                    <div className="font-semibold text-fg">No transcripts yet</div>
                    <div>Voice STT interactions will appear here once the backend has processed audio.</div>
                  </div>
                )}
                {transcripts.map((tr) => (
                  <button
                    key={tr.id}
                    type="button"
                    onClick={() => setSelectedTranscript(tr)}
                    className={[
                      "w-full border-b border-border/60 px-3 py-2 text-left last:border-0 hover:bg-surface2/60",
                      selectedTranscript?.id === tr.id ? "bg-accent-cyan/10" : "",
                    ].join(" ")}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={[
                        "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold",
                        tr.status === "ready" ? "bg-accent-green/15 text-accent-green" : "bg-accent-amber/15 text-accent-amber",
                      ].join(" ")}>
                        {tr.status === "ready" ? <Mic size={10} /> : <MicOff size={10} />}
                        {tr.status}
                      </span>
                      <span className="font-mono text-[10px] text-muted">{formatTs(tr.tsUtc)}</span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] text-fg">
                      {tr.transcript || <span className="text-muted italic">(no transcript text)</span>}
                    </p>
                    <div className="mt-0.5 flex gap-2 text-[10px] text-muted">
                      {tr.locale && <span>{tr.locale}</span>}
                      {tr.phraseCount !== undefined && <span>{tr.phraseCount} phrase{tr.phraseCount !== 1 ? "s" : ""}</span>}
                      {tr.bytes !== undefined && <span>{formatBytes(tr.bytes)}</span>}
                    </div>
                  </button>
                ))}
              </div>

              {/* Right: detail + playback controls */}
              <div className="flex min-h-0 flex-col gap-2 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
                {selectedTranscript ? (
                  <>
                    <div className="flex items-center gap-2 font-semibold text-fg">
                      <Mic size={14} className="text-accent-cyan" />
                      Transcript Detail
                    </div>
                    <div className="grid gap-1 text-[11px]">
                      <Row label="ID" value={selectedTranscript.id} mono />
                      <Row label="Status" value={selectedTranscript.status} />
                      <Row label="Locale" value={selectedTranscript.locale || "—"} />
                      <Row label="Provider" value={selectedTranscript.provider || "—"} />
                      {selectedTranscript.phraseCount !== undefined && (
                        <Row label="Phrases" value={String(selectedTranscript.phraseCount)} />
                      )}
                      {selectedTranscript.bytes !== undefined && (
                        <Row label="Audio size" value={formatBytes(selectedTranscript.bytes)} />
                      )}
                      <Row label="Timestamp" value={selectedTranscript.tsUtc} />
                      <Row label="Proof event" value={selectedTranscript.proofEventId} mono />
                    </div>
                    {selectedTranscript.transcript && (
                      <div className="mt-1 rounded border border-border bg-bg p-2">
                        <div className="mb-1 text-[10px] font-semibold text-muted uppercase tracking-wide">Transcript</div>
                        <p className="text-[12px] text-fg leading-relaxed whitespace-pre-wrap">{selectedTranscript.transcript}</p>
                      </div>
                    )}
                    {/* Agent voice playback — backend-proxied, no direct device access */}
                    <div className="mt-auto rounded border border-border bg-surface p-2">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <div className="text-[10px] font-semibold text-muted uppercase tracking-wide">Agent Voice Playback</div>
                        <button
                          type="button"
                          onClick={() => setMuted((current) => !current)}
                          title={muted ? "Audio muted — text always visible. Click to unmute." : "Mute audio. Text transcript stays visible."}
                          className={[
                            "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px]",
                            muted ? "border-accent-amber/60 bg-accent-amber/10 text-accent-amber" : "border-border text-muted hover:text-fg",
                          ].join(" ")}
                        >
                          {muted ? <VolumeX size={11} /> : <Volume2 size={11} />}
                          {muted ? "Muted" : "Sound on"}
                        </button>
                      </div>
                      <p className="mb-2 text-[10px] text-muted">
                        Audio is fetched from the local backend. No API keys are exposed to the browser.
                        {muted ? " Muted — audio is suppressed but text transcript is always shown." : ""}
                      </p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={playbackState === "loading" || muted}
                          onClick={() => !muted && playRecording(selectedTranscript.proofEventId)}
                          title={muted ? "Unmute to play audio. Text is always visible above." : undefined}
                          className={[
                            "inline-flex flex-1 items-center justify-center gap-1.5 rounded px-2 py-1.5 text-xs font-medium",
                            muted
                              ? "border border-border text-muted cursor-not-allowed opacity-50"
                              : playbackState === "playing" && playbackRecordingId === selectedTranscript.proofEventId
                                ? "bg-accent-amber/20 text-accent-amber border border-accent-amber/40"
                                : "bg-accent-cyan/90 text-bg disabled:opacity-50 disabled:cursor-not-allowed",
                          ].join(" ")}
                        >
                          {playbackState === "loading" && playbackRecordingId === selectedTranscript.proofEventId ? (
                            <><RefreshCw size={12} className="animate-spin" /> Buffering</>
                          ) : playbackState === "playing" && playbackRecordingId === selectedTranscript.proofEventId ? (
                            <><Pause size={12} /> Pause</>
                          ) : playbackState === "paused" && playbackRecordingId === selectedTranscript.proofEventId ? (
                            <><Play size={12} /> Resume</>
                          ) : muted ? (
                            <><VolumeX size={12} /> Audio muted</>
                          ) : (
                            <><Play size={12} /> Play Recording</>
                          )}
                        </button>
                        {playbackRecordingId === selectedTranscript.proofEventId && playbackState !== "idle" && (
                          <button
                            type="button"
                            onClick={stopPlayback}
                            className="inline-flex items-center justify-center gap-1.5 rounded border border-border px-2 py-1.5 text-xs text-muted hover:text-fg"
                          >
                            <Square size={12} /> Stop
                          </button>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex h-full items-center justify-center text-center text-muted">
                    <div>
                      <ChevronRight size={20} className="mx-auto mb-1 opacity-40" />
                      <p>Select a transcript to view detail and play its recording.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Proof Review tab */}
        {activeTab === "proof" && (
          <section
            data-testid="voice-proof-review"
            className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_minmax(0,1fr)] rounded-card border border-border bg-surface"
          >
            <header className="flex items-center justify-between border-b border-border p-3">
              <div>
                <h2 className="text-[13px] font-semibold text-fg">Voice Proof Review</h2>
                <p className="mt-0.5 text-[11px] text-muted">
                  Immutable proof events emitted by the voice runtime. TTS and STT keys stay in the backend; the frontend only receives event metadata.
                </p>
              </div>
              <button
                type="button"
                title="Refresh proof events"
                onClick={() => void loadProofEvents()}
                disabled={proofLoading}
                className="rounded border border-border p-1.5 text-muted hover:text-fg disabled:opacity-50"
              >
                <RefreshCw size={14} className={proofLoading ? "animate-spin" : ""} />
              </button>
            </header>

            <div className="min-h-0 overflow-auto p-3">
              {proofError && (
                <div className="mb-3 rounded border border-accent-red/40 bg-accent-red/10 p-3 text-xs text-accent-red">
                  {proofError}
                </div>
              )}
              {!proofError && proofEvents.length === 0 && !proofLoading && (
                <div className="flex min-h-[180px] flex-col items-center justify-center gap-2 text-center text-xs text-muted">
                  <Shield size={22} />
                  <div className="font-semibold text-fg">No voice proof events yet</div>
                  <div>Events are recorded each time TTS or STT is invoked through the backend.</div>
                </div>
              )}
              <div className="flex flex-col gap-1">
                {proofEvents.map((ev) => (
                  <div
                    key={ev.id}
                    className="rounded border border-border bg-bg/40"
                  >
                    <button
                      type="button"
                      onClick={() => setExpandedProofId(expandedProofId === ev.id ? null : ev.id)}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left"
                    >
                      <ProofEventBadge eventType={ev.eventType} status={ev.status} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] text-fg">{ev.eventType}</span>
                          <span className="text-[10px] text-muted">{formatTs(ev.tsUtc)}</span>
                        </div>
                        <p className="truncate text-[11px] text-muted">{ev.summary}</p>
                      </div>
                      <ChevronRight
                        size={13}
                        className={["text-muted transition-transform", expandedProofId === ev.id ? "rotate-90" : ""].join(" ")}
                      />
                    </button>
                    {expandedProofId === ev.id && (
                      <div className="border-t border-border px-3 pb-2 pt-2">
                        <div className="grid gap-1 text-[11px]">
                          <Row label="Event ID" value={ev.id} mono />
                          <Row label="Source agent" value={ev.sourceAgent || "voice-runtime"} />
                          <Row label="Status" value={ev.status} />
                          <Row label="Timestamp" value={ev.tsUtc} />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

// ── helper components ────────────────────────────────────────────────────────

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

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex gap-2">
      <span className="w-24 shrink-0 text-muted">{label}</span>
      <span className={["break-all text-fg", mono ? "font-mono" : ""].join(" ")}>{value}</span>
    </div>
  );
}

function ProofEventBadge({ eventType, status }: { eventType: string; status: string }) {
  const isBlocked = eventType.includes("blocked") || eventType.includes("failed");
  const isOk = status === "ready" || eventType.includes("synthesized") || eventType.includes("transcribed") || eventType.includes("saved");
  const color = isBlocked ? "bg-accent-red/15 text-accent-red" : isOk ? "bg-accent-green/15 text-accent-green" : "bg-accent-amber/15 text-accent-amber";
  return (
    <span className={["inline-flex shrink-0 items-center justify-center rounded px-1.5 py-0.5 text-[10px] font-semibold", color].join(" ")}>
      {isBlocked ? "FAIL" : isOk ? "OK" : "WARN"}
    </span>
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

function formatTs(ts: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString(undefined, { dateStyle: "short", timeStyle: "medium" });
  } catch {
    return ts;
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
