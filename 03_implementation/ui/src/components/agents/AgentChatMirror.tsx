import { Bot, ChevronDown, ChevronUp, ClipboardCheck, FileSearch, Mic, MicOff, Paperclip, Send, ShieldCheck, Trash2, Volume2, VolumeX, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { adapters } from "../../api/adapters";
import { useStore } from "../../app/store";
import type { Agent } from "../../types/agent";
import type { VoiceAgent } from "../../types/voice";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

type AgentMessage = {
  id: string;
  persona_id: string;
  role: "user" | "assistant" | "system";
  message_type: string;
  content: string;
  action_id: string | null;
  created_at: string;
};

type AgentAttachment = {
  id: string;
  label: string;
  file_size: number;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionEventLike = {
  results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }>;
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const QUICK_PROMPTS = [
  {
    id: "build-plate",
    label: "Build plate",
    icon: ClipboardCheck,
    prompt: "Check the visible printer build plates from Observe before any next print. Tell me which plates look clear, which need removal, and what proof you used.",
  },
  {
    id: "attached-file",
    label: "Attached file",
    icon: FileSearch,
    prompt: "Review the attached Hermes3D artifact. Identify file type, print/model risks, required slicer or repair steps, and the safest next action.",
  },
  {
    id: "safe-print",
    label: "Safe print",
    icon: ShieldCheck,
    prompt: "Plan a safe print using current printer locks and live status. Do not use S1 for movement, upload, or testing. Require approval and proof gates before print start.",
  },
] as const;

export function AgentChatMirror() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [voiceAgents, setVoiceAgents] = useState<VoiceAgent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("print-safety-agent");
  const [history, setHistory] = useState<AgentMessage[]>([]);
  const [attachments, setAttachments] = useState<AgentAttachment[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [listening, setListening] = useState(false);
  const [recording, setRecording] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [speakReplies, setSpeakReplies] = useState(true);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [status, setStatus] = useState("Loading Hermes agents.");
  const [height, setHeight] = useState<"compact" | "normal" | "tall">("normal");
  const [activeSurface, setActiveSurface] = useState(window.location.hash || "#dashboard");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const selectedAgent = useMemo(() => agents.find((agent) => agent.id === selectedAgentId) ?? agents[0] ?? null, [agents, selectedAgentId]);
  const selectedVoice = useMemo(() => voiceAgents.find((agent) => agent.id === selectedAgent?.id) ?? null, [selectedAgent?.id, voiceAgents]);
  const speechSupported = getSpeechRecognitionConstructor() != null;
  const audioRecordingSupported = getAudioRecordingSupported();
  const micSupported = speechSupported || audioRecordingSupported;

  const loadHistory = useCallback(async (agentId: string) => {
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/agents/${encodeURIComponent(agentId)}/history`, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => []);
      setHistory(Array.isArray(payload) ? payload.map(parseAgentMessage).filter((item): item is AgentMessage => item != null) : []);
      setStatus(response.ok ? "Connected to local agent conversation history." : "Agent history endpoint returned an error.");
    } catch {
      setHistory([]);
      setStatus("Hermes agent backend is unreachable.");
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    void adapters.getAgents().then((rows) => {
      if (!mounted) {
        return;
      }
      setAgents(rows);
      const nextId = rows.some((agent) => agent.id === selectedAgentId) ? selectedAgentId : rows[0]?.id ?? selectedAgentId;
      setSelectedAgentId(nextId);
      void loadHistory(nextId);
    });
    return () => {
      mounted = false;
    };
  }, [loadHistory, selectedAgentId]);

  useEffect(() => {
    let mounted = true;
    void adapters.getVoiceAgents()
      .then((rows) => {
        if (mounted) {
          setVoiceAgents(rows);
        }
      })
      .catch(() => {
        if (mounted) {
          setVoiceAgents([]);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const updateSurface = () => setActiveSurface(window.location.hash || "#dashboard");
    window.addEventListener("hashchange", updateSurface);
    return () => window.removeEventListener("hashchange", updateSurface);
  }, []);

  const sendMessage = async () => {
    const message = draft.trim();
    const agentId = selectedAgent?.id;
    if (!agentId || (message.length === 0 && attachments.length === 0) || sending) {
      return;
    }
    setSending(true);
    setDraft("");
    const sentAttachments = attachments;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/agents/${encodeURIComponent(agentId)}/chat`, {
        method: "POST",
        headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          context: {
            source: "left_rail_chat_mirror",
            active_surface: window.location.hash || "#dashboard",
            attachments: sentAttachments.map((attachment) => ({
              id: attachment.id,
              label: attachment.label,
              file_size: attachment.file_size,
            })),
          },
        }),
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        // Extract the actual blocked reason from the response body (e.g. HTTP 401 from MiniMax/DeepSeek shows real reason)
        const errPayload: unknown = await response.json().catch(() => null);
        const errReason = agentBlockedReason(errPayload, response.status, response.statusText);
        setStatus(`Agent chat blocked: ${errReason}`);
        return;
      }
      const localUserMessage: AgentMessage = {
        id: `local-${Date.now()}`,
        persona_id: agentId,
        role: "user",
        message_type: "TEXT",
        content: formatUserMessage(message, sentAttachments),
        action_id: null,
        created_at: new Date().toISOString(),
      };
      setHistory((current) => [...current, localUserMessage]);
      setAttachments([]);
      const reply = await readFirstAgentReply(response.body, controller);
      if (reply) {
        setHistory((current) => [...current, reply]);
        setStatus("Agent reply received from local backend.");
        void speakAgentReply(agentId, reply.content);
      } else {
        setStatus("Agent chat stream opened but returned no reply before timeout.");
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setStatus("Agent chat stream closed after first reply or timeout.");
      } else {
        setStatus("Hermes agent chat API is unreachable.");
      }
    } finally {
      window.clearTimeout(timeout);
      setSending(false);
    }
  };

  const uploadFiles = async (files: FileList | File[] | null): Promise<boolean> => {
    const agentId = selectedAgent?.id;
    if (!agentId || !files || files.length === 0 || uploading) {
      return false;
    }
    setUploading(true);
    try {
      const uploaded: AgentAttachment[] = [];
      for (const file of Array.from(files)) {
        const result = await adapters.uploadAgentAttachment(agentId, file);
        uploaded.push({
          id: result.artifact.id,
          label: result.artifact.label ?? file.name,
          file_size: result.artifact.file_size,
        });
      }
      setAttachments((current) => [...current, ...uploaded].slice(-12));
      setStatus(`Attached ${uploaded.length} local Hermes3D artifact${uploaded.length === 1 ? "" : "s"} to the next message.`);
      return true;
    } catch (error) {
      setStatus(`Attachment blocked: ${error instanceof Error ? error.message : "upload failed"}`);
      return false;
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setUploading(false);
    }
  };

  const stopAudioTracks = () => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
  };

  const toggleMic = async () => {
    if (recording || listening) {
      recognitionRef.current?.stop();
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.stop();
      } else {
        stopAudioTracks();
      }
      setListening(false);
      setRecording(false);
      return;
    }
    let startedAudio = false;
    if (audioRecordingSupported) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = preferredAudioMimeType();
        const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        mediaStreamRef.current = stream;
        mediaRecorderRef.current = recorder;
        audioChunksRef.current = [];
        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };
        recorder.onerror = () => {
          setStatus("Mic recording blocked by the browser recorder.");
          setRecording(false);
          stopAudioTracks();
        };
        recorder.onstop = () => {
          const chunks = audioChunksRef.current;
          audioChunksRef.current = [];
          const type = mimeType || chunks[0]?.type || "audio/webm";
          stopAudioTracks();
          setRecording(false);
          if (chunks.length === 0) {
            setStatus("Mic recording stopped without captured audio.");
            return;
          }
          const file = new File(chunks, `voice-note-${new Date().toISOString().replace(/[:.]/g, "-")}.${audioExtension(type)}`, { type });
          void uploadFiles([file]).then((ok) => {
            if (ok) {
              setStatus("Voice note captured and attached as a local Hermes3D artifact.");
            }
          });
          void transcribeVoiceNote(file);
        };
        recorder.start();
        startedAudio = true;
        setRecording(true);
      } catch (error) {
        setStatus(`Mic recording blocked: ${error instanceof Error ? error.message : "browser media permission denied"}.`);
      }
    }
    const SpeechRecognition = getSpeechRecognitionConstructor();
    let startedSpeech = false;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";
      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0]?.transcript ?? "")
          .join(" ")
          .trim();
        if (transcript) {
          setDraft((current) => `${current}${current.trim().length > 0 ? " " : ""}${transcript}`.trimStart());
        }
      };
      recognition.onerror = (event) => {
        setStatus(`Mic dictation blocked: ${event.error ?? "browser speech recognition error"}.`);
        setListening(false);
      };
      recognition.onend = () => {
        setListening(false);
      };
      try {
        recognition.start();
        startedSpeech = true;
        setListening(true);
      } catch (error) {
        setStatus(`Mic dictation blocked: ${error instanceof Error ? error.message : "browser speech recognition could not start"}.`);
        setListening(false);
      }
    }
    if (startedAudio && startedSpeech) {
      setStatus("Recording voice note and listening for browser dictation. Permission stays in the browser.");
    } else if (startedAudio) {
      setStatus("Recording voice note for the selected Hermes agent.");
    } else if (startedSpeech) {
      setStatus("Listening through browser mic dictation. Permission stays in the browser.");
    } else {
      setStatus("Mic is unavailable or blocked in this browser. Type a message or attach a file.");
    }
  };

  const clearHistory = async () => {
    const agentId = selectedAgent?.id;
    if (!agentId) {
      return;
    }
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/agents/${encodeURIComponent(agentId)}/history`, {
        method: "DELETE",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!response.ok) {
        const payload: unknown = await response.json().catch(() => null);
        setStatus(`Could not clear agent history: ${agentSummary(payload, response.statusText)}.`);
        return;
      }
      setHistory([]);
      setStatus("Agent conversation history cleared in the local backend.");
    } catch {
      setStatus("Could not clear agent history; backend unreachable.");
    }
  };

  const speakAgentReply = async (agentId: string, content: string) => {
    const cleanContent = content.trim();
    if (!speakReplies || !cleanContent) {
      return;
    }
    const assignment = voiceAgents.find((agent) => agent.id === agentId);
    if (!assignment?.voice) {
      setStatus("Agent reply received. Voice playback blocked: no Azure voice assignment for this agent.");
      return;
    }
    setSpeaking(true);
    try {
      const result = await adapters.previewVoice(agentId, assignment.voice, cleanContent);
      if (!result.accepted || !result.audioBase64 || !result.mimeType) {
        setStatus(`Agent voice blocked: ${result.reason ?? result.status}.`);
        return;
      }
      const audio = new Audio(`data:${result.mimeType};base64,${result.audioBase64}`);
      await audio.play().catch(() => undefined);
      setStatus(`Agent reply spoken with ${assignment.voice}; proof ${result.proofEventId ?? "recorded"}.`);
    } catch {
      setStatus("Agent voice blocked: Azure TTS preview endpoint is unreachable.");
    } finally {
      setSpeaking(false);
    }
  };

  const transcribeVoiceNote = async (file: File) => {
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/voice/stt?locale=en-US`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": file.type || "application/octet-stream",
          "X-Hermes-Filename": file.name,
        },
        body: file,
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      const transcript = sttTranscript(payload);
      if (response.ok && transcript) {
        addPromptToDraft(`Voice note transcript:\n${transcript}`, setDraft);
        setStatus(`Azure STT transcript inserted; proof ${sttProof(payload) ?? "recorded"}.`);
        return;
      }
      setStatus(`Azure STT blocked: ${agentSummary(payload, response.statusText)}.`);
    } catch {
      setStatus("Azure STT endpoint is unreachable; voice note remains attached.");
    }
  };

  const decideAction = async (actionId: string, decision: "confirm" | "deny") => {
    const agentId = selectedAgent?.id;
    if (!agentId || actionBusy) {
      return;
    }
    setActionBusy(actionId);
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/agents/${encodeURIComponent(agentId)}/${decision}-action/${encodeURIComponent(actionId)}`, {
        method: "POST",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        setStatus(`Agent action ${decision} blocked: ${agentSummary(payload, response.statusText)}.`);
        return;
      }
      await loadHistory(agentId);
      setStatus(`Agent action ${decision === "confirm" ? "approved" : "denied"}: ${actionId}.`);
    } catch {
      setStatus(`Agent action ${decision} blocked: backend unreachable.`);
    } finally {
      setActionBusy(null);
    }
  };

  return (
    <section
      data-testid="agent-chat-mirror"
      onDragOver={(event) => {
        event.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragOver(false);
        void uploadFiles(event.dataTransfer.files);
      }}
      className={[
        "flex min-h-0 shrink-0 flex-col border-t bg-bg/50",
        dragOver ? "border-accent-cyan" : "border-border",
        heightClass(height),
      ].join(" ")}
    >
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border px-2 py-1.5">
        <div className="flex min-w-0 items-center gap-1.5">
          <Bot size={13} className="shrink-0 text-accent-cyan" />
          <span className="truncate text-[11px] font-semibold text-fg">Hermes Agents</span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button type="button" onClick={() => setHeight(nextHeight(height))} className="rounded border border-border p-1 text-muted hover:text-fg" title="Resize chat mirror">
            {height === "tall" ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
          </button>
          <button type="button" onClick={() => void clearHistory()} className="rounded border border-border p-1 text-muted hover:text-fg" title="Clear selected agent history">
            <Trash2 size={12} />
          </button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)_auto] gap-1.5 p-2">
        <select
          value={selectedAgent?.id ?? selectedAgentId}
          onChange={(event) => {
            setSelectedAgentId(event.currentTarget.value);
            void loadHistory(event.currentTarget.value);
          }}
          className="min-w-0 rounded border border-border bg-surface px-2 py-1 text-[11px] text-fg"
        >
          {agents.map((agent) => (
            <option key={agent.id} value={agent.id}>{agent.role}</option>
          ))}
          {agents.length === 0 && <option value={selectedAgentId}>Agents unavailable</option>}
        </select>

        <div className="min-h-[5rem] overflow-auto rounded border border-border bg-surface/70 p-1.5 text-[10px]">
          {/* Provider blocked banner: shown when chat is blocked due to 401/unavailable agent */}
          {agents.length === 0 && (
            <div className="mb-1.5 rounded border border-accent-amber/40 bg-accent-amber/10 px-2 py-1.5 text-accent-amber">
              <div className="font-semibold uppercase">Providers blocked</div>
              <div className="mt-0.5 text-muted">
                {status.toLowerCase().includes("blocked") || status.toLowerCase().includes("unreachable")
                  ? status
                  : "Agent roster is empty. Configure provider API keys in G:\\private\\.env to enable chat."}
              </div>
            </div>
          )}
          {history.slice(-8).map((message) => (
            <div key={message.id} className={`mb-1 rounded px-1.5 py-1 ${message.role === "user" ? "bg-blue-950/40 text-blue-100" : "bg-surface2 text-fg"}`}>
              <div className="mb-0.5 uppercase text-muted">{message.role}</div>
              <div className="whitespace-pre-wrap break-words">{message.content}</div>
              {message.action_id && (
                <div className="mt-1 flex gap-1">
                  <button
                    type="button"
                    disabled={actionBusy === message.action_id}
                    onClick={() => void decideAction(message.action_id as string, "confirm")}
                    className="rounded border border-green-500/50 px-1.5 py-0.5 text-[10px] text-green-300 disabled:opacity-50"
                    title={`Approve real pending Hermes action ${message.action_id}`}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={actionBusy === message.action_id}
                    onClick={() => void decideAction(message.action_id as string, "deny")}
                    className="rounded border border-amber-500/50 px-1.5 py-0.5 text-[10px] text-amber-300 disabled:opacity-50"
                    title={`Deny real pending Hermes action ${message.action_id}`}
                  >
                    Deny
                  </button>
                </div>
              )}
            </div>
          ))}
          {history.length === 0 && agents.length > 0 && <div className="flex h-full items-center justify-center text-center text-muted">No conversation history from the selected agent.</div>}
        </div>

        <div className="grid gap-1">
          <div className="max-h-8 overflow-hidden text-[10px] leading-snug text-muted">{status}</div>
          <div className="flex flex-wrap gap-1">
            <span className="rounded border border-border bg-surface/80 px-1.5 py-0.5 font-mono text-[10px] text-accent-cyan" title="Current Hermes3D surface context">
              {activeSurface}
            </span>
            <button
              type="button"
              onClick={() => setSpeakReplies((current) => !current)}
              className={[
                "inline-flex items-center gap-1 rounded border bg-surface/80 px-1.5 py-0.5 text-[10px]",
                speakReplies ? "border-accent-cyan/40 text-accent-cyan" : "border-border text-muted hover:text-fg",
              ].join(" ")}
              title={selectedVoice ? `Speak agent replies with ${selectedVoice.voice}` : "Speak agent replies with the selected Azure voice assignment"}
            >
              {speakReplies ? <Volume2 size={10} /> : <VolumeX size={10} />}
              {speaking ? "Speaking" : selectedVoice?.voice ? "Speak" : "Speak blocked"}
            </button>
            {QUICK_PROMPTS.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => addPromptToDraft(item.prompt, setDraft)}
                  className="inline-flex items-center gap-1 rounded border border-border bg-surface/80 px-1.5 py-0.5 text-[10px] text-muted hover:text-fg"
                  title={`Add ${item.label} prompt to message`}
                >
                  <Icon size={10} />
                  {item.label}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setActiveTabId("agents")}
              className="rounded border border-border bg-surface/80 px-1.5 py-0.5 text-[10px] text-muted hover:text-fg"
              title="Open full Agents dashboard"
            >
              Open Agents
            </button>
          </div>
          {attachments.length > 0 && (
            <div className="flex max-h-14 flex-wrap gap-1 overflow-auto rounded border border-border bg-surface/60 p-1">
              {attachments.map((attachment) => (
                <span key={attachment.id} className="inline-flex max-w-full items-center gap-1 rounded bg-surface2 px-1.5 py-0.5 text-[10px] text-fg">
                  <span className="truncate">{attachment.label}</span>
                  <span className="shrink-0 text-muted">{formatBytes(attachment.file_size)}</span>
                  <button
                    type="button"
                    onClick={() => setAttachments((current) => current.filter((item) => item.id !== attachment.id))}
                    className="shrink-0 text-muted hover:text-fg"
                    title={`Remove ${attachment.label}`}
                  >
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-1">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".stl,.3mf,.obj,.amf,.ply,.glb,.gltf,.fbx,.dae,.off,.mesh,.step,.stp,.iges,.igs,.scad,.blend,.gcode,.gco,.nc,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.svg,.json,.toml,.yaml,.yml,.ini,.cfg,.conf,.csv,.log,.txt,.md,.pdf,.docx,.py,.js,.mjs,.ts,.tsx,.css,.html,.zip,.wav,.mp3,.m4a,.webm,.ogg,.flac"
              onChange={(event) => void uploadFiles(event.currentTarget.files)}
              className="hidden"
            />
            <button
              type="button"
              disabled={!selectedAgent || uploading}
              onClick={() => fileInputRef.current?.click()}
              className="rounded border border-border px-2 text-fg disabled:cursor-not-allowed disabled:opacity-50"
              title="Attach Hermes3D model, image, G-code, CAD, audio, config, or project file"
            >
              <Paperclip size={13} />
            </button>
            <button
              type="button"
              disabled={!micSupported}
              onClick={() => void toggleMic()}
              className={[
                "rounded border px-2 text-fg disabled:cursor-not-allowed disabled:opacity-50",
                recording || listening ? "border-accent-cyan bg-accent-cyan/10 text-accent-cyan" : "border-border",
              ].join(" ")}
              title={micSupported ? "Record a voice note and dictate with browser mic" : "Mic recording and dictation are unavailable in this browser"}
            >
              {recording || listening ? <MicOff size={13} /> : <Mic size={13} />}
            </button>
            <textarea
              value={draft}
              rows={2}
              onChange={(event) => setDraft(event.currentTarget.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                  void sendMessage();
                }
              }}
              aria-label="Message selected Hermes agent"
              className="min-w-0 flex-1 resize-none rounded border border-border bg-surface px-2 py-1 text-[11px] text-fg outline-none focus:border-accent-cyan"
            />
            <button
              type="button"
              disabled={!selectedAgent || (draft.trim().length === 0 && attachments.length === 0) || sending}
              onClick={() => void sendMessage()}
              className="rounded border border-border px-2 text-fg disabled:cursor-not-allowed disabled:opacity-50"
              title="Send to selected Hermes agent"
            >
              <Send size={13} />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

async function readFirstAgentReply(body: ReadableStream<Uint8Array>, controller: AbortController): Promise<AgentMessage | null> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let streamedContent = "";
  let streamedId = `stream-${Date.now()}`;
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      return streamedContent ? streamMessage(streamedId, streamedContent) : null;
    }
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const line = chunk.split("\n").find((item) => item.startsWith("data: "));
      if (!line) {
        continue;
      }
      const data = line.slice(6).trim();
      if (data === "[DONE]") {
        return streamedContent ? streamMessage(streamedId, streamedContent) : null;
      }
      let payload: unknown;
      try {
        payload = JSON.parse(data) as unknown;
      } catch {
        continue;
      }
      const parsed = parseAgentMessage(payload);
      if (parsed) {
        controller.abort();
        return parsed;
      }
      const content = openAiContent(payload);
      if (content) {
        if (isRecord(payload) && typeof payload.id === "string") {
          streamedId = payload.id;
        }
        streamedContent += content;
      }
    }
  }
}

function parseAgentMessage(value: unknown): AgentMessage | null {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.persona_id !== "string" || typeof value.content !== "string") {
    return null;
  }
  const role = value.role === "user" || value.role === "assistant" || value.role === "system" ? value.role : "assistant";
  return {
    id: value.id,
    persona_id: value.persona_id,
    role,
    message_type: typeof value.message_type === "string" ? value.message_type : "TEXT",
    content: value.content,
    action_id: typeof value.action_id === "string" && value.action_id.length > 0 ? value.action_id : null,
    created_at: typeof value.created_at === "string" ? value.created_at : "",
  };
}

function agentSummary(value: unknown, fallback: string): string {
  if (!isRecord(value)) {
    return fallback || "backend returned an error";
  }
  if (isRecord(value.detail)) {
    return String(value.detail.reason ?? value.detail.status ?? fallback);
  }
  if (typeof value.detail === "string") {
    return value.detail;
  }
  return String(value.reason ?? value.error ?? fallback);
}

function sttTranscript(value: unknown): string {
  if (!isRecord(value) || typeof value.transcript !== "string") {
    return "";
  }
  return value.transcript.trim();
}

function sttProof(value: unknown): string | null {
  if (!isRecord(value) || typeof value.proof_event_id !== "string") {
    return null;
  }
  return value.proof_event_id;
}

function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  const candidate = (window as Window & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }).SpeechRecognition ?? (window as Window & {
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }).webkitSpeechRecognition;
  return candidate ?? null;
}

function getAudioRecordingSupported(): boolean {
  return typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia) && typeof MediaRecorder !== "undefined";
}

function preferredAudioMimeType(): string {
  const options = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4", "audio/wav"];
  return options.find((item) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(item)) ?? "";
}

function audioExtension(type: string): string {
  if (type.includes("wav")) {
    return "wav";
  }
  if (type.includes("ogg")) {
    return "ogg";
  }
  if (type.includes("mp4") || type.includes("m4a")) {
    return "m4a";
  }
  return "webm";
}

function openAiContent(payload: unknown): string {
  if (!isRecord(payload) || !Array.isArray(payload.choices)) {
    return "";
  }
  return payload.choices.map((choice) => {
    if (!isRecord(choice)) {
      return "";
    }
    const delta = choice.delta;
    if (isRecord(delta) && typeof delta.content === "string") {
      return delta.content;
    }
    const message = choice.message;
    if (isRecord(message) && typeof message.content === "string") {
      return message.content;
    }
    return "";
  }).join("");
}

function streamMessage(id: string, content: string): AgentMessage {
  return {
    id,
    persona_id: "runtime",
    role: "assistant",
    message_type: "RUNTIME_STREAM",
    content,
    action_id: null,
    created_at: new Date().toISOString(),
  };
}

function addPromptToDraft(prompt: string, setDraft: (updater: (current: string) => string) => void) {
  setDraft((current) => {
    const trimmed = current.trim();
    return trimmed.length > 0 ? `${trimmed}\n\n${prompt}` : prompt;
  });
}

function formatUserMessage(message: string, attachments: AgentAttachment[]): string {
  const text = message || "Attached Hermes3D artifact(s).";
  if (attachments.length === 0) {
    return text;
  }
  const lines = attachments.map((attachment) => `- ${attachment.label} (${formatBytes(attachment.file_size)}, artifact ${attachment.id})`);
  return `${text}\n\nAttachments:\n${lines.join("\n")}`;
}

function formatBytes(value: number): string {
  if (value >= 1024 * 1024) {
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (value >= 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${value} B`;
}

function heightClass(height: "compact" | "normal" | "tall"): string {
  if (height === "compact") {
    return "h-[12.5rem] max-h-[42vh]";
  }
  if (height === "tall") {
    return "h-[min(40rem,58vh)]";
  }
  return "h-[min(28rem,46vh)]";
}

function nextHeight(height: "compact" | "normal" | "tall"): "compact" | "normal" | "tall" {
  return height === "compact" ? "normal" : height === "normal" ? "tall" : "compact";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Extracts a human-readable blocked reason from a failed chat response payload.
 * Shows the real provider error (e.g. HTTP 401 from MiniMax or DeepSeek) rather
 * than just the HTTP status code.
 */
function agentBlockedReason(payload: unknown, status: number, statusText: string): string {
  if (isRecord(payload)) {
    // FastAPI detail field — may be string or object
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      return `${payload.detail} (HTTP ${status})`;
    }
    if (isRecord(payload.detail)) {
      const reason = payload.detail.reason ?? payload.detail.status ?? payload.detail.message;
      if (typeof reason === "string" && reason.length > 0) {
        return `${reason} (HTTP ${status})`;
      }
    }
    const reason = payload.reason ?? payload.error ?? payload.message ?? payload.status;
    if (typeof reason === "string" && reason.length > 0) {
      return `${reason} (HTTP ${status})`;
    }
    // Provider-specific: 401 typically means API key blocked
    if (status === 401) {
      return `Provider API key is not configured or was rejected (HTTP 401). Check G:\\private\\.env for the agent's provider credentials.`;
    }
  }
  return `HTTP ${status}${statusText ? ` ${statusText}` : ""}.`;
}
