/**
 * StatusBannerHost — top-of-page region that stacks active banners.
 *
 * Drop this directly under the topbar (still owned by another lane, so
 * adopters wire it from `<App />` or their shell). Layout:
 *
 *   <header>...topbar...</header>
 *   <StatusBannerHost />
 *   <main>...page content...</main>
 *
 * The host is intentionally side-effect-light: all data flows through
 * `useBannerSources()`. Tests override the data via the `sourcesOverride`
 * prop without monkey-patching the hook tree.
 */
import { StatusBanner } from "./StatusBanner";
import {
  useBannerSources,
  type BannerSourcesOverride,
} from "./useBannerSources";

export interface StatusBannerHostProps {
  /**
   * Test seam — when set, replaces the live data sources with the given
   * snapshot so component tests stay deterministic.
   */
  sourcesOverride?: BannerSourcesOverride;
  /**
   * Optional hash-fragment navigator. Defaults to writing
   * `window.location.hash`.
   */
  navigate?: (path: string) => void;
  /** Optional className — host wrapper. */
  className?: string;
}

export function StatusBannerHost({
  sourcesOverride,
  navigate,
  className,
}: StatusBannerHostProps): JSX.Element | null {
  const { banners, dismiss } = useBannerSources({
    override: sourcesOverride,
    navigate,
  });

  if (banners.length === 0) return null;

  return (
    <div
      data-testid="status-banner-host"
      className={[
        "flex flex-col gap-1.5",
        "border-b border-border bg-bg/95 px-3 py-2",
        className ?? "",
      ].join(" ")}
    >
      {banners.map((banner) => (
        <StatusBanner key={banner.id} banner={banner} onDismiss={dismiss} />
      ))}
    </div>
  );
}
