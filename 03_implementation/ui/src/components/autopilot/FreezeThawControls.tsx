/**
 * FreezeThawControls — Wave 15 A14.
 *
 * Freeze / thaw the autopilot loop. The current Hermes3D backend exposes no
 * `/api/autopilot/freeze` or `/api/autopilot/thaw` endpoint (verified
 * 2026-05-10 against `src/hermes3d/api/routes/autopilot.py` — only
 * /readiness, /next-gate, /write-plan, /write-report, /guardrails exist).
 *
 * Strict rules:
 *   - No fake "frozen" state that lies to the operator. We probe the
 *     endpoint and surface the real outcome.
 *   - When the endpoint is missing we render an explicit "blocked" notice
 *     so the operator knows the control is not wired yet (per W15 A20).
 *   - When the endpoint exists and accepts the call we record a proof event.
 */
import { useState } from "react";
import { Snowflake, Sun } from "lucide-react";
import { adapters } from "../../api/adapters";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

type Mode = "frozen" | "thawed" | "unknown";

export function FreezeThawControls() {
  const [mode, setMode] = useState<Mode>("unknown");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState<boolean>(false);

  const trigger = async (path: "freeze" | "thaw") => {
    setPending(true);
    let accepted = false;
    let summary = "no response";
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/autopilot/${path}`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ source: "autopilot.freeze_thaw_controls" }),
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      if (response.status === 404 || response.status === 405) {
        summary = `Blocked: /api/autopilot/${path} is not implemented on this backend (W15 A20 owns the endpoint).`;
      } else if (!response.ok) {
        summary = `Blocked: backend rejected ${path} (${response.status} ${response.statusText}).`;
      } else {
        accepted = true;
        summary = payloadSummary(payload, path);
        setMode(path === "freeze" ? "frozen" : "thawed");
      }
    } catch (error) {
      summary = `Blocked: backend unreachable at ${LIVE_BASE_URL} (${describeError(error)}).`;
    } finally {
      setPending(false);
    }
    setMessage(summary);
    await adapters
      .emitProofEvent(`autopilot.${path}.requested`, { accepted, summary })
      .catch(() => {/* best effort */});
  };

  return (
    <section
      id="autopilot.freeze_thaw"
      data-testid="autopilot-freeze-thaw"
      data-autopilot-mode={mode}
      className="rounded border border-border bg-surface p-4"
    >
      <header className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-fg">FREEZE / THAW</h2>
          <p className="text-xs text-muted">
            Stop or resume the autopilot loop. Calls /api/autopilot/freeze + /thaw.
          </p>
        </div>
        <span
          data-testid="autopilot-freeze-thaw-state"
          className={`rounded px-2 py-1 text-xs uppercase ${modeTone(mode)}`}
        >
          {mode}
        </span>
      </header>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          data-testid="autopilot-freeze-button"
          disabled={pending}
          onClick={() => void trigger("freeze")}
          className="inline-flex items-center gap-2 rounded border border-border bg-bg/50 px-3 py-2 text-sm text-fg hover:border-amber-500 disabled:opacity-50"
        >
          <Snowflake size={14} className="text-cyan-300" />
          Freeze autopilot
        </button>
        <button
          type="button"
          data-testid="autopilot-thaw-button"
          disabled={pending}
          onClick={() => void trigger("thaw")}
          className="inline-flex items-center gap-2 rounded border border-border bg-bg/50 px-3 py-2 text-sm text-fg hover:border-accent-blue disabled:opacity-50"
        >
          <Sun size={14} className="text-amber-300" />
          Thaw autopilot
        </button>
      </div>
      {message && (
        <div
          data-testid="autopilot-freeze-thaw-message"
          className="mt-3 rounded border border-border bg-bg/40 p-2 text-xs text-muted"
        >
          {message}
        </div>
      )}
    </section>
  );
}

function modeTone(mode: Mode): string {
  if (mode === "frozen") return "bg-cyan-900/40 text-cyan-200";
  if (mode === "thawed") return "bg-green-900/40 text-green-200";
  return "bg-surface2 text-muted";
}

function payloadSummary(payload: unknown, fallback: string): string {
  if (typeof payload === "object" && payload !== null && !Array.isArray(payload)) {
    const record = payload as Record<string, unknown>;
    if (typeof record.message === "string") return record.message;
    if (typeof record.status === "string") return record.status;
    if (typeof record.proof_event_id === "string") return `proof ${record.proof_event_id}`;
  }
  return `${fallback} accepted`;
}

function describeError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "unknown";
}
