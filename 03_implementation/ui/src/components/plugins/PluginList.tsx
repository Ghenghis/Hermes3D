/**
 * PluginList — grid of installed-plugin cards. Falls back to an honest
 * "no plugins returned" message when `GET /api/plugins` returns an empty
 * list (never synthesizes fake data).
 *
 * Sources consulted:
 *   - VS Code Extensions Marketplace grid layout:
 *     https://marketplace.visualstudio.com/vscode
 *   - GitHub Apps gallery card grid:
 *     https://github.com/marketplace?type=apps
 */
import type { Plugin } from "../../types/plugin";
import { PluginCard } from "./PluginCard";

interface PluginListProps {
  plugins: Plugin[];
  onOpenEndpoint: (plugin: Plugin, kind: "config" | "logs") => void | Promise<void>;
  onActivate: (plugin: Plugin) => void | Promise<void>;
}

export function PluginList({ plugins, onOpenEndpoint, onActivate }: PluginListProps) {
  if (plugins.length === 0) {
    return (
      <section
        data-testid="plugin-list-empty"
        className="rounded border border-border bg-surface p-4 text-sm text-muted sm:col-span-2 md:col-span-3"
      >
        No plugins returned from the live plugin API.
      </section>
    );
  }

  return (
    <>
      {plugins.map((plugin) => (
        <PluginCard
          key={plugin.id}
          plugin={plugin}
          onOpenEndpoint={onOpenEndpoint}
          onActivate={onActivate}
        />
      ))}
    </>
  );
}
