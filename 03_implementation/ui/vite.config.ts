import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Compute __dirname in an ESM-safe way without requiring @types/node `__dirname`
// or `node:path.resolve(__dirname, ...)`. Vite 8 / Node 20+ support this idiom
// and it keeps tsconfig.node.json from needing `@types/node`.
const here = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
  build: {
    rollupOptions: {
      input: {
        main: `${here}index.html`,
        actionWindow: `${here}action-window.html`,
      },
    },
  },
});
