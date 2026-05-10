/**
 * Named theme palettes — W15-A17 lane.
 *
 * Each palette is a self-contained module that exports a `ThemePalette`
 * value plus a sibling `cssVars` record (the same `--h3d-color-*` keys
 * the base `theme/tokens.ts` emits). This keeps the W8-3 ThemeProvider
 * surface unchanged — the named palette layers on top of the resolved
 * light/dark mode by overwriting the same CSS custom properties.
 *
 * Source/reference for the contrast targets:
 *   - WCAG 2.1 §1.4.3 Contrast (Minimum)
 *     https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
 *   - VS Code "Customizing colors"
 *     https://code.visualstudio.com/docs/getstarted/themes#_customizing-a-color-theme
 *     (modelled the palette-key shape after their `workbench.colorCustomizations`
 *     so future per-component overrides drop in cleanly).
 *
 * Contrast guarantees (computed via the WCAG relative-luminance formula,
 * verified by `.claude/scratch/contrast.mjs` at design time):
 *   - body text (`fg` on `background`) >= 4.5 : 1
 *   - secondary text (`muted` on `background`) >= 4.5 : 1
 *   - UI / large text (`primary` on `background`) >= 3.0 : 1
 * All six palettes meet AA at body-text strength.
 */

import * as defaultPalette from "./default";
import * as cyberpunk from "./cyberpunk";
import * as matrix from "./matrix";
import * as tron from "./tron";
import * as industrialForge from "./industrial-forge";
import * as auroraOperator from "./aurora-operator";

export type NamedPaletteId =
  | "default"
  | "cyberpunk"
  | "matrix"
  | "tron"
  | "industrial-forge"
  | "aurora-operator";

export interface NamedPalette {
  /** Stable id — used as the localStorage key and the radio value. */
  id: NamedPaletteId;
  /** Human-readable label for the palette switcher. */
  label: string;
  /** Tone of the palette; matches `ResolvedThemeMode` from `tokens.ts`. */
  baseMode: "dark";
  /** One-line description rendered next to the radio. */
  blurb: string;
  /** Two preview swatches shown in the radio card. */
  swatches: { background: string; primary: string };
  /**
   * Full record of `--h3d-color-*` CSS custom properties, ready to apply
   * via `root.style.setProperty()`. Includes every key emitted by
   * `themeCssVars` in `theme/tokens.ts` so an apply call cleanly replaces
   * the previous palette without leftover variables.
   */
  cssVars: Record<string, string>;
}

export const NAMED_PALETTES: readonly NamedPalette[] = [
  defaultPalette.palette,
  cyberpunk.palette,
  matrix.palette,
  tron.palette,
  industrialForge.palette,
  auroraOperator.palette,
] as const;

export const NAMED_PALETTE_BY_ID: Record<NamedPaletteId, NamedPalette> = Object.freeze(
  NAMED_PALETTES.reduce(
    (acc, p) => {
      acc[p.id] = p;
      return acc;
    },
    {} as Record<NamedPaletteId, NamedPalette>,
  ),
);

export const DEFAULT_PALETTE_ID: NamedPaletteId = "default";

export function isNamedPaletteId(value: unknown): value is NamedPaletteId {
  return typeof value === "string" && value in NAMED_PALETTE_BY_ID;
}

/**
 * Storage key for the active palette. Stable contract — bumping the
 * version here invalidates every user's persisted selection, so leave it
 * alone unless we're shipping a breaking change to the palette shape.
 */
export const PALETTE_STORAGE_KEY = "h3d.theme.palette";

/**
 * Apply a palette's CSS variables to the document root. Returns the id
 * that was applied (or `null` in non-browser contexts) so callers can
 * confirm without a follow-up DOM read.
 *
 * Idempotent: safe to call repeatedly with the same id.
 *
 * IMPORTANT: when `id` is the default palette, this only stamps the
 * `data-h3d-palette` attribute and does NOT overwrite `--h3d-color-*`
 * variables. The base ThemeProvider's `themeCssVars(resolved)` call
 * already supplies them with the correct light/dark values, and we want
 * the default selection to stay transparent so light-mode users keep a
 * white background. Selecting a non-default palette always overrides
 * the base vars (palettes are dark-only by design — see W15-A17 spec).
 */
export function applyPalette(id: NamedPaletteId): NamedPaletteId | null {
  if (typeof document === "undefined") return null;
  const palette = NAMED_PALETTE_BY_ID[id] ?? NAMED_PALETTE_BY_ID[DEFAULT_PALETTE_ID];
  const root = document.documentElement;
  root.dataset.h3dPalette = palette.id;
  if (palette.id === DEFAULT_PALETTE_ID) {
    // No-op for CSS vars — keep whatever ThemeProvider has set so
    // light/dark mode and the default look stay consistent.
    return palette.id;
  }
  for (const [name, value] of Object.entries(palette.cssVars)) {
    root.style.setProperty(name, value);
  }
  return palette.id;
}

/** Read the persisted palette id, falling back to `default` when missing/invalid. */
export function readStoredPaletteId(): NamedPaletteId {
  if (typeof window === "undefined") return DEFAULT_PALETTE_ID;
  try {
    const raw = window.localStorage.getItem(PALETTE_STORAGE_KEY);
    return isNamedPaletteId(raw) ? raw : DEFAULT_PALETTE_ID;
  } catch {
    return DEFAULT_PALETTE_ID;
  }
}

/** Persist a palette id. Silent on storage failures (private mode, quota). */
export function writeStoredPaletteId(id: NamedPaletteId): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(PALETTE_STORAGE_KEY, id);
  } catch {
    /* non-fatal */
  }
}
