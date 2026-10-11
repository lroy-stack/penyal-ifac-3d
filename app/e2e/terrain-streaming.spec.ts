import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";
import { flatGridGlb } from "./support/glb";

// The real tiles come from the pipeline. This test exercises the streaming path (manifest, fetch,
// glTF parse, LOD swap, concurrency limit) with synthetic flat tiles served by request
// interception around the start of the route; nothing is written to `public/`.

const TILE = 256;
const TILE_IDS = [1, 2, 3].flatMap((i) => [-6, -5, -4].map((j) => ({ i, j })));
const LEVELS = [
  { level: 0, maxError: 0.25, cells: 16, color: [0.2, 0.7, 0.2] },
  { level: 1, maxError: 1, cells: 8, color: [0.7, 0.7, 0.2] },
  { level: 2, maxError: 3, cells: 2, color: [0.7, 0.3, 0.2] },
] as const;
const GROUND_Y = 60;

const manifest = {
  version: 1,
  frame: { crs: "EPSG:25830", origin: { e: 767000, n: 4280000 } },
  near: {
    tileSize: TILE,
    tiles: TILE_IDS.map(({ i, j }) => ({
      id: `t_${i}_${j}`,
      bounds: {
        minX: i * TILE,
        maxX: (i + 1) * TILE,
        minZ: j * TILE,
        maxZ: (j + 1) * TILE,
        minY: GROUND_Y,
        maxY: GROUND_Y,
      },
      lods: LEVELS.map((lod) => ({
        level: lod.level,
        url: `tiles/t_${i}_${j}_lod${lod.level}.glb`,
        maxError: lod.maxError,
        texture: 256,
        triangles: lod.cells * lod.cells * 2,
        bytes: 0,
      })),
    })),
  },
  far: {
    url: "far.glb",
    maxError: 4,
    texture: 256,
    bounds: { minX: -600, maxX: 2000, minZ: -2000, maxZ: 550, minY: 1, maxY: 1 },
    triangles: 8,
    bytes: 0,
  },
};

async function readState(page: Page): Promise<AppState> {
  const state = await page.evaluate(() => window.__appState);
  if (state === undefined) throw new Error("window.__appState is not published.");
  return state;
}

test("streams far, coarse and fine tiles with at most two requests in flight", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (error) => {
    errors.push(`pageerror: ${error.message}`);
  });

  const requested: string[] = [];
  let active = 0;
  let maxActive = 0;
  const glb = { contentType: "model/gltf-binary" } as const;

  await page.route("**/assets/generated/terrain/manifest.json", (route) =>
    route.fulfill({ json: manifest }),
  );
  await page.route("**/assets/generated/terrain/far.glb", async (route) => {
    requested.push("far");
    active++;
    maxActive = Math.max(maxActive, active);
    await new Promise((resolve) => setTimeout(resolve, 60));
    active--;
    await route.fulfill({
      ...glb,
      body: flatGridGlb({ ...manifest.far.bounds, y: 1, cells: 4, color: [0.3, 0.4, 0.5] }),
    });
  });
  await page.route("**/assets/generated/terrain/tiles/*.glb", async (route) => {
    const name = new URL(route.request().url()).pathname.split("/").pop() ?? "";
    const match = /^t_(-?\d+)_(-?\d+)_lod(\d)\.glb$/.exec(name);
    if (match === null) return route.fulfill({ status: 404 });
    const [i, j, level] = [Number(match[1]), Number(match[2]), Number(match[3])];
    const lod = LEVELS[level as 0 | 1 | 2];
    requested.push(name);
    active++;
    maxActive = Math.max(maxActive, active);
    await new Promise((resolve) => setTimeout(resolve, 60));
    active--;
    return route.fulfill({
      ...glb,
      body: flatGridGlb({
        minX: i * TILE,
        maxX: (i + 1) * TILE,
        minZ: j * TILE,
        maxZ: (j + 1) * TILE,
        y: GROUND_Y,
        cells: lod.cells,
        color: [...lod.color],
      }),
    });
  });

  await page.goto("/");
  await expect
    .poll(async () => (await readState(page)).terrain.stats?.displayed[0] ?? 0, {
      timeout: 45_000,
    })
    .toBeGreaterThan(0);

  const state = await readState(page);
  const stats = state.terrain.stats;
  expect(state.terrain.status).toBe("ready");
  expect(stats?.farLoaded).toBe(true);
  expect(stats?.failed).toBe(0);
  expect(stats?.bytesLoaded).toBeGreaterThan(0);
  await expect
    .poll(async () => (await readState(page)).terrain.stats?.resident[2] ?? 0, { timeout: 45_000 })
    .toBe(TILE_IDS.length);
  expect(requested[0]).toBe("far");
  const firstFine = requested.findIndex(
    (name) => name.endsWith("lod0.glb") || name.endsWith("lod1.glb"),
  );
  const coarseBefore = requested.slice(0, firstFine).filter((name) => name.endsWith("lod2.glb"));
  expect(coarseBefore.length).toBeGreaterThan(0);
  expect(maxActive).toBeLessThanOrEqual(2);
  expect((await readState(page)).render.triangles).toBeGreaterThan(0);

  await page.screenshot({ path: "test-results/terrain-streaming-synthetic.png" });
  expect(errors).toEqual([]);
});
