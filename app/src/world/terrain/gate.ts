import type { TerrainStats } from "./streamer";

/** Longest the poster waits for the critical path (far mesh + coarse tiles) before it gives up. */
export const TERRAIN_GATE_TIMEOUT_MS = 45_000;

export type TerrainGateOutcome = "waiting" | "visible" | "failed";

/**
 * Decides whether the loading poster can stop waiting for the terrain. The streamer reports
 * `gaveUp` once every retry is spent; the wall clock is the safety net for requests that hang
 * or retries that keep being rescheduled.
 */
export function terrainGateOutcome(
  stats: Pick<TerrainStats, "visible" | "gaveUp">,
  elapsedMs: number,
  timeoutMs: number = TERRAIN_GATE_TIMEOUT_MS,
): TerrainGateOutcome {
  if (stats.visible) return "visible";
  if (stats.gaveUp || elapsedMs >= timeoutMs) return "failed";
  return "waiting";
}
