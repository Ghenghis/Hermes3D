/**
 * `cyberpunk` palette — neon magenta on deep violet.
 *
 * Inspired by the cyberpunk-genre conventions in
 * Images-GUI/09-themes/theme-variants-reference.png: a saturated pink/magenta
 * primary against a near-black violet background.
 *
 * Contrast (verified):
 *   fg:bg = 17.55   muted:bg = 7.18   primary:bg = 6.41
 */
import type { NamedPalette } from "./index";

export const palette: NamedPalette = {
  id: "cyberpunk",
  label: "Cyberpunk",
  baseMode: "dark",
  blurb: "Neon magenta on deep-violet — high contrast for nighttime ops.",
  swatches: { background: "#0b0014", primary: "#ff2bd6" },
  cssVars: {
    "--h3d-color-background": "#0b0014",
    "--h3d-color-surface": "#140524",
    "--h3d-color-surface-2": "#1f0b37",
    "--h3d-color-border": "#3f1d68",
    "--h3d-color-text-primary": "#f5e9ff",
    "--h3d-color-text-secondary": "#b288d3",
    "--h3d-color-primary": "#ff2bd6",
    "--h3d-color-secondary": "#7e3cff",
    "--h3d-color-accent": "#ffd23f",
    "--h3d-color-error": "#ff4d6d",
    "--h3d-color-warning": "#ffb84d",
    "--h3d-color-success": "#5cffba",
    "--h3d-color-info": "#7aa8ff",
  },
};
