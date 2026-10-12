import { describe, expect, it } from "vitest";
import { countLevels, isKept, type LodBands, levelFor, selectLevels } from "./lod";

const BANDS: LodBands = [30, 70, 120];

describe("vegetation LOD", () => {
  it("keeps an instance when keep < 100 * density", () => {
    expect(isKept(69, 0.7)).toBe(true);
    expect(isKept(70, 0.7)).toBe(false);
    expect(isKept(0, 0)).toBe(false);
    expect(isKept(99, 1)).toBe(true);
  });

  it("picks the level by distance, inclusive at the band edge, nothing beyond the far band", () => {
    expect(levelFor(0, BANDS)).toBe(0);
    expect(levelFor(30 * 30, BANDS)).toBe(0);
    expect(levelFor(30.01 ** 2, BANDS)).toBe(1);
    expect(levelFor(70 * 70, BANDS)).toBe(1);
    expect(levelFor(100 ** 2, BANDS)).toBe(2);
    expect(levelFor(120.01 ** 2, BANDS)).toBe(-1);
  });

  it("buckets a column set by 3D distance and density", () => {
    const columns = {
      count: 5,
      x: [0, 20, 50, 100, 500],
      y: [0, 0, 0, 0, 0],
      z: [0, 0, 0, 0, 0],
      keep: [10, 80, 10, 10, 10],
    };
    const out = new Int8Array(5);
    selectLevels(columns, { x: 0, y: 0, z: 0 }, 0.7, BANDS, out);
    expect(Array.from(out)).toEqual([0, -1, 1, 2, -1]);
    expect(countLevels(out, 5)).toEqual([1, 1, 1]);
  });

  it("counts the camera height in the distance", () => {
    const out = new Int8Array(1);
    selectLevels(
      { count: 1, x: [0], y: [0], z: [0], keep: [0] },
      { x: 0, y: 40, z: 0 },
      1,
      BANDS,
      out,
    );
    expect(out[0]).toBe(1);
  });

  it("a lower density only removes instances, never adds", () => {
    const n = 200;
    const columns = {
      count: n,
      x: Array.from({ length: n }, (_, i) => i),
      y: new Array<number>(n).fill(0),
      z: new Array<number>(n).fill(0),
      keep: Array.from({ length: n }, (_, i) => i % 100),
    };
    const high = new Int8Array(n);
    const low = new Int8Array(n);
    selectLevels(columns, { x: 0, y: 0, z: 0 }, 1, BANDS, high);
    selectLevels(columns, { x: 0, y: 0, z: 0 }, 0.35, BANDS, low);
    for (let i = 0; i < n; i++) if ((low[i] as number) >= 0) expect(high[i]).toBe(low[i]);
  });
});
