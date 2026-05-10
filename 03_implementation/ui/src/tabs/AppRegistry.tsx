/**
 * AppRegistryTab — host for the App Status Panel + Detail Panel.
 *
 * Routing:
 *   - `#apps`         → AppStatusPanel (60-app table)
 *   - `#apps/<id>`    → AppDetailPanel for that app
 *
 * Both views share the same root testid (`apps-root`) so the existing
 * Playwright openTab() helper works without tab-fixture changes.
 *
 * Coordination:
 *   - W6-3 owns DashboardAdvanced. If/when that branch lands, embedding
 *     <AppStatusPanel /> directly in DashboardAdvanced is a one-line
 *     import. Until then, this tab is the standalone surface called out
 *     in the deliverable list.
 */

import { useEffect, useState } from "react";
import { AppStatusPanel } from "../components/AppRegistry/AppStatusPanel";
import { AppDetailPanel } from "../components/AppRegistry/AppDetailPanel";

const APPS_HASH_PREFIX = "apps";

function parseAppsHash(rawHash: string): string | null {
  const trimmed = rawHash.replace(/^#/, "").trim();
  if (!trimmed) {
    return null;
  }
  const [prefix, id] = trimmed.split("/", 2);
  if (prefix !== APPS_HASH_PREFIX) {
    return null;
  }
  return id ? decodeURIComponent(id) : null;
}

export function AppRegistryTab() {
  const [activeAppId, setActiveAppId] = useState<string | null>(() =>
    typeof window === "undefined" ? null : parseAppsHash(window.location.hash),
  );

  useEffect(() => {
    const sync = () => {
      setActiveAppId(parseAppsHash(window.location.hash));
    };
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  const handleClose = () => {
    window.location.hash = APPS_HASH_PREFIX;
  };

  return (
    <div data-testid="apps-root" className="flex min-h-0 w-full flex-col gap-3">
      {activeAppId ? (
        <AppDetailPanel appId={activeAppId} onClose={handleClose} />
      ) : (
        <AppStatusPanel
          onNavigateDetail={(id) => {
            window.location.hash = `${APPS_HASH_PREFIX}/${encodeURIComponent(id)}`;
          }}
        />
      )}
    </div>
  );
}
