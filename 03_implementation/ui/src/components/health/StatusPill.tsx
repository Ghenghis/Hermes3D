import { StatusBadge, type StatusTone } from "../badges/StatusBadge";
import type { ServiceStatus } from "../../types/serviceHealth";

/**
 * Maps the FastAPI ``status`` enum to a {@link StatusBadge} tone +
 * human-friendly label. Centralised here so the ServiceCard, header
 * summary, and any future Service Health-related panels stay in sync.
 */
const TONE_BY_STATUS: Record<ServiceStatus, { tone: StatusTone; label: string }> = {
  online: { tone: "green", label: "online" },
  offline: { tone: "red", label: "offline" },
  unreachable: { tone: "amber", label: "unreachable" },
  "auth-required": { tone: "blue", label: "auth required" },
  disabled: { tone: "muted", label: "disabled" },
  unknown: { tone: "muted", label: "unknown" },
};

export function StatusPill({ status }: { status: ServiceStatus }) {
  const { tone, label } = TONE_BY_STATUS[status] ?? TONE_BY_STATUS.unknown;
  return (
    <span data-status-pill data-status={status}>
      <StatusBadge tone={tone} label={label} />
    </span>
  );
}
