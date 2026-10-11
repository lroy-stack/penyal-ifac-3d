import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";
import { waitForApp } from "./support/frames";

async function readState(page: Page): Promise<AppState> {
  const state = await page.evaluate(() => window.__appState);
  if (state === undefined) throw new Error("window.__appState is not published.");
  return state;
}

async function open(page: Page, query: string): Promise<string[]> {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (error) => {
    errors.push(`pageerror: ${error.message}`);
  });
  await page.setViewportSize({ width: 640, height: 360 });
  await page.goto(`/?${query}`);
  await waitForApp(page);
  return errors;
}

test.describe("auto-walk controls", () => {
  test.setTimeout(120_000);

  test("P starts the walk to the summit, P again stops it", async ({ page }) => {
    const errors = await open(page, "start=turnstile&timescale=4");
    expect((await readState(page)).autowalk).toEqual({ active: false, target: null, progress: 0 });
    const start = await readState(page);

    await page.keyboard.press("KeyP");
    await expect.poll(async () => (await readState(page)).autowalk.active).toBe(true);
    expect((await readState(page)).autowalk.target).toBe("summit");
    await expect
      .poll(async () => {
        const { x, z } = (await readState(page)).player;
        return Math.hypot(x - start.player.x, z - start.player.z);
      })
      .toBeGreaterThan(2);

    await page.keyboard.press("KeyP");
    await expect.poll(async () => (await readState(page)).autowalk.active).toBe(false);
    expect(errors).toEqual([]);
  });

  test("manual movement cancels the walk", async ({ page }) => {
    const errors = await open(page, "start=turnstile&autowalk=summit&timescale=4");
    await expect.poll(async () => (await readState(page)).autowalk.active).toBe(true);
    await page.keyboard.down("KeyS");
    await expect.poll(async () => (await readState(page)).autowalk.active).toBe(false);
    await page.keyboard.up("KeyS");
    const progress = (await readState(page)).autowalk.progress;
    await page.waitForTimeout(1000);
    expect((await readState(page)).autowalk.progress).toBe(progress);
    expect(errors).toEqual([]);
  });

  test("an unknown target explains itself and does not walk", async ({ page }) => {
    const errors = await open(page, "start=turnstile&autowalk=nowhere");
    expect((await readState(page)).autowalk.active).toBe(false);
    await expect(page.locator("#status")).toContainText("Unknown auto-walk target");
    expect(errors).toEqual([]);
  });
});
