import { z } from "zod";
import { fetchChecked, NotFoundError } from "../../core/http";
import type { GroundSurface } from "../ground";

const point2 = z.tuple([z.number(), z.number()]);

const tread = z.object({
  /** Height (m) of the walkable top of the tread. */
  top: z.number(),
  /** The four corners (x, z) of the horizontal quad. */
  quad: z.tuple([point2, point2, point2, point2]),
});

const staircase = z.object({
  id: z.string(),
  name: z.string(),
  stepCount: z.number().int().positive(),
  collision: z.object({ kind: z.literal("treads"), treads: z.array(tread).min(1) }),
});

/** `structures.json` from the pipeline (OSM-derived, ODbL: ADR 0007). Extra keys are ignored. */
export const structuresSchema = z.object({
  version: z.literal(1),
  licence: z.string(),
  attribution: z.string(),
  /** File name of the visual mesh, relative to `structures.json`. */
  glb: z.string().min(1),
  constants: z.object({ status: z.string() }).passthrough(),
  staircases: z.array(staircase).min(1),
});

export type Structures = z.infer<typeof structuresSchema>;
export type Tread = z.infer<typeof tread>;

export const STRUCTURES_PATH = "assets/generated/structures.json";
export const STRUCTURES_DIRECTORY = "assets/generated/";

export function parseStructures(json: unknown): Structures {
  return structuresSchema.parse(json);
}

export type StructuresResult =
  | { readonly status: "ready"; readonly structures: Structures }
  | { readonly status: "missing" }
  | { readonly status: "error"; readonly message: string };

/** Loads `structures.json`. Optional: a missing or invalid file is a status, not a crash. */
export async function loadStructures(url: string, signal?: AbortSignal): Promise<StructuresResult> {
  try {
    const opened = await fetchChecked(url, signal);
    const parsed = structuresSchema.safeParse(await opened.read((r) => r.json()));
    if (!parsed.success) {
      return { status: "error", message: `${url} is not valid: ${parsed.error.message}` };
    }
    return { status: "ready", structures: parsed.data };
  } catch (error) {
    if (error instanceof NotFoundError) return { status: "missing" };
    if (signal?.aborted) throw error;
    return { status: "error", message: error instanceof Error ? error.message : String(error) };
  }
}

/** Points this close (m) outside a tread still count as on it, so adjacent treads leave no seam. */
export const TREAD_EDGE_TOLERANCE = 1e-4;

type Prepared = {
  readonly top: number;
  readonly quad: Tread["quad"];
  readonly minX: number;
  readonly maxX: number;
  readonly minZ: number;
  readonly maxZ: number;
};

function prepare(treadOf: Tread): Prepared {
  const xs = treadOf.quad.map((p) => p[0]);
  const zs = treadOf.quad.map((p) => p[1]);
  return {
    top: treadOf.top,
    quad: treadOf.quad,
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minZ: Math.min(...zs),
    maxZ: Math.max(...zs),
  };
}

/** Whether (x, z) lies in the convex quad, whatever its winding, within the tolerance. */
function inQuad(quad: Tread["quad"], x: number, z: number): boolean {
  let sign = 0;
  for (let i = 0; i < 4; i++) {
    const [ax, az] = quad[i] as readonly [number, number];
    const [bx, bz] = quad[(i + 1) % 4] as readonly [number, number];
    const length = Math.hypot(bx - ax, bz - az);
    if (length === 0) continue;
    const side = ((bx - ax) * (z - az) - (bz - az) * (x - ax)) / length;
    if (Math.abs(side) <= TREAD_EDGE_TOLERANCE) continue;
    const s = Math.sign(side);
    if (sign === 0) sign = s;
    else if (s !== sign) return false;
  }
  return true;
}

/**
 * The treads of every staircase as walkable ground: one horizontal quad per step. At a point the
 * highest tread within reach (`top <= y`, `top >= y - maxDrop`) wins, so the player climbs one
 * tread at a time (the controller's step limit is its `y` margin) and drops down them.
 */
export class TreadsGroundSurface implements GroundSurface {
  private readonly treads: readonly Prepared[];

  constructor(treads: readonly Tread[]) {
    this.treads = treads.map(prepare);
  }

  surfaceBelow(x: number, y: number, z: number, maxDrop: number): number | null {
    let best: number | null = null;
    for (const t of this.treads) {
      if (x < t.minX || x > t.maxX || z < t.minZ || z > t.maxZ) continue;
      if (t.top > y || t.top < y - maxDrop) continue;
      if (best !== null && t.top <= best) continue;
      if (inQuad(t.quad, x, z)) best = t.top;
    }
    return best;
  }
}
