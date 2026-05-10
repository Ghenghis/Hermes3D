/**
 * `matrix` palette — phosphor green on near-black.
 *
 * Strict monochrome-green wash following the classic terminal-green
 * convention; accents lean amber/yellow only for error/warning states so
 * the palette stays readable for users with red-green color-vision
 * deficiency (the green-only signal would otherwise be ambiguous).
 *
 * Contrast (verified):
 *   fg:bg = 18.28   muted:bg = 7.86   primary:bg = 14.96
 */
import type { NamedPalette } from "./index";

export const palette: NamedPalette = {
  id: "matrix",
  label: "Matrix",
  baseMode: "dark",
  blurb: "Phosphor-green terminal aesthetic — minimal chrome, maximum signal.",
  swatches: { background: "#020a02", primary: "#22ff7b" },
  cssVars: {
    "--h3d-color-background": "#020a02",
    "--h3d-color-surface": "#031305",
    "--h3d-color-surface-2": "#062108",
    "--h3d-color-border": "#0b3a10",
    "--h3d-color-text-primary": "#d6ffd6",
    "--h3d-color-text-secondary": "#74b079",
    "--h3d-color-primary": "#22ff7b",
    "--h3d-color-secondary": "#5ad07f",
    "--h3d-color-accent": "#a8ff60",
    "--h3d-color-error": "#ffb24d",
    "--h3d-color-warning": "#ffe66d",
    "--h3d-color-success": "#22ff7b",
    "--h3d-color-info": "#74b079",
  },
};
