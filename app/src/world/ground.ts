import { z } from "zod";

/** Terrain height in the local frame (ADR 0004). */
export interface HeightField {
  /** Height (m) at world (x, z), or null outside the covered area. */
  heightAt(x: number, z: number): number | null;
}

/**
 * Extra walkable surfaces that the terrain height field cannot express: the tunnel floor, stone
 * steps, platforms. The terrain may lie far above them (rock over the tunnel).
 */
export interface GroundSurface {
  /**
   * Highest walkable surface height h at (x, z) with `y - maxDrop <= h <= y`, or null.
   * The caller passes `y = feetY + stepHeight`, so surfaces up to one step above the feet count.
   */
  surfaceBelow(x: number, y: number, z: number, maxDrop: number): number | null;
}

/**
 * A closed volume (the tunnel interior) that the third-person camera must not leave while the
 * player is inside it: past the walls it would see the back of the rock.
 */
export interface Enclosure {
  /** Whether (x, y, z) lies inside the volume, at least `margin` metres from its boundary. */
  contains(x: number, y: number, z: number, margin: number): boolean;
}

/** The area the player may walk in (ADR 0006). */
export interface Corridor {
  contains(x: number, z: number): boolean;
  /**
   * Resolves a motion from (fromX, fromZ) to (toX, toZ). Returns the target when it is inside;
   * otherwise the point on the boundary closest to the target, so the player slides along the
   * boundary instead of stopping dead.
   */
  clamp(fromX: number, fromZ: number, toX: number, toZ: number): { x: number; z: number };
}

export type Point2 = readonly [number, number];

/** Points closer than this to the boundary count as inside (clamp results sit on the boundary). */
const BOUNDARY_TOLERANCE = 1e-6;

function closestPointOnSegment(
  px: number,
  pz: number,
  ax: number,
  az: number,
  bx: number,
  bz: number,
): { x: number; z: number; distSq: number } {
  const abx = bx - ax;
  const abz = bz - az;
  const lengthSq = abx * abx + abz * abz;
  const t =
    lengthSq === 0 ? 0 : Math.max(0, Math.min(1, ((px - ax) * abx + (pz - az) * abz) / lengthSq));
  const x = ax + abx * t;
  const z = az + abz * t;
  return { x, z, distSq: (px - x) ** 2 + (pz - z) ** 2 };
}

export class PolygonCorridor implements Corridor {
  private readonly vertices: readonly Point2[];
  private readonly minX: number;
  private readonly maxX: number;
  private readonly minZ: number;
  private readonly maxZ: number;

  constructor(polygon: readonly Point2[]) {
    if (polygon.length < 3) {
      throw new Error(`A corridor polygon needs at least 3 vertices, got ${polygon.length}.`);
    }
    this.vertices = polygon;
    this.minX = Math.min(...polygon.map((p) => p[0]));
    this.maxX = Math.max(...polygon.map((p) => p[0]));
    this.minZ = Math.min(...polygon.map((p) => p[1]));
    this.maxZ = Math.max(...polygon.map((p) => p[1]));
  }

  contains(x: number, z: number): boolean {
    if (
      x < this.minX - BOUNDARY_TOLERANCE ||
      x > this.maxX + BOUNDARY_TOLERANCE ||
      z < this.minZ - BOUNDARY_TOLERANCE ||
      z > this.maxZ + BOUNDARY_TOLERANCE
    ) {
      return false;
    }
    if (this.closestBoundaryPoint(x, z).distSq <= BOUNDARY_TOLERANCE ** 2) return true;
    let inside = false;
    const v = this.vertices;
    for (let i = 0, j = v.length - 1; i < v.length; j = i++) {
      const [xi, zi] = v[i] as Point2;
      const [xj, zj] = v[j] as Point2;
      if (zi > z !== zj > z && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) inside = !inside;
    }
    return inside;
  }

  clamp(_fromX: number, _fromZ: number, toX: number, toZ: number): { x: number; z: number } {
    if (this.contains(toX, toZ)) return { x: toX, z: toZ };
    const { x, z } = this.closestBoundaryPoint(toX, toZ);
    return { x, z };
  }

  private closestBoundaryPoint(px: number, pz: number): { x: number; z: number; distSq: number } {
    const v = this.vertices;
    let best = { x: px, z: pz, distSq: Number.POSITIVE_INFINITY };
    for (let i = 0, j = v.length - 1; i < v.length; j = i++) {
      const [ax, az] = v[j] as Point2;
      const [bx, bz] = v[i] as Point2;
      const candidate = closestPointOnSegment(px, pz, ax, az, bx, bz);
      if (candidate.distSq < best.distSq) best = candidate;
    }
    return best;
  }
}

/**
 * Metadata of the pipeline's collision asset. Row 0 is the northmost row (most negative z),
 * column 0 the westmost (most negative x); (x0, z0) is the centre of cell [0, 0].
 * height(m) = heightOffset + heightScale * uint16.
 */
export const quantizedHeightFieldMetaSchema = z.object({
  width: z.number().int().min(2),
  height: z.number().int().min(2),
  cellSize: z.number().positive(),
  x0: z.number(),
  z0: z.number(),
  heightOffset: z.number(),
  heightScale: z.number().positive(),
});

export type QuantizedHeightFieldMeta = z.infer<typeof quantizedHeightFieldMetaSchema>;

export function parseQuantizedHeightFieldMeta(json: unknown): QuantizedHeightFieldMeta {
  return quantizedHeightFieldMetaSchema.parse(json);
}

export class QuantizedHeightField implements HeightField {
  constructor(
    private readonly meta: QuantizedHeightFieldMeta,
    private readonly samples: Uint16Array,
  ) {
    const expected = meta.width * meta.height;
    if (samples.length !== expected) {
      throw new Error(
        `Collision grid has ${samples.length} samples but its metadata (${meta.width} x ${meta.height}) needs ${expected}.`,
      );
    }
  }

  /** Builds the field from the raw asset bytes (uint16 little-endian, row-major). */
  static fromBuffer(metaJson: unknown, buffer: ArrayBuffer): QuantizedHeightField {
    const meta = parseQuantizedHeightFieldMeta(metaJson);
    if (buffer.byteLength !== meta.width * meta.height * 2) {
      throw new Error(
        `Collision grid is ${buffer.byteLength} bytes but its metadata (${meta.width} x ${meta.height}) needs ${meta.width * meta.height * 2}.`,
      );
    }
    const view = new DataView(buffer);
    const samples = new Uint16Array(meta.width * meta.height);
    for (let i = 0; i < samples.length; i++) samples[i] = view.getUint16(i * 2, true);
    return new QuantizedHeightField(meta, samples);
  }

  heightAt(x: number, z: number): number | null {
    const { width, height, cellSize, x0, z0, heightOffset, heightScale } = this.meta;
    const col = (x - x0) / cellSize;
    const row = (z - z0) / cellSize;
    if (!(col >= 0 && col <= width - 1 && row >= 0 && row <= height - 1)) return null;

    const c0 = Math.min(Math.floor(col), width - 2);
    const r0 = Math.min(Math.floor(row), height - 2);
    const fc = col - c0;
    const fr = row - r0;
    const at = (r: number, c: number): number => this.samples[r * width + c] as number;

    const north = at(r0, c0) * (1 - fc) + at(r0, c0 + 1) * fc;
    const south = at(r0 + 1, c0) * (1 - fc) + at(r0 + 1, c0 + 1) * fc;
    return heightOffset + heightScale * (north * (1 - fr) + south * fr);
  }
}
