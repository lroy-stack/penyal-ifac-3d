import { BufferGeometry, Int16BufferAttribute, Matrix4 } from "three";
import { describe, expect, it } from "vitest";
import { bakeTransform } from "./bake";

describe("bakeTransform", () => {
  it("restores quantised positions to metres instead of clamping them to [-1, 1]", () => {
    const geometry = new BufferGeometry();
    // Normalised int16: 32767 reads back as 1.
    geometry.setAttribute(
      "position",
      new Int16BufferAttribute([0, 0, 0, 32767, 32767, 32767], 3, true),
    );
    const baked = bakeTransform(geometry, new Matrix4().makeScale(2, 3, 4));
    const position = baked.getAttribute("position");
    expect([position.getX(1), position.getY(1), position.getZ(1)]).toEqual([2, 3, 4]);
    expect(baked.getAttribute("position").array).toBeInstanceOf(Float32Array);
    expect(geometry.getAttribute("position").array).toBeInstanceOf(Int16Array);
  });
});
