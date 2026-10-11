import { describe, expect, it } from "vitest";
import { loadProgress } from "./loadProgress";

const terrain = (farLoaded: boolean, required: number, loaded: number) => ({
  farLoaded,
  required,
  loaded,
});

describe("loadProgress", () => {
  it("starts at zero and ends at one", () => {
    expect(loadProgress({ data: false, terrain: terrain(false, 0, 0), collision: false })).toBe(0);
    expect(loadProgress({ data: true, terrain: terrain(true, 5, 5), collision: true })).toBe(1);
  });

  it("only moves forward as the pieces arrive: data, far mesh, coarse tiles, collision", () => {
    const steps = [
      { data: false, terrain: terrain(false, 0, 0), collision: false },
      { data: true, terrain: terrain(false, 4, 0), collision: false },
      { data: true, terrain: terrain(true, 4, 0), collision: false },
      { data: true, terrain: terrain(true, 4, 2), collision: false },
      { data: true, terrain: terrain(true, 4, 4), collision: false },
      { data: true, terrain: terrain(true, 4, 4), collision: true },
    ].map(loadProgress);

    for (let i = 1; i < steps.length; i++) {
      expect(steps[i] as number, `step ${i}`).toBeGreaterThan(steps[i - 1] as number);
    }
  });

  it("weights terrain above walking readiness so the poster is not nearly full when the terrain appears", () => {
    const atTerrainVisible = loadProgress({
      data: true,
      terrain: terrain(true, 4, 4),
      collision: false,
    });
    expect(atTerrainVisible).toBeGreaterThan(0.5);
    expect(atTerrainVisible).toBeLessThan(0.75);
  });

  it("counts a missing terrain as not applicable", () => {
    expect(loadProgress({ data: true, terrain: null, collision: false })).toBeCloseTo(0.2, 12);
    expect(loadProgress({ data: true, terrain: null, collision: true })).toBe(1);
  });

  it("stays within 0..1 even if more tiles load than were required", () => {
    expect(loadProgress({ data: true, terrain: terrain(true, 2, 9), collision: true })).toBe(1);
  });
});
