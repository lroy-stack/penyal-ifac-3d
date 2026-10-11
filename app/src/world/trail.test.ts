import { describe, expect, it } from "vitest";
import { PolygonCorridor } from "./ground";
import {
  headingAlongRoute,
  markReachedAnchors,
  parseTrail,
  type RoutePoint,
  routePoints,
  startAnchor,
} from "./trail";

const minimal = {
  licence: "ODbL-1.0",
  attribution: "(c) OpenStreetMap contributors",
  route: {
    segments: [
      {
        id: "a",
        points: [
          [0, 0, 0],
          [0, 1, -10],
        ],
      },
      {
        id: "b",
        points: [
          [0, 1, -10],
          [10, 2, -10],
        ],
      },
    ],
  },
  corridor: {
    polygon: [
      [-1, 1],
      [11, 1],
      [11, -11],
    ],
  },
  anchors: { centre: { x: 0, y: 0, z: 0 }, turnstile: { x: 0, y: 1, z: -10, osm: "node/1" } },
};

describe("parseTrail", () => {
  it("accepts the pipeline shape and ignores unknown keys", () => {
    const trail = parseTrail({ ...minimal, source: { id: "osm" } });

    expect(trail.route.segments).toHaveLength(2);
    expect(trail.anchors.turnstile?.osm).toBe("node/1");
  });

  it("rejects a corridor with fewer than three vertices", () => {
    expect(() =>
      parseTrail({
        ...minimal,
        corridor: {
          polygon: [
            [0, 0],
            [1, 1],
          ],
        },
      }),
    ).toThrow();
  });

  it("rejects a route point that is not 3D", () => {
    const bad = {
      ...minimal,
      route: {
        segments: [
          {
            id: "a",
            points: [
              [0, 0],
              [1, 1],
            ],
          },
        ],
      },
    };

    expect(() => parseTrail(bad)).toThrow();
  });
});

describe("routePoints", () => {
  it("drops the joint repeated between consecutive segments", () => {
    expect(routePoints(parseTrail(minimal))).toEqual([
      [0, 0, 0],
      [0, 1, -10],
      [10, 2, -10],
    ]);
  });
});

describe("startAnchor", () => {
  it("prefers the turnstile", () => {
    expect(startAnchor(parseTrail(minimal)).name).toBe("turnstile");
  });

  it("falls back to the centre", () => {
    const { turnstile: _unused, ...anchors } = minimal.anchors;

    expect(startAnchor(parseTrail({ ...minimal, anchors })).name).toBe("centre");
  });

  it("fails clearly when neither exists", () => {
    expect(() => startAnchor(parseTrail({ ...minimal, anchors: {} }))).toThrow(/turnstile/);
  });

  describe("with a requested anchor (?start=)", () => {
    const anchors = {
      ...minimal.anchors,
      summit: { x: 8, y: 3, z: -5 },
      pobla: { x: -5, y: 0, z: 5 },
    };
    const trail = parseTrail({ ...minimal, anchors });
    const corridor = new PolygonCorridor(trail.corridor.polygon);

    it("starts there when it lies inside the walkable corridor", () => {
      expect(startAnchor(trail, "summit", corridor).name).toBe("summit");
    });

    it("ignores an anchor outside the corridor, such as the Pobla seen from a viewpoint", () => {
      expect(startAnchor(trail, "pobla", corridor).name).toBe("turnstile");
    });

    it("ignores an unknown anchor name", () => {
      expect(startAnchor(trail, "nowhere", corridor).name).toBe("turnstile");
    });
  });
});

describe("headingAlongRoute", () => {
  const north: RoutePoint[] = [
    [0, 0, 0],
    [0, 0, -5],
    [0, 0, -10],
    [0, 0, -20],
  ];

  it("faces -Z (yaw 0) on a route heading north", () => {
    expect(headingAlongRoute(north, { x: 0, z: 0 })).toBeCloseTo(0, 9);
  });

  it("turns left (positive yaw) on a route heading west", () => {
    const west: RoutePoint[] = [
      [0, 0, 0],
      [-20, 0, 0],
    ];

    expect(headingAlongRoute(west, { x: 0, z: 0 })).toBeCloseTo(Math.PI / 2, 9);
  });

  it("turns right (negative yaw) on a route heading east", () => {
    const east: RoutePoint[] = [
      [0, 0, 0],
      [20, 0, 0],
    ];

    expect(headingAlongRoute(east, { x: 0, z: 0 })).toBeCloseTo(-Math.PI / 2, 9);
  });

  it("looks ahead from the vertex nearest to the start, not from the route start", () => {
    const bend: RoutePoint[] = [
      [0, 0, 0],
      [0, 0, -20],
      [20, 0, -20],
    ];

    expect(headingAlongRoute(bend, { x: 0, z: -20 }, 5)).toBeCloseTo(-Math.PI / 2, 9);
  });

  it("uses the arrival direction at the end of the route", () => {
    expect(headingAlongRoute(north, { x: 0, z: -20 })).toBeCloseTo(0, 9);
  });
});

describe("markReachedAnchors", () => {
  const anchors = { a: { x: 0, y: 0, z: 0 }, b: { x: 100, y: 0, z: 0 } };

  it("marks anchors within the radius once", () => {
    const reached = new Set<string>();

    expect(markReachedAnchors({ x: 3, z: 4 }, anchors, 5, reached)).toEqual(["a"]);
    expect(markReachedAnchors({ x: 3, z: 4 }, anchors, 5, reached)).toEqual([]);
    expect(markReachedAnchors({ x: 98, z: 0 }, anchors, 5, reached)).toEqual(["b"]);
    expect([...reached]).toEqual(["a", "b"]);
  });

  it("ignores anchors outside the radius", () => {
    expect(markReachedAnchors({ x: 6, z: 0 }, anchors, 5, new Set())).toEqual([]);
  });
});
