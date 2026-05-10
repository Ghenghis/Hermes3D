/**
 * Voice tab — host that delegates to URL-addressable subtabs.
 *
 * Routing (URL hash):
 *   - `#voice`                       → default (browser)
 *   - `#voice/browser`               → VoiceBrowserSubtab (Web Speech API)
 *   - `#voice/transcript-history`    → TranscriptHistorySubtab
 *   - `#voice/proof-review`          → ProofReviewSubtab
 *
 * The left rail keeps the existing Hermes voice agent picker so the
 * agent context survives when navigating between subtabs (agent rail
 * state lives in the host).
 *
 * Voice catalog + provider state live in this host so the rail can
 * render Azure status even when the active subtab is the Web Speech
 * API browser surface.
 */
import { Mic, RefreshCw, Shield, Volume2 } from "lucide-react";
import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { adapters } from "../api/adapters";
import { ResizablePane } from "../components/layout/ResizablePane";
import { ProofReviewSubtab } from "../components/voice/ProofReviewSubtab";
import { TranscriptHistorySubtab } from "../components/voice/TranscriptHistorySubtab";
import { VoiceBrowserSubtab } from "../components/voice/VoiceBrowserSubtab";
import { voiceSubtabFromHash, type VoiceSubtabKey } from "../app/store";
import type { VoiceAgent, VoiceCatalog, VoiceProvider } from "../types/voice";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const VOICE_HASH_PREFIX = "voice";
const SUBTABS = [
  { id: "browser", hash: "browser", label: "Browser Voice", icon: Volume2 },
  { id: "transcript-history", hash: "transcript-history", label: "Transcript History", icon: Mic },
  { id: "proof-review", hash: "proof-review", label: "Proof Review", icon: Shield },
] as const;
type SubtabId = VoiceSubtabKey;

function parseVoiceSub(hash: string): SubtabId {
  // Generic subtab helper (W15-A17/A18) — case-insensitive match against VOICE_SUBTAB_KEYS.
  return voiceSubtabFromHash(hash) ?? "browser";
}

export function VoiceTab() {
  const [activeSub, setActiveSub] = useState<SubtabId>(() =>
    typeof window === "undefined" ? "browser" : parseVoiceSub(window.location.hash),
  );

  // Agent rail state — shared across subtabs.
  const [agents, setAgents] = useState<VoiceAgent[]>([]);
  const [providers, setProviders] = useState<VoiceProvider[]>([]);
  const [catalog, setCatalog] = useState<VoiceCatalog | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string>("");
  const [selectedVoiceId, setSelectedVoiceId] = useState<string>("");
  const [railMessage, setRailMessage] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => setActiveSub(parseVoiceSub(window.location.hash));
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  useEffect(() => {
    void loadAgents(setAgents, setSelectedAgentId, setSelectedVoiceId);
    void loadProviders(setProviders, setRailMessage);
    void loadCatalog("en", setCatalog, setSelectedVoiceId, setRailMessage);
  }, []);

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? agents[0] ?? null;
  const provider = providers.find((item) => item.id === "azure") ?? null;

  const navigate = (hash: string) => {
    if (typeof window !== "undefined") {
      window.location.hash = `${VOICE_HASH_PREFIX}/${hash}`;
    }
  };

  return (
    <div
      data-testid="voice-root"
      data-active-subtab={activeSub}
      className="flex h-[calc(100vh-5rem)] min-h-0 min-w-0 flex-col gap-2.5 lg:flex-row"
    >
      <ResizablePane
        storageKey="h3d.voice.agentRail.width"
        defaultWidth={300}
        minWidth={240}
        maxWidth={520}
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
              void loadProviders(setProviders, setRailMessage);
              void loadCatalog("en", setCatalog, setSelectedVoiceId, setRailMessage);
            }}
            className="rounded border border-border p-1.5 text-muted hover:text-fg"
          >
            <RefreshCw size={14} />
          </button>
        </header>
        <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)_auto] gap-2 p-3">
          <ProviderStatus provider={provider} catalog={catalog} />
          <div className="min-h-0 overflow-auto rounded border border-border bg-bg/40">
            {agents.length === 0 ? (
              <div className="p-3 text-[11px] text-muted">
                {railMessage ?? "No voice agents returned by the backend."}
              </div>
            ) : (
              agents.map((agent) => (
                <button
                  type="button"
                  key={agent.id}
                  onClick={() => {
                    setSelectedAgentId(agent.id);
                    setSelectedVoiceId(agent.voice);
                  }}
                  className={[
                    "flex w-full flex-col gap-1 border-b border-border/60 px-3 py-2 text-left text-xs last:border-0 hover:bg-surface2/60",
                    agent.id === selectedAgentId ? "bg-accent-cyan/10 text-fg" : "text-muted",
                  ].join(" ")}
                >
                  <span className="font-semibold text-fg">{agent.name}</span>
                  <span className="truncate font-mono text-[10px]">{agent.voice}</span>
                </button>
              ))
            )}
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
        <nav
          data-testid="voice-subtab-nav"
          role="tablist"
          aria-label="Voice subtabs"
          className="flex gap-1 rounded-card border border-border bg-surface px-2 py-1.5"
        >
          {SUBTABS.map(({ id, hash, label, icon: Icon }) => {
            const selected = activeSub === id;
            return (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={selected}
                data-testid={`voice-subtab-${id}`}
                onClick={() => navigate(hash)}
                className={[
                  "inline-flex items-center gap-1.5 rounded px-3 py-1 text-xs font-medium transition-colors",
                  selected
                    ? "bg-accent-cyan/20 text-accent-cyan"
                    : "text-muted hover:text-fg",
                ].join(" ")}
              >
                <Icon size={13} />
                {label}
              </button>
            );
          })}
        </nav>

        {activeSub === "browser" && <VoiceBrowserSubtab />}
        {activeSub === "transcript-history" && <TranscriptHistorySubtab />}
        {activeSub === "proof-review" && <ProofReviewSubtab />}
      </div>
    </div>
  );
}

// ── Agent rail data loaders ───────────────────────────────────────────────

async function loadAgents(
  setAgents: (agents: VoiceAgent[]) => void,
  setSelectedAgentId: (id: string) => void,
  setSelectedVoiceId: (id: string) => void,
) {
  try {
    const next = await adapters.getVoiceAgents();
    setAgents(next);
    if (next[0]) {
      setSelectedAgentId(next[0].id);
      setSelectedVoiceId(next[0].voice);
    }
  } catch {
    setAgents([]);
  }
}

async function loadProviders(
  setProviders: (providers: VoiceProvider[]) => void,
  setMessage: (message: string | null) => void,
) {
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
  try {
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
  } catch (err) {
    setMessage(`Blocked: catalog fetch failed — ${err instanceof Error ? err.message : String(err)}`);
  }
}

function ProviderStatus({
  provider,
  catalog,
}: {
  provider: VoiceProvider | null;
  catalog: VoiceCatalog | null;
}) {
  const ready = catalog?.status === "ready" && catalog.configured;
  return (
    <div className="rounded border border-border bg-bg/50 p-2 text-[11px]">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-fg">{provider?.name ?? "Azure Speech"}</span>
        <span className={ready ? "text-accent-green" : "text-accent-amber"}>
          {ready ? "READY" : catalog?.status ?? "LOADING"}
        </span>
      </div>
      <div className="mt-1 text-muted">
        {ready
          ? `Region: ${catalog?.region ?? provider?.region ?? "configured"}`
          : catalog?.reason ?? "Waiting for provider status."}
      </div>
      <div className="mt-1 text-[10px] text-muted">
        Backend handles Azure TTS/STT. Web Speech API in the Browser Voice subtab runs purely
        client-side; no audio is uploaded by the frontend.
      </div>
    </div>
  );
}

function isVoiceProvider(value: unknown): value is VoiceProvider {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  const row = value as Record<string, unknown>;
  return typeof row.id === "string" && typeof row.name === "string" && typeof row.configured === "boolean";
}
