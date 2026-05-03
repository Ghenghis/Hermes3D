/**
 * Settings → About subtab.
 *
 * Static panel showing version, license and reference links. All anchors
 * use `target="_blank" rel="noopener noreferrer"` because the universal
 * app frame forbids in-process navigation.
 */
import { BookOpen, ExternalLink, Github, Info, Scale } from "lucide-react";

const VERSION = "0.5.0";
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

export function AboutSubtab() {
  return (
    <div className="flex flex-col gap-3 text-xs" data-testid="settings-about">
      <header className="flex items-center gap-2 text-muted">
        <Info size={14} />
        <span className="text-fg font-medium">About Hermes3D</span>
      </header>

      <section className="grid grid-cols-2 gap-2" data-testid="settings-about-meta">
        <MetaCard label="Version" value={VERSION} />
        <MetaCard label="License" value={LICENSE} />
        <MetaCard label="Build channel" value="stable" />
        <MetaCard label="Edition" value="contract-kit" />
      </section>

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
        Hermes3D-OS — local-first 3D printing orchestrator. Phase 2 ships a mock-only React frontend.
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
