import { expect, type Page } from "@playwright/test";
import type { AppState } from "../../src/appState";

/** What the terrain statistics say `detail` is once the maps for a tier have loaded. */
export type DetailSource = "procedural" | "1k" | "2k";

/** The app refreshes the terrain statistics every 15 frames; one snapshot can be a refresh behind. */
export const SETTLE_FRAMES = 16;

export async function readState(page: Page): Promise<AppState> {
  const state = await page.evaluate(() => window.__appState);
  if (state === undefined) throw new Error("window.__appState is not published.");
  return state;
}

/**
 * Waits until the terrain is settled: the far mesh is in, nothing is loading, the detail maps are
 * the expected ones, and two statistics snapshots at least `SETTLE_FRAMES` frames apart show the
 * same tiles. Returns the state of the last snapshot.
 */
export async function waitForSettledTerrain(
  page: Page,
  detail: DetailSource,
  timeout = 480_000,
): Promise<AppState> {
  let reference: { readonly frames: number; readonly displayed: string } | null = null;
  const settled = async (): Promise<boolean> => {
    const state = await readState(page);
    const stats = state.terrain.stats;
    if (
      stats?.farLoaded !== true ||
      stats.pending !== 0 ||
      stats.inFlight !== 0 ||
      stats.detail !== detail
    ) {
      reference = null;
      return false;
    }
    const displayed = JSON.stringify(stats.displayed);
    if (reference === null || reference.displayed !== displayed) {
      reference = { frames: state.frames, displayed };
      return false;
    }
    return state.frames - reference.frames >= SETTLE_FRAMES;
  };
  await expect.poll(settled, { timeout, intervals: [500] }).toBe(true);
  return readState(page);
}

/**
 * What is still loading besides the terrain tiles: world systems that are `pending` (background
 * ones start after the walk) or `loading`, and the painted-surface masks (the manifest, the
 * detail map and the masks of the resident tiles; they are up to 10.7 MiB). Debug systems are
 * ignored. Empty when everything has loaded, failed or is missing.
 */
export function unsettledWork(state: AppState): string[] {
  const work = Object.entries(state.systems)
    .filter(([id]) => !id.startsWith("debug-"))
    .filter(([, system]) => system.status.state === "pending" || system.status.state === "loading")
    .map(([id, system]) => `${id} is ${system.status.state}`);
  const pending = state.terrain.stats?.surfaces.pending ?? 0;
  if (pending > 0) work.push(`${pending} surface request(s) pending`);
  return work;
}

/**
 * Waits until every non-debug system has finished initialising and the surface masks have
 * loaded or failed, so a measurement does not count a system that has not started yet as free.
 * Call it after `waitForSettledTerrain`; it settles on the same two-snapshot rule, because masks
 * start when a tile LOD arrives.
 */
export async function waitForSettledWorld(page: Page, timeout = 480_000): Promise<AppState> {
  let quietSince: number | null = null;
  const settled = async (): Promise<boolean> => {
    const state = await readState(page);
    if (Object.keys(state.systems).length === 0) return false;
    if (unsettledWork(state).length > 0) {
      quietSince = null;
      return false;
    }
    quietSince ??= state.frames;
    return state.frames - quietSince >= SETTLE_FRAMES;
  };
  await expect.poll(settled, { timeout, intervals: [500] }).toBe(true);
  return readState(page);
}

/** Waits for `count` more rendered frames. */
export async function waitForFrames(page: Page, count: number, timeout = 120_000): Promise<void> {
  const { frames } = await readState(page);
  await expect
    .poll(async () => (await readState(page)).frames, { timeout })
    .toBeGreaterThanOrEqual(frames + count);
}
