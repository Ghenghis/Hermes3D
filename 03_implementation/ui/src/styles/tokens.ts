/**
 * Token constants exported for components that need raw values
 * (recharts dimensions, inline styles, etc.). Tailwind theme remains
 * the source of truth for class-based styling — see tailwind.config.ts.
 */
export const tokens = {
  radius: { card: "20px", chip: "999px" },
  spacing: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, "2xl": 32 },
  iconSize: { sm: 16, md: 20, lg: 24 },
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
