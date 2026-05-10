import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AppRegistryTab } from "./tabs/AppRegistry";
import "./styles/globals.css";

const APPS_HASH_PREFIX = "apps";

function isAppsHash(hash: string): boolean {
  const trimmed = hash.replace(/^#/, "").trim();
  if (!trimmed) {
    return false;
  }
  const [prefix] = trimmed.split("/", 1);
  return prefix === APPS_HASH_PREFIX;
}

/**
 * Root — gates on `#apps[/<id>]` so the App Registry surface can be
 * reached as a standalone route without modifying App.tsx (currently
 * owned by W6-3 lane).
 *
 * TODO(W6-3 follow-up): once W6-3 lands DashboardAdvanced, embed
 * <AppStatusPanel /> directly in that mode and remove this hash gate.
 * The gate is purely an integration shim while the dashboard tabs are
 * being authored by parallel lanes.
 */
function Root() {
  const [appsRoute, setAppsRoute] = useState<boolean>(() =>
    typeof window === "undefined" ? false : isAppsHash(window.location.hash),
  );

  useEffect(() => {
    const sync = () => setAppsRoute(isAppsHash(window.location.hash));
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

  return <App />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
