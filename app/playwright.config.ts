import { resolve } from "node:path";
import { defineConfig, devices } from "@playwright/test";
import { laneDefaults } from "./e2e/support/lane";

// E2E_PORT and E2E_OUTPUT_DIR let two e2e runs share the machine: each needs its own dev server
// and its own artifacts directory (Playwright empties the output directory when it starts). In a
// phase B lane worktree (.worktrees/l<n>) they default to 5180 + n and test-results/l<n>, with one
// worker; explicit variables win. The main checkout keeps 5175.
const { port: PORT, outputDir, workers } = laneDefaults(import.meta.dirname, process.env);

// Headless Chromium renders WebGL2 through SwiftShader, so these checks run without a GPU or a
// visible window. They verify behaviour and correctness, not real-device performance.
export default defineConfig({
  testDir: "e2e",
  outputDir,
  ...(workers === undefined ? {} : { workers }),
  timeout: 60_000,
  // Baselines of the fixed-viewpoint check stay out of git: see e2e/viewpoints.spec.ts.
  snapshotPathTemplate: resolve(
    import.meta.dirname,
    "../build/e2e-baselines/{testFileName}/{arg}{ext}",
  ),
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
