// Playwright-UI-Smoke des Composers: startet Backend (FastAPI, Wegwerf-Registry
// via e2e/start-backend.sh) und Vite-Dev-Server auf eigenen Ports, damit der
// Smoke parallel zu einem laufenden dev-up.sh funktioniert.

import { defineConfig } from "@playwright/test";

const BACKEND_PORT = Number(process.env.COMPOSER_E2E_BACKEND_PORT ?? 8788);
const UI_PORT = Number(process.env.COMPOSER_E2E_UI_PORT ?? 5199);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["github"]] : [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${UI_PORT}`,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "bash e2e/start-backend.sh",
      url: `http://127.0.0.1:${BACKEND_PORT}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { COMPOSER_E2E_BACKEND_PORT: String(BACKEND_PORT) },
    },
    {
      // `--host 127.0.0.1`: ohne das bindet Vite je nach DNS-Auflösung von
      // `localhost` nur auf ::1 — die Wartebedingung unten fragt IPv4 ab.
      command: `pnpm exec vite --port ${UI_PORT} --strictPort --host 127.0.0.1`,
      url: `http://127.0.0.1:${UI_PORT}`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { COMPOSER_PROXY_TARGET: `http://127.0.0.1:${BACKEND_PORT}` },
    },
  ],
});
