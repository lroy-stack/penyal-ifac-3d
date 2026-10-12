import { existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import { SYSTEM_BUDGETS } from "../src/core/budget";
import { readState, waitForFrames } from "./support/terrain";

// Measured vegetation (E2.5, ADR 0010 section 4): at the turnstile the LiDAR pines and the
// understory are instanced around the camera, within the `medium` row of the budget, with no
// console errors. Set E2E_SHOTS_DIR to also save canvas screenshots of a few anchors.
const VEGETATION = resolve(import.meta.dirname, "../public/assets/generated/vegetation.json");
const shotsDirectory = process.env.E2E_SHOTS_DIR;

test.use({ reducedMotion: "reduce", viewport: { width: 1280, height: 720 } });
test.skip(!existsSync(VEGETATION), "vegetation not generated (run the vegetation pipeline)");

async function openAt(page: import("@playwright/test").Page, anchor: string): Promise<void> {
  await page.goto(`/?start=${anchor}&quality=medium`);
  await expect
    .poll(async () => (await readState(page)).systems.vegetation?.status.state, {
      timeout: 120_000,
      intervals: [500],
    })
    .toBe("ready");
  await waitForFrames(page, 12);
}

test.describe("vegetation", () => {
  test.setTimeout(300_000);

  test("is ready at the turnstile with instances in range, within the medium budget", async ({
    page,
  }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));

    await openAt(page, "turnstile");
    const counts = await page.evaluate(() => window.__vegetation?.counts());
    expect(counts, "the vegetation test hook").toBeDefined();
    const trees = counts?.trees.reduce((a, b) => a + b, 0) ?? 0;
    const understory = counts?.understory.reduce((a, b) => a + b, 0) ?? 0;
    expect(trees, "trees drawn near the turnstile").toBeGreaterThan(0);
    expect(understory, "understory drawn near the turnstile").toBeGreaterThan(0);
    console.log(`[vegetation] ${JSON.stringify(counts)}`);

    await page.evaluate(() => window.__world?.freezeTime(0));
    await waitForFrames(page, 2);
    const on = (await readState(page)).render;
    await page.evaluate(() => window.__world?.setEnabled("vegetation", false));
    await waitForFrames(page, 2);
    const off = (await readState(page)).render;
    const row = SYSTEM_BUDGETS.medium.vegetation;
    expect(row).toBeDefined();
    expect(on.calls - off.calls, "vegetation draw calls").toBeGreaterThan(0);
    expect(on.calls - off.calls, "vegetation draw calls").toBeLessThanOrEqual(row?.drawCalls ?? 0);
    expect(on.triangles - off.triangles, "vegetation triangles").toBeLessThanOrEqual(
      row?.triangles ?? 0,
    );
    console.log(
      `[vegetation] calls ${on.calls - off.calls}, triangles ${on.triangles - off.triangles}`,
    );
    expect(errors).toEqual([]);
  });

  test("saves screenshots of three anchors", async ({ page }) => {
    test.skip(shotsDirectory === undefined, "set E2E_SHOTS_DIR to save screenshots");
    test.setTimeout(900_000);
    await page.setViewportSize({ width: 960, height: 540 });
    const directory = shotsDirectory as string;
    mkdirSync(directory, { recursive: true });
    for (const [name, anchor] of [
      ["turnstile-eye-level", "turnstile"],
      ["up-the-trail", "viewpoint-3635481356"],
      ["pobla-pines", "pobla"],
    ] as const) {
      await openAt(page, anchor);
      await page.addStyleTag({ content: "body > :not(#scene) { visibility: hidden !important; }" });
      await waitForFrames(page, 3);
      await page.locator("#scene").screenshot({ path: resolve(directory, `${name}.png`) });
    }
  });
});
