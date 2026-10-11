import { describe, expect, it } from "vitest";
import { PolygonCorridor, parseQuantizedHeightFieldMeta, QuantizedHeightField } from "./ground";

describe("PolygonCorridor", () => {
  const square = new PolygonCorridor([
    [0, 0],
    [10, 0],
    [10, 10],
    [0, 10],
  ]);

  it("rejects polygons with fewer than 3 vertices", () => {
    expect(
      () =>
        new PolygonCorridor([
          [0, 0],
          [1, 1],
        ]),
    ).toThrow(/at least 3/);
  });

  it("contains interior points and boundary points, not exterior ones", () => {
    expect(square.contains(5, 5)).toBe(true);
    expect(square.contains(10, 5)).toBe(true);
    expect(square.contains(0, 0)).toBe(true);
    expect(square.contains(10.01, 5)).toBe(false);
    expect(square.contains(-1, -1)).toBe(false);
  });

  it("returns the target when the motion stays inside", () => {
    expect(square.clamp(2, 2, 3, 4)).toEqual({ x: 3, z: 4 });
  });

  it("stops on the edge when a motion crosses it head-on", () => {
    const result = square.clamp(9.9, 5, 10.5, 5);
    expect(result.x).toBeCloseTo(10, 9);
    expect(result.z).toBeCloseTo(5, 9);
    expect(square.contains(result.x, result.z)).toBe(true);
  });

  it("slides along the edge when the motion is oblique", () => {
    const result = square.clamp(9.9, 2, 10.3, 3);
    expect(result.x).toBeCloseTo(10, 9);
    expect(result.z).toBeCloseTo(3, 9);
  });

  it("stays inside at a concave corner", () => {
    // L shape: the notch occupies x in (5, 10), z in (0, 5).
    const ell = new PolygonCorridor([
      [0, 0],
      [5, 0],
      [5, 5],
      [10, 5],
      [10, 10],
      [0, 10],
    ]);
    expect(ell.contains(7, 2)).toBe(false);
    expect(ell.contains(7, 7)).toBe(true);

    // Walk diagonally from the upper arm into the notch next to the reflex vertex (5, 5).
    const intoNotch = ell.clamp(6, 5.5, 5.5, 4.5);
    expect(ell.contains(intoNotch.x, intoNotch.z)).toBe(true);
    expect(Math.hypot(intoNotch.x - 5.5, intoNotch.z - 4.5)).toBeCloseTo(0.5, 9);

    // Sliding down the notch wall x = 5 from the lower arm side.
    const slide = ell.clamp(4.9, 3, 5.4, 4);
    expect(slide.x).toBeCloseTo(5, 9);
    expect(slide.z).toBeCloseTo(4, 9);
    expect(ell.contains(slide.x, slide.z)).toBe(true);

    // Pushing through the reflex vertex lands on the vertex, still inside.
    const corner = ell.clamp(6, 5.2, 4.9, 2);
    expect(ell.contains(corner.x, corner.z)).toBe(true);
  });
});

describe("QuantizedHeightField", () => {
  // 3 columns x 2 rows, row 0 northmost (z0), column 0 westmost (x0).
  const meta = {
    width: 3,
    height: 2,
    cellSize: 2,
    x0: -2,
    z0: -10,
    heightOffset: 100,
    heightScale: 0.5,
  };
  const field = new QuantizedHeightField(meta, new Uint16Array([0, 2, 4, 10, 12, 14]));

  it("reads cell centres with the row-0-north, column-0-west orientation", () => {
    expect(field.heightAt(-2, -10)).toBeCloseTo(100, 9);
    expect(field.heightAt(2, -10)).toBeCloseTo(102, 9);
    expect(field.heightAt(-2, -8)).toBeCloseTo(105, 9);
    expect(field.heightAt(2, -8)).toBeCloseTo(107, 9);
  });

  it("interpolates bilinearly and is exact on a plane", () => {
    // Plane: h = 100 + 0.5 * (value) with value = 2 * col + 10 * row.
    for (const [x, z] of [
      [-1, -9.5],
      [0.3, -8.4],
      [1.9, -9.9],
    ] as const) {
      const col = (x + 2) / 2;
      const row = (z + 10) / 2;
      expect(field.heightAt(x, z)).toBeCloseTo(100 + 0.5 * (2 * col + 10 * row), 9);
    }
  });

  it("is defined on the outermost cell centres and null just outside", () => {
    expect(field.heightAt(2, -8)).not.toBeNull();
    expect(field.heightAt(2.001, -8)).toBeNull();
    expect(field.heightAt(-2.001, -8)).toBeNull();
    expect(field.heightAt(0, -10.001)).toBeNull();
    expect(field.heightAt(0, -7.999)).toBeNull();
    expect(field.heightAt(Number.NaN, 0)).toBeNull();
  });

  it("parses the asset: little-endian uint16 grid and zod-validated metadata", () => {
    const bytes = new Uint8Array([
      0x34, 0x12, 0x00, 0x00, 0xff, 0xff, 0x01, 0x00, 0x02, 0x00, 0x03, 0x00,
    ]);
    const parsed = QuantizedHeightField.fromBuffer(meta, bytes.buffer);
    expect(parsed.heightAt(-2, -10)).toBeCloseTo(100 + 0.5 * 0x1234, 9);
    expect(parsed.heightAt(2, -10)).toBeCloseTo(100 + 0.5 * 0xffff, 9);
    expect(parsed.heightAt(-2, -8)).toBeCloseTo(100.5, 9);
  });

  it("rejects a buffer that does not match the metadata", () => {
    expect(() => QuantizedHeightField.fromBuffer(meta, new ArrayBuffer(10))).toThrow(/12/);
  });

  it("rejects invalid metadata", () => {
    expect(() => parseQuantizedHeightFieldMeta({ ...meta, cellSize: 0 })).toThrow();
    expect(() => parseQuantizedHeightFieldMeta({ ...meta, width: undefined })).toThrow();
  });
});
