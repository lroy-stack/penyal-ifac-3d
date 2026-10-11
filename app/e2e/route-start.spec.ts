import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";
import { PolygonCorridor, QuantizedHeightField } from "../src/world/ground";
import { parseTrail } from "../src/world/trail";

const GENERATED = resolve(import.meta.dirname, "../public/assets/generated");

// Independent check against the same generated files the app loads: the test reads them from
// disk and compares the app's state with them.
function loadHeightField(): QuantizedHeightField {
  const meta: unknown = JSON.parse(
    readFileSync(resolve(GENERATED, "terrain/collision.json"), "utf8"),
  );
  const bin = readFileSync(resolve(GENERATED, "terrain/collision.bin"));
  const buffer = bin.buffer.slice(bin.byteOffset, bin.byteOffset + bin.byteLength) as ArrayBuffer;
  return QuantizedHeightField.fromBuffer(meta, buffer);
}

const trail = parseTrail(JSON.parse(readFileSync(resolve(GENERATED, "trail.json"), "utf8")));
const heightField = loadHeightField();
const corridor = new PolygonCorridor(trail.corridor.polygon.map(([x, z]) => [x, z] as const));
const turnstile = trail.anchors.turnstile;
if (turnstile === undefined) throw new Error("trail.json has no turnstile anchor.");

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

test("starts grounded at the turnstile and walks inside the corridor", async ({ page }, info) => {
  const errors = collectErrors(page);
  await page.goto("/?debug=trail");
  await expect
    .poll(async () => (await readState(page)).ready && (await readState(page)).frames, {
      timeout: 45_000,
    })
    .toBeGreaterThan(3);

  const start = await readState(page);
  const terrainTiles = start.terrain.status === "ready";
  info.annotations.push({
    type: "terrain-tiles",
    description: terrainTiles
      ? "present"
      : `absent (status: ${start.terrain.status}); only the collision height field was exercised`,
  });
  expect(["ready", "missing"]).toContain(start.terrain.status);

  expect(start.player.grounded).toBe(true);
  expect(Math.hypot(start.player.x - turnstile.x, start.player.z - turnstile.z)).toBeLessThan(2);
  const ground = heightField.heightAt(start.player.x, start.player.z);
  expect(ground).not.toBeNull();
  expect(Math.abs(start.player.y - (ground ?? Number.NaN))).toBeLessThan(0.2);
  expect(corridor.contains(start.player.x, start.player.z)).toBe(true);
  await expect(page.locator("#status")).not.toBeEmpty();
  await page.screenshot({ path: "test-results/route-start-first-person.png" });

  await page.keyboard.down("KeyW");
  const samples: AppState[] = [];
  for (let i = 0; i < 6; i++) {
    await page.waitForTimeout(500);
    samples.push(await readState(page));
  }
  await page.keyboard.up("KeyW");

  for (const sample of samples) {
    expect(corridor.contains(sample.player.x, sample.player.z)).toBe(true);
    expect(sample.player.grounded).toBe(true);
  }
  const end = samples[samples.length - 1] as AppState;
  const moved = Math.hypot(end.player.x - start.player.x, end.player.z - start.player.z);
  expect(moved).toBeGreaterThan(0.3);
  expect(end.player.elapsed).toBeGreaterThan(start.player.elapsed);
  expect(end.render.calls).toBeGreaterThan(0);
  expect(end.frameTimeP95Ms).not.toBeNull();

  await page.keyboard.press("KeyC");
  await expect.poll(async () => (await readState(page)).player.cameraMode).toBe("third");
  await page.waitForTimeout(1500);
  await page.screenshot({ path: "test-results/route-start-third-person.png" });

  expect(errors).toEqual([]);
});
