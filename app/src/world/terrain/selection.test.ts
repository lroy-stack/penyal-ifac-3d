import { describe, expect, it } from "vitest";
import { makeTile } from "./fixtures";
import {
  chooseDisplayed,
  coarsestLevel,
  constrainLodSteps,
  distanceToBounds,
  FAR_ID,
  isBehindCamera,
  loadRequests,
  planTiles,
  REQUIRED_RADIUS,
  requiredTiles,
  screenSpaceError,
  selectLod,
  tileNeighbours,
  type View,
} from "./selection";

/** Screen-space error budgets of the quality profile: touch devices tolerate twice as much. */
const FINE_SSE = 2;
const COARSE_SSE = 4;
const FOV = (60 * Math.PI) / 180;
const VIEW = { fovY: FOV, viewportHeight: 1080 };
const camera = (x: number, y: number, z: number, forward = { x: 0, y: 0, z: -1 }): View => ({
  position: { x, y, z },
  forward,
  ...VIEW,
});

/** Distance at which a geometric error shows as exactly `px` pixels. */
const distanceForSse = (maxError: number, px: number): number =>
  (maxError * VIEW.viewportHeight) / (2 * Math.tan(FOV / 2) * px);

describe("screenSpaceError", () => {
  it("follows maxError * height / (2 tan(fov/2) * distance)", () => {
    const expected = (1 * 1080) / (2 * Math.tan(Math.PI / 6) * 100);
    expect(screenSpaceError(1, 100, VIEW)).toBeCloseTo(expected, 9);
  });

  it("is infinite at distance zero and halves when the distance doubles", () => {
    expect(screenSpaceError(1, 0, VIEW)).toBe(Number.POSITIVE_INFINITY);
    expect(screenSpaceError(1, 200, VIEW)).toBeCloseTo(screenSpaceError(1, 100, VIEW) / 2, 9);
  });
});

describe("distanceToBounds", () => {
  const { bounds } = makeTile(0, 0);

  it("is zero inside the box", () => {
    expect(distanceToBounds({ x: 10, y: 50, z: 10 }, bounds)).toBe(0);
  });

  it("measures to the nearest face, not the centre", () => {
    expect(distanceToBounds({ x: -30, y: 50, z: 100 }, bounds)).toBe(30);
  });

  it("measures to the nearest corner diagonally in 3D", () => {
    expect(distanceToBounds({ x: 256 + 3, y: 100 + 4, z: 256 }, bounds)).toBe(5);
  });
});

describe("isBehindCamera", () => {
  const { bounds } = makeTile(0, 0);

  it("is true when every corner is behind the camera plane", () => {
    expect(isBehindCamera(bounds, camera(0, 50, 1000))).toBe(false);
    expect(isBehindCamera(bounds, camera(0, 50, -300, { x: 0, y: 0, z: 1 }))).toBe(false);
    expect(isBehindCamera(bounds, camera(0, 50, 1000, { x: 0, y: 0, z: 1 }))).toBe(true);
  });
});

describe("selectLod", () => {
  const tile = makeTile(0, 0);
  const threshold = 2;

  it("picks the finest LOD when no level meets the threshold (very close)", () => {
    expect(selectLod(tile, 5, VIEW, threshold)).toBe(0);
    expect(selectLod(tile, 0, VIEW, threshold)).toBe(0);
  });

  it("picks the coarsest LOD that meets the threshold", () => {
    expect(selectLod(tile, distanceForSse(3, 2) * 1.01, VIEW, threshold)).toBe(2);
    expect(selectLod(tile, distanceForSse(3, 2) * 0.99, VIEW, threshold)).toBe(1);
    expect(selectLod(tile, distanceForSse(1, 2) * 0.99, VIEW, threshold)).toBe(0);
    expect(selectLod(tile, distanceForSse(1, 2) * 1.01, VIEW, threshold)).toBe(1);
  });

  it("tolerates twice the error on coarse pointers", () => {
    const d = distanceForSse(1, 4) * 1.01;
    expect(selectLod(tile, d, VIEW, COARSE_SSE)).toBe(1);
    expect(selectLod(tile, d, VIEW, FINE_SSE)).toBe(0);
  });

  it("refines immediately but coarsens only past the hysteresis band", () => {
    const boundary = distanceForSse(1, threshold);
    // Level 0 on screen: just beyond the boundary LOD1 would be acceptable, but not yet.
    expect(selectLod(tile, boundary * 1.1, VIEW, threshold, 0)).toBe(0);
    // Clearly beyond the band (error < threshold / 1.5): coarsen.
    expect(selectLod(tile, boundary * 1.6, VIEW, threshold, 0)).toBe(1);
    // Level 1 on screen and closer than the boundary: refine at once.
    expect(selectLod(tile, boundary * 0.9, VIEW, threshold, 1)).toBe(0);
  });

  it("does not flap when the camera hovers around a boundary", () => {
    const boundary = distanceForSse(1, threshold);
    let level: number | undefined;
    const seen = new Set<number>();
    for (const factor of [0.97, 1.03, 0.98, 1.05, 0.99, 1.1, 0.96]) {
      level = selectLod(tile, boundary * factor, VIEW, threshold, level);
      seen.add(level);
    }
    expect(seen).toEqual(new Set([0]));
  });

  it("can skip levels when moving far in one frame", () => {
    expect(selectLod(tile, distanceForSse(3, 2) * 2, VIEW, threshold, 0)).toBe(2);
  });

  it("ignores a previous level the tile does not have", () => {
    expect(selectLod(tile, 5, VIEW, threshold, 7)).toBe(0);
  });
});

describe("planTiles", () => {
  const near = makeTile(0, 0);
  const behind = makeTile(0, 5);

  it("keeps tiles that are behind the camera and far at the coarsest LOD", () => {
    const view = camera(128, 50, 128, { x: 0, y: 0, z: -1 });
    const plans = planTiles([near, behind], view, 2, new Map());
    const byId = new Map(plans.map((p) => [p.id, p]));

    expect(byId.get(near.id)?.wanted).toBe(0);
    expect(byId.get(behind.id)?.wanted).toBe(coarsestLevel(behind));
  });

  it("applies the previous level for hysteresis", () => {
    const boundary = distanceForSse(1, 2);
    const view = camera(-boundary * 1.1, 50, 128);
    const tile = makeTile(0, 0);
    const sticky = planTiles([tile], view, 2, new Map([[tile.id, 0]]));
    const fresh = planTiles([tile], view, 2, new Map());

    expect(sticky[0]?.wanted).toBe(0);
    expect(fresh[0]?.wanted).toBe(1);
  });
});

describe("requiredTiles", () => {
  const tiles = [makeTile(0, 0), makeTile(1, 0), makeTile(4, 0), makeTile(0, 3)];

  it("is the tiles within one tile size of the camera, whichever way it looks", () => {
    expect(REQUIRED_RADIUS).toBe(256);
    const ids = requiredTiles(tiles, camera(128, 50, 128)).sort();
    expect(ids).toEqual(["t_0_0", "t_1_0"]);
    const facingAway = requiredTiles(tiles, camera(128, 50, 128, { x: 0, y: 0, z: 1 })).sort();
    expect(facingAway).toEqual(ids);
  });

  it("follows the camera and honours a custom radius", () => {
    expect(requiredTiles(tiles, camera(1100, 50, 128)).sort()).toEqual(["t_4_0"]);
    expect(requiredTiles(tiles, camera(128, 50, 128), 10_000)).toHaveLength(4);
    expect(requiredTiles(tiles, camera(5000, 50, 5000))).toEqual([]);
  });
});

describe("loadRequests", () => {
  const a = makeTile(0, 0);
  const b = makeTile(1, 0);
  const c = makeTile(2, 0);
  const plans = [
    { id: a.id, wanted: 0, distance: 10 },
    { id: b.id, wanted: 1, distance: 300 },
    { id: c.id, wanted: 2, distance: 100 },
  ];

  it("orders far first, then coarsest of every tile, then finer wanted LODs by distance", () => {
    const requests = loadRequests([a, b, c], plans, () => false);

    expect(requests.map((r) => `${r.id}:${r.level}`)).toEqual([
      `${FAR_ID}:0`,
      `${a.id}:2`,
      `${c.id}:2`,
      `${b.id}:2`,
      `${a.id}:0`,
      `${b.id}:1`,
    ]);
  });

  it("skips what is already resident", () => {
    const requests = loadRequests([a, b, c], plans, (id, level) => id === FAR_ID || level === 2);

    expect(requests.map((r) => `${r.id}:${r.level}`)).toEqual([`${a.id}:0`, `${b.id}:1`]);
  });

  it("is empty when everything wanted is resident", () => {
    expect(loadRequests([a, b, c], plans, () => true)).toEqual([]);
  });
});

describe("chooseDisplayed", () => {
  it("shows the wanted level once it is loaded", () => {
    expect(chooseDisplayed(0, 2, new Set([0, 2]))).toBe(0);
  });

  it("keeps the displayed level while the wanted one is still loading", () => {
    expect(chooseDisplayed(0, 2, new Set([1, 2]))).toBe(2);
  });

  it("falls back to the closest loaded level when the displayed one is gone", () => {
    expect(chooseDisplayed(0, 1, new Set([2, 1]))).toBe(1);
    expect(chooseDisplayed(0, 0, new Set([2]))).toBe(2);
  });

  it("shows nothing when nothing is loaded", () => {
    expect(chooseDisplayed(0, undefined, new Set())).toBeUndefined();
  });
});

describe("tileNeighbours", () => {
  it("links tiles that share an edge and ignores corner contact", () => {
    const tiles = [makeTile(0, 0), makeTile(1, 0), makeTile(1, 1), makeTile(3, 0)];
    const n = tileNeighbours(tiles);
    expect([...(n.get("t_0_0") ?? [])]).toEqual(["t_1_0"]);
    expect([...(n.get("t_1_0") ?? [])].sort()).toEqual(["t_0_0", "t_1_1"]);
    expect(n.get("t_3_0")).toEqual([]);
  });
});

describe("constrainLodSteps", () => {
  const grid = [makeTile(0, 0), makeTile(1, 0), makeTile(2, 0), makeTile(3, 0)];
  const plan = (levels: readonly number[]) =>
    grid.map((t, i) => ({ id: t.id, wanted: levels[i] as number, distance: 0 }));
  const levelsOf = (plans: readonly { wanted: number }[]) => plans.map((p) => p.wanted);

  it("leaves plans that already differ by one level alone", () => {
    expect(levelsOf(constrainLodSteps(grid, plan([0, 1, 2, 2]), 1))).toEqual([0, 1, 2, 2]);
  });

  it("refines a coarse tile that touches a tile two levels finer", () => {
    expect(levelsOf(constrainLodSteps(grid, plan([0, 2, 2, 2]), 1))).toEqual([0, 1, 2, 2]);
  });

  it("propagates along a chain until every seam is within one level", () => {
    const result = levelsOf(constrainLodSteps(grid, plan([0, 2, 2, 2]), 1));
    for (let i = 1; i < result.length; i++) {
      expect(Math.abs((result[i] as number) - (result[i - 1] as number))).toBeLessThanOrEqual(1);
    }
  });

  it("never coarsens a tile and never changes the input", () => {
    const input = plan([2, 0, 2, 1]);
    const result = constrainLodSteps(grid, input, 1);
    for (const [i, p] of result.entries()) {
      expect(p.wanted).toBeLessThanOrEqual((input[i] as { wanted: number }).wanted);
    }
    expect(levelsOf(input)).toEqual([2, 0, 2, 1]);
  });

  it("supports a step of zero and an unlimited step", () => {
    expect(levelsOf(constrainLodSteps(grid, plan([0, 2, 2, 2]), 0))).toEqual([0, 0, 0, 0]);
    expect(levelsOf(constrainLodSteps(grid, plan([0, 2, 2, 2]), Number.POSITIVE_INFINITY))).toEqual(
      [0, 2, 2, 2],
    );
  });

  it("satisfies the constraint on a random 2D grid", () => {
    const tiles = [];
    for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) tiles.push(makeTile(i, j));
    let seed = 12345;
    const next = () => {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      return seed / 2147483648;
    };
    const plans = tiles.map((t) => ({ id: t.id, wanted: Math.floor(next() * 3), distance: 0 }));
    const result = new Map(constrainLodSteps(tiles, plans, 1).map((p) => [p.id, p.wanted]));
    const neighbours = tileNeighbours(tiles);
    for (const [id, others] of neighbours) {
      for (const other of others) {
        expect(
          Math.abs((result.get(id) as number) - (result.get(other) as number)),
        ).toBeLessThanOrEqual(1);
      }
    }
  });
});
