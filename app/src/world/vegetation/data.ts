import { z } from "zod";
import type { QualityTier } from "../../core/quality";

/** Where the generated vegetation lives, relative to `public/`. */
export const VEGETATION_DIRECTORY = "assets/generated";
export const VEGETATION_PATH = `${VEGETATION_DIRECTORY}/vegetation.json`;
export const PINE_PATH = `${VEGETATION_DIRECTORY}/vegetation/pine.glb`;
export const PLANTS_PATH = `${VEGETATION_DIRECTORY}/vegetation/plants.glb`;

/** Mesh names of `pine.glb` (pipeline/blender/pine.py). */
export const pineMeshName = (variant: number, level: 0 | 1): string =>
  `pine_v${variant}_lod${level}`;
export const PINE_CARD = "pine_far_card";

const numbers = z.array(z.number());
/** An index column: `Uint8Array.from` would wrap -1 to 255 and drop the instance silently. */
const indices = z.array(z.number().int().min(0));

const tierSchema = z.object({
  density: z.number().min(0).max(1),
  distanceM: z.number().positive(),
  treeLodM: z.tuple([z.number(), z.number(), z.number()]),
  understoryLodM: z.tuple([z.number(), z.number(), z.number()]),
});

/** The parts of `vegetation.json` the app reads (the pipeline documents the rest). */
export const vegetationSchema = z.object({
  version: z.literal(1),
  variants: z.number().int().min(1),
  crowns: z.object({
    count: z.number().int(),
    x: numbers,
    y: numbers,
    z: numbers,
    height: numbers,
    scaleXZ: numbers,
    keep: numbers,
    variant: indices,
    yaw: numbers,
    leanX: numbers,
    leanZ: numbers,
    apexY: numbers,
  }),
  understory: z.object({
    count: z.number().int(),
    models: z.array(
      z.object({
        id: z.string(),
        meshes: z.object({ lod0: z.string(), lod1: z.string(), card: z.string() }),
      }),
    ),
    x: numbers,
    y: numbers,
    z: numbers,
    height: numbers,
    scale: numbers,
    yaw: numbers,
    model: indices,
    keep: numbers,
  }),
  budget: z.object({
    tiers: z.object({ low: tierSchema, medium: tierSchema, high: tierSchema }),
  }),
});

export type VegetationData = z.infer<typeof vegetationSchema>;
export type TierParams = z.infer<typeof tierSchema>;

/** Density and the three LOD distances (near, mid, far/max) the pipeline recorded for a tier. */
export function tierParams(data: VegetationData, tier: QualityTier): TierParams {
  return data.budget.tiers[tier];
}

/**
 * Rejects columns of different lengths (a mismatch would silently read `undefined`) and indices
 * beyond the variants or models (the instance would have no mesh and be dropped silently).
 */
export function assertConsistent(data: VegetationData): void {
  const check = (name: string, count: number, columns: Record<string, readonly number[]>): void => {
    for (const [column, values] of Object.entries(columns)) {
      if (values.length !== count) {
        throw new Error(
          `vegetation.json ${name}.${column} has ${values.length} values, expected ${count}.`,
        );
      }
    }
  };
  const { count: crowns, ...c } = data.crowns;
  check("crowns", crowns, c);
  const { count: understory, models: _models, ...u } = data.understory;
  check("understory", understory, u);
  const inRange = (name: string, values: readonly number[], limit: number): void => {
    const bad = values.findIndex((value) => value >= limit);
    if (bad >= 0) {
      throw new Error(
        `vegetation.json ${name}[${bad}] is ${values[bad]}, but there are only ${limit} to pick from.`,
      );
    }
  };
  inRange("crowns.variant", data.crowns.variant, data.variants);
  inRange("understory.model", data.understory.model, data.understory.models.length);
}
