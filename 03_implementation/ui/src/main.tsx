import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AppRegistryTab } from "./tabs/AppRegistry";
import { ServiceHealthPage } from "./components/health/ServiceHealthPage";
import "./styles/globals.css";

const APPS_HASH_PREFIX = "apps";
const HEALTH_HASH_PREFIX = "health";

function hashPrefix(hash: string): string | null {
  const trimmed = hash.replace(/^#/, "").trim();
  if (!trimmed) {
    return null;
  }
  const [prefix] = trimmed.split("/", 1);
  return prefix ?? null;
}

function isAppsHash(hash: string): boolean {
  return hashPrefix(hash) === APPS_HASH_PREFIX;
}

function isHealthHash(hash: string): boolean {
  return hashPrefix(hash) === HEALTH_HASH_PREFIX;
}

/**
 * Root — gates on `#apps[/<id>]` so the App Registry surface can be
 * reached as a standalone route without modifying App.tsx (currently
 * owned by W6-3 lane). W11-2 adds a parallel `#health` gate so the
 * Service Health page (#42) is reachable for E2E proof while AppShell
 * wiring of `ServiceHealthPage` is owned by a downstream lane.
 *
 * TODO(W6-3 follow-up): once W6-3 lands DashboardAdvanced, embed
 * <AppStatusPanel /> + <ServiceHealthPage /> directly in that mode and
 * remove these hash gates. They are purely integration shims while the
 * dashboard tabs are being authored by parallel lanes.
 */
function Root() {
  const [appsRoute, setAppsRoute] = useState<boolean>(() =>
    typeof window === "undefined" ? false : isAppsHash(window.location.hash),
  );
  const [healthRoute, setHealthRoute] = useState<boolean>(() =>
    typeof window === "undefined" ? false : isHealthHash(window.location.hash),
  );

  useEffect(() => {
    const sync = () => {
      setAppsRoute(isAppsHash(window.location.hash));
      setHealthRoute(isHealthHash(window.location.hash));
    };
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
    };
  }, []);

  if (appsRoute) {
    return (
      <div className="flex h-screen flex-col overflow-hidden bg-bg p-3 text-fg">
        <header className="mb-3 flex items-center justify-between border-b border-border/60 pb-2">
          <h1 className="text-sm font-semibold text-fg">Hermes3D · App Registry</h1>
          <a
            href="#dashboard"
            className="rounded border border-border px-2 py-1 text-[11px] text-fg hover:bg-surface2"
          >
            Back to dashboard
          </a>
        </header>
        <main className="min-h-0 flex-1 overflow-auto">
          <AppRegistryTab />
        </main>
      </div>
    );
  }

  if (healthRoute) {
    return (
      <div className="flex h-screen flex-col overflow-hidden bg-bg p-3 text-fg">
        <header className="mb-3 flex items-center justify-between border-b border-border/60 pb-2">
          <h1 className="text-sm font-semibold text-fg">Hermes3D · Service Health</h1>
          <a
            href="#dashboard"
            className="rounded border border-border px-2 py-1 text-[11px] text-fg hover:bg-surface2"
          >
            Back to dashboard
          </a>
        </header>
        <main className="min-h-0 flex-1 overflow-auto">
          <ServiceHealthPage />
        </main>
      </div>
    );
  }

  return <App />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
