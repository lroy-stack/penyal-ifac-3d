import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";

// Visual evidence of the real terrain along the Ruta Roja: start at known anchors, let the
// streamer settle, and save first- and third-person screenshots for review.
const MANIFEST = resolve(import.meta.dirname, "../public/assets/generated/terrain/manifest.json");
const VIEWPOINTS = [
  "turnstile",
  "viewpoint-1795591637",
  "tunnel-east",
  "bifurcation",
  "summit",
  "carabiners",
];

// Desktop budget from the spec (AC7): draw calls ≤ 300, triangles ≤ 1.5 M.
const MAX_CALLS = 300;
const MAX_TRIANGLES = 1_500_000;

async function readState(page: Page): Promise<AppState> {
  const state = await page.evaluate(() => window.__appState);
  if (state === undefined) throw new Error("window.__appState is not published.");
  return state;
}

async function waitForSettledTerrain(page: Page): Promise<AppState> {
  await expect
    .poll(
      async () => {
        const stats = (await readState(page)).terrain.stats;
        return stats?.farLoaded === true && stats.pending === 0 && stats.inFlight === 0;
      },
      { timeout: 45_000, intervals: [500] },
    )
    .toBe(true);
  return readState(page);
}

test.describe("real terrain along the Ruta Roja", () => {
  test.skip(!existsSync(MANIFEST), "terrain tiles not generated (run `penyal terrain`)");

  for (const anchor of VIEWPOINTS) {
    test(`renders settled terrain at ${anchor}`, async ({ page }) => {
      const errors: string[] = [];
      page.on("console", (msg) => {
        if (msg.type() === "error") errors.push(msg.text());
      });
      page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));

      await page.setViewportSize({ width: 1280, height: 720 });
      await page.goto(`/?start=${anchor}`);
      const state = await waitForSettledTerrain(page);

      expect(state.terrain.stats?.failed ?? 0).toBe(0);
      expect(state.player.grounded).toBe(true);
      await page.screenshot({ path: `test-results/viewpoints/${anchor}-first.png` });

      await page.keyboard.press("KeyC");
      await expect.poll(async () => (await readState(page)).player.cameraMode).toBe("third");
      const third = await waitForSettledTerrain(page);
      await page.screenshot({ path: `test-results/viewpoints/${anchor}-third.png` });

      expect(third.render.calls).toBeLessThanOrEqual(MAX_CALLS);
      expect(third.render.triangles).toBeLessThanOrEqual(MAX_TRIANGLES);
      expect(errors).toEqual([]);
    });
  }
});
