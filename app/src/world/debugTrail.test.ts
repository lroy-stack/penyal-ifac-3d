import { describe, expect, it } from "vitest";
import { corridorLinePositions, LINE_LIFT, routeLinePositions } from "./debugTrail";
import { parseTrail } from "./trail";

const trail = parseTrail({
  licence: "ODbL-1.0",
  attribution: "x",
  route: {
    segments: [
      {
        id: "a",
        points: [
          [1, 10, 2],
          [3, 11, 4],
        ],
      },
      {
        id: "b",
        points: [
          [3, 11, 4],
          [5, 12, 6],
        ],
      },
    ],
  },
  corridor: {
    polygon: [
      [0, 0],
      [10, 0],
      [10, 10],
    ],
  },
  anchors: {},
});

describe("routeLinePositions", () => {
  it("lifts each segment above its draped heights", () => {
    const [first, second] = routeLinePositions(trail);

    expect([...(first ?? [])]).toEqual(
      [1, 10 + LINE_LIFT, 2, 3, 11 + LINE_LIFT, 4].map((v) => Math.fround(v)),
    );
    expect(second).toHaveLength(6);
  });
});

describe("corridorLinePositions", () => {
  it("drapes the outline on the height field and tolerates gaps", () => {
    const field = { heightAt: (x: number) => (x > 5 ? 100 : null) };

    const positions = corridorLinePositions(trail, field);

    expect([positions[1], positions[4], positions[7]]).toEqual([
      Math.fround(LINE_LIFT),
      Math.fround(100 + LINE_LIFT),
      Math.fround(100 + LINE_LIFT),
    ]);
  });
});
