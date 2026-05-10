/**
 * `industrial-forge` palette — warm amber on graphite.
 *
 * Workshop / foundry vibe: graphite-grey surfaces with a hot-metal amber
 * primary, suitable for long shop-floor sessions where blue-light strain
 * is a concern.
 *
 * Contrast (verified):
 *   fg:bg = 15.83   muted:bg = 7.05   primary:bg = 9.35
 */
import type { NamedPalette } from "./index";

export const palette: NamedPalette = {
  id: "industrial-forge",
  label: "Industrial Forge",
  baseMode: "dark",
  blurb: "Warm amber on graphite — workshop palette tuned for long sessions.",
  swatches: { background: "#161310", primary: "#ffa432" },
  cssVars: {
    "--h3d-color-background": "#161310",
    "--h3d-color-surface": "#221d18",
    "--h3d-color-surface-2": "#332921",
    "--h3d-color-border": "#4a3b2e",
    "--h3d-color-text-primary": "#f5ece1",
    "--h3d-color-text-secondary": "#b39c84",
    "--h3d-color-primary": "#ffa432",
    "--h3d-color-secondary": "#e07b2c",
    "--h3d-color-accent": "#ffd25a",
    "--h3d-color-error": "#ff6b50",
    "--h3d-color-warning": "#ffc857",
    "--h3d-color-success": "#9fd47b",
    "--h3d-color-info": "#c08850",
  },
};
