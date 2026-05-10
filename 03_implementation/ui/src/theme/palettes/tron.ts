/**
 * `tron` palette — pale cyan grid on inky navy.
 *
 * Higher saturation than the default cyan, but a colder, paler shift to
 * read as the eponymous "lightcycle grid" rather than Hermes-default.
 *
 * Contrast (verified):
 *   fg:bg = 18.32   muted:bg = 8.47   primary:bg = 16.16
 */
import type { NamedPalette } from "./index";

export const palette: NamedPalette = {
  id: "tron",
  label: "Tron",
  baseMode: "dark",
  blurb: "Pale-cyan grid on inky navy — every edge looks lit from inside.",
  swatches: { background: "#000812", primary: "#7df9ff" },
  cssVars: {
    "--h3d-color-background": "#000812",
    "--h3d-color-surface": "#001327",
    "--h3d-color-surface-2": "#012244",
    "--h3d-color-border": "#0a3c6c",
    "--h3d-color-text-primary": "#e6f7ff",
    "--h3d-color-text-secondary": "#7faecd",
    "--h3d-color-primary": "#7df9ff",
    "--h3d-color-secondary": "#33e7ff",
    "--h3d-color-accent": "#ffb300",
    "--h3d-color-error": "#ff6363",
    "--h3d-color-warning": "#ffb300",
    "--h3d-color-success": "#3ddcae",
    "--h3d-color-info": "#7df9ff",
  },
};
