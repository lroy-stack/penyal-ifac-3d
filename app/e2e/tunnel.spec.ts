import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";
import { parseTunnel, TunnelGroundSurface } from "../src/world/tunnel";
import { drainFrames, type FrameSample, installFrameRecorder, waitForApp } from "./support/frames";

const GENERATED = resolve(import.meta.dirname, "../public/assets/generated");

// Independent check: the test reads tunnel.json from disk and compares the app's state with it.
const tunnel = parseTunnel(JSON.parse(readFileSync(resolve(GENERATED, "tunnel.json"), "utf8")));
const surface = new TunnelGroundSurface(tunnel);
const MAX_FLOOR_ERROR = 0.2;

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
  await page.setViewportSize({ width: 800, height: 450 });
  await page.goto(`/?${query}`);
  await waitForApp(page);
  await expect
    .poll(async () => (await readState(page)).tunnel.status, { timeout: 15_000 })
    .toBe("ready");
}

/** Every frame must be on the tunnel floor, in the corridor of the tunnel strip. */
function expectOnFloor(frames: readonly FrameSample[]): void {
  for (const f of frames) {
    const floor = surface.floorAt(f.x, f.z);
    expect(floor, `frame ${f.frames} at (${f.x}, ${f.z}) left the tunnel strip`).not.toBeNull();
    expect(f.grounded, `frame ${f.frames} not grounded`).toBe(true);
    expect(Math.abs(f.y - (floor as number)), `frame ${f.frames} off the floor`).toBeLessThan(
      MAX_FLOOR_ERROR,
    );
  }
}

test.describe("tunnel", () => {
  test.setTimeout(240_000);

  test("the tunnel data loaded and the portals match the anchors", async ({ page }) => {
    const errors = collectErrors(page);
    await open(page, "start=tunnel-west");
    const state = await readState(page);
    expect(state.tunnel.message).toBeNull();
    await expect
      .poll(async () => (await readState(page)).tunnel.meshLoaded, { timeout: 30_000 })
      .toBe(true);

    expect(state.player.grounded).toBe(true);
    const floor = surface.floorAt(state.player.x, state.player.z);
    expect(floor).not.toBeNull();
    expect(Math.abs(state.player.y - (floor as number))).toBeLessThan(MAX_FLOOR_ERROR);
    expect(errors).toEqual([]);
  });

  test("walks from tunnel-west to tunnel-east on the floor, in first person", async ({ page }) => {
    const errors = collectErrors(page);
    await open(page, "start=tunnel-west&autowalk=tunnel-east&timescale=8");
    const frames: FrameSample[] = [];
    let shot = false;
    await expect
      .poll(
        async () => {
          frames.push(...(await drainFrames(page)));
          const state = await readState(page);
          if (!shot && state.autowalk.progress > 0.5) {
            shot = true;
            await page.screenshot({ path: "test-results/tunnel-first-person.png" });
          }
          return state.anchorsReached.includes("tunnel-east");
        },
        { timeout: 120_000, intervals: [250] },
      )
      .toBe(true);
    frames.push(...(await drainFrames(page)));

    expect(frames.length).toBeGreaterThan(10);
    expectOnFloor(frames);
    expect(shot).toBe(true);
    const last = frames[frames.length - 1] as FrameSample;
    expect(Math.hypot(last.x - tunnel.portals.east.x, last.z - tunnel.portals.east.z)).toBeLessThan(
      8,
    );
    expect(errors).toEqual([]);
  });

  test("walks the tunnel in third person with the camera inside it", async ({ page }) => {
    const errors = collectErrors(page);
    await open(page, "start=tunnel-west&autowalk=tunnel-east&timescale=8");
    await page.keyboard.press("KeyC");
    await expect.poll(async () => (await readState(page)).player.cameraMode).toBe("third");

    const frames: FrameSample[] = [];
    let shot = false;
    await expect
      .poll(
        async () => {
          frames.push(...(await drainFrames(page)));
          const state = await readState(page);
          if (!shot && state.autowalk.progress > 0.5) {
            shot = true;
            await page.screenshot({ path: "test-results/tunnel-third-person.png" });
          }
          return state.anchorsReached.includes("tunnel-east");
        },
        { timeout: 120_000, intervals: [250] },
      )
      .toBe(true);
    frames.push(...(await drainFrames(page)));

    expectOnFloor(frames);
    expect(shot).toBe(true);
    const thirdPerson = frames.filter((f) => f.cameraMode === "third");
    expect(thirdPerson.length).toBeGreaterThan(10);
    for (const f of thirdPerson) {
      const { x, y, z } = f.camera;
      expect(surface.contains(x, y, z, 0), `frame ${f.frames}: camera left the tunnel`).toBe(true);
    }
    expect(errors).toEqual([]);
  });

  test("holding W from tunnel-west walks into the tunnel on its floor", async ({ page }) => {
    const errors = collectErrors(page);
    await open(page, "start=tunnel-west&timescale=8");
    const before = await readState(page);
    await drainFrames(page);
    await page.keyboard.down("KeyW");
    await expect
      .poll(async () => (await readState(page)).player.elapsed - before.player.elapsed, {
        timeout: 60_000,
      })
      .toBeGreaterThan(8);
    await page.keyboard.up("KeyW");
    const frames = await drainFrames(page);
    const after = await readState(page);

    expectOnFloor(frames);
    expect(
      Math.hypot(after.player.x - before.player.x, after.player.z - before.player.z),
    ).toBeGreaterThan(5);
    expect(errors).toEqual([]);
  });
});
