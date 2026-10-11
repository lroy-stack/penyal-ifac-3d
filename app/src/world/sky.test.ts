import { describe, expect, it } from "vitest";
import { fogRangeFor, SUN_DIRECTION } from "./sky";

describe("fogRangeFor", () => {
  it("is opaque exactly at the nearest work-area edge seen from the summit", () => {
    const { near, far } = fogRangeFor({ x: 613.893, z: -754.184 });

    expect(far).toBeCloseTo(1213.893, 3);
    expect(near).toBeCloseTo(far * 0.2, 6);
  });

  it("never exceeds the distance to the nearest edge from any viewpoint", () => {
    const { far } = fogRangeFor({ x: 1136, z: -482 });

    expect(far).toBe(864);
  });
});

describe("SUN_DIRECTION", () => {
  it("is a unit vector pointing above the horizon", () => {
    expect(SUN_DIRECTION.length()).toBeCloseTo(1, 9);
    expect(SUN_DIRECTION.y).toBeGreaterThan(0.5);
  });
});
