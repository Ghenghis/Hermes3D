/**
 * VoiceBrowserSubtab — browser-side Web Speech API input + real-time transcript.
 *
 * Reference (official Mozilla):
 *   https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API
 *
 * Reference (cross-project): chat-app transcript pattern (Slack/Discord live
 * caption surfaces) — interim results render in a "ghost" line that is
 * replaced once a final result arrives.
 *
 * Honesty:
 *   - When the browser does not expose `SpeechRecognition` /
 *     `webkitSpeechRecognition` we render an honest blocked banner.
 *     We never fabricate transcripts.
 *   - Permission denied / start errors are surfaced as honest errors.
 *   - Recording state mirrors the browser; there is no fake "recording"
 *     state when the API is unavailable.
 */
import { Mic, MicOff, RefreshCw, Save, ShieldAlert, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { adapters } from "../../api/adapters";

// ── Web Speech API typings ────────────────────────────────────────────────
// The DOM lib does not ship these types in lib.dom.d.ts (the spec is still
// "Living Standard"), so we declare the minimal surface we use. Vendor
// prefix `webkitSpeechRecognition` is honoured at runtime for Chromium/WebKit.

type SpeechRecognitionAlternative = { transcript: string; confidence: number };
type SpeechRecognitionResult = {
  isFinal: boolean;
  length: number;
  [index: number]: SpeechRecognitionAlternative;
};
type SpeechRecognitionResultList = {
  length: number;
  [index: number]: SpeechRecognitionResult;
};

interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message?: string;
}

interface SpeechRecognitionInstance extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionInstance;

interface SpeechWindow extends Window {
  SpeechRecognition?: SpeechRecognitionCtor;
  webkitSpeechRecognition?: SpeechRecognitionCtor;
}

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as SpeechWindow;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

// ── Locale list (subset; same locales as the existing Voice tab) ─────────
const RECOGNITION_LOCALES = [
  { value: "en-US", label: "English (US)" },
  { value: "en-GB", label: "English (UK)" },
  { value: "en-AU", label: "English (AU)" },
  { value: "en-CA", label: "English (CA)" },
  { value: "en-IN", label: "English (IN)" },
  { value: "es-ES", label: "Spanish (ES)" },
  { value: "fr-FR", label: "French (FR)" },
  { value: "de-DE", label: "German (DE)" },
  { value: "it-IT", label: "Italian (IT)" },
  { value: "ja-JP", label: "Japanese (JP)" },
  { value: "zh-CN", label: "Chinese (CN)" },
] as const;

export function VoiceBrowserSubtab() {
  const ctor = useMemo(getSpeechRecognitionCtor, []);
  const supported = ctor !== null;

  const [listening, setListening] = useState(false);
  const [locale, setLocale] = useState<string>("en-US");
  const [finalTranscript, setFinalTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [autoSent, setAutoSent] = useState(false);

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);

  // Tear down on unmount.
  useEffect(() => {
    return () => {
      const rec = recognitionRef.current;
      if (rec) {
        rec.onresult = null;
        rec.onerror = null;
        rec.onend = null;
        rec.onstart = null;
        try {
          rec.abort();
        } catch {
          // ignore — recognizer may already be stopped
        }
        recognitionRef.current = null;
      }
    };
  }, []);

  const startListening = () => {
    if (!supported || !ctor) {
      setError("Voice input not supported in this browser. Use a recent Chromium-based browser or Edge.");
      return;
    }
    setError(null);
    setSavedMessage(null);
    setAutoSent(false);

    let rec: SpeechRecognitionInstance;
    try {
      rec = new ctor();
    } catch (err) {
      setError(`Failed to construct SpeechRecognition: ${err instanceof Error ? err.message : String(err)}`);
      return;
    }

    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    rec.lang = locale;

    rec.onstart = () => {
      setListening(true);
    };
    rec.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let finals = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const alt = result[0];
        if (!alt) continue;
        if (result.isFinal) {
          finals += alt.transcript;
        } else {
          interim += alt.transcript;
        }
      }
      if (finals) {
        setFinalTranscript((current) => (current ? `${current} ${finals}` : finals).trim());
      }
      setInterimTranscript(interim);
    };
    rec.onerror = (event: SpeechRecognitionErrorEvent) => {
      const code = event.error;
      const friendly =
        code === "not-allowed"
          ? "Microphone permission denied by the browser. Grant permission and try again."
          : code === "no-speech"
            ? "No speech detected — the recognizer timed out without input."
            : code === "audio-capture"
              ? "No microphone was detected on this device."
              : code === "network"
                ? "Speech recognition network error — check connectivity."
                : `SpeechRecognition error: ${code}${event.message ? ` (${event.message})` : ""}`;
      setError(friendly);
    };
    rec.onend = () => {
      setListening(false);
      setInterimTranscript("");
    };

    try {
      rec.start();
    } catch (err) {
      // Calling start() while a recognizer is already running throws.
      setError(`Could not start recognizer: ${err instanceof Error ? err.message : String(err)}`);
      setListening(false);
      return;
    }
    recognitionRef.current = rec;
  };

  const stopListening = () => {
    const rec = recognitionRef.current;
    if (!rec) {
      setListening(false);
      return;
    }
    try {
      rec.stop();
    } catch {
      // ignore — already stopped
    }
  };

  const clearTranscript = () => {
    setFinalTranscript("");
    setInterimTranscript("");
    setSavedMessage(null);
    setAutoSent(false);
  };

  const sendToBackend = async () => {
    const text = finalTranscript.trim();
    if (!text) {
      setError("No final transcript text to send.");
      return;
    }
    setError(null);
    try {
      await adapters.emitProofEvent("voice.browser.transcript.submitted", {
        transcript: text,
        locale,
        provider: "web-speech-api",
        source: "browser",
      });
      setSavedMessage(`Submitted ${text.length} chars to proof ledger (${locale}).`);
      setAutoSent(true);
    } catch (err) {
      setError(`Blocked: backend rejected transcript proof — ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────
  if (!supported) {
    return (
      <section
        data-testid="voice-browser-unsupported"
        className="grid min-h-[320px] place-items-center rounded-card border border-border bg-surface p-6"
      >
        <div className="max-w-xl text-center">
          <ShieldAlert className="mx-auto mb-3 text-accent-amber" size={32} />
          <h3 className="text-sm font-semibold text-fg">Voice input not supported in this browser</h3>
          <p className="mt-2 text-xs text-muted">
            The Web Speech API (<code className="font-mono">SpeechRecognition</code>) is unavailable in
            this user-agent. We refuse to fabricate transcripts. Use a recent Chromium-based browser
            (Chrome, Edge, Brave) or rely on the backend Azure STT pipeline.
          </p>
          <p className="mt-2 text-[11px] text-muted">
            Reference:{" "}
            <a
              className="text-accent-cyan underline"
              href="https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API"
              target="_blank"
              rel="noreferrer noopener"
            >
              MDN — Web Speech API
            </a>
          </p>
        </div>
      </section>
    );
  }

  const hasFinal = finalTranscript.length > 0;

  return (
    <section
      data-testid="voice-browser-subtab"
      className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_minmax(0,1fr)] rounded-card border border-border bg-surface"
    >
      <header className="grid gap-2 border-b border-border p-3 lg:grid-cols-[1fr_auto]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-[13px] font-semibold text-fg">Browser Voice Input</h2>
            <span
              className={[
                "rounded-chip px-2 py-0.5 text-[10px] font-semibold",
                listening
                  ? "bg-accent-red/15 text-accent-red"
                  : "bg-accent-green/15 text-accent-green",
              ].join(" ")}
            >
              {listening ? "LISTENING" : "IDLE"}
            </span>
            <span className="rounded-chip border border-border bg-bg px-2 py-0.5 text-[10px] text-muted">
              Web Speech API · client-side
            </span>
          </div>
          <p className="mt-1 text-[11px] text-muted">
            Microphone access is requested by the browser. Recognition runs locally in the user-agent;
            no audio is uploaded by the frontend. Final transcripts may be submitted to the backend
            proof ledger on demand.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            data-testid="voice-browser-locale"
            disabled={listening}
            value={locale}
            onChange={(event) => setLocale(event.target.value)}
            className="rounded border border-border bg-bg px-2 py-1 text-xs text-fg disabled:opacity-50"
          >
            {RECOGNITION_LOCALES.map((row) => (
              <option key={row.value} value={row.value}>
                {row.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="grid min-h-0 gap-3 p-3 lg:grid-cols-[minmax(0,1fr)_18rem]">
        {/* Live transcript panel */}
        <div className="flex min-h-0 flex-col gap-2 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-muted">
            <Mic size={11} className="text-accent-cyan" /> Real-time transcript
          </div>
          <div
            data-testid="voice-browser-transcript"
            className="min-h-[10rem] flex-1 rounded border border-border bg-bg p-3 text-[13px] leading-relaxed text-fg"
          >
            {hasFinal ? (
              <span data-testid="voice-browser-final">{finalTranscript}</span>
            ) : (
              <span className="text-muted italic">
                {listening
                  ? "Listening… speak into your microphone."
                  : "Click Start to begin browser-side voice capture."}
              </span>
            )}
            {interimTranscript && (
              <>
                {hasFinal ? " " : ""}
                <span
                  data-testid="voice-browser-interim"
                  className="text-muted italic"
                  aria-live="polite"
                >
                  {interimTranscript}
                </span>
              </>
            )}
          </div>
          {error && (
            <div
              data-testid="voice-browser-error"
              role="alert"
              className="rounded border border-accent-red/40 bg-accent-red/10 p-2 text-[11px] text-accent-red"
            >
              {error}
            </div>
          )}
          {savedMessage && (
            <div
              data-testid="voice-browser-saved"
              className="rounded border border-accent-green/40 bg-accent-green/10 p-2 text-[11px] text-accent-green"
            >
              {savedMessage}
            </div>
          )}
        </div>

        {/* Controls panel */}
        <div className="flex min-h-0 flex-col gap-2 overflow-auto rounded border border-border bg-bg/40 p-3 text-xs">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">Controls</div>
          {!listening ? (
            <button
              type="button"
              data-testid="voice-browser-start"
              onClick={startListening}
              className="inline-flex items-center justify-center gap-1.5 rounded bg-accent-cyan px-2 py-1.5 font-semibold text-bg hover:opacity-90"
            >
              <Mic size={13} />
              Start listening
            </button>
          ) : (
            <button
              type="button"
              data-testid="voice-browser-stop"
              onClick={stopListening}
              className="inline-flex items-center justify-center gap-1.5 rounded bg-accent-red px-2 py-1.5 font-semibold text-bg hover:opacity-90"
            >
              <MicOff size={13} />
              Stop listening
            </button>
          )}
          <button
            type="button"
            data-testid="voice-browser-submit"
            disabled={!hasFinal || autoSent}
            onClick={() => void sendToBackend()}
            className="inline-flex items-center justify-center gap-1.5 rounded border border-border px-2 py-1.5 text-fg hover:border-accent-blue disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Save size={13} />
            {autoSent ? "Submitted" : "Submit to ledger"}
          </button>
          <button
            type="button"
            data-testid="voice-browser-clear"
            disabled={!hasFinal && !interimTranscript && !savedMessage && !error}
            onClick={clearTranscript}
            className="inline-flex items-center justify-center gap-1.5 rounded border border-border px-2 py-1.5 text-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Trash2 size={13} />
            Clear
          </button>
          <button
            type="button"
            data-testid="voice-browser-reset"
            disabled={listening}
            onClick={() => {
              const rec = recognitionRef.current;
              if (rec) {
                try {
                  rec.abort();
                } catch {
                  // ignore
                }
              }
              recognitionRef.current = null;
              setListening(false);
              setInterimTranscript("");
              setError(null);
            }}
            className="inline-flex items-center justify-center gap-1.5 rounded border border-border px-2 py-1.5 text-muted hover:text-fg disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw size={13} />
            Reset recognizer
          </button>
          <p className="mt-1 text-[10px] text-muted">
            Final results are saved to the proof ledger only when you click Submit. We never auto-send
            audio or transcripts.
          </p>
        </div>
      </div>
    </section>
  );
}
