/**
 * Vitest config — W6-3 lane.
 *
 * Unit tests live under `tests/unit/`. The Playwright suite stays in
 * `tests/e2e/` and is run via the existing `test:visual` script.
 *
 * jsdom is required for any test that imports a React component because
 * Zustand-backed stores read `window` at module load.
 *
 * NODE_ENV is forced to "development" so that the development build of
 * react-dom is loaded (required for `act()` inside @testing-library).
 */
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

process.env.NODE_ENV = "development";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    globals: false,
    setupFiles: ["./tests/unit/setup.ts"],
    css: false,
  },
});
