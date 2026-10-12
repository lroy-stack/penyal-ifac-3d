import { describe, expect, it } from "vitest";
import { assertConsistent, type VegetationData, vegetationSchema } from "./data";

const tier = { density: 1, distanceM: 60, treeLodM: [15, 35, 60], understoryLodM: [4, 12, 30] };

const DATA: VegetationData = {
  version: 1,
  variants: 2,
  crowns: {
    count: 1,
    x: [0],
    y: [0],
    z: [0],
    height: [5],
    scaleXZ: [1],
    keep: [0],
    variant: [1],
    yaw: [0],
    leanX: [0],
    leanZ: [0],
    apexY: [5],
  },
  understory: {
    count: 1,
    models: [{ id: "grass", meshes: { lod0: "g0", lod1: "g1", card: "gc" } }],
    x: [0],
    y: [0],
    z: [0],
    height: [1],
    scale: [1],
    yaw: [0],
    model: [0],
    keep: [0],
  },
  budget: { tiers: { low: tier, medium: tier, high: tier } },
} as VegetationData;

const withCrownVariant = (variant: number): unknown => ({
  ...DATA,
  crowns: { ...DATA.crowns, variant: [variant] },
});
const withPlantModel = (model: number): unknown => ({
  ...DATA,
  understory: { ...DATA.understory, model: [model] },
});

describe("vegetation.json", () => {
  it("accepts well-formed data", () => {
    expect(() => assertConsistent(vegetationSchema.parse(DATA))).not.toThrow();
  });

  it("rejects a negative or fractional variant or model (Uint8Array would wrap -1 to 255)", () => {
    expect(vegetationSchema.safeParse(withCrownVariant(-1)).success).toBe(false);
    expect(vegetationSchema.safeParse(withCrownVariant(0.5)).success).toBe(false);
    expect(vegetationSchema.safeParse(withPlantModel(-1)).success).toBe(false);
  });

  it("rejects a variant beyond the variant count instead of dropping the tree silently", () => {
    const data = vegetationSchema.parse(withCrownVariant(2));
    expect(() => assertConsistent(data)).toThrow(/crowns\.variant/);
  });

  it("rejects a model beyond the models list instead of dropping the plant silently", () => {
    const data = vegetationSchema.parse(withPlantModel(1));
    expect(() => assertConsistent(data)).toThrow(/understory\.model/);
  });
});
