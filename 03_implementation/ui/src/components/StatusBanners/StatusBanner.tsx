/**
 * StatusBanner — atomic banner card. The host (StatusBannerHost) renders a
 * stack of these from a `BannerDescriptor[]` source.
 *
 * Severity tiers control:
 *   - icon glyph
 *   - background tone (token-driven so theme switches stay consistent)
 *   - ARIA role: `alert` for critical, `status` for info/success.
 *
 * Action button is optional; when omitted the banner is purely
 * informational. Dismiss button is always rendered unless `dismissible`
 * is explicitly false.
 */
import {
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Info,
  X,
} from "lucide-react";

export type BannerSeverity = "info" | "success" | "warning" | "error";

export interface BannerAction {
  label: string;
  onClick: () => void;
  /** href for plain anchor links — when set, renders `<a>` instead. */
  href?: string;
}

export interface BannerDescriptor {
  /** Unique identifier — used for dismiss persistence + React keys. */
  id: string;
  severity: BannerSeverity;
  title: string;
  /** Optional secondary message. */
  description?: string;
  /** Optional CTA button. */
  action?: BannerAction;
  /** Set to false to hide the dismiss button. Defaults to true. */
  dismissible?: boolean;
  /**
   * If set, the host will treat the banner as "auto-dismissed" once the
   * underlying source returns false (resolution). Distinct from a manual
   * user dismiss.
   */
  autoResolveOn?: () => boolean;
}

const SEVERITY_STYLES: Record<
  BannerSeverity,
  { container: string; icon: JSX.Element; ariaRole: "alert" | "status" }
> = {
  error: {
    container:
      "border-accent-red/60 bg-accent-red/10 text-fg",
    icon: <AlertOctagon size={16} className="text-accent-red" aria-hidden />,
    ariaRole: "alert",
  },
  warning: {
    container:
      "border-accent-amber/60 bg-accent-amber/10 text-fg",
    icon: <AlertTriangle size={16} className="text-accent-amber" aria-hidden />,
    ariaRole: "alert",
  },
  info: {
    container:
      "border-accent-blue/60 bg-accent-blue/10 text-fg",
    icon: <Info size={16} className="text-accent-blue" aria-hidden />,
    ariaRole: "status",
  },
  success: {
    container:
      "border-accent-green/60 bg-accent-green/10 text-fg",
    icon: <CheckCircle2 size={16} className="text-accent-green" aria-hidden />,
    ariaRole: "status",
  },
};

export interface StatusBannerProps {
  banner: BannerDescriptor;
  onDismiss: (id: string) => void;
}

export function StatusBanner({
  banner,
  onDismiss,
}: StatusBannerProps): JSX.Element {
  const style = SEVERITY_STYLES[banner.severity];
  const dismissible = banner.dismissible !== false;
  return (
    <div
      role={style.ariaRole}
      aria-live={style.ariaRole === "alert" ? "assertive" : "polite"}
      data-testid={`status-banner-${banner.id}`}
      data-severity={banner.severity}
      className={[
        "flex flex-wrap items-center gap-2 border-l-4 px-3 py-2",
        "rounded-r-md text-xs",
        style.container,
      ].join(" ")}
    >
      <span className="flex shrink-0 items-center">{style.icon}</span>
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="font-semibold text-sm leading-tight">
          {banner.title}
        </span>
        {banner.description ? (
          <span className="text-muted text-[11px] leading-tight mt-0.5">
            {banner.description}
          </span>
        ) : null}
      </div>
      {banner.action ? (
        banner.action.href ? (
          <a
            href={banner.action.href}
            data-testid={`status-banner-action-${banner.id}`}
            className="rounded border border-border bg-surface px-2 py-1 text-xs font-medium text-fg hover:bg-surface2"
            onClick={banner.action.onClick}
          >
            {banner.action.label}
          </a>
        ) : (
          <button
            type="button"
            data-testid={`status-banner-action-${banner.id}`}
            onClick={banner.action.onClick}
            className="rounded border border-border bg-surface px-2 py-1 text-xs font-medium text-fg hover:bg-surface2"
          >
            {banner.action.label}
          </button>
        )
      ) : null}
      {dismissible ? (
        <button
          type="button"
          aria-label={`Dismiss ${banner.title}`}
          data-testid={`status-banner-dismiss-${banner.id}`}
          onClick={() => onDismiss(banner.id)}
          className="ml-1 rounded p-1 text-muted hover:text-fg hover:bg-surface2"
        >
          <X size={14} aria-hidden />
        </button>
      ) : null}
    </div>
  );
}
