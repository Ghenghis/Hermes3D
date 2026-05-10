/**
 * useBannerSources — adapts cross-cutting GUI status hooks into a unified
 * banner descriptor list.
 *
 * The four canonical sources for v0 are:
 *   1. Hermes Agent outdated  — when `useAgents()` reports a newer
 *      upstream version available (W8-2 will provide this hook; until
 *      it ships we read a window-injected stub or returns an empty array).
 *   2. Provider failure       — when any LLM provider (LM Studio,
 *      DeepSeek, MiniMax, SiliconFlow) is in `error` state.
 *   3. Recovery in progress   — RC v2 active loop running.
 *   4. Printer safety blocked — W6-9 printer-bed safety gate triggered.
 *
 * Each source is wired through a small adapter so the hook is testable in
 * isolation: tests pass a `BannerSourcesOverride` to short-circuit the
 * real hooks.
 *
 * If a sibling lane has not yet shipped its hook, the adapter falls back
 * to `null` -- producing zero banners, never a runtime error.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import type { BannerDescriptor } from "./StatusBanner";

const DISMISS_STORAGE_KEY = "h3d.banners.dismissed";

export interface AgentSnapshot {
  installed_version?: string | null;
  upstream_version?: string | null;
  upstream_release_url?: string | null;
}

export interface ProviderSnapshot {
  id: string;
  label: string;
  state: "ok" | "degraded" | "error" | "unknown";
  message?: string | null;
}

export interface RecoverySnapshot {
  active: boolean;
  phase?: string | null;
  /** Human-readable label, e.g. "saga step 3/5". */
  detail?: string | null;
}

export interface PrinterSafetySnapshot {
  blocked: boolean;
  reason?: string | null;
}

export interface BannerSourcesOverride {
  agent?: AgentSnapshot | null;
  providers?: ProviderSnapshot[] | null;
  recovery?: RecoverySnapshot | null;
  printerSafety?: PrinterSafetySnapshot | null;
}

interface DismissedRecord {
  /** banner id -> resolved flag at dismissal time, so re-dismiss isn't required. */
  [bannerId: string]: { dismissedAtMs: number };
}

function readDismissed(): DismissedRecord {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(DISMISS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as DismissedRecord;
    }
  } catch {
    // ignore
  }
  return {};
}

function writeDismissed(record: DismissedRecord): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(DISMISS_STORAGE_KEY, JSON.stringify(record));
  } catch {
    // ignore
  }
}

/**
 * Build the banner list from the four source snapshots. Pure function for
 * testing. The dismissed set + auto-resolve filter is applied separately
 * inside the hook.
 */
export function buildBanners(
  sources: BannerSourcesOverride,
  navigate: (path: string) => void,
): BannerDescriptor[] {
  const out: BannerDescriptor[] = [];

  // 1. Hermes Agent outdated.
  const agent = sources.agent;
  if (
    agent &&
    agent.installed_version &&
    agent.upstream_version &&
    agent.installed_version !== agent.upstream_version
  ) {
    out.push({
      id: "agent-outdated",
      severity: "warning",
      title: "Hermes Agent update available",
      description: `Installed ${agent.installed_version}, upstream ${agent.upstream_version}. Update to pick up the latest provider patches.`,
      action: {
        label: "View update",
        onClick: () => navigate("#agents"),
        href: agent.upstream_release_url ?? undefined,
      },
    });
  }

  // 2. Provider failure.
  const providers = sources.providers ?? [];
  const failed = providers.filter((p) => p.state === "error");
  if (failed.length > 0) {
    const names = failed.map((p) => p.label).join(", ");
    out.push({
      id: "provider-failure",
      severity: "error",
      title: `${failed.length} provider${failed.length === 1 ? "" : "s"} unreachable`,
      description: `Failed: ${names}. Open Settings to inspect error logs.`,
      action: {
        label: "Open settings",
        onClick: () => navigate("#settings"),
      },
    });
  }

  // 3. Recovery in progress.
  const recovery = sources.recovery;
  if (recovery?.active) {
    out.push({
      id: "recovery-active",
      severity: "info",
      title: "Recovery Controller active",
      description:
        recovery.detail ??
        recovery.phase ??
        "Hermes Agent Recovery Controller is running a saga.",
      action: {
        label: "Open Observe",
        onClick: () => navigate("#observe"),
      },
      dismissible: false,
    });
  }

  // 4. Printer safety blocked.
  const printer = sources.printerSafety;
  if (printer?.blocked) {
    out.push({
      id: "printer-safety",
      severity: "error",
      title: "Printer safety gate engaged",
      description:
        printer.reason ??
        "A printer safety pre-check failed. Print jobs are paused until cleared.",
      action: {
        label: "Open Printers",
        onClick: () => navigate("#printers"),
      },
      dismissible: false,
    });
  }

  return out;
}

export interface UseBannerSourcesOptions {
  /**
   * Test-only: bypass the real hooks (which a sibling lane provides) and
   * inject deterministic snapshots.
   */
  override?: BannerSourcesOverride;
  /**
   * Hash-fragment navigator. Defaults to writing to `window.location.hash`.
   */
  navigate?: (path: string) => void;
}

/**
 * Production hook. Reads sibling-lane hooks defensively (try/catch) so
 * banner-host mounts never crash if a hook isn't shipped yet.
 */
export function useBannerSources(
  options: UseBannerSourcesOptions = {},
): {
  banners: BannerDescriptor[];
  dismiss: (id: string) => void;
  reset: () => void;
} {
  const navigate = useMemo(
    () =>
      options.navigate ??
      ((path: string) => {
        if (typeof window !== "undefined") {
          window.location.hash = path.startsWith("#") ? path.slice(1) : path;
        }
      }),
    [options.navigate],
  );

  const [dismissed, setDismissed] = useState<DismissedRecord>(() =>
    readDismissed(),
  );

  // Merge override (test) with whatever fallback we can read at runtime.
  // For now the production fallback is "no data" -- W8-2 will provide
  // useAgents/useProviders/useRecovery/usePrinterSafety hooks; until then
  // we render zero banners unless tests pass an override.
  const sources: BannerSourcesOverride = options.override ?? {
    agent: null,
    providers: null,
    recovery: null,
    printerSafety: null,
  };

  const all = useMemo(
    () => buildBanners(sources, navigate),
    [sources, navigate],
  );

  // Filter out user-dismissed banners; auto-resolve uses descriptor's
  // `autoResolveOn` if present.
  const banners = useMemo(
    () =>
      all.filter((banner) => {
        if (dismissed[banner.id]) return false;
        if (banner.autoResolveOn && banner.autoResolveOn() === false) {
          return false;
        }
        return true;
      }),
    [all, dismissed],
  );

  // Auto-prune dismissed records for banners that no longer appear in the
  // source list — that way if (e.g.) a provider recovers then re-fails,
  // the user still sees the new banner.
  useEffect(() => {
    const liveIds = new Set(all.map((b) => b.id));
    let mutated = false;
    const next: DismissedRecord = { ...dismissed };
    for (const id of Object.keys(next)) {
      if (!liveIds.has(id)) {
        delete next[id];
        mutated = true;
      }
    }
    if (mutated) {
      setDismissed(next);
      writeDismissed(next);
    }
  }, [all, dismissed]);

  const dismiss = useCallback((id: string) => {
    setDismissed((prev) => {
      const next: DismissedRecord = {
        ...prev,
        [id]: { dismissedAtMs: Date.now() },
      };
      writeDismissed(next);
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    setDismissed({});
    writeDismissed({});
  }, []);

  return { banners, dismiss, reset };
}

export const __testing = { DISMISS_STORAGE_KEY, readDismissed, writeDismissed };
