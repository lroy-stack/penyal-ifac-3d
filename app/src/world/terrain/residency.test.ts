import { describe, expect, it } from "vitest";
import { chooseEvictions, EVICTION_GRACE_MS, type ResidentEntry } from "./residency";

const entry = (id: string, level: number, lastNeeded: number): ResidentEntry => ({
  id,
  level,
  lastNeeded,
});

describe("chooseEvictions", () => {
  const now = 100_000;

  it("keeps everything while within budget, however old", () => {
    const entries = [entry("a", 0, 0), entry("b", 0, 0)];

    expect(chooseEvictions(entries, { 0: 2 }, now)).toEqual([]);
  });

  it("evicts the least recently needed entries over budget", () => {
    const entries = [entry("a", 0, 10_000), entry("b", 0, 5_000), entry("c", 0, 20_000)];

    expect(chooseEvictions(entries, { 0: 1 }, now).map((e) => e.id)).toEqual(["b", "a"]);
  });

  it("never evicts an entry needed within the grace period", () => {
    const entries = [entry("a", 0, now - EVICTION_GRACE_MS + 1), entry("b", 0, now)];

    expect(chooseEvictions(entries, { 0: 0 }, now)).toEqual([]);
  });

  it("evicts exactly at the grace boundary", () => {
    const entries = [entry("a", 0, now - EVICTION_GRACE_MS)];

    expect(chooseEvictions(entries, { 0: 0 }, now)).toHaveLength(1);
  });

  it("enforces each level separately and ignores unbudgeted levels", () => {
    const entries = [
      entry("a", 0, 0),
      entry("b", 0, 0),
      entry("c", 1, 0),
      entry("d", 1, 0),
      entry("e", 2, 0),
    ];

    const evicted = chooseEvictions(entries, { 0: 1, 1: 2 }, now);

    expect(evicted.map((e) => `${e.id}${e.level}`).sort()).toEqual(["a0"]);
  });
});
