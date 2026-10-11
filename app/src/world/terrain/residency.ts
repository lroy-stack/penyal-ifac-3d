export type ResidentEntry = {
  readonly id: string;
  readonly level: number;
  /** Last time (ms) the entry was wanted or on screen. */
  readonly lastNeeded: number;
};

/** Resident tile budget per level; levels without an entry are never evicted. */
export type ResidentBudget = Readonly<Record<number, number>>;

export const DEFAULT_BUDGET: ResidentBudget = { 0: 6, 1: 12 };
/** An entry unused for this long (ms) may be evicted once its level is over budget. */
export const EVICTION_GRACE_MS = 10_000;

/**
 * Which resident entries to drop. Per budgeted level, while the level holds more than its budget,
 * the least recently needed entry goes, but only if it has been unused for `graceMs`. Entries in
 * use are never candidates, so a budget smaller than the working set simply is not enforced.
 */
export function chooseEvictions(
  entries: readonly ResidentEntry[],
  budget: ResidentBudget,
  now: number,
  graceMs: number = EVICTION_GRACE_MS,
): ResidentEntry[] {
  const evictions: ResidentEntry[] = [];
  for (const [levelText, limit] of Object.entries(budget)) {
    const level = Number(levelText);
    const atLevel = entries.filter((e) => e.level === level);
    let excess = atLevel.length - limit;
    if (excess <= 0) continue;
    const candidates = atLevel
      .filter((e) => now - e.lastNeeded >= graceMs)
      .sort((a, b) => a.lastNeeded - b.lastNeeded);
    for (const entry of candidates) {
      if (excess <= 0) break;
      evictions.push(entry);
      excess--;
    }
  }
  return evictions;
}
