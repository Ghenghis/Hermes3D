/**
 * Vitest config — shared by W6-3 / W6-8 / W8-2 lanes.
 *
 * Unit tests live under `tests/unit/`. The Playwright suite stays in
 * `tests/e2e/` and is run via the existing `test:visual` script.
 *
 * jsdom is required for any test that imports a React component because
 * Zustand-backed stores read `window` at module load.
 *
 * NODE_ENV is forced to "development" so that the development build of
 * react-dom is loaded (required for `act()` inside @testing-library).
 * W8-2 also adds the `define` + `resolve.conditions` belt-and-braces to
 * keep the dev build present when Vite probes packaged condition exports.
 */
/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

process.env.NODE_ENV = "development";

export default defineConfig({
  plugins: [react()],
  // Force the development build of React in unit tests so React Testing
  // Library's act(...) helper is available — production builds drop the
  // act/scheduler hooks that RTL relies on.
  define: {
    "process.env.NODE_ENV": JSON.stringify("development"),
  },
  resolve: {
    conditions: ["development", "browser", "import", "module", "default"],
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/unit/setup.ts"],
    include: ["tests/unit/**/*.{test,spec}.{ts,tsx}"],
    css: false,
  },
});
