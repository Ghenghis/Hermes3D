/**
 * TranscriptHistorySubtab — past STT transcripts surfaced from the backend
 * `/api/voice/transcripts` endpoint.
 *
 * Honesty:
 *   - When the backend API is unreachable (e.g. no Hermes3D bridge), we
 *     surface the error message verbatim. We never fabricate transcript
 *     rows.
 *   - Recording playback is backend-proxied; no audio device access from
 *     the frontend. If the recording fetch fails, playback resets to idle.
 *
 * Cross-project pattern: chat-app transcript surfaces (Slack/Discord)
 * follow the same "list of utterances + detail pane + audio playback"
 * layout, with audio bytes streamed by a server that holds the keys.
 */
import { ChevronRight, Clock, Mic, MicOff, Pause, Play, RefreshCw, Square, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { adapters } from "../../api/adapters";
import type { VoiceTranscript } from "../../types/voice";

type PlaybackState = "idle" | "loading" | "playing" | "paused";

export function TranscriptHistorySubtab() {
  const [transcripts, setTranscripts] = useState<VoiceTranscript[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<VoiceTranscript | null>(null);

  // Playback state — recordings are streamed from the backend.
  const [playbackState, setPlaybackState] = useState<PlaybackState>("idle");
  const [playbackRecordingId, setPlaybackRecordingId] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    void load();
    return () => {
      // Stop any in-flight audio on unmount.
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.src = "";
      }
      audioRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const items = await adapters.getVoiceTranscripts(50);
      setTranscripts(items);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function playRecording(recordingId: string) {
    if (playbackRecordingId === recordingId && playbackState === "playing") {
      audioRef.current?.pause();
      setPlaybackState("paused");
      return;
    }
    if (playbackRecordingId === recordingId && playbackState === "paused") {
      void audioRef.current?.play().catch(() => undefined);
      setPlaybackState("playing");
      return;
    }
    // Stop any existing audio before starting a new recording.
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    setPlaybackRecordingId(recordingId);
    setPlaybackState("loading");
    const url = adapters.getVoiceRecordingUrl(recordingId);
    const audio = new Audio(url);
    audio.muted = muted;
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
  }

  function stopPlayback() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    setPlaybackState("idle");
    setPlaybackRecordingId(null);
  }

  function toggleMute() {
    setMuted((current) => {
      const next = !current;
      if (audioRef.current) {
        audioRef.current.muted = next;
      }
      return next;
    });
  }

  return (
    <section
      data-testid="voice-transcript-history-subtab"
      className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_minmax(0,1fr)] rounded-card border border-border bg-surface"
    >
      <header className="flex items-center justify-between border-b border-border p-3">
        <div>
          <h2 className="text-[13px] font-semibold text-fg">Transcript History</h2>
          <p className="mt-0.5 text-[11px] text-muted">
            STT interactions stored by the backend, newest first. Audio playback is proxied through
            the local Hermes3D bridge — no API keys are exposed to the browser.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {playbackState !== "idle" && (
            <div className="flex items-center gap-1 rounded border border-accent-cyan/40 bg-accent-cyan/10 px-2 py-1">
              <span className="max-w-24 truncate font-mono text-[10px] text-accent-cyan">
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
            data-testid="voice-transcript-history-refresh"
            title="Refresh transcript history"
            onClick={() => void load()}
            disabled={loading}
            className="rounded border border-border p-1.5 text-muted hover:text-fg disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </header>

      <div className="grid min-h-0 gap-2 p-3 lg:grid-cols-[minmax(0,1fr)_22rem]">
        {/* Transcript list */}
        <div className="min-h-0 overflow-auto rounded border border-border bg-bg/40">
          {error && (
            <div
              data-testid="voice-transcript-history-error"
              className="flex items-center gap-2 border-b border-accent-red/40 bg-accent-red/10 p-3 text-xs text-accent-red"
            >
              <MicOff size={14} className="shrink-0" />
              <span>Blocked: {error}</span>
            </div>
          )}
          {!error && transcripts.length === 0 && !loading && (
            <div
              data-testid="voice-transcript-history-empty"
              className="flex h-full min-h-[180px] flex-col items-center justify-center gap-2 p-4 text-center text-xs text-muted"
            >
              <Clock size={22} />
              <div className="font-semibold text-fg">No transcripts yet</div>
              <div>STT interactions appear here once the backend has processed audio.</div>
            </div>
          )}
          {transcripts.map((tr) => (
            <button
              key={tr.id}
              type="button"
              data-testid={`voice-transcript-row-${tr.id}`}
              onClick={() => setSelected(tr)}
              className={[
                "w-full border-b border-border/60 px-3 py-2 text-left last:border-0 hover:bg-surface2/60",
                selected?.id === tr.id ? "bg-accent-cyan/10" : "",
              ].join(" ")}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={[
                    "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold",
                    tr.status === "ready"
                      ? "bg-accent-green/15 text-accent-green"
                      : "bg-accent-amber/15 text-accent-amber",
                  ].join(" ")}
                >
                  {tr.status === "ready" ? <Mic size={10} /> : <MicOff size={10} />}
                  {tr.status}
                </span>
                <span className="font-mono text-[10px] text-muted">{formatTs(tr.tsUtc)}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-[11px] text-fg">
                {tr.transcript || <span className="italic text-muted">(no transcript text)</span>}
              </p>
              <div className="mt-0.5 flex gap-2 text-[10px] text-muted">
                {tr.locale && <span>{tr.locale}</span>}
                {tr.phraseCount !== undefined && (
                  <span>
                    {tr.phraseCount} phrase{tr.phraseCount !== 1 ? "s" : ""}
                  </span>
                )}
                {tr.bytes !== undefined && <span>{formatBytes(tr.bytes)}</span>}
              </div>
            </button>
          ))}
        </div>

        {/* Detail pane */}
        <div className="flex min-h-0 flex-col gap-2 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
          {selected ? (
            <>
              <div className="flex items-center gap-2 font-semibold text-fg">
                <Mic size={14} className="text-accent-cyan" />
                Transcript Detail
              </div>
              <div className="grid gap-1 text-[11px]">
                <Row label="ID" value={selected.id} mono />
                <Row label="Status" value={selected.status} />
                <Row label="Locale" value={selected.locale || "—"} />
                <Row label="Provider" value={selected.provider || "—"} />
                {selected.phraseCount !== undefined && (
                  <Row label="Phrases" value={String(selected.phraseCount)} />
                )}
                {selected.bytes !== undefined && (
                  <Row label="Audio size" value={formatBytes(selected.bytes)} />
                )}
                <Row label="Timestamp" value={selected.tsUtc} />
                <Row label="Proof event" value={selected.proofEventId} mono />
              </div>
              {selected.transcript && (
                <div className="mt-1 rounded border border-border bg-bg p-2">
                  <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Transcript
                  </div>
                  <p className="whitespace-pre-wrap text-[12px] leading-relaxed text-fg">
                    {selected.transcript}
                  </p>
                </div>
              )}
              <div className="mt-auto rounded border border-border bg-surface p-2">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Recording Playback
                  </div>
                  <button
                    type="button"
                    data-testid="voice-transcript-history-mute"
                    onClick={toggleMute}
                    title={muted ? "Audio muted — text is always visible. Click to unmute." : "Mute audio."}
                    className={[
                      "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px]",
                      muted
                        ? "border-accent-amber/60 bg-accent-amber/10 text-accent-amber"
                        : "border-border text-muted hover:text-fg",
                    ].join(" ")}
                  >
                    {muted ? <VolumeX size={11} /> : <Volume2 size={11} />}
                    {muted ? "Muted" : "Sound on"}
                  </button>
                </div>
                <p className="mb-2 text-[10px] text-muted">
                  Audio is streamed from the local backend. Mute suppresses audio output but never
                  hides the transcript text above.
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    data-testid="voice-transcript-history-play"
                    disabled={playbackState === "loading"}
                    onClick={() => playRecording(selected.proofEventId)}
                    className={[
                      "inline-flex flex-1 items-center justify-center gap-1.5 rounded px-2 py-1.5 text-xs font-medium",
                      playbackState === "playing" && playbackRecordingId === selected.proofEventId
                        ? "border border-accent-amber/40 bg-accent-amber/20 text-accent-amber"
                        : "bg-accent-cyan/90 text-bg disabled:cursor-not-allowed disabled:opacity-50",
                    ].join(" ")}
                  >
                    {playbackState === "loading" && playbackRecordingId === selected.proofEventId ? (
                      <>
                        <RefreshCw size={12} className="animate-spin" /> Buffering
                      </>
                    ) : playbackState === "playing" && playbackRecordingId === selected.proofEventId ? (
                      <>
                        <Pause size={12} /> Pause
                      </>
                    ) : playbackState === "paused" && playbackRecordingId === selected.proofEventId ? (
                      <>
                        <Play size={12} /> Resume
                      </>
                    ) : (
                      <>
                        <Play size={12} /> Play Recording
                      </>
                    )}
                  </button>
                  {playbackRecordingId === selected.proofEventId && playbackState !== "idle" && (
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
