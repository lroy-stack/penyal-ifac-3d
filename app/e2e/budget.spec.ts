import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import {
  classifyTexture,
  FRAME_BUDGET,
  MS_CALIBRATION,
  SYSTEM_BUDGETS,
  textureBytes,
  toMiB,
} from "../src/core/budget";
import type { QualityTier } from "../src/core/quality";
import type { TextureSample } from "../src/world/textures";
import {
  type DetailSource,
  readState,
  waitForFrames,
  waitForSettledTerrain,
} from "./support/terrain";

// The per-system budget of ADR 0010 section 4 and Amendment 1: at each viewpoint and tier, switch
// every system off in turn and check what it costs in draw calls and triangles against its row,
// its texture estimate against its row, and the totals against the caps. Counts do not depend on
// the GPU, so this runs in SwiftShader and in CI. With PENYAL_E2E_GPU=metal it also measures the
// median frame time with each system on and off and writes the result to budget.json; the ms
// checks fail only once MS_CALIBRATION is set.
const MANIFEST = resolve(import.meta.dirname, "../public/assets/generated/terrain/manifest.json");
const VIEWPOINTS = ["centre", "turnstile", "viewpoint-1795591637", "tunnel-east"];
const TIERS: readonly QualityTier[] = ["low", "medium", "high"];
/** What the detail maps of each tier are on a desktop browser. */
const DETAIL: Readonly<Record<QualityTier, DetailSource>> = {
  low: "procedural",
  medium: "1k",
  high: "2k",
};
const GPU_FRAMES = 300;
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
test.use({ reducedMotion: "reduce", viewport: { width: 1280, height: 720 } });

type Cost = { readonly calls: number; readonly triangles: number };

async function cost(page: Page): Promise<Cost> {
  const { render } = await readState(page);
  return { calls: render.calls, triangles: render.triangles };
}

async function toggle(page: Page, id: string, enabled: boolean): Promise<void> {
  await page.evaluate(
    ([system, on]) => window.__world?.setEnabled(system as string, on as boolean),
    [id, enabled],
  );
  await waitForFrames(page, 2);
}

/** Median of the frame intervals (ms) over `GPU_FRAMES` frames, with the frame cap and vsync off. */
async function medianFrameMs(page: Page): Promise<number> {
  return page.evaluate(async (count) => {
    const intervals: number[] = [];
    let last = performance.now();
    await new Promise<void>((done) => {
      const tick = (now: number): void => {
        intervals.push(now - last);
        last = now;
        if (intervals.length >= count) done();
        else requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    const sorted = intervals.sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)] ?? 0;
  }, GPU_FRAMES);
}

function textureMiB(samples: readonly TextureSample[]): number {
  return toMiB(
    samples.reduce(
      (total, sample) =>
        total +
        textureBytes(
          sample.width,
          sample.height,
          classifyTexture(sample.format, sample.compressed),
          sample.mips,
        ),
      0,
    ),
  );
}

test.describe("per-system budget", () => {
  test.skip(!existsSync(MANIFEST), "terrain tiles not generated (run `penyal terrain`)");

  for (const tier of TIERS) {
    for (const anchor of VIEWPOINTS) {
      test(`${tier} at ${anchor}`, async ({ page }, testInfo) => {
        test.setTimeout(1_200_000);
        const errors: string[] = [];
        page.on("console", (msg) => {
          if (msg.type() === "error") errors.push(msg.text());
        });
        page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));

        await page.goto(`/?start=${anchor}&quality=${tier}`);
        await waitForSettledTerrain(page, DETAIL[tier]);
        await page.evaluate(() => window.__world?.freezeTime(0));
        await waitForFrames(page, 2);

        const state = await readState(page);
        expect(state.quality?.tier).toBe(tier);
        const budgets = SYSTEM_BUDGETS[tier];
        const caps = FRAME_BUDGET[tier];
        const ids = Object.keys(state.systems).filter((id) => !id.startsWith("debug-"));
        expect(ids.length).toBeGreaterThan(0);

        const total = await cost(page);
        expect(total.calls, "draw calls").toBeLessThanOrEqual(caps.drawCallsCap);
        expect(total.triangles, "triangles").toBeLessThanOrEqual(caps.trianglesCap);

        const textures = await page.evaluate(() => window.__world?.textures() ?? {});
        const textureTotal = Object.values(textures).reduce(
          (sum, samples) => sum + textureMiB(samples),
          0,
        );
        expect(textureTotal, "texture MiB").toBeLessThanOrEqual(caps.textureMiBCap);

        const report: Record<string, Record<string, number>> = {};
        const onMs = useMetal ? await medianFrameMs(page) : 0;
        for (const id of ids) {
          const row = budgets[id];
          expect(row, `a budget row for ${id}`).toBeDefined();
          if (row === undefined) continue;
          const mib = textureMiB(textures[id] ?? []);
          expect(mib, `${id} texture MiB`).toBeLessThanOrEqual(row.textureMiB);

          await toggle(page, id, false);
          const off = await cost(page);
          const offMs = useMetal ? await medianFrameMs(page) : 0;
          await toggle(page, id, true);

          const calls = total.calls - off.calls;
          const triangles = total.triangles - off.triangles;
          expect(calls, `${id} draw calls`).toBeLessThanOrEqual(row.drawCalls);
          expect(triangles, `${id} triangles`).toBeLessThanOrEqual(row.triangles);
          const ms = Math.max(0, onMs - offMs);
          if (useMetal && MS_CALIBRATION !== null) {
            expect(ms * MS_CALIBRATION, `${id} ms`).toBeLessThanOrEqual(row.ms);
          }
          report[id] = {
            calls,
            triangles,
            textureMiB: mib,
            ms,
            cpuMs: state.systems[id]?.cpuMs ?? 0,
          };
        }

        const result = { tier, anchor, total, textureMiB: textureTotal, onMs, systems: report };
        console.log(`[budget] ${JSON.stringify(result)}`);
        const directory = process.env.E2E_OUTPUT_DIR ?? testInfo.outputDir;
        mkdirSync(directory, { recursive: true });
        writeFileSync(
          resolve(directory, `budget-${tier}-${anchor}.json`),
          `${JSON.stringify(result, null, 2)}\n`,
        );
        if (useMetal) {
          const file = resolve(directory, "budget.json");
          const all = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : {};
          all[`${tier}/${anchor}`] = result;
          writeFileSync(file, `${JSON.stringify(all, null, 2)}\n`);
        }
        expect(errors).toEqual([]);
      });
    }
  }
});
