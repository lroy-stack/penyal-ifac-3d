import { BINARY_TIMEOUT_MS } from "../../core/http";

/**
 * Longest the critical path (far mesh + coarse tiles) may go without any progress before the
 * poster gives up. A hung tile request is aborted after `BINARY_TIMEOUT_MS` and the streamer
 * retries it after its first backoff (2 s); the limit adds 28 s on top, so the retry has
 * launched and has had time to start delivering bytes before the gate gives up. Progress resets
 * the clock, so a slow but moving link never fails.
 */
export const TERRAIN_STALL_LIMIT_MS = BINARY_TIMEOUT_MS + 30_000;

export type TerrainGateOutcome = "waiting" | "visible" | "failed";

/** What the gate needs from the streamer's statistics. */
export type TerrainGateProbe = {
  readonly visible: boolean;
  readonly gaveUp: boolean;
  readonly bytesLoaded: number;
  /** Required near tiles that already have a LOD. */
  readonly loadedTiles: number;
};

export type TerrainGateState = {
  /** Time (ms) since the last progress, counted only while frames run. */
  readonly stalledMs: number;
  readonly bytesLoaded: number;
  readonly loadedTiles: number;
};

export const INITIAL_TERRAIN_GATE: TerrainGateState = {
  stalledMs: 0,
  bytesLoaded: 0,
  loadedTiles: 0,
};

/**
 * Advances the gate by `elapsedMs` of simulated time (the loop's dt: zero while the tab is
 * hidden, so hidden time never counts). Progress (more bytes or more required tiles) restarts the
 * stall clock. The outcome is not latched: a failed gate returns to `waiting` when progress
 * resumes and to `visible` as soon as the terrain shows.
 */
export function stepTerrainGate(
  state: TerrainGateState,
  probe: TerrainGateProbe,
  elapsedMs: number,
): { readonly state: TerrainGateState; readonly outcome: TerrainGateOutcome } {
  const progressed = probe.bytesLoaded > state.bytesLoaded || probe.loadedTiles > state.loadedTiles;
  const next: TerrainGateState = {
    stalledMs: progressed ? 0 : state.stalledMs + elapsedMs,
    bytesLoaded: Math.max(state.bytesLoaded, probe.bytesLoaded),
    loadedTiles: Math.max(state.loadedTiles, probe.loadedTiles),
  };
  if (probe.visible) return { state: next, outcome: "visible" };
  if (probe.gaveUp || next.stalledMs >= TERRAIN_STALL_LIMIT_MS) {
    return { state: next, outcome: "failed" };
  }
  return { state: next, outcome: "waiting" };
}
