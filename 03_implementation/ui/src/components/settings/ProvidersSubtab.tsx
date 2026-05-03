/**
 * Settings → Providers subtab.
 *
 * Read-only display of `config/llm_policy.yaml` shape — local LLM endpoints
 * (LM Studio + Ollama) and cloud provider toggles. Phase 2 mock data only;
 * the underlying provider chain itself is owned by another track and is NOT
 * touched here. Save actions stay locked until the config-diff/validation
 * pipeline ships.
 */
import { Cloud, Cpu, Server } from "lucide-react";
import { LockedAction } from "../badges/LockedAction";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";

type ProviderRow = {
  id: string;
  label: string;
  endpoint: string;
  detail: string;
  tone: StatusTone;
  status: string;
};

const LOCAL_PROVIDERS: ProviderRow[] = [
  {
    id: "lm_studio",
    label: "LM Studio",
    endpoint: "http://127.0.0.1:1234/v1",
    detail: "OpenAI-compatible · local",
    tone: "green",
    status: "configured",
  },
  {
    id: "ollama",
    label: "Ollama",
    endpoint: "http://127.0.0.1:11434",
    detail: "native · local",
    tone: "green",
    status: "configured",
  },
];

const CLOUD_PROVIDERS: ProviderRow[] = [
  {
    id: "minimax",
    label: "MiniMax",
    endpoint: "https://api.minimax.io/v1",
    detail: "api_key_env: HERMES3D_MINIMAX_API_KEY",
    tone: "muted",
    status: "disabled",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    endpoint: "https://api.deepseek.com/v1",
    detail: "api_key_env: HERMES3D_DEEPSEEK_API_KEY",
    tone: "muted",
    status: "disabled",
  },
  {
    id: "openai_fixture",
    label: "openai-fixture",
    endpoint: "fixture://openai",
    detail: "default allowlisted provider",
    tone: "cyan",
    status: "allowlisted",
  },
];

const POLICY_ROWS: { k: string; v: string; tone: StatusTone }[] = [
  { k: "default_mode", v: "template", tone: "cyan" },
  { k: "fallback_mode", v: "template", tone: "muted" },
  { k: "cost_cap_usd_per_run", v: "0.05", tone: "amber" },
  { k: "cost_cap_usd_per_day", v: "1.00", tone: "amber" },
  { k: "timeout_seconds", v: "30", tone: "muted" },
  { k: "max_completion_tokens", v: "1024", tone: "muted" },
];

export function ProvidersSubtab() {
  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="settings-providers">
      <header className="flex items-center gap-2 text-muted">
        <Server size={14} />
        <span className="text-fg font-medium">LLM provider configuration</span>
        <span className="text-[10px]">·</span>
        <span className="text-[10px]">read-only view of llm_policy.yaml</span>
      </header>

      <ProviderGroup
        title="Local providers"
        Icon={Cpu}
        rows={LOCAL_PROVIDERS}
        testid="settings-providers-local"
      />
      <ProviderGroup
        title="Cloud providers"
        Icon={Cloud}
        rows={CLOUD_PROVIDERS}
        testid="settings-providers-cloud"
      />

      <section
        className="flex flex-col gap-1 border-t border-border pt-3"
        data-testid="settings-providers-policy"
      >
        <h3 className="text-fg text-[11px] uppercase tracking-wide">Policy caps</h3>
        <ul className="flex flex-col gap-1">
          {POLICY_ROWS.map((r) => (
            <li
              key={r.k}
              className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border"
            >
              <span className="text-muted text-[10px] uppercase tracking-wide w-44 shrink-0 truncate">
                {r.k}
              </span>
              <span className="text-fg font-mono text-[11px] flex-1 truncate">{r.v}</span>
              <StatusBadge tone={r.tone} label="config" />
            </li>
          ))}
        </ul>
      </section>

      <footer className="flex items-center justify-between pt-2 border-t border-border">
        <span className="text-muted text-[10px]">
          Provider chain is owned upstream — this view is read-only. Save wiring lands in Phase 6.
        </span>
        <div className="flex gap-1.5">
          <LockedAction label="Reload llm_policy.yaml" />
          <LockedAction label="Save changes" hint="locked · provider chain is read-only here" />
        </div>
      </footer>
    </div>
  );
}

function ProviderGroup({
  title,
  Icon,
  rows,
  testid,
}: {
  title: string;
  Icon: typeof Cpu;
  rows: ProviderRow[];
  testid: string;
}) {
  return (
    <section className="flex flex-col gap-1" data-testid={testid}>
      <h3 className="flex items-center gap-1.5 text-fg text-[11px] uppercase tracking-wide">
        <Icon size={12} />
        {title}
      </h3>
      <ul className="flex flex-col gap-1">
        {rows.map((r) => (
          <li
            key={r.id}
            className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border"
          >
            <span className="text-fg text-[11px] font-medium w-32 shrink-0 truncate">
              {r.label}
            </span>
            <span className="text-fg font-mono text-[11px] flex-1 truncate">{r.endpoint}</span>
            <span className="text-muted text-[10px] hidden md:inline truncate">{r.detail}</span>
            <StatusBadge tone={r.tone} label={r.status} />
          </li>
        ))}
      </ul>
    </section>
  );
}
