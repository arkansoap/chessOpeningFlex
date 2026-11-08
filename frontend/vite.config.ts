import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

/**
 * Stockfish's multi-threaded WASM build needs `SharedArrayBuffer`, which the
 * browser only exposes on cross-origin isolated pages. These two headers turn
 * isolation on; without them the engine silently falls back to the (slower)
 * single-threaded build.
 */
const crossOriginIsolation = {
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Embedder-Policy": "require-corp",
};

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // The engine is loaded from public/ as a classic worker at runtime, so Vite
  // must not try to pre-bundle or transform the emscripten glue.
  optimizeDeps: {
    exclude: ["stockfish"],
  },
  server: {
    port: 5173,
    headers: crossOriginIsolation,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    headers: crossOriginIsolation,
  },
});
