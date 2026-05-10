/**
 * Hermes Agent version banner — shows the current `exact_tag` (or
 * `nearest_tag`) reported by `/api/agents/update/status`. When the backend
 * is unreachable the banner renders a muted "offline" pill instead of
 * disappearing, so the topbar layout remains stable.
 *
 * Owned by W6-5 (GUI wiring layer). Component shells for Dashboard modes,
 * Action Window, and Task Monitor remain owned by W6-3 / W6-4.
 */
import { useAgentUpdateStatus } from "../../hooks/useAgents";

const MISSING = "offline";

export function HermesAgentBanner({ compact = false }: { compact?: boolean } = {}) {
  const { data, error, isLoading } = useAgentUpdateStatus();
  const tag = pickTag(data);
  const outdated = data?.outdated ?? false;
  const tone = error ? "amber" : outdated ? "amber" : tag === MISSING ? "amber" : "green";
  const label = isLoading && !data ? "…" : tag;

  return (
    <div
      data-testid="hermes-agent-banner"
      data-version={tag}
      data-outdated={String(outdated)}
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 ${
        compact ? "py-0.5 text-[11px]" : "py-1 text-xs"
      } ${toneClass(tone)}`}
      title={describeTitle(data, error)}
    >
      <span className="font-semibold uppercase tracking-wide text-[10px]">
        Hermes Agent
      </span>
      <span className="font-mono">{label}</span>
      {outdated && (
        <span className="text-[10px] uppercase tracking-wide">update</span>
      )}
    </div>
  );
}

function pickTag(
  data: { current?: { exact_tag?: string | null; nearest_tag?: string | null }; latest_release?: { tag?: string | null } } | null,
): string {
  if (!data) return MISSING;
  const exact = data.current?.exact_tag;
  if (typeof exact === "string" && exact.length > 0) return exact;
  const nearest = data.current?.nearest_tag;
  if (typeof nearest === "string" && nearest.length > 0) return nearest;
  const latest = data.latest_release?.tag;
  if (typeof latest === "string" && latest.length > 0) return latest;
  return MISSING;
}

function describeTitle(
  data: { current?: { commit?: string }; latest_release?: { tag?: string | null } } | null,
  error: Error | null,
): string {
  if (error) return `Hermes Agent status unreachable: ${error.message}`;
  if (!data) return "Hermes Agent status pending";
  const commit = data.current?.commit ? ` @ ${data.current.commit.slice(0, 7)}` : "";
  const latest = data.latest_release?.tag ? ` (latest: ${data.latest_release.tag})` : "";
  return `Hermes Agent${commit}${latest}`;
}

function toneClass(tone: "green" | "amber" | "muted"): string {
  switch (tone) {
    case "green":
      return "border-accent-green/40 bg-accent-green/10 text-accent-green";
    case "amber":
      return "border-accent-amber/40 bg-accent-amber/10 text-accent-amber";
    default:
      return "border-border bg-surface2 text-muted";
  }
}
