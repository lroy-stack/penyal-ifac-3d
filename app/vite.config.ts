import { rmSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vitest/config";
import { creditsModule, htmlStrings } from "./vite/plugins";

/** The asset spike is a dev-only fixture; it must not ship in `dist`. */
function excludeSpikeAssets(): Plugin {
  let outDir = "dist";
  return {
    name: "penyal:exclude-spike-assets",
    apply: "build",
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir);
    },
    closeBundle() {
      rmSync(resolve(outDir, "assets/generated/spike"), { recursive: true, force: true });
    },
  };
}

export default defineConfig({
  // Hashed bundles go to /bundle/ so they never share a directory with the unhashed, separately
  // cached generated assets under /assets/.
  build: { target: "es2022", assetsDir: "bundle" },
  plugins: [excludeSpikeAssets(), creditsModule(), htmlStrings()],
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
