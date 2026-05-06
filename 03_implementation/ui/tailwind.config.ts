import type { Config } from "tailwindcss";

/**
 * Hermes3D UI-Final design tokens.
 *
 * Source of truth: 06_release/UI_FINAL_VISUAL_CONTRACT.png + the kit's
 * 03_implementation/ui/REACT_STRUCTURE.md. Per feedback_no_ui_design.md,
 * these tokens RECREATE the visual contract — they are not invented.
 *
 * Color palette (dark-first):
 * - bg / surface / surface2 / border: progressively lighter near-blacks
 *   matching the contract's deep-navy chrome.
 * - fg / muted: foreground text + secondary text.
 * - accent.{cyan,blue,green,amber,red}: status + glow accents.
 */
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0e1a",
        surface: "#0f1626",
        surface2: "#141d33",
        border: "#1f2a44",
        fg: "#e6edf7",
        muted: "#7c8aa8",
        accent: {
          cyan: "#22d3ee",
          blue: "#3b82f6",
          green: "#22c55e",
          amber: "#f59e0b",
          red: "#ef4444",
        },
      },
      borderRadius: {
        card: "8px",
        chip: "999px",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34,211,238,0.18)",
      },
    },
  },
  plugins: [],
};

export default config;
