/**
 * Settings → Environment subtab.
 *
 * Renders presence/absence of expected Hermes3D env vars as `[set]` /
 * `[not set]`. The actual VALUES are NEVER read or rendered — only the
 * boolean "is this populated" — to avoid leaking API keys or local paths
 * into screenshots/logs/proof artifacts.
 *
 * Even browser-side `import.meta.env.VITE_*` is intentionally avoided here
 * because Vite would inline literal values into the bundle.
 */
import { Eye, EyeOff, Terminal } from "lucide-react";
import { StatusBadge } from "../badges/StatusBadge";

type EnvVar = {
  name: string;
  description: string;
  /**
   * `true` if the variable is observed to be set in this environment.
   *
   * The browser cannot read host env vars, so this is a deterministic mock
   * tied to the visual contract until the bridge ships an
   * `/api/env/status` endpoint that returns booleans only.
   */
  set: boolean;
  sensitive: boolean;
};

const ENV_VARS: EnvVar[] = [
  {
    name: "HERMES3D_ENV_FILE",
    description: "Path to the .env file consumed by the launcher",
    set: true,
    sensitive: false,
  },
  {
    name: "HERMES3D_PROFILE",
    description: "Active runtime profile (dev / staging / prod)",
    set: true,
    sensitive: false,
  },
  {
    name: "HERMES3D_LM_STUDIO_BASE_URL",
    description: "Base URL for the local LM Studio server",
    set: true,
    sensitive: false,
  },
  {
    name: "HERMES3D_OLLAMA_BASE_URL",
    description: "Base URL for the local Ollama server",
    set: false,
    sensitive: false,
  },
  {
    name: "HERMES3D_MINIMAX_API_KEY",
    description: "Cloud LLM API key (MiniMax)",
    set: false,
    sensitive: true,
  },
  {
    name: "HERMES3D_DEEPSEEK_API_KEY",
    description: "Cloud LLM API key (DeepSeek)",
    set: false,
    sensitive: true,
  },
];

export function EnvironmentSubtab() {
  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="settings-environment">
      <header className="flex items-center gap-2 text-muted">
        <Terminal size={14} />
        <span className="text-fg font-medium">Environment variables</span>
        <span className="text-[10px]">·</span>
        <span className="text-[10px]">presence only · values redacted</span>
      </header>

      <div
        className="rounded border border-accent-amber/40 bg-accent-amber/10 px-3 py-2 text-[11px] text-accent-amber"
        role="note"
      >
        <span className="font-semibold">Privacy:</span> only the presence of each variable is
        shown. Actual values are never read into the UI or rendered, so screenshots and proof
        artifacts cannot leak credentials.
      </div>

      <ul className="flex flex-col gap-1">
        {ENV_VARS.map((v) => (
          <li
            key={v.name}
            data-testid={`settings-environment-row-${v.name}`}
            className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border"
          >
            <span className="flex items-center gap-1.5 w-72 shrink-0">
              {v.sensitive ? (
                <EyeOff size={11} className="text-accent-amber shrink-0" />
              ) : (
                <Eye size={11} className="text-muted shrink-0" />
              )}
              <span className="text-fg font-mono text-[11px] truncate">{v.name}</span>
            </span>
            <span className="text-muted text-[10px] flex-1 truncate">{v.description}</span>
            <span
              data-testid={`settings-environment-status-${v.name}`}
              className="font-mono text-[11px] text-fg"
            >
              {v.set ? "[set]" : "[not set]"}
            </span>
            <StatusBadge tone={v.set ? "green" : "muted"} label={v.set ? "set" : "not set"} />
          </li>
        ))}
      </ul>

      <footer className="text-muted text-[10px] pt-2 border-t border-border">
        Sensitive variables (API keys) are flagged with the closed-eye icon. The UI never has
        access to their contents.
      </footer>
    </div>
  );
}
