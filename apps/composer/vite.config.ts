import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Tauri-2-Rahmenbedingung: statischer Export mit relativen Pfaden (`base: "./"`),
// keine SSR-/Server-Features. Das Backend liegt hinter einer sauberen
// HTTP-Grenze — im Dev proxied Vite `/api` auf das FastAPI-Backend (:8000),
// in einer Tauri-Shell zeigt `VITE_API_BASE` später auf den Sidecar.
// `COMPOSER_PROXY_TARGET` erlaubt dem Playwright-Smoke ein Backend auf
// abweichendem Port (Wegwerf-Registry, kollisionsfrei zu dev-up.sh).
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.COMPOSER_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
