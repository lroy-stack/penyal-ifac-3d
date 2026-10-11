import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";

// Before/after evidence for the terrain material (T2.2): the same anchor rendered with the `low`
// tier (F1 look: plain orthophoto) and the `high` tier (cliff limestone + near-ground detail).
// Screenshots go to test-results/material/<anchor>-<view>-<tier>.png. With PENYAL_E2E_GPU=metal the
// browser uses the Metal ANGLE backend instead of SwiftShader (frame times are then meaningful).
const MANIFEST = resolve(import.meta.dirname, "../public/assets/generated/terrain/manifest.json");
const ANCHORS = [
  "turnstile",
  "viewpoint-1795591637",
  "tunnel-east",
  "bifurcation",
  "summit",
  "carabiners",
];
const TIERS = ["low", "high"] as const;
const OUT = "test-results/material";

const useMetal = process.env.PENYAL_E2E_GPU === "metal";
if (useMetal) {
  test.use({
    launchOptions: {
      args: [
        "--use-angle=metal",
        "--ignore-gpu-blocklist",
        "--enable-gpu-rasterization",
        "--disable-gpu-vsync",
        "--disable-frame-rate-limit",
      ],
    },
  });
}

async function readState(page: Page): Promise<AppState> {
  const state = await page.evaluate(() => window.__appState);
  if (state === undefined) throw new Error("window.__appState is not published.");
  return state;
}

async function settle(page: Page): Promise<AppState> {
  await expect
    .poll(
      async () => {
        const stats = (await readState(page)).terrain.stats;
        return stats?.farLoaded === true && stats.pending === 0 && stats.inFlight === 0;
      },
      { timeout: 240_000, intervals: [500] },
    )
    .toBe(true);
  return readState(page);
}

/** The high tier loads its marble maps through the shared KTX2 loader; wait for the 2k set. */
async function settleWithDetail(page: Page, tier: "low" | "high"): Promise<void> {
  await settle(page);
  const expected = tier === "high" ? "2k" : "procedural";
  await expect
    .poll(async () => (await readState(page)).terrain.stats?.detail, {
      timeout: 240_000,
      intervals: [500],
    })
    .toBe(expected);
}

test.describe("terrain material tiers", () => {
  test.skip(!existsSync(MANIFEST), "terrain tiles not generated (run `penyal terrain`)");
  // The dev server reloads the page when another change lands during a long software-GL run.
  test.describe.configure({ retries: 1 });
  test.beforeAll(() => mkdirSync(OUT, { recursive: true }));

  for (const anchor of ANCHORS) {
    test(`high differs from low at ${anchor} without shader errors`, async ({ page }) => {
      test.setTimeout(900_000);
      const errors: string[] = [];
      page.on("console", (msg) => {
        if (msg.type() === "error") errors.push(msg.text());
      });
      page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
      await page.setViewportSize({ width: 1280, height: 720 });

      const shots: Record<string, Buffer> = {};
      for (const tier of TIERS) {
        await page.goto(`/?start=${anchor}&terrain=${tier}`);
        await settleWithDetail(page, tier);
        shots[`${tier}-first`] = await page.screenshot({
          path: `${OUT}/${anchor}-first-${tier}.png`,
        });
        await page.keyboard.press("KeyC");
        await expect
          .poll(async () => (await readState(page)).player.cameraMode, { timeout: 60_000 })
          .toBe("third");
        await settle(page);
        shots[`${tier}-third`] = await page.screenshot({
          path: `${OUT}/${anchor}-third-${tier}.png`,
        });
      }

      expect(shots["high-first"]?.equals(shots["low-first"] as Buffer)).toBe(false);
      expect(shots["high-third"]?.equals(shots["low-third"] as Buffer)).toBe(false);
      expect(errors).toEqual([]);
      expect(readFileSync(`${OUT}/${anchor}-first-high.png`).length).toBeGreaterThan(10_000);
    });
  }

  test("frame time of high vs low at the turnstile and the bifurcation", async ({ page }) => {
    test.setTimeout(900_000);
    await page.setViewportSize(
      useMetal ? { width: 2560, height: 1440 } : { width: 1440, height: 810 },
    );
    const rows: string[] = [];
    await page.goto("/");
    const gpu = await page.evaluate(() => {
      const gl = document.createElement("canvas").getContext("webgl2");
      const info = gl?.getExtension("WEBGL_debug_renderer_info");
      return gl && info ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)) : "unknown";
    });
    rows.push(`renderer: ${gpu}`);
    for (const anchor of ["turnstile", "bifurcation"]) {
      for (const tier of TIERS) {
        await page.goto(`/?start=${anchor}&terrain=${tier}`);
        await settleWithDetail(page, tier);
        await page.waitForTimeout(4000);
        const state = await readState(page);
        rows.push(
          `${anchor} ${tier}: p95 ${state.frameTimeP95Ms?.toFixed(2)} ms, ` +
            `calls ${state.render.calls}, triangles ${state.render.triangles}`,
        );
        expect(state.frameTimeP95Ms).not.toBeNull();
      }
    }
    console.log(`[frame-time ${useMetal ? "metal" : "swiftshader"}]\n${rows.join("\n")}`);
  });
});
