import { describe, expect, it } from "vitest";
import { STEP_HEIGHT } from "../../player/controller";
import { parseStructures, type Tread, TreadsGroundSurface } from "./structures";

/** Three treads going north (-z), 0.6 m deep, 1.5 m wide, 0.166 m rise, the first top at 10.166. */
function flight(): Tread[] {
  return [0, 1, 2].map((i) => ({
    top: 10 + 0.166 * (i + 1),
    quad: [
      [-0.75, -0.6 * i],
      [0.75, -0.6 * i],
      [0.75, -0.6 * (i + 1)],
      [-0.75, -0.6 * (i + 1)],
    ],
  }));
}

const UNIT_SQUARE: Tread["quad"] = [
  [0, 0],
  [1, 0],
  [1, 1],
  [0, 1],
];

describe("TreadsGroundSurface", () => {
  const surface = new TreadsGroundSurface(flight());

  it("returns the tread top under the point", () => {
    expect(surface.surfaceBelow(0, 10.5, -0.3, STEP_HEIGHT)).toBeCloseTo(10.166, 6);
    expect(surface.surfaceBelow(0, 10.7, -1.5, STEP_HEIGHT)).toBeCloseTo(10.498, 6);
  });

  it("is null off the flight and beside it", () => {
    expect(surface.surfaceBelow(0, 11, 1, STEP_HEIGHT)).toBeNull();
    expect(surface.surfaceBelow(0, 11, -2, STEP_HEIGHT)).toBeNull();
    expect(surface.surfaceBelow(1, 11, -0.3, STEP_HEIGHT)).toBeNull();
  });

  it("ignores a tread higher than the reach and one deeper than the drop", () => {
    expect(surface.surfaceBelow(0, 10.2, -1.5, STEP_HEIGHT)).toBeNull();
    expect(surface.surfaceBelow(0, 12, -0.3, 0.4)).toBeNull();
  });

  it("leaves no seam between two treads", () => {
    expect(surface.surfaceBelow(0, 10.5, -0.6, STEP_HEIGHT)).not.toBeNull();
  });

  it("climbs one tread at a time within the player's step limit", () => {
    const feet = 10.166;
    expect(surface.surfaceBelow(0, feet + STEP_HEIGHT, -0.9, STEP_HEIGHT)).toBeCloseTo(10.332, 6);
    expect(surface.surfaceBelow(0, feet + STEP_HEIGHT, -0.3, STEP_HEIGHT)).toBeCloseTo(10.166, 6);
  });

  it("takes the highest tread when several cover the point", () => {
    const stacked = new TreadsGroundSurface([
      { top: 5, quad: UNIT_SQUARE },
      { top: 5.2, quad: UNIT_SQUARE },
    ]);
    expect(stacked.surfaceBelow(0.5, 5.5, 0.5, 0.4)).toBe(5.2);
  });

  it("accepts either winding of the quad", () => {
    const reversed = new TreadsGroundSurface([
      {
        top: 1,
        quad: [
          [0, 0],
          [0, 1],
          [1, 1],
          [1, 0],
        ],
      },
    ]);
    expect(reversed.surfaceBelow(0.5, 1.2, 0.5, 0.4)).toBe(1);
  });
});

describe("parseStructures", () => {
  it("rejects a staircase with no treads", () => {
    expect(() =>
      parseStructures({
        version: 1,
        licence: "ODbL",
        attribution: "OSM",
        glb: "structures.glb",
        constants: { status: "provisional" },
        staircases: [
          { id: "a", name: "A", stepCount: 3, collision: { kind: "treads", treads: [] } },
        ],
      }),
    ).toThrow();
  });
});
