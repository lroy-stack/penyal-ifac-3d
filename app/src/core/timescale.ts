/** Largest `?timescale=` accepted. */
export const MAX_TIMESCALE = 16;

/**
 * Test-only simulation speed-up from `?timescale=N`: 1 (default) to 16. Anything that is not a
 * finite number is ignored; numbers outside the range are clamped.
 */
export function parseTimescale(search: string): number {
  const value = new URLSearchParams(search).get("timescale");
  if (value === null || value.trim() === "") return 1;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 1;
  return Math.min(MAX_TIMESCALE, Math.max(1, parsed));
}

/**
 * Splits one frame of simulation time (the loop's delta, already clamped, times the timescale)
 * into updates of at most `maxStep` seconds, which the player can take without truncating them.
 */
export function simulationSteps(dt: number, timescale: number, maxStep: number): number[] {
  const total = Math.max(dt, 0) * timescale;
  if (total === 0) return [];
  const count = Math.ceil(total / maxStep);
  return Array.from({ length: count }, () => total / count);
}
