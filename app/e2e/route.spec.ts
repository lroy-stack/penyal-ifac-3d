import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";
import { PolygonCorridor, QuantizedHeightField } from "../src/world/ground";
import { parseTrail } from "../src/world/trail";
import { parseTunnel, TunnelGroundSurface } from "../src/world/tunnel";
import {
  dataUrlToBuffer,
  drainAnchorShots,
  drainFrames,
  type FrameSample,
  installFrameRecorder,
  waitForApp,
} from "./support/frames";

const GENERATED = resolve(import.meta.dirname, "../public/assets/generated");
const RESULTS = resolve(import.meta.dirname, "../test-results");
const METRICS_PATH = resolve(RESULTS, "route-metrics.json");
const SHOTS_DIR = resolve(RESULTS, "route");

// The loop clamps each frame to 0.1 s and SwiftShader renders a few frames per second, so the
// walk is paced by the frame rate: 16x at a small viewport covers the 1.8 km in a few minutes.
const TIMESCALE = 16;
/**
 * 1.8 km at walking pace is about 22 simulated minutes: a few minutes of wall clock on an idle
 * machine, much longer when other browsers compete for the CPU. The test therefore fails when
 * the walker stops making progress (stuck against a wall), not when the machine is slow, with an
 * absolute cap as a backstop.
 */
const STALL_TIMEOUT_MS = 90_000;
const ROUTE_TIMEOUT_MS = 20 * 60_000;
/** The player may be this far (m) from the ground it should stand on (a stone step is 0.4 m). */
const GROUND_TOLERANCE = 0.5;

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(resolve(GENERATED, path), "utf8"));
}

// Independent check against the same generated files the app loads.
const bin = readFileSync(resolve(GENERATED, "terrain/collision.bin"));
const heightField = QuantizedHeightField.fromBuffer(
  readJson("terrain/collision.json"),
  bin.buffer.slice(bin.byteOffset, bin.byteOffset + bin.byteLength) as ArrayBuffer,
);
const trail = parseTrail(readJson("trail.json"));
const corridor = new PolygonCorridor(trail.corridor.polygon.map(([x, z]) => [x, z] as const));
const tunnel = new TunnelGroundSurface(parseTunnel(readJson("tunnel.json")));

type MetricPoint = {
  anchor: string;
  wallSeconds: number;
  simulatedSeconds: number;
  frameTimeP95Ms: number | null;
  drawCalls: number;
  triangles: number;
};

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

// Both tests run in this worker; the file is rewritten in full so it always holds every result.
const allMetrics: Record<string, MetricPoint[]> = {};

function recordMetrics(target: string, points: MetricPoint[]): void {
  allMetrics[target] = points;
  mkdirSync(RESULTS, { recursive: true });
  writeFileSync(METRICS_PATH, `${JSON.stringify(allMetrics, null, 2)}\n`);
}

function expectFrameOnRoute(frame: FrameSample): void {
  const where = `frame ${frame.frames} at (${frame.x.toFixed(1)}, ${frame.z.toFixed(1)})`;
  expect(corridor.contains(frame.x, frame.z), `${where} left the corridor`).toBe(true);
  expect(frame.grounded, `${where} is not grounded`).toBe(true);
  const supports = [heightField.heightAt(frame.x, frame.z), tunnel.floorAt(frame.x, frame.z)];
  const nearest = Math.min(
    ...supports.filter((h): h is number => h !== null).map((h) => Math.abs(frame.y - h)),
  );
  expect(nearest, `${where} floats or sinks (y = ${frame.y.toFixed(2)})`).toBeLessThan(
    GROUND_TOLERANCE,
  );
}

async function walkTo(
  page: Page,
  target: string,
  inOrder: readonly string[],
): Promise<{ metrics: MetricPoint[]; frames: number }> {
  await installFrameRecorder(page);
  await page.setViewportSize({ width: 640, height: 360 });
  await page.goto(`/?start=turnstile&autowalk=${target}&timescale=${TIMESCALE}`);
  await waitForApp(page);
  expect((await readState(page)).autowalk).toMatchObject({ active: true, target });
  const wallStart = Date.now();
  const metrics: MetricPoint[] = [];
  const seen = new Set<string>();
  let frames = 0;
  const deadline = Date.now() + ROUTE_TIMEOUT_MS;
  let bestProgress = 0;
  let lastAdvance = Date.now();
  for (let reached = false; !reached; ) {
    if (Date.now() > deadline || Date.now() - lastAdvance > STALL_TIMEOUT_MS) {
      const { player, autowalk, anchorsReached, frames: rendered } = await readState(page);
      throw new Error(
        `Never reached "${target}" (no progress for ${STALL_TIMEOUT_MS / 1000} s or over the time limit): ${JSON.stringify({ player, autowalk, anchorsReached, rendered })}`,
      );
    }
    await page.waitForTimeout(1000);
    for (const frame of await drainFrames(page)) {
      expectFrameOnRoute(frame);
      frames++;
    }
    const state = await readState(page);
    if (state.autowalk.progress > bestProgress + 1e-4) {
      bestProgress = state.autowalk.progress;
      lastAdvance = Date.now();
    }
    const shots = await drainAnchorShots(page);
    for (const [anchor, dataUrl] of Object.entries(shots)) {
      mkdirSync(SHOTS_DIR, { recursive: true });
      writeFileSync(resolve(SHOTS_DIR, `${anchor}.png`), dataUrlToBuffer(dataUrl));
    }
    for (const anchor of state.anchorsReached) {
      if (!inOrder.includes(anchor) || seen.has(anchor)) continue;
      seen.add(anchor);
      metrics.push({
        anchor,
        wallSeconds: (Date.now() - wallStart) / 1000,
        simulatedSeconds: state.player.elapsed,
        frameTimeP95Ms: state.frameTimeP95Ms,
        drawCalls: state.render.calls,
        triangles: state.render.triangles,
      });
    }
    reached = state.anchorsReached.includes(target);
  }

  for (const frame of await drainFrames(page)) {
    expectFrameOnRoute(frame);
    frames++;
  }
  const final = await readState(page);
  const order = inOrder.map((anchor) => final.anchorsReached.indexOf(anchor));
  expect(
    order.every((index) => index >= 0),
    `anchors reached: ${final.anchorsReached}`,
  ).toBe(true);
  expect(order, "anchors were reached out of order").toEqual([...order].sort((a, b) => a - b));
  expect(final.player.grounded).toBe(true);
  return { metrics, frames };
}

test.describe.configure({ mode: "serial" });
test.describe("full route", () => {
  test.setTimeout(ROUTE_TIMEOUT_MS + 120_000);

  test("auto-walks from the turnstile to the summit through the tunnel", async ({ page }) => {
    const errors = collectErrors(page);
    const { metrics, frames } = await walkTo(page, "summit", [
      "tunnel-west",
      "tunnel-east",
      "bifurcation",
      "summit",
    ]);
    recordMetrics("summit", metrics);
    expect(frames).toBeGreaterThan(100);
    expect(metrics.map((m) => m.anchor)).toEqual([
      "tunnel-west",
      "tunnel-east",
      "bifurcation",
      "summit",
    ]);
    expect(errors).toEqual([]);
  });

  test("auto-walks from the turnstile to the Mirador de Carabiners", async ({ page }) => {
    const errors = collectErrors(page);
    const { metrics, frames } = await walkTo(page, "carabiners", [
      "tunnel-west",
      "tunnel-east",
      "bifurcation",
      "carabiners",
    ]);
    recordMetrics("carabiners", metrics);
    expect(frames).toBeGreaterThan(100);
    expect(errors).toEqual([]);
  });
});
