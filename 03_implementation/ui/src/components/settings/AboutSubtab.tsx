/**
 * Settings → About subtab.
 *
 * Displays version, license, and reference links.  Version data is fetched
 * from GET /api/settings/update-center so no version string is hardcoded here.
 * Falls back to "loading…" / "unknown" if the backend is unreachable.
 *
 * All anchors use `target="_blank" rel="noopener noreferrer"` because the
 * universal app frame forbids in-process navigation.
 */
import { useEffect, useState } from "react";
import { BookOpen, ExternalLink, Github, Info, Scale } from "lucide-react";

type HermesImportMeta = ImportMeta & {
  env: { VITE_HERMES3D_BRIDGE_PORT?: string };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const LICENSE = "Apache-2.0";

const LINKS: { label: string; href: string; Icon: typeof Github; description: string }[] = [
  {
    label: "GitHub",
    href: "https://github.com/Ghenghis/Hermes3D",
    Icon: Github,
    description: "Source repository, issues, releases",
  },
  {
    label: "Documentation",
    href: "https://github.com/Ghenghis/Hermes3D#readme",
    Icon: BookOpen,
    description: "README + contract kit reference",
  },
  {
    label: "License",
    href: "https://www.apache.org/licenses/LICENSE-2.0",
    Icon: Scale,
    description: "Apache License, Version 2.0",
  },
];

type ComponentVersion = {
  component: string;
  version: string;
};

export function AboutSubtab() {
  const [versions, setVersions] = useState<ComponentVersion[]>([]);
  const [versionState, setVersionState] = useState<"loading" | "ready" | "unavailable">("loading");

  useEffect(() => {
    let mounted = true;
    fetch(`${BASE_URL}/api/settings/update-center`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status}`))))
      .then((data: { components?: ComponentVersion[] }) => {
        if (!mounted) return;
        setVersions(Array.isArray(data.components) ? data.components : []);
        setVersionState("ready");
      })
      .catch(() => {
        if (!mounted) return;
        setVersionState("unavailable");
      });
    return () => {
      mounted = false;
    };
  }, []);

  const uiVersion =
    versions.find((c) => c.component === "hermes3d-ui")?.version ??
    (versionState === "loading" ? "loading…" : "unknown");

  const backendVersion =
    versions.find((c) => c.component === "hermes3d-backend")?.version ??
    (versionState === "loading" ? "loading…" : "unknown");

  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="settings-about">
      <header className="flex items-center gap-2 text-muted">
        <Info size={14} />
        <span className="text-fg font-medium">About Hermes3D</span>
      </header>

      <section className="grid grid-cols-2 gap-2" data-testid="settings-about-meta">
        <MetaCard label="UI Version" value={uiVersion} />
        <MetaCard label="Backend Version" value={backendVersion} />
        <MetaCard label="License" value={LICENSE} />
        <MetaCard label="Edition" value="contract-kit" />
      </section>

      {versionState === "unavailable" && (
        <p className="text-[10px] text-muted">
          Could not fetch live version data from the backend. Versions shown as &quot;unknown&quot;.
        </p>
      )}

      <section className="flex flex-col gap-1" data-testid="settings-about-links">
        <h3 className="text-fg text-[11px] uppercase tracking-wide">Links</h3>
        <ul className="flex flex-col gap-1">
          {LINKS.map((link) => {
            const Icon = link.Icon;
            return (
              <li key={link.label}>
                <a
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-2 py-1.5 rounded bg-surface2/40 border border-border hover:bg-surface2/60"
                >
                  <Icon size={13} className="text-accent-cyan shrink-0" />
                  <span className="text-fg text-[11px] font-medium w-36 shrink-0 truncate">
                    {link.label}
                  </span>
                  <span className="text-muted text-[10px] flex-1 truncate">
                    {link.description}
                  </span>
                  <span className="text-muted font-mono text-[10px] hidden md:inline truncate">
                    {link.href}
                  </span>
                  <ExternalLink size={11} className="text-muted shrink-0" />
                </a>
              </li>
            );
          })}
        </ul>
      </section>

      <footer className="text-muted text-[10px] pt-2 border-t border-border">
        Hermes3D-OS — local-first 3D printing orchestrator backed by the local GUI API.
      </footer>
    </div>
  );
}

function MetaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 px-3 py-2 rounded bg-surface2/40 border border-border">
      <span className="text-muted text-[10px] uppercase tracking-wide">{label}</span>
      <span className="text-fg font-mono text-[12px]">{value}</span>
    </div>
  );
}
