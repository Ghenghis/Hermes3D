import { BrainCircuit, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { adapters, type AgentHealthResult, type HermesAgentUpdateStatus, type HermesDesktopUpdateStatus } from "../../api/adapters";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";

const READ_ONLY_POLICY_ROWS = [
  { key: "planner_model", label: "Planner model", value: "ollama/llama3.1:8b" },
  { key: "coder_model", label: "Implementer model", value: "ollama/qwen2.5-coder:14b" },
  { key: "review_gate", label: "Review gate", value: "required before writes" },
  { key: "max_parallel", label: "Max parallel agents", value: "4" },
];

type BusyState = "health" | "backup" | "update" | "rollback" | "desktop-backup" | "desktop-download" | null;

export function AgentConfigSection() {
  const [message, setMessage] = useState<string | null>(null);
  const [health, setHealth] = useState<AgentHealthResult | null>(null);
  const [updateStatus, setUpdateStatus] = useState<HermesAgentUpdateStatus | null>(null);
  const [desktopStatus, setDesktopStatus] = useState<HermesDesktopUpdateStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [busy, setBusy] = useState<BusyState>(null);

  useEffect(() => {
    let mounted = true;
    void adapters.getAgentHealth()
      .then((result) => {
        if (!mounted) return;
        setHealth(result);
        setMessage(result.healthy ? result.reason : `Controls disabled: ${result.reason}`);
      })
      .finally(() => {
        if (mounted) {
          setLoadingHealth(false);
        }
      });
    void adapters.getHermesAgentUpdateStatus()
      .then((status) => {
        if (!mounted) return;
        setUpdateStatus(status);
      });
    void adapters.getHermesDesktopUpdateStatus()
      .then((status) => {
        if (!mounted) return;
        setDesktopStatus(status);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const policySaveReason = "Policy editing is blocked until a live backend policy editor endpoint is wired; these rows are read-only defaults.";
  const healthRefreshDisabled = loadingHealth || busy !== null;
  const backendReason = loadingHealth
    ? "Checking /api/agents/health before enabling agent settings controls."
    : health?.reason ?? "Agent backend health has not returned a status.";
  const statusLabel = loadingHealth ? "checking" : health?.status ?? "unavailable";

  return (
    <section className="rounded border border-border bg-surface2/30 p-3" data-testid="agent-config-section">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <BrainCircuit size={16} className="shrink-0 text-accent-cyan" />
          <div className="min-w-0">
            <div className="truncate text-xs font-semibold text-fg">Agent runtime policy status</div>
            <div className="truncate text-[10px] text-muted">Read-only defaults; policy writes are blocked until a live editor exists.</div>
          </div>
        </div>
        <StatusBadge tone={healthTone(loadingHealth, health)} label={statusLabel} />
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
        {READ_ONLY_POLICY_ROWS.map((row) => (
          <div key={row.key} className="rounded border border-border bg-surface px-2 py-1.5 text-xs">
            <div className="text-[10px] uppercase text-muted">{row.label}</div>
            <div className="truncate font-mono text-fg">{row.value}</div>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded border border-border bg-surface px-2 py-1.5 text-xs" data-testid="agent-auto-update-policy">
        <div className="text-[10px] uppercase text-muted">Hermes Agent auto-update</div>
        {updateStatus ? (
          <div className="mt-1 grid gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone={updateTone(updateStatus)} label={updateLabel(updateStatus)} />
              <span className="text-muted">
                {updateStatus.current.nearest_tag ?? updateStatus.current.commit ?? "unknown"} → {updateStatus.latest_release.tag ?? "unknown"}
              </span>
              {updateStatus.outdated_by > 0 && (
                <span className="text-amber-300">{updateStatus.outdated_by} staged release{updateStatus.outdated_by === 1 ? "" : "s"} pending</span>
              )}
            </div>
            <div className="truncate font-mono text-[10px] text-muted" title={updateStatus.checkout_path}>{updateStatus.checkout_path || updateStatus.reason}</div>
            <div className="text-muted">
              Failsafe: create a git bundle backup before update, apply one release at a time, run gates, and auto-rollback on failed gates without deleting data.
            </div>
            {updateStatus.latest_backup && (
              <div className="truncate text-[10px] text-muted" title={updateStatus.latest_backup.bundle_path}>
                Latest backup: {updateStatus.latest_backup.tag ?? updateStatus.latest_backup.commit} · {updateStatus.latest_backup.backup_id}
              </div>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              <button
                type="button"
                disabled={busy !== null || !updateStatus.repo_ready}
                onClick={() => void backupAgent(setMessage, setBusy, setUpdateStatus)}
                className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
              >
                Backup now
              </button>
              <button
                type="button"
                disabled={busy !== null || !updateStatus.repo_ready || !updateStatus.outdated}
                onClick={() => void updateOneRelease(setMessage, setBusy, setUpdateStatus)}
                className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
              >
                Update one release + gates
              </button>
              <button
                type="button"
                disabled={busy !== null || !updateStatus.repo_ready || !updateStatus.backup_available}
                onClick={() => void rollbackAgent(setMessage, setBusy, setUpdateStatus, updateStatus.latest_backup?.backup_id)}
                className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
              >
                Rollback
              </button>
            </div>
          </div>
        ) : (
          <div className="text-muted">Checking Hermes Agent GitHub release status.</div>
        )}
      </div>

      <div className="mt-3 rounded border border-border bg-surface px-2 py-1.5 text-xs" data-testid="hermes-desktop-update-policy">
        <div className="text-[10px] uppercase text-muted">Hermes Desktop Windows updater</div>
        {desktopStatus ? (
          <div className="mt-1 grid gap-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone={desktopTone(desktopStatus)} label={desktopLabel(desktopStatus)} />
              <span className="text-muted">
                {desktopStatus.current.package_version ?? desktopStatus.current.nearest_tag ?? "unknown"} → {desktopStatus.latest_release.tag ?? "unknown"}
              </span>
              <span className="text-cyan-200">Desktop bridge: http://127.0.0.1:8642</span>
            </div>
            <div className="truncate font-mono text-[10px] text-muted" title={desktopStatus.checkout_path}>{desktopStatus.checkout_path || desktopStatus.reason}</div>
            <div className="text-muted">
              Compatibility probe: Hermes Desktop can reach <span className="font-mono">/health</span> and streams chat through <span className="font-mono">/v1/chat/completions</span> when a trusted runtime is configured. Installer downloads verify SHA-256 against GitHub release metadata when a digest is present and fail closed on mismatch; Desktop source update remains blocked unless the backend reports a staged update route.
            </div>
            {desktopStatus.latest_release.installer_asset?.name && (
              <div className="truncate text-[10px] text-muted">
                Installer: {desktopStatus.latest_release.installer_asset.name}
                {desktopStatus.latest_release.installer_asset.digest ? " · GitHub SHA-256 available" : " · no upstream digest"}
              </div>
            )}
            {desktopStatus.latest_backup && (
              <div className="truncate text-[10px] text-muted" title={desktopStatus.latest_backup.bundle_path ?? desktopStatus.latest_backup.source_zip_path ?? ""}>
                Latest backup: {desktopStatus.latest_backup.package_version ?? desktopStatus.latest_backup.tag ?? "source"} · {desktopStatus.latest_backup.backup_id}
              </div>
            )}
            <div className="flex flex-wrap gap-1.5 pt-1">
              <button
                type="button"
                disabled={busy !== null || !desktopStatus.source_ready}
                onClick={() => void backupDesktop(setMessage, setBusy, setDesktopStatus)}
                className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
              >
                Backup Desktop source
              </button>
              <button
                type="button"
                disabled={busy !== null || !desktopStatus.installer_download_supported}
                onClick={() => void downloadDesktop(setMessage, setBusy, setDesktopStatus)}
                className="rounded border border-border px-2 py-1 text-[10px] text-fg disabled:cursor-not-allowed disabled:opacity-50"
              >
                Download installer + verify SHA-256
              </button>
            </div>
          </div>
        ) : (
          <div className="text-muted">Checking Hermes Desktop release status.</div>
        )}
      </div>

      <div className="mt-2 rounded border border-border bg-surface px-2 py-1 text-[10px] text-muted" data-testid="agent-backend-reason">
        {backendReason}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <SlidersHorizontal size={13} className="text-muted" />
        <button
          type="button"
          disabled
          title={policySaveReason}
          className="rounded border border-border px-2 py-1 text-xs text-fg disabled:cursor-not-allowed disabled:opacity-50"
        >
          Policy editor blocked
        </button>
        <button
          type="button"
          disabled={healthRefreshDisabled}
          title={backendReason}
          onClick={() => void refreshAgentHealth(setMessage, setHealth, setBusy)}
          className="rounded border border-border px-2 py-1 text-xs text-fg disabled:cursor-not-allowed disabled:opacity-50"
        >
          Refresh agent health
        </button>
      </div>
      {message && <div className="mt-2 rounded border border-border bg-surface px-2 py-1 text-[10px] text-muted">{message}</div>}
    </section>
  );
}

async function refreshAgentHealth(
  setMessage: (message: string) => void,
  setHealth: (health: AgentHealthResult) => void,
  setBusy: (busy: BusyState) => void,
) {
  setBusy("health");
  try {
    const result = await adapters.getAgentHealth();
    setHealth(result);
    setMessage(`${result.available ? "Health" : "Blocked"}: ${result.reason}`);
  } catch (error) {
    setMessage(`Blocked: ${error instanceof Error ? error.message : "agent health check failed"}`);
  } finally {
    setBusy(null);
  }
}

async function refreshUpdateStatus(setUpdateStatus: (status: HermesAgentUpdateStatus) => void) {
  const status = await adapters.getHermesAgentUpdateStatus();
  setUpdateStatus(status);
  return status;
}

async function backupAgent(
  setMessage: (message: string) => void,
  setBusy: (busy: BusyState) => void,
  setUpdateStatus: (status: HermesAgentUpdateStatus) => void,
) {
  setBusy("backup");
  try {
    const backup = await adapters.backupHermesAgent("manual backup from Hermes3D Settings before update");
    setMessage(`Backup created: ${backup.backup_id}`);
    await refreshUpdateStatus(setUpdateStatus);
  } catch (error) {
    setMessage(`Blocked: ${error instanceof Error ? error.message : "backup failed"}`);
  } finally {
    setBusy(null);
  }
}

async function updateOneRelease(
  setMessage: (message: string) => void,
  setBusy: (busy: BusyState) => void,
  setUpdateStatus: (status: HermesAgentUpdateStatus) => void,
) {
  setBusy("update");
  try {
    const result = await adapters.updateHermesAgentStaged(1);
    const step = result.steps?.at(-1);
    setMessage(`${result.updated ? "Updated" : "Stopped"}: ${step?.tag ?? result.status}${result.reason ? ` · ${result.reason}` : ""}`);
    await refreshUpdateStatus(setUpdateStatus);
  } catch (error) {
    setMessage(`Blocked: ${error instanceof Error ? error.message : "Hermes Agent update failed"}`);
  } finally {
    setBusy(null);
  }
}

async function rollbackAgent(
  setMessage: (message: string) => void,
  setBusy: (busy: BusyState) => void,
  setUpdateStatus: (status: HermesAgentUpdateStatus) => void,
  backupId?: string,
) {
  setBusy("rollback");
  try {
    const result = await adapters.rollbackHermesAgent(backupId);
    setMessage(`${result.updated === false ? "Rollback checked" : "Rollback"}: ${result.status}`);
    await refreshUpdateStatus(setUpdateStatus);
  } catch (error) {
    setMessage(`Blocked: ${error instanceof Error ? error.message : "Hermes Agent rollback failed"}`);
  } finally {
    setBusy(null);
  }
}

async function refreshDesktopStatus(setDesktopStatus: (status: HermesDesktopUpdateStatus) => void) {
  const status = await adapters.getHermesDesktopUpdateStatus();
  setDesktopStatus(status);
  return status;
}

async function backupDesktop(
  setMessage: (message: string) => void,
  setBusy: (busy: BusyState) => void,
  setDesktopStatus: (status: HermesDesktopUpdateStatus) => void,
) {
  setBusy("desktop-backup");
  try {
    const backup = await adapters.backupHermesDesktop("manual backup from Hermes3D Settings before Desktop update");
    setMessage(`Hermes Desktop backup created: ${backup.backup_id}`);
    await refreshDesktopStatus(setDesktopStatus);
  } catch (error) {
    setMessage(`Blocked: ${error instanceof Error ? error.message : "Hermes Desktop backup failed"}`);
  } finally {
    setBusy(null);
  }
}

async function downloadDesktop(
  setMessage: (message: string) => void,
  setBusy: (busy: BusyState) => void,
  setDesktopStatus: (status: HermesDesktopUpdateStatus) => void,
) {
  setBusy("desktop-download");
  try {
    const result = await adapters.downloadHermesDesktopInstaller();
    const status = result.verification_status === "sha256_verified_github_release_digest" ? "verified" : "recorded";
    setMessage(`Hermes Desktop installer ${status}: ${result.asset_name} · ${result.sha256.slice(0, 16)}...`);
    await refreshDesktopStatus(setDesktopStatus);
  } catch (error) {
    setMessage(`Blocked: ${error instanceof Error ? error.message : "Hermes Desktop download failed"}`);
  } finally {
    setBusy(null);
  }
}

function healthTone(loading: boolean, health: AgentHealthResult | null): StatusTone {
  if (loading) {
    return "cyan";
  }
  if (!health?.available) {
    return "red";
  }
  if (health.healthy) {
    return "green";
  }
  return health.status === "not_configured" ? "amber" : "muted";
}

function updateTone(status: HermesAgentUpdateStatus): StatusTone {
  if (!status.available || !status.repo_ready) return "red";
  if (status.outdated) return "amber";
  return status.current.dirty ? "cyan" : "green";
}

function updateLabel(status: HermesAgentUpdateStatus): string {
  if (!status.available) return "unavailable";
  if (!status.repo_ready) return "repo blocked";
  if (status.outdated) return "update ready";
  return status.current.dirty ? "current + local edits" : "current";
}

function desktopTone(status: HermesDesktopUpdateStatus): StatusTone {
  if (!status.available || !status.source_ready) return "red";
  if (status.outdated) return "amber";
  return status.git_ready ? "green" : "cyan";
}

function desktopLabel(status: HermesDesktopUpdateStatus): string {
  if (!status.available) return "unavailable";
  if (!status.source_ready) return "source blocked";
  if (status.outdated && status.source_update_supported) return "update ready";
  if (status.outdated && status.installer_download_supported) return "installer available";
  if (status.outdated) return "update blocked";
  return status.git_ready ? "current" : "source copy";
}
