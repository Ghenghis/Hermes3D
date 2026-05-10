/**
 * `default` palette — Hermes3D dark, matching `tokens.ts#darkPalette` so
 * existing screenshot baselines remain stable.
 *
 * Contrast (verified):
 *   fg:bg = 16.34   muted:bg = 5.55   primary:bg = 10.65
 *
 * This palette is intentionally identical to the current production dark
 * theme so selecting "default" is a no-op for users on the live build.
 */
import type { NamedPalette } from "./index";

export const palette: NamedPalette = {
  id: "default",
  label: "Default Dark",
  baseMode: "dark",
  blurb: "The standard Hermes3D dark theme — cyan accents on midnight.",
  swatches: { background: "#0a0e1a", primary: "#22d3ee" },
  cssVars: {
    "--h3d-color-background": "#0a0e1a",
    "--h3d-color-surface": "#0f1626",
    "--h3d-color-surface-2": "#141d33",
    "--h3d-color-border": "#1f2a44",
    "--h3d-color-text-primary": "#e6edf7",
    "--h3d-color-text-secondary": "#7c8aa8",
    "--h3d-color-primary": "#22d3ee",
    "--h3d-color-secondary": "#3b82f6",
    "--h3d-color-accent": "#a78bfa",
    "--h3d-color-error": "#ef4444",
    "--h3d-color-warning": "#f59e0b",
    "--h3d-color-success": "#22c55e",
    "--h3d-color-info": "#3b82f6",
  },
};
