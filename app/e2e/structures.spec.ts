import { mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";
import { parseStructures, TreadsGroundSurface } from "../src/world/structures/structures";
import { drainFrames, type FrameSample, installFrameRecorder, waitForApp } from "./support/frames";
import { waitForFrames } from "./support/terrain";

const GENERATED = resolve(import.meta.dirname, "../public/assets/generated");
const SHOTS = process.env.E2E_SHOTS_DIR ?? "test-results";

// Independent check: the test reads structures.json from disk and compares the player with it.
const structures = parseStructures(
  JSON.parse(readFileSync(resolve(GENERATED, "structures.json"), "utf8")),
);
const flight = structures.staircases.find((s) => s.id === "centre-steps");
if (flight === undefined) throw new Error("structures.json has no centre-steps flight.");
const treads = new TreadsGroundSurface(flight.collision.treads);
/** The tread top under (x, z), whatever the feet height. */
const treadTop = (x: number, z: number): number | null => treads.surfaceBelow(x, 1e6, z, 2e6);
const MAX_ERROR = 0.05;

async function readState(page: Page): Promise<AppState> {
  const state = await page.evaluate(() => window.__appState);
  if (state === undefined) throw new Error("window.__appState is not published.");
  return state;
}

function collectErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (error) => {
    errors.push(`pageerror: ${error.message}`);
  });
  return errors;
}

async function open(page: Page, query: string): Promise<void> {
  await installFrameRecorder(page);
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(`/?${query}`);
  await waitForApp(page);
  mkdirSync(SHOTS, { recursive: true });
}

test.describe("structures and painted surfaces", () => {
  test.setTimeout(240_000);

  test("walking up the 30-step flight follows the treads, with no sinking and no hovering", async ({
    page,
  }) => {
    const errors = collectErrors(page);
    await open(page, "start=centre&autowalk=turnstile&timescale=4");
    await expect
      .poll(async () => (await readState(page)).systems.structures?.status.state, {
        timeout: 30_000,
      })
      .toBe("ready");

    const frames: FrameSample[] = [];
    let shots = 0;
    await expect
      .poll(
        async () => {
          frames.push(...(await drainFrames(page)));
          const state = await readState(page);
          const onFlight = treadTop(state.player.x, state.player.z) !== null;
          if (onFlight && shots === 0 && state.player.y > 72) {
            shots = 1;
            await page.screenshot({ path: `${SHOTS}/staircase-climb.png` });
          }
          return state.anchorsReached.includes("turnstile");
        },
        { timeout: 180_000, intervals: [200] },
      )
      .toBe(true);
    frames.push(...(await drainFrames(page)));

    const onFlight = frames.filter((f) => treadTop(f.x, f.z) !== null);
    expect(onFlight.length, "frames on the flight").toBeGreaterThan(10);
    const heights = onFlight.map((f) => f.y);
    expect(
      Math.max(...heights) - Math.min(...heights),
      "height climbed on the flight",
    ).toBeGreaterThan(2);
    for (const f of onFlight) {
      const top = treadTop(f.x, f.z) as number;
      expect(f.y - top, `frame ${f.frames} hovers over a tread`).toBeLessThan(MAX_ERROR);
      expect(top - f.y, `frame ${f.frames} sinks into a tread`).toBeLessThan(MAX_ERROR);
    }
    expect(shots).toBe(1);
    expect(errors).toEqual([]);
  });

  test("the staircase meshes load and the surface masks load for the resident tiles", async ({
    page,
  }) => {
    const errors = collectErrors(page);
    const masks: string[] = [];
    let detail = 0;
    page.on("response", (response) => {
      const url = new URL(response.url()).pathname;
      if (response.status() !== 200) return;
      if (/\/surfaces\/t_[^/]+\.ktx2$/.test(url)) masks.push(url);
      if (url.endsWith("rocks_ground_05_diff_1k.ktx2")) detail++;
    });
    await open(page, "start=turnstile&quality=high");
    await expect.poll(() => masks.length, { timeout: 60_000 }).toBeGreaterThan(0);
    await expect.poll(() => detail, { timeout: 60_000 }).toBe(1);
    // One request per tile mask, never more than the 8 tiles of the manifest.
    expect(new Set(masks).size).toBe(masks.length);
    expect(masks.length).toBeLessThanOrEqual(8);
    await waitForFrames(page, 3);
    const terrain = (await page.evaluate(() => window.__world?.textures().terrain)) ?? [];
    const rgba1k = terrain.filter((t) => t.compressed && t.width === 1024 && t.mips);
    expect(rgba1k.length, "1024 px mipmapped compressed terrain textures").toBeGreaterThan(0);
    await page.screenshot({ path: `${SHOTS}/turnstile-staircase.png` });
    expect(errors).toEqual([]);
  });
});
