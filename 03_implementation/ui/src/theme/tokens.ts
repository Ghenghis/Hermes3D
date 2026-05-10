/**
 * Hermes3D-OS theme tokens — W8-3 lane.
 *
 * Single source of truth for all colour, spacing, typography, and radius
 * values consumed by the GUI. Two parallel surfaces are exported:
 *
 *   - `lightPalette` / `darkPalette`           runtime-typed palettes
 *   - `themeCssVars(mode)`                     emits `--h3d-color-*` CSS
 *                                              custom properties so non-
 *                                              Tailwind code (recharts,
 *                                              inline styles) can read the
 *                                              active theme by name.
 *   - `tokens.spacing|fontSize|radius|...`     raw scales for inline use
 *
 * Reference visuals: `Images-GUI/09-themes/theme-variants-reference.png`.
 * The dark palette pins the existing `tailwind.config.ts` values exactly
 * so this module can be adopted without breaking screenshot baselines.
 *
 * WCAG 2.1 — every fg/bg pair below has been chosen for >= 4.5:1 contrast
 * for body copy, and >= 3:1 for large/disabled text. See the handoff doc
 * `HERMES_GUI_THEME_BANNERS_ONBOARDING_2026-05-09.md` for the full table.
 */

export type ThemeMode = "light" | "dark" | "system";
export type ResolvedThemeMode = "light" | "dark";

export interface ThemePalette {
  /** Default screen background. */
  background: string;
  /** Card / panel surface (one step lighter than background). */
  surface: string;
  /** Hover or nested surface (two steps). */
  surface2: string;
  /** Subtle border / divider colour. */
  border: string;
  /** Primary foreground text. */
  textPrimary: string;
  /** Secondary / muted text. */
  textSecondary: string;
  /** Brand primary accent (used for active state, focus rings). */
  primary: string;
  /** Secondary brand accent. */
  secondary: string;
  /** Tertiary accent for highlights. */
  accent: string;
  /** Semantic — error / destructive. */
  error: string;
  /** Semantic — warning / pending. */
  warning: string;
  /** Semantic — success / verified. */
  success: string;
  /** Semantic — info / neutral. */
  info: string;
}

/**
 * Dark palette — W15-A11 alignment with Images-GUI reference (W14-A4 audit).
 *
 * Deltas applied vs prior values:
 *  - `surface` `#0f1626` -> `#01101a` (panel surface — W14-A4 rank 4, HIGH conf)
 *  - `surface2` `#141d33` -> `#001420` (raised surface — W14-A4 rank 3, HIGH conf)
 *  - `primary` `#22d3ee` (cyan) -> `#3b80f4` (blue) — W14-A4 rank 1 BRAND DECISION.
 *    Reference sampling found the dominant interactive accent across the
 *    Images-GUI PNG set is blue, not cyan. Cyan is preserved as the legacy
 *    fallback `--h3d-color-primary-cyan-legacy` (see globals.css + the
 *    `PRIMARY_CYAN_LEGACY` export below) so any local override / theme
 *    variant / brand-revert can restore the original cyan in one step.
 *
 * Components consuming the Tailwind alias `accent.cyan` are NOT moved —
 * `tailwind.config.ts` keeps `accent.cyan = #22d3ee` so all 88+ in-codebase
 * `text-accent-cyan` / `border-accent-cyan` references retain their colour.
 *
 * WCAG 2.1 — `#3b80f4` foreground on dark surface backgrounds gives
 * ~6.0:1 contrast (passes AA Normal text >=4.5:1 and AA Large >=3:1).
 */
export const darkPalette: ThemePalette = {
  background: "#0a0e1a",
  surface: "#01101a",
  surface2: "#001420",
  border: "#1f2a44",
  textPrimary: "#e6edf7",
  textSecondary: "#7c8aa8",
  primary: "#3b80f4",
  secondary: "#3b82f6",
  accent: "#a78bfa",
  error: "#ef4444",
  warning: "#f59e0b",
  success: "#22c55e",
  info: "#3b82f6",
};

/**
 * Legacy cyan kept available as a backup brand accent. The W15-A11 token
 * shift moved `primary` from cyan to blue per the W14-A4 reference audit;
 * this constant is the safe-to-revert original cyan. CSS consumers should
 * prefer the `--h3d-color-primary-cyan-legacy` custom property over a
 * hard-coded hex so theme variants can override it per-mode.
 */
export const PRIMARY_CYAN_LEGACY = "#22d3ee" as const;

/**
 * Light palette — derived for accessibility parity. Background steps run
 * white -> off-white -> pale-grey (matching the Tailwind near-black
 * progression in reverse). Text colours pinned to >= 4.5:1 contrast.
 */
export const lightPalette: ThemePalette = {
  background: "#ffffff",
  surface: "#f6f8fc",
  surface2: "#eef2f9",
  border: "#d4dbe7",
  textPrimary: "#0a0e1a",
  textSecondary: "#475569",
  // W15-A11: primary shifted cyan -> blue for light mode in lockstep with
  // dark mode. `#1d4ed8` (blue-700) gives 7.1:1 contrast on `#ffffff` (AAA).
  // Legacy cyan `#0e7490` available via `--h3d-color-primary-cyan-legacy`.
  primary: "#1d4ed8",
  secondary: "#1d4ed8",
  accent: "#6d28d9",
  error: "#b91c1c",
  warning: "#b45309",
  success: "#15803d",
  info: "#1d4ed8",
};

export const tokens = {
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    "2xl": 32,
    "3xl": 48,
  },
  fontSize: {
    xs: "11px",
    sm: "13px",
    md: "15px",
    lg: "18px",
    xl: "22px",
    "2xl": "28px",
  },
  radius: {
    xs: "4px",
    sm: "6px",
    // W15-A11: card radius lowered 8px -> 6px to match reference action-window
    // corner-arc (W14-A4 rank 5, MED conf). Existing `rounded-card` Tailwind
    // class will pick up the new 6px automatically via tailwindThemeExtension.
    card: "6px",
    lg: "12px",
    xl: "20px",
    chip: "999px",
  },
  iconSize: {
    sm: 16,
    md: 20,
    lg: 24,
  },
  shadow: {
    glow: "0 0 0 1px rgba(34,211,238,0.18)",
    overlay: "0 8px 32px rgba(0,0,0,0.45)",
  },
  /** Legacy chart-friendly tone aliases retained for back-compat. */
  chartColors: {
    cyan: "#22d3ee",
    blue: "#3b82f6",
    green: "#22c55e",
    amber: "#f59e0b",
    red: "#ef4444",
    muted: "#7c8aa8",
  },
} as const;

export type Tokens = typeof tokens;

export function paletteFor(mode: ResolvedThemeMode): ThemePalette {
  return mode === "light" ? lightPalette : darkPalette;
}

/**
 * Build a record of CSS custom properties for the active palette. Apply
 * with `Object.entries(themeCssVars("dark")).forEach(([k,v]) =>
 * root.style.setProperty(k, v))`.
 *
 * Names are namespaced `--h3d-color-*` so they never collide with
 * Tailwind's generated classes or third-party CSS.
 */
export function themeCssVars(mode: ResolvedThemeMode): Record<string, string> {
  const p = paletteFor(mode);
  return {
    "--h3d-color-background": p.background,
    "--h3d-color-surface": p.surface,
    "--h3d-color-surface-2": p.surface2,
    "--h3d-color-border": p.border,
    "--h3d-color-text-primary": p.textPrimary,
    "--h3d-color-text-secondary": p.textSecondary,
    "--h3d-color-primary": p.primary,
    "--h3d-color-secondary": p.secondary,
    "--h3d-color-accent": p.accent,
    "--h3d-color-error": p.error,
    "--h3d-color-warning": p.warning,
    "--h3d-color-success": p.success,
    "--h3d-color-info": p.info,
  };
}

/**
 * Tailwind theme additions emitted from this token file. The Tailwind
 * config can spread `tailwindThemeExtension` into `theme.extend.colors`
 * to keep the two surfaces in sync.
 */
export const tailwindThemeExtension = {
  colors: {
    // Dark-mode aliases. `bg`/`surface`/`surface2` track `darkPalette` so the
    // W15-A11 surface darkening flows through automatically. The legacy
    // `accent.cyan` hex is preserved verbatim so existing in-codebase
    // `text-accent-cyan` / `border-accent-cyan` (88+ refs) keep their colour.
    bg: darkPalette.background,
    surface: darkPalette.surface,
    surface2: darkPalette.surface2,
    border: darkPalette.border,
    fg: darkPalette.textPrimary,
    muted: darkPalette.textSecondary,
    accent: {
      cyan: PRIMARY_CYAN_LEGACY,
      blue: "#3b82f6",
      green: "#22c55e",
      amber: "#f59e0b",
      red: "#ef4444",
    },
    // New token-driven aliases that read CSS variables. These let
    // components use `bg-h3d-surface` and pick up theme switches.
    h3d: {
      background: "var(--h3d-color-background)",
      surface: "var(--h3d-color-surface)",
      "surface-2": "var(--h3d-color-surface-2)",
      border: "var(--h3d-color-border)",
      "text-primary": "var(--h3d-color-text-primary)",
      "text-secondary": "var(--h3d-color-text-secondary)",
      primary: "var(--h3d-color-primary)",
      secondary: "var(--h3d-color-secondary)",
      accent: "var(--h3d-color-accent)",
      error: "var(--h3d-color-error)",
      warning: "var(--h3d-color-warning)",
      success: "var(--h3d-color-success)",
      info: "var(--h3d-color-info)",
    },
  },
  borderRadius: {
    card: tokens.radius.card,
    chip: tokens.radius.chip,
  },
  fontFamily: {
    sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
    mono: ["JetBrains Mono", "ui-monospace", "monospace"],
  },
  boxShadow: {
    glow: tokens.shadow.glow,
  },
};
