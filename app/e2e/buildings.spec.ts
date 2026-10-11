import { expect, type Page, test } from "@playwright/test";
import { SYSTEM_BUDGETS } from "../src/core/budget";
import { readState, waitForFrames } from "./support/terrain";

// E3: the two visitor-centre buildings. The system must be ready, its meshes must be drawn when
// the camera looks at them (switching the system off removes triangles and draw calls, within the
// system's budget row) and the page must stay free of console errors. The screenshot goes to the
// test output directory as evidence.
const TURNSTILE = { x: 549.331, z: -1024.352 };
const CENTRE_OF_BUILDINGS = { x: 545, z: -1040 };
const YAW_TOLERANCE = 0.08;

test.use({ reducedMotion: "reduce", viewport: { width: 1280, height: 720 } });

/** Turns with the arrow keys until the player's yaw is within tolerance of `target` (radians). */
async function faceYaw(page: Page, target: number): Promise<void> {
  for (let attempt = 0; attempt < 200; attempt++) {
    const { yaw } = (await readState(page)).player;
    const error = Math.atan2(Math.sin(target - yaw), Math.cos(target - yaw));
    if (Math.abs(error) < YAW_TOLERANCE) return;
    const key = error > 0 ? "ArrowLeft" : "ArrowRight";
    await page.keyboard.down(key);
    await waitForFrames(page, 2);
    await page.keyboard.up(key);
    await waitForFrames(page, 1);
  }
  throw new Error(`Could not face yaw ${target}.`);
}

test.describe("visitor-centre buildings", () => {
  test.setTimeout(240_000);

  test("the system is ready and its meshes are drawn from the turnstile", async ({
    page,
  }, testInfo) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));

    await page.goto("/?start=turnstile");
    await expect
      .poll(async () => (await readState(page)).systems.buildings?.status.state, {
        timeout: 60_000,
      })
      .toBe("ready");

    const target = Math.atan2(
      -(CENTRE_OF_BUILDINGS.x - TURNSTILE.x),
      -(CENTRE_OF_BUILDINGS.z - TURNSTILE.z),
    );
    await faceYaw(page, target);
    await page.addStyleTag({ content: "body > :not(#scene) { visibility: hidden !important; }" });
    await waitForFrames(page, 4);

    const on = (await readState(page)).render;
    await page.evaluate(() => window.__world?.setEnabled("buildings", false));
    await waitForFrames(page, 4);
    const off = (await readState(page)).render;
    await page.evaluate(() => window.__world?.setEnabled("buildings", true));
    await waitForFrames(page, 4);

    const triangles = on.triangles - off.triangles;
    const calls = on.calls - off.calls;
    const row = SYSTEM_BUDGETS.medium.buildings;
    expect(triangles, "triangles drawn by the buildings").toBeGreaterThan(0);
    expect(calls, "draw calls of the buildings").toBeGreaterThan(0);
    expect(triangles).toBeLessThanOrEqual(row?.triangles ?? 0);
    expect(calls).toBeLessThanOrEqual(row?.drawCalls ?? 0);

    await page.screenshot({ path: testInfo.outputPath("buildings-from-turnstile.png") });
    expect(errors).toEqual([]);
  });

  test("the system is ready when the walk starts at the centre", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
    await page.goto("/?start=centre");
    await expect
      .poll(async () => (await readState(page)).systems.buildings?.status.state, {
        timeout: 60_000,
      })
      .toBe("ready");
    expect(errors).toEqual([]);
  });
});
