/**
 * `aurora-operator` palette — soft blue-violet on midnight.
 *
 * Calmer counterpart to the default cyan: indigo-leaning primary, low
 * saturation, designed for sustained agent-supervision sessions where
 * the GUI is the background of attention, not the foreground.
 *
 * Contrast (verified):
 *   fg:bg = 16.55   muted:bg = 7.57   primary:bg = 7.98
 */
import type { NamedPalette } from "./index";

export const palette: NamedPalette = {
  id: "aurora-operator",
  label: "Aurora Operator",
  baseMode: "dark",
  blurb: "Soft blue-violet on midnight — calm palette for long supervision shifts.",
  swatches: { background: "#0a1024", primary: "#7aa8ff" },
  cssVars: {
    "--h3d-color-background": "#0a1024",
    "--h3d-color-surface": "#11173a",
    "--h3d-color-surface-2": "#1c2155",
    "--h3d-color-border": "#2e3680",
    "--h3d-color-text-primary": "#eaf0ff",
    "--h3d-color-text-secondary": "#92a3d5",
    "--h3d-color-primary": "#7aa8ff",
    "--h3d-color-secondary": "#a78bfa",
    "--h3d-color-accent": "#5cd6ff",
    "--h3d-color-error": "#ff7a7a",
    "--h3d-color-warning": "#ffc857",
    "--h3d-color-success": "#5cffba",
    "--h3d-color-info": "#7aa8ff",
  },
};
