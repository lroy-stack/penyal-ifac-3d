import { defineConfig, devices } from "@playwright/test";

// E2E_PORT and E2E_OUTPUT_DIR let two e2e runs share the machine: each needs its own dev server
// and its own artifacts directory (Playwright empties the output directory when it starts).
const PORT = Number(process.env.E2E_PORT ?? 5175);

// Headless Chromium renders WebGL2 through SwiftShader, so these checks run without a GPU or a
// visible window. They verify behaviour and correctness, not real-device performance.
export default defineConfig({
  testDir: "e2e",
  outputDir: process.env.E2E_OUTPUT_DIR ?? "test-results",
  timeout: 60_000,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
    launchOptions: { args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] },
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], channel: "chromium-headless-shell" } },
  ],
  webServer: {
    command: `pnpm dev --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
