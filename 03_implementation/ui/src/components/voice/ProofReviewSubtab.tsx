/**
 * ProofReviewSubtab — proof bundles awaiting voice acknowledgement.
 *
 * Loads voice proof events from the backend ledger, distinguishes
 * "pending acknowledgement" entries (typically `*.requested` /
 * `*.preview.triggered` events that have not been confirmed by an
 * agent), and lets the operator emit an explicit
 * `voice.proof.acknowledged` event for the selected row.
 *
 * Honesty:
 *   - When the backend ledger is unreachable, we surface the verbatim
 *     error string. We never invent proof rows.
 *   - "Acknowledge" buttons only enable when the source event id is
 *     non-empty — the emit goes through `adapters.emitProofEvent`, which
 *     is the same channel the rest of the dashboard uses.
 */
import { Check, ChevronRight, RefreshCw, Shield, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { adapters } from "../../api/adapters";
import type { VoiceProofEvent } from "../../types/voice";

type Filter = "all" | "pending" | "acknowledged";

const PENDING_PREFIXES = [
  "voice.agent.preview.triggered",
  "voice.agent.voice_saved",
  "voice.browser.transcript.submitted",
  "voice.stt",
  "voice.tts",
];

function isPending(ev: VoiceProofEvent): boolean {
  if (ev.eventType === "voice.proof.acknowledged") return false;
  if (ev.status === "acknowledged") return false;
  return PENDING_PREFIXES.some((prefix) => ev.eventType.startsWith(prefix));
}

export function ProofReviewSubtab() {
  const [events, setEvents] = useState<VoiceProofEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("pending");
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);
  const [ackedIds, setAckedIds] = useState<Set<string>>(() => new Set());
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const items = await adapters.getVoiceProofEvents(100);
      setEvents(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function acknowledge(ev: VoiceProofEvent) {
    if (!ev.id) {
      setMessage("Blocked: event has no id; cannot acknowledge.");
      return;
    }
    setAcknowledgingId(ev.id);
    setMessage(null);
    try {
      await adapters.emitProofEvent("voice.proof.acknowledged", {
        source_event_id: ev.id,
        source_event_type: ev.eventType,
        source_agent: ev.sourceAgent,
        ts_source_utc: ev.tsUtc,
      });
      setAckedIds((current) => {
        const next = new Set(current);
        next.add(ev.id);
        return next;
      });
      setMessage(`Acknowledged ${ev.eventType} (${ev.id}).`);
    } catch (err) {
      setMessage(`Blocked: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setAcknowledgingId(null);
    }
  }

  const filtered = useMemo(() => {
    return events.filter((ev) => {
      const acked = ackedIds.has(ev.id) || ev.status === "acknowledged" || ev.eventType === "voice.proof.acknowledged";
      if (filter === "pending") {
        return isPending(ev) && !acked;
      }
      if (filter === "acknowledged") {
        return acked;
      }
      return true;
    });
  }, [events, filter, ackedIds]);

  const pendingCount = useMemo(
    () => events.filter((ev) => isPending(ev) && !ackedIds.has(ev.id)).length,
    [events, ackedIds],
  );

  return (
    <section
      data-testid="voice-proof-review-subtab"
      className="grid min-h-0 min-w-0 flex-1 grid-rows-[auto_minmax(0,1fr)] rounded-card border border-border bg-surface"
    >
      <header className="flex items-center justify-between border-b border-border p-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[13px] font-semibold text-fg">Voice Proof Review</h2>
            <span
              data-testid="voice-proof-pending-count"
              className={[
                "rounded-chip px-2 py-0.5 text-[10px] font-semibold",
                pendingCount > 0
                  ? "bg-accent-amber/15 text-accent-amber"
                  : "bg-accent-green/15 text-accent-green",
              ].join(" ")}
            >
              {pendingCount} pending
            </span>
          </div>
          <p className="mt-0.5 text-[11px] text-muted">
            Immutable proof events emitted by the voice runtime. Acknowledge after manual review;
            acknowledgements are written back to the ledger as
            <code className="ml-1 font-mono text-[10px]">voice.proof.acknowledged</code>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            data-testid="voice-proof-filter"
            role="tablist"
            aria-label="Proof event filter"
            className="flex rounded border border-border bg-bg p-0.5 text-[10px]"
          >
            {(["pending", "acknowledged", "all"] as Filter[]).map((f) => (
              <button
                key={f}
                type="button"
                role="tab"
                aria-selected={filter === f}
                data-testid={`voice-proof-filter-${f}`}
                onClick={() => setFilter(f)}
                className={[
                  "rounded px-2 py-1 font-medium capitalize",
                  filter === f
                    ? "bg-accent-cyan/20 text-accent-cyan"
                    : "text-muted hover:text-fg",
                ].join(" ")}
              >
                {f}
              </button>
            ))}
          </div>
          <button
            type="button"
            data-testid="voice-proof-refresh"
            title="Refresh proof events"
            onClick={() => void load()}
            disabled={loading}
            className="rounded border border-border p-1.5 text-muted hover:text-fg disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </header>

      <div className="min-h-0 overflow-auto p-3">
        {error && (
          <div
            data-testid="voice-proof-error"
            className="mb-3 flex items-center gap-2 rounded border border-accent-red/40 bg-accent-red/10 p-3 text-xs text-accent-red"
          >
            <ShieldAlert size={14} className="shrink-0" />
            <span>Blocked: {error}</span>
          </div>
        )}
        {message && (
          <div
            data-testid="voice-proof-message"
            className="mb-3 rounded border border-border bg-bg/40 p-2 text-[11px] text-muted"
          >
            {message}
          </div>
        )}

        {!error && filtered.length === 0 && !loading && (
          <div
            data-testid="voice-proof-empty"
            className="flex min-h-[180px] flex-col items-center justify-center gap-2 text-center text-xs text-muted"
          >
            <Shield size={22} />
            <div className="font-semibold text-fg">
              {filter === "pending"
                ? "No voice proof events awaiting acknowledgement"
                : filter === "acknowledged"
                  ? "No acknowledged voice proof events yet"
                  : "No voice proof events recorded yet"}
            </div>
            <div>Events are emitted each time TTS or STT is invoked through the backend.</div>
          </div>
        )}

        <div className="flex flex-col gap-1">
          {filtered.map((ev) => {
            const acked = ackedIds.has(ev.id) || ev.status === "acknowledged" || ev.eventType === "voice.proof.acknowledged";
            const pending = isPending(ev) && !acked;
            const expanded = expandedId === ev.id;
            return (
              <div
                key={ev.id}
                data-testid={`voice-proof-row-${ev.id}`}
                className={[
                  "rounded border bg-bg/40",
                  pending ? "border-accent-amber/40" : "border-border",
                ].join(" ")}
              >
                <button
                  type="button"
                  onClick={() => setExpandedId(expanded ? null : ev.id)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left"
                >
                  <ProofEventBadge eventType={ev.eventType} status={ev.status} acked={acked} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] text-fg">{ev.eventType}</span>
                      <span className="text-[10px] text-muted">{formatTs(ev.tsUtc)}</span>
                    </div>
                    <p className="truncate text-[11px] text-muted">{ev.summary}</p>
                  </div>
                  <ChevronRight
                    size={13}
                    className={[
                      "text-muted transition-transform",
                      expanded ? "rotate-90" : "",
                    ].join(" ")}
                  />
                </button>
                {expanded && (
                  <div className="border-t border-border px-3 pb-2 pt-2">
                    <div className="grid gap-1 text-[11px]">
                      <Row label="Event ID" value={ev.id} mono />
                      <Row label="Source agent" value={ev.sourceAgent || "voice-runtime"} />
                      <Row label="Status" value={ev.status} />
                      <Row label="Timestamp" value={ev.tsUtc} />
                    </div>
                    {pending && (
                      <div className="mt-2 flex justify-end">
                        <button
                          type="button"
                          data-testid={`voice-proof-ack-${ev.id}`}
                          disabled={acknowledgingId === ev.id}
                          onClick={() => void acknowledge(ev)}
                          className="inline-flex items-center gap-1.5 rounded bg-accent-cyan px-2 py-1 text-[11px] font-semibold text-bg hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <Check size={12} />
                          {acknowledgingId === ev.id ? "Acknowledging…" : "Acknowledge"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
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

function ProofEventBadge({
  eventType,
  status,
  acked,
}: {
  eventType: string;
  status: string;
  acked: boolean;
}) {
  if (acked) {
    return (
      <span className="inline-flex shrink-0 items-center justify-center rounded bg-accent-green/15 px-1.5 py-0.5 text-[10px] font-semibold text-accent-green">
        ACK
      </span>
    );
  }
  const isBlocked = eventType.includes("blocked") || eventType.includes("failed");
  const isOk =
    status === "ready" ||
    eventType.includes("synthesized") ||
    eventType.includes("transcribed") ||
    eventType.includes("saved");
  const color = isBlocked
    ? "bg-accent-red/15 text-accent-red"
    : isOk
      ? "bg-accent-green/15 text-accent-green"
      : "bg-accent-amber/15 text-accent-amber";
  return (
    <span
      className={[
        "inline-flex shrink-0 items-center justify-center rounded px-1.5 py-0.5 text-[10px] font-semibold",
        color,
      ].join(" ")}
    >
      {isBlocked ? "FAIL" : isOk ? "OK" : "WARN"}
    </span>
  );
}

function formatTs(ts: string): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString(undefined, { dateStyle: "short", timeStyle: "medium" });
  } catch {
    return ts;
  }
}
