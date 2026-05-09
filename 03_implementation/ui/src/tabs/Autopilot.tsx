import { useEffect, useMemo, useState } from "react";
import { adapters } from "../api/adapters";
import { TABS } from "../app/routes";
import { useStore } from "../app/store";
import type { AutopilotCheck, GuardrailPolicy } from "../types/autopilot";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

export function AutopilotTab() {
  const setActiveTabId = useStore((state) => state.setActiveTabId);
  const [checks, setChecks] = useState<AutopilotCheck[]>([]);
  const [guardrails, setGuardrails] = useState<GuardrailPolicy[]>([]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const readyCount = useMemo(() => checks.filter((check) => check.status === "ready").length, [checks]);
  // readinessTotal reflects what the API actually returned — no hardcoded expectation.
  const readinessTotal = checks.length;
  // allReady is true only when the backend confirms every returned check passes.
  // A hardcoded count was removed: the API is the source of truth for how many checks exist.
  const allReady = checks.length > 0 && readyCount === checks.length;

  useEffect(() => {
    let mounted = true;
    const load = () => {
      void adapters.getAutopilotReadiness().then((next) => {
        if (mounted) {
          setChecks(next.map(normalizeAutopilotCheck).filter(isPresent));
        }
      });
      void adapters.getAutopilotGuardrails().then((next) => {
        if (mounted) {
          setGuardrails(next);
        }
      });
    };
    load();
    const timer = window.setInterval(load, 30_000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const postAction = async (path: string, eventType: string, payload: Record<string, unknown> = {}) => {
    if (eventType === "autopilot.action.triggered" && !window.confirm("This will advance the autopilot to the next approved gate. Continue?")) {
      return;
    }
    let accepted = false;
    let responsePayload: unknown = null;
    try {
      const response = await fetch(`${LIVE_BASE_URL}${path}`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      });
      responsePayload = await response.json().catch(() => null);
      accepted = response.ok && actionAccepted(responsePayload);
      setActionMessage(`${accepted ? "Accepted" : "Blocked"}: ${actionSummary(responsePayload, response.statusText)}`);
    } catch {
      setActionMessage(`Blocked: backend API is unreachable at ${LIVE_BASE_URL}.`);
    }
    if (accepted) {
      await adapters.emitProofEvent(eventType, { ...payload, accepted, response: responsePayload });
    }
    if (eventType === "autopilot.local_pilot_job.created" && accepted) {
      setActiveTabId("jobs");
    }
  };

  return (
    <div data-testid="autopilot-root" className="grid min-h-[calc(100vh-6.5rem)] grid-rows-[minmax(0,1.35fr)_auto_minmax(0,1fr)] gap-3">
      <section id="autopilot.readiness" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-fg">READINESS CHECKS</h2>
          <span className="rounded bg-surface2 px-2 py-1 text-xs text-muted">
            {readinessTotal === 0 ? "loading…" : `${readyCount}/${readinessTotal} READY`}
          </span>
        </div>
        <div className="mt-3 grid min-h-0 flex-1 gap-2 overflow-auto md:grid-cols-2">
          {checks.length === 0 && (
            <div className="col-span-2 flex items-center justify-center rounded border border-border bg-bg/40 px-3 py-4 text-sm text-muted">
              Waiting for readiness checks from the backend API…
            </div>
          )}
          {checks.map((check) => (
            <div key={check.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-2 rounded border border-border bg-bg/40 px-3 py-2 text-sm">
              <div className="min-w-0">
                <div className="truncate text-fg">{check.name}</div>
                {check.detail && <div className="truncate text-xs text-muted">{check.detail}</div>}
              </div>
              <span className={`rounded px-2 py-1 text-xs ${check.status === "ready" ? "bg-green-900/50 text-green-300" : "bg-amber-900/50 text-amber-200"}`}>
                {check.status === "ready" ? "READY" : "NEEDS SETUP"}
              </span>
              {check.status !== "ready" && (
                <button type="button" onClick={() => setActiveTabId(safeTabId(check.fix_target))} className="rounded border border-border px-2 py-1 text-xs text-fg">
                  Fix
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      <section id="autopilot.actions" className="rounded border border-border bg-surface p-4">
        <h2 className="text-base font-semibold text-fg">SAFE ACTIONS</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          <ActionButton disabled={!allReady} onClick={() => postAction("/api/autopilot/next-gate", "autopilot.action.triggered")}>Autopilot To Next Safe Gate</ActionButton>
          <ActionButton onClick={() => postAction("/api/autopilot/write-plan", "autopilot.plan.written")}>Write Agent Plan</ActionButton>
          <ActionButton onClick={() => postAction("/api/autopilot/write-report", "autopilot.report.written")}>Write Setup Report</ActionButton>
          <ActionButton onClick={() => postAction("/api/jobs", "autopilot.local_pilot_job.created", { type: "pilot_calibration_cube", dry_run: true })}>Create Local Pilot Job</ActionButton>
        </div>
        {actionMessage && <div className="mt-3 rounded border border-border bg-bg/50 p-2 text-xs text-muted">{actionMessage}</div>}
      </section>

      <section id="autopilot.guardrails" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4">
        <h2 className="text-base font-semibold text-fg">ACTIVE GUARDRAILS</h2>
        <div className="mt-3 grid min-h-0 flex-1 gap-2 overflow-auto">
          {guardrails.map((guardrail) => (
            <div key={guardrail.id} className="flex items-center justify-between gap-3 rounded border border-border bg-bg/40 px-3 py-2 text-sm">
              <div>
                <div className="font-medium text-fg">{guardrail.name}</div>
                <div className="text-xs text-muted">{guardrail.description}</div>
              </div>
              <span className="rounded bg-green-900/50 px-2 py-1 text-xs text-green-300">{guardrail.enabled ? "ACTIVE" : "OVERRIDE"}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function normalizeAutopilotCheck(value: AutopilotCheck): AutopilotCheck | null {
  if (!isRecord(value) || typeof value.id !== "string" || typeof value.name !== "string") {
    return null;
  }
  const ready = typeof value.ready === "boolean" ? value.ready : value.status === "ready";
  return {
    id: value.id,
    name: value.name,
    status: ready ? "ready" : "needs_setup",
    detail: typeof value.detail === "string" ? value.detail : typeof value.message === "string" && value.message.length > 0 ? value.message : null,
    fix_target: typeof value.fix_target === "string" || value.fix_target === null ? value.fix_target : "settings",
  };
}

function actionAccepted(payload: unknown): boolean {
  if (payload === false) {
    return false;
  }
  if (!isRecord(payload)) {
    return true;
  }
  if (payload.accepted === false || payload.success === false || payload.ok === false || payload.ready === false || payload.queued === false) {
    return false;
  }
  if (payload.status === "not_configured" || payload.status === "blocked" || payload.status === "failed" || payload.status === "error" || payload.status === "unreachable") {
    return false;
  }
  return true;
}

function actionSummary(payload: unknown, fallback: string): string {
  if (payload === false) {
    return "Backend returned false.";
  }
  if (!isRecord(payload)) {
    return fallback || "No response body.";
  }
  if (typeof payload.reason === "string") {
    return payload.reason;
  }
  if (typeof payload.message === "string") {
    return payload.message;
  }
  if (typeof payload.report_path === "string") {
    return payload.report_path;
  }
  if (typeof payload.id === "string") {
    return payload.id;
  }
  if (typeof payload.status === "string") {
    return payload.status;
  }
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  if (isRecord(payload.detail)) {
    const next = payload.detail.next;
    if (isRecord(next) && typeof next.name === "string") {
      return `Next failing check: ${next.name}`;
    }
    return JSON.stringify(payload.detail);
  }
  return fallback || JSON.stringify(payload);
}

function isPresent<T>(value: T | null | undefined): value is T {
  return value != null;
}

function safeTabId(target: string | null | undefined): string {
  const normalized = target === "source-os" ? "source_os" : target;
  return TABS.some((tab) => tab.id === normalized) ? normalized as string : "settings";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function ActionButton({
  children,
  disabled = false,
  onClick,
}: {
  children: React.ReactNode;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" disabled={disabled} onClick={onClick} className="rounded border border-border bg-bg/50 px-3 py-2 text-left text-sm font-medium text-fg hover:border-accent-blue disabled:cursor-not-allowed disabled:opacity-50">
      {children}
    </button>
  );
}
