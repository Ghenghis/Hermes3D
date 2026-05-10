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
 *
 * W8-3 update: enabled `darkMode: "class"` so the W8-3 theme provider
 * can toggle the active palette via `<html class="dark">` /
 * `<html class="light">`. Added a parallel `h3d.*` colour group whose
 * values resolve from `--h3d-color-*` CSS custom properties — so any
 * component using `bg-h3d-surface` etc. picks up theme switches at
 * runtime without re-rendering. The original `bg`, `surface`, `fg`
 * aliases are preserved verbatim for visual-contract back-compat.
 */
// W15-A11 token deltas applied (aligned with `src/theme/tokens.ts` +
// `src/styles/globals.css`):
//   - colors.surface  : #0f1626 -> #01101a (W14-A4 rank 4)
//   - colors.surface2 : #141d33 -> #001420 (W14-A4 rank 3)
//   - borderRadius.card : 8px -> 6px (W14-A4 rank 5)
//   - accent.cyan kept verbatim (#22d3ee) — 88+ existing in-codebase refs
//     to `text-accent-cyan` / `border-accent-cyan` retain their colour. The
//     brand primary shift (cyan -> blue) lives on the `--h3d-color-primary`
//     CSS variable and the `h3d.primary` Tailwind alias only.
const config: Config = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0e1a",
        surface: "#01101a",
        surface2: "#001420",
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
        h3d: {
          background: "var(--h3d-color-background)",
          surface: "var(--h3d-color-surface)",
          "surface-2": "var(--h3d-color-surface-2)",
          border: "var(--h3d-color-border)",
          "text-primary": "var(--h3d-color-text-primary)",
          "text-secondary": "var(--h3d-color-text-secondary)",
          primary: "var(--h3d-color-primary)",
          "primary-cyan-legacy": "var(--h3d-color-primary-cyan-legacy)",
          secondary: "var(--h3d-color-secondary)",
          accent: "var(--h3d-color-accent)",
          error: "var(--h3d-color-error)",
          warning: "var(--h3d-color-warning)",
          success: "var(--h3d-color-success)",
          info: "var(--h3d-color-info)",
        },
      },
      borderRadius: {
        card: "6px",
        chip: "999px",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        // Glow shadow keeps cyan rgba — active-state sidebar row pairs this
        // shadow with `border-accent-cyan` (still `#22d3ee` via `accent.cyan`).
        // Both stay cyan together for visual consistency.
        glow: "0 0 0 1px rgba(34,211,238,0.18)",
      },
    },
  },
  plugins: [],
};

export default config;
