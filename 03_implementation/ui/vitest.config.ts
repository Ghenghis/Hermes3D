/// <reference types="vitest" />
/**
 * Vitest config for the W6-4 lane (ActionWindow + TaskMonitor).
 *
 * Kept separate from vite.config.ts so that `npm run build` (which only invokes
 * `tsc -b && vite build`) does not require vitest types or test deps to be
 * installed. Run with `npx vitest run --config vitest.config.ts` once vitest +
 * @testing-library/react + jsdom are installed locally.
 *
 * Why a dedicated config:
 *   - Vitest reads `vitest.config.ts` (or merges with vite.config.ts when no
 *     dedicated file exists). Splitting gives a clean separation of concerns
 *     and matches Vitest's documented multi-config pattern.
 *   - The `include` pattern points at `tests/unit/**` (NOT `src/**`) so that
 *     tsc's `include: ["src"]` in tsconfig.json never tries to type-check
 *     these files at build time.
 */
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // `development` flag + matching resolve.conditions ensures vitest pulls
  // react.development.js (which exports `act`) instead of react.production.min.js
  // (which throws "act is not supported in production builds"). Vite 8 +
  // Vitest 2 require this explicit selection because `mode` defaults to "test"
  // and React's package.json conditional exports key off NODE_ENV/condition.
  define: {
    "process.env.NODE_ENV": JSON.stringify("development"),
  },
  resolve: {
    conditions: ["development", "browser"],
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./tests/unit/setup.ts"],
    // W6-4 ships its own targeted suite — full repo unit run is owned by W6-3.
    // Restricting `include` to ActionWindow + TaskMonitor means new authors
    // can run `npx vitest run` from the ui/ dir without picking up unrelated
    // tests from other lanes.
    include: [
      "tests/unit/ActionWindow.test.tsx",
      "tests/unit/TaskMonitorDrawer.test.tsx",
    ],
    css: false,
  },
});
