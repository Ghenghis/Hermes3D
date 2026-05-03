/**
 * Settings → Printers subtab.
 *
 * Lists the 12 printers declared in `config/printers.toml`. When the
 * service-health endpoint is available (`/api/health/services`) the live
 * online/offline status is rendered; otherwise the panel gracefully
 * degrades to the static config view.
 *
 * The service-health work itself lives on a separate branch — this subtab
 * MUST NOT change health-endpoint shape; it just consumes whatever it can.
 */
import { useEffect, useState } from "react";
import { Printer as PrinterIcon, RefreshCcw } from "lucide-react";
import { StatusBadge, type StatusTone } from "../badges/StatusBadge";

type PrinterEntry = {
  id: string;
  manufacturer: string;
  model: string;
  moonraker_url: string;
  group: string;
};

/**
 * Mock representation of `config/printers.toml`. In Phase 6 this is replaced
 * by a fetch from `/api/printers/manifest`; for now the subtab ships with a
 * deterministic mock that matches the on-disk TOML row-for-row.
 */
const PRINTERS: PrinterEntry[] = [
  // FLSUN delta fleet (6)
  { id: "flsun_qqs_pro",     manufacturer: "FLSUN",          model: "QQ-S Pro",    moonraker_url: "http://flsun-qqs-pro.local",  group: "FLSUN delta" },
  { id: "flsun_t1_a",        manufacturer: "FLSUN",          model: "T1",          moonraker_url: "http://flsun-t1-a.local",     group: "FLSUN delta" },
  { id: "flsun_t1_b",        manufacturer: "FLSUN",          model: "T1",          moonraker_url: "http://flsun-t1-b.local",     group: "FLSUN delta" },
  { id: "flsun_super_racer", manufacturer: "FLSUN",          model: "Super Racer", moonraker_url: "http://flsun-sr.local",       group: "FLSUN delta" },
  { id: "flsun_s1",          manufacturer: "FLSUN",          model: "S1",          moonraker_url: "http://flsun-s1.local",       group: "FLSUN delta" },
  { id: "flsun_v400",        manufacturer: "FLSUN",          model: "V400",        moonraker_url: "http://flsun-v400.local",     group: "FLSUN delta" },
  // Cartesian bed-slingers (4)
  { id: "creality_cr10s",    manufacturer: "Creality",       model: "CR-10S",      moonraker_url: "http://creality-cr10s.local", group: "Cartesian" },
  { id: "creality_cr6_max",  manufacturer: "Creality",       model: "CR-6 Max",    moonraker_url: "http://creality-cr6max.local",group: "Cartesian" },
  { id: "prusa_mk3s",        manufacturer: "Prusa Research", model: "MK3S+",       moonraker_url: "http://prusa-mk3s.local",     group: "Cartesian" },
  { id: "sovol_sv01",        manufacturer: "Sovol",          model: "SV01",        moonraker_url: "http://sovol-sv01.local",     group: "Cartesian" },
  // CoreXY (2)
  { id: "tronxy_d01_pro",    manufacturer: "Tronxy",         model: "D01 Pro",     moonraker_url: "http://tronxy-d01.local",     group: "CoreXY" },
  { id: "voron_2_4",         manufacturer: "Voron",          model: "2.4",         moonraker_url: "http://voron24.local",        group: "CoreXY" },
];

type HealthState = "loading" | "live" | "unavailable";

type ServiceHealthEntry = {
  id?: string;
  online?: boolean;
  status?: string;
};

export function PrintersSubtab() {
  const [health, setHealth] = useState<Record<string, boolean>>({});
  const [state, setState] = useState<HealthState>("loading");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch("/api/health/services", {
          method: "GET",
          headers: { Accept: "application/json" },
          cache: "no-store",
        });
        if (!response.ok) {
          if (!cancelled) setState("unavailable");
          return;
        }
        const payload = (await response.json()) as unknown;
        const map: Record<string, boolean> = {};
        if (Array.isArray(payload)) {
          for (const raw of payload) {
            if (raw && typeof raw === "object") {
              const entry = raw as ServiceHealthEntry;
              if (typeof entry.id === "string") {
                map[entry.id] = entry.online === true || entry.status === "online";
              }
            }
          }
        } else if (payload && typeof payload === "object") {
          const obj = payload as Record<string, unknown>;
          for (const key of Object.keys(obj)) {
            const v = obj[key];
            if (typeof v === "boolean") map[key] = v;
            else if (v && typeof v === "object") {
              const entry = v as ServiceHealthEntry;
              map[key] = entry.online === true || entry.status === "online";
            }
          }
        }
        if (!cancelled) {
          setHealth(map);
          setState("live");
        }
      } catch {
        if (!cancelled) setState("unavailable");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const groups = Array.from(new Set(PRINTERS.map((p) => p.group)));

  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="settings-printers">
      <header className="flex items-center gap-2 text-muted">
        <PrinterIcon size={14} />
        <span className="text-fg font-medium">Printer fleet</span>
        <span className="text-[10px]">·</span>
        <span className="text-[10px]">{PRINTERS.length} units · printers.toml</span>
        <span className="ml-auto inline-flex items-center gap-1.5">
          <RefreshCcw size={11} className="text-muted" />
          <HealthStateBadge state={state} />
        </span>
      </header>

      {groups.map((group) => (
        <section
          key={group}
          className="flex flex-col gap-1"
          data-testid={`settings-printers-group-${group.replace(/\s+/g, "-").toLowerCase()}`}
        >
          <h3 className="text-fg text-[11px] uppercase tracking-wide">{group}</h3>
          <ul className="flex flex-col gap-1">
            {PRINTERS.filter((p) => p.group === group).map((p) => {
              const online = state === "live" ? !!health[p.id] : null;
              const tone: StatusTone =
                online === null ? "muted" : online ? "green" : "red";
              const label =
                online === null ? "config" : online ? "online" : "offline";
              return (
                <li
                  key={p.id}
                  data-testid={`settings-printers-row-${p.id}`}
                  className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border"
                >
                  <span className="text-fg text-[11px] font-medium w-44 shrink-0 truncate">
                    {p.manufacturer} {p.model}
                  </span>
                  <span className="text-muted font-mono text-[10px] hidden md:inline truncate">
                    {p.id}
                  </span>
                  <span className="text-fg font-mono text-[10px] flex-1 truncate">
                    {p.moonraker_url}
                  </span>
                  <StatusBadge tone={tone} label={label} />
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      <footer className="text-muted text-[10px] pt-2 border-t border-border">
        Health is fetched from <span className="font-mono">/api/health/services</span> when
        available; the static config view renders otherwise.
      </footer>
    </div>
  );
}

function HealthStateBadge({ state }: { state: HealthState }) {
  if (state === "live") return <StatusBadge tone="green" label="live" />;
  if (state === "loading") return <StatusBadge tone="cyan" label="loading" />;
  return <StatusBadge tone="muted" label="config-only" />;
}
