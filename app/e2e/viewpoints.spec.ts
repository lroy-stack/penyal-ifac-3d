import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";
import type { AppState } from "../src/appState";
import { type DetailSource, readState, waitForSettledTerrain } from "./support/terrain";

// Regression evidence of the real terrain along the Ruta Roja: start at known anchors, let the
// streamer settle and compare the canvas and the render metrics with the baselines in
// `build/e2e-baselines/` (not committed: they belong to the machine and the generated assets that
// produced them). Create them with `--update-snapshots` before a refactor, run again after it.
//
// Reduced motion makes the camera snap (no smoothing), so a capture does not depend on frame
// timing. The six anchors run at `low`, which is what SwiftShader gets by default; two of them
// also run with `?terrain=high`, so the terrain shader patch is exercised.
const MANIFEST = resolve(import.meta.dirname, "../public/assets/generated/terrain/manifest.json");

type Case = { readonly id: string; readonly anchor: string; readonly tier: "low" | "high" };

const LOW_ANCHORS = [
  "turnstile",
  "viewpoint-1795591637",
  "tunnel-east",
  "bifurcation",
  "summit",
  "carabiners",
];
const HIGH_ANCHORS = ["turnstile", "viewpoint-1795591637"];
const CASES: readonly Case[] = [
  ...LOW_ANCHORS.map((anchor) => ({ id: `${anchor}-low`, anchor, tier: "low" as const })),
  ...HIGH_ANCHORS.map((anchor) => ({ id: `${anchor}-high`, anchor, tier: "high" as const })),
];

// Desktop budget from the spec (AC7): draw calls ≤ 300, triangles ≤ 1.5 M.
const MAX_CALLS = 300;
const MAX_TRIANGLES = 1_500_000;
/** Per-pixel colour threshold is 0; this many pixels may differ (SwiftShader run-to-run noise). */
const MAX_DIFF_PIXELS = 16;

test.use({ reducedMotion: "reduce", viewport: { width: 1280, height: 720 } });

const DETAIL: Readonly<Record<Case["tier"], DetailSource>> = { low: "procedural", high: "2k" };

const round = (value: number): number => Math.round(value * 1000) / 1000;

function metricsOf(state: AppState): Record<string, unknown> {
  const { player, camera, render, terrain } = state;
  return {
    calls: render.calls,
    triangles: render.triangles,
    programs: render.programs,
    quality: terrain.stats?.quality ?? null,
    detail: terrain.stats?.detail ?? null,
    displayed: terrain.stats?.displayed ?? null,
    player: { x: round(player.x), y: round(player.y), z: round(player.z), yaw: round(player.yaw) },
    camera: { x: round(camera.x), y: round(camera.y), z: round(camera.z) },
  };
}

test.describe("real terrain along the Ruta Roja", () => {
  test.skip(!existsSync(MANIFEST), "terrain tiles not generated (run `penyal terrain`)");

  for (const { id, anchor, tier } of CASES) {
    test(`renders settled terrain at ${id}`, async ({ page }) => {
      // The high tier shades every pixel with the terrain patch, which is slow in SwiftShader
      // (a frame every 3 s on a busy machine).
      test.setTimeout(900_000);
      const errors: string[] = [];
      page.on("console", (msg) => {
        if (msg.type() === "error") errors.push(msg.text());
      });
      page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));

      await page.goto(`/?start=${anchor}${tier === "high" ? "&terrain=high" : ""}`);
      // Only the canvas is compared: hints and notices fade on timers.
      await page.addStyleTag({ content: "body > :not(#scene) { visibility: hidden !important; }" });
      const first = await waitForSettledTerrain(page, DETAIL[tier]);

      expect(first.terrain.stats?.failed ?? 0).toBe(0);
      expect(first.terrain.stats?.quality).toBe(tier);
      expect(first.player.grounded).toBe(true);
      await expect(page).toHaveScreenshot(`${id}-first.png`, {
        threshold: 0,
        maxDiffPixels: MAX_DIFF_PIXELS,
        animations: "disabled",
        timeout: 60_000,
      });

      await page.keyboard.press("KeyC");
      await expect
        .poll(async () => (await readState(page)).player.cameraMode, { timeout: 120_000 })
        .toBe("third");
      const third = await waitForSettledTerrain(page, DETAIL[tier]);
      await expect(page).toHaveScreenshot(`${id}-third.png`, {
        threshold: 0,
        maxDiffPixels: MAX_DIFF_PIXELS,
        animations: "disabled",
        timeout: 60_000,
      });

      expect(third.render.calls).toBeLessThanOrEqual(MAX_CALLS);
      expect(third.render.triangles).toBeLessThanOrEqual(MAX_TRIANGLES);
      const metrics = `${JSON.stringify({ first: metricsOf(first), third: metricsOf(third) }, null, 2)}\n`;
      expect(metrics).toMatchSnapshot(`${id}.metrics.json`);
      expect(errors).toEqual([]);
    });
  }
});
