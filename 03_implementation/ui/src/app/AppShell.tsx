import type { ReactNode } from "react";
import { Sidebar } from "../components/layout/Sidebar";
import { TopBar } from "../components/layout/TopBar";
import {
  StatusBannerHost,
  type BannerSourcesOverride,
} from "../components/StatusBanners";
import { TABS } from "./routes";
import { useStore } from "./store";

/**
 * Read the `?banner=test` query flag and return a deterministic
 * `BannerSourcesOverride` that emits exactly one provider-failure banner.
 *
 * The override is keyed off a synthetic provider id (`__test_provider`) so
 * it can never collide with a real provider, and is only produced when the
 * URL explicitly opts in. Production paths receive `undefined` and fall
 * through to the live `useBannerSources()` hook.
 *
 * Why a query flag and not env: the failing Playwright spec
 * `tests/e2e/gui-theme-banners.spec.ts` navigates to `/?banner=test` after
 * detecting that `<ThemeProvider>`/`<ThemeSwitcher>` are mounted (live-host
 * branch). This hook is the wiring contract that spec assumed.
 */
function useTestBannerOverride(): BannerSourcesOverride | undefined {
  if (typeof window === "undefined") return undefined;
  const search = new URLSearchParams(window.location.search);
  if (search.get("banner") !== "test") return undefined;
  return {
    providers: [
      {
        id: "__test_provider",
        label: "(test) provider",
        state: "error",
        message: "deterministic provider-failure for E2E spec",
      },
    ],
  };
}

/**
 * Universal shell per `TAB_SPECS.md` §"Universal shell":
 *  - Left vertical sidebar with icons + labels.
 *  - Top header with system state, branch/release, proof status.
 *  - Banner host stacked directly under the topbar, above main content.
 *  - Main content uses responsive grid cards.
 *  - Right inspector rail appears where helpful (per-tab, not in shell).
 */
export function AppShell({ children }: { children?: ReactNode }) {
  const activeTabId = useStore((s) => s.activeTabId);
  const activeTab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];
  const dashboard = activeTab.id === "dashboard";
  const bannerOverride = useTestBannerOverride();

  return (
    <div className="flex h-screen overflow-hidden bg-bg text-fg">
      <Sidebar />
      <div className="flex min-h-0 flex-1 flex-col">
        <TopBar activeLabel={activeTab.label} />
        <StatusBannerHost sourcesOverride={bannerOverride} />
        <main className={dashboard ? "min-h-0 flex-1 overflow-auto p-2.5" : "min-h-0 flex-1 overflow-auto p-2.5"}>
          {children}
        </main>
      </div>
    </div>
  );
}
