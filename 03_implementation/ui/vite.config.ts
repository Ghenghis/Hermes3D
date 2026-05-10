/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        actionWindow: resolve(__dirname, "action-window.html"),
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./src/test-setup-w6-4.ts"],
    // W6-4 ships its own targeted suite — full repo unit run is owned by W6-3.
    // Restricting `include` to ActionWindow + TaskMonitor means new authors
    // can run `npx vitest run` from the ui/ dir without picking up unrelated
    // tests from other lanes.
    include: [
      "src/components/ActionWindow/**/*.test.{ts,tsx}",
      "src/components/TaskMonitor/**/*.test.{ts,tsx}",
    ],
    css: false,
  },
});
