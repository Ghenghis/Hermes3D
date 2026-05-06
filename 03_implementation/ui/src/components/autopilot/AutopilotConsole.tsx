import { ShieldAlert } from "lucide-react";
import { LockedAction } from "../badges/LockedAction";
import { StatusBadge } from "../badges/StatusBadge";
import { Panel } from "../layout/Panel";

/**
 * AutopilotConsole — display widget for autopilot runbook and guardrails.
 *
 * This component is a pure display widget. All live readiness data comes
 * from the AutopilotTab (which calls /api/autopilot/readiness and
 * /api/autopilot/guardrails). Do NOT add hardcoded fake status values here;
 * if no props are passed the component shows "not connected" state honestly.
 */

const RUNBOOK = [
  { id: "observe", label: "Observe printer and queue state", status: "ready" },
  { id: "triage", label: "Triage warnings into while-away summary", status: "ready" },
  { id: "proof", label: "Attach proof bundle references", status: "ready" },
  { id: "action", label: "Request operator approval for writes", status: "locked" },
];

const GUARDS = [
  "No printer writes without approval token",
  "No external app launch from UI",
  "No secret values shown in notifications",
  "Loopback-only live bridge policy",
];

export interface AutopilotConsoleProps {
  /** Live readiness check count from /api/autopilot/readiness. Omit = not connected. */
  readyCount?: number;
  /** Total expected checks from /api/autopilot/readiness. Omit = not connected. */
  totalChecks?: number;
}

export function AutopilotConsole({ readyCount, totalChecks }: AutopilotConsoleProps = {}) {
  const connected = readyCount !== undefined && totalChecks !== undefined;
  const allReady = connected && readyCount === totalChecks && totalChecks > 0;
  const loopStatus = allReady ? "ready" : "not configured";
  const riskStatus = connected ? (allReady ? "low" : "blocked") : "unknown";

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min">
      <div className="col-span-12 lg:col-span-7">
        <Panel
          id="autopilot.runbook"
          title="AUTOPILOT RUNBOOK"
          dense
          status={{ tone: "cyan", label: "read-only" }}
          className="h-[350px]"
        >
          <ol className="flex h-full flex-col gap-2 overflow-auto text-xs">
            {RUNBOOK.map((step, index) => (
              <li key={step.id} className="flex items-center gap-2 rounded border border-border bg-surface2/40 px-2 py-2">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-surface font-mono text-[11px] text-accent-cyan">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1 truncate text-fg">{step.label}</span>
                <StatusBadge tone={step.status === "locked" ? "amber" : "green"} label={step.status} />
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      <div className="col-span-12 lg:col-span-5 grid grid-cols-1 gap-2.5">
        <Panel
          id="autopilot.readiness"
          title="READINESS"
          dense
          status={{ tone: allReady ? "green" : "amber", label: connected ? `${readyCount}/${totalChecks} ready` : "not connected" }}
          className="h-[165px]"
        >
          <div className="grid grid-cols-3 gap-2 text-xs">
            <ReadinessCell label="Loop" value={loopStatus} ready={allReady} />
            <ReadinessCell label="Risk" value={riskStatus} ready={allReady} />
            <ReadinessCell label="Data" value={connected ? "live" : "unavailable"} ready={connected} />
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <LockedAction label="Start writes" hint="Requires explicit operator approval" />
            <LockedAction label="Change policy" />
          </div>
        </Panel>

        <Panel
          id="autopilot.guards"
          title="GUARDRAILS"
          dense
          status={{ tone: "green", label: `${GUARDS.length} checks` }}
          className="h-[175px]"
        >
          <ul className="flex h-full flex-col gap-1 overflow-auto text-xs">
            {GUARDS.map((guard) => (
              <li key={guard} className="flex items-center gap-2 rounded bg-surface2/40 px-2 py-1.5">
                <ShieldAlert size={13} className="shrink-0 text-accent-green" />
                <span className="truncate text-fg">{guard}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function ReadinessCell({ label, value, ready }: { label: string; value: string; ready: boolean }) {
  return (
    <div className="rounded border border-border bg-surface2/40 p-2">
      <div className="text-[10px] uppercase text-muted">{label}</div>
      <div className={`mt-1 font-semibold ${ready ? "text-fg" : "text-accent-amber"}`}>{value}</div>
    </div>
  );
}
