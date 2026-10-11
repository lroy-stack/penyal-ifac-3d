import { z } from "zod";
import { fetchChecked, NotFoundError } from "../core/http";
import type { Enclosure, GroundSurface } from "./ground";

const point3 = z.tuple([z.number(), z.number(), z.number()]);
const portal = z.object({ x: z.number(), y: z.number(), z: z.number() });

/** `tunnel.json` from the pipeline (OSM-derived, ODbL: ADR 0007). Extra keys are ignored. */
export const tunnelSchema = z.object({
  version: z.literal(1),
  licence: z.string(),
  attribution: z.string(),
  /** "approximate" until the cross-section is measured on site. */
  status: z.string(),
  /** Floor centreline west to east; y is the floor height. */
  axis: z.array(point3).min(2),
  width: z.number().positive(),
  height: z.number().positive(),
  sectionBasis: z.string(),
  portals: z.object({ west: portal, east: portal }),
  sources: z.object({ axis: z.string(), portalHeights: z.string() }),
  /** File name of the visual interior shell, relative to `tunnel.json`. */
  mesh: z.string().min(1),
});

export type Tunnel = z.infer<typeof tunnelSchema>;

export const TUNNEL_PATH = "assets/generated/tunnel.json";
export const TUNNEL_DIRECTORY = "assets/generated/";

/** The floor reaches this far (m) beyond each portal so the player steps on and off it cleanly. */
export const PORTAL_OVERRUN = 1;

export function parseTunnel(json: unknown): Tunnel {
  return tunnelSchema.parse(json);
}

export type TunnelResult =
  | { readonly status: "ready"; readonly tunnel: Tunnel }
  | { readonly status: "missing" }
  | { readonly status: "error"; readonly message: string };

/** Loads `tunnel.json`. The tunnel is optional: a missing or invalid file is a status, not a crash. */
export async function loadTunnel(url: string, signal?: AbortSignal): Promise<TunnelResult> {
  try {
    const response = await fetchChecked(url, signal);
    const parsed = tunnelSchema.safeParse(await response.json());
    if (!parsed.success) {
      return { status: "error", message: `${url} is not valid: ${parsed.error.message}` };
    }
    return { status: "ready", tunnel: parsed.data };
  } catch (error) {
    if (error instanceof NotFoundError) return { status: "missing" };
    if (signal?.aborted) throw error;
    return { status: "error", message: error instanceof Error ? error.message : String(error) };
  }
}

type Vertex = { readonly x: number; readonly y: number; readonly z: number };

/** The axis with its two end vertices pushed `overrun` metres outwards along the end segments. */
function extendAxis(axis: readonly Vertex[], overrun: number): Vertex[] {
  const first = axis[0] as Vertex;
  const second = axis.find((v) => v.x !== first.x || v.z !== first.z);
  const last = axis[axis.length - 1] as Vertex;
  const beforeLast = [...axis].reverse().find((v) => v.x !== last.x || v.z !== last.z);
  if (second === undefined || beforeLast === undefined) {
    throw new Error("The tunnel axis has no horizontal extent.");
  }
  const push = (from: Vertex, towards: Vertex): Vertex => {
    const length = Math.hypot(from.x - towards.x, from.z - towards.z);
    return {
      x: from.x + ((from.x - towards.x) / length) * overrun,
      y: from.y,
      z: from.z + ((from.z - towards.z) / length) * overrun,
    };
  };
  return [push(first, second), ...axis, push(last, beforeLast)];
}

/**
 * The tunnel as walkable ground: a strip `width` wide centred on the axis, from PORTAL_OVERRUN
 * outside one portal to PORTAL_OVERRUN outside the other, with the floor height interpolated
 * along the axis. The terrain above it is rock and plays no part. Also an {@link Enclosure}: the
 * volume between the floor and `height` above it, which the third-person camera must stay in.
 */
export class TunnelGroundSurface implements GroundSurface, Enclosure {
  private readonly path: readonly Vertex[];
  private readonly halfWidth: number;
  private readonly height: number;
  private readonly bounds: { minX: number; maxX: number; minZ: number; maxZ: number };

  constructor(tunnel: Pick<Tunnel, "axis" | "width" | "height">) {
    this.path = extendAxis(
      tunnel.axis.map(([x, y, z]) => ({ x, y, z })),
      PORTAL_OVERRUN,
    );
    this.halfWidth = tunnel.width / 2;
    this.height = tunnel.height;
    const xs = this.path.map((v) => v.x);
    const zs = this.path.map((v) => v.z);
    this.bounds = {
      minX: Math.min(...xs) - this.halfWidth,
      maxX: Math.max(...xs) + this.halfWidth,
      minZ: Math.min(...zs) - this.halfWidth,
      maxZ: Math.max(...zs) + this.halfWidth,
    };
  }

  /** The floor ends in straight, square caps at the extended ends. */
  private betweenEnds(x: number, z: number): boolean {
    const n = this.path.length;
    const [a, b, c, d] = [this.path[0], this.path[1], this.path[n - 2], this.path[n - 1]] as [
      Vertex,
      Vertex,
      Vertex,
      Vertex,
    ];
    return (
      (x - a.x) * (b.x - a.x) + (z - a.z) * (b.z - a.z) >= 0 &&
      (x - d.x) * (d.x - c.x) + (z - d.z) * (d.z - c.z) <= 0
    );
  }

  /** Floor height at (x, z) when it lies within `limit` metres of the axis, else null. */
  private floorWithin(x: number, z: number, limit: number): number | null {
    const b = this.bounds;
    if (x < b.minX || x > b.maxX || z < b.minZ || z > b.maxZ) return null;
    if (!this.betweenEnds(x, z)) return null;
    const last = this.path.length - 2;
    let bestDistSq = limit * limit;
    let floor: number | null = null;
    for (let i = 0; i <= last; i++) {
      const a = this.path[i] as Vertex;
      const c = this.path[i + 1] as Vertex;
      const abx = c.x - a.x;
      const abz = c.z - a.z;
      const lengthSq = abx * abx + abz * abz;
      if (lengthSq === 0) continue;
      const raw = ((x - a.x) * abx + (z - a.z) * abz) / lengthSq;
      // A point behind a segment belongs to the previous segment, which clamps it to the vertex
      // they share (the outside of a bend).
      if (raw < 0) continue;
      const t = Math.max(0, Math.min(1, raw));
      const distSq = (x - (a.x + abx * t)) ** 2 + (z - (a.z + abz * t)) ** 2;
      if (distSq <= bestDistSq) {
        bestDistSq = distSq;
        floor = a.y + (c.y - a.y) * t;
      }
    }
    return floor;
  }

  /** Floor height at (x, z), or null when (x, z) is not on the tunnel floor. */
  floorAt(x: number, z: number): number | null {
    return this.floorWithin(x, z, this.halfWidth);
  }

  surfaceBelow(x: number, y: number, z: number, maxDrop: number): number | null {
    const floor = this.floorAt(x, z);
    return floor !== null && floor <= y && floor >= y - maxDrop ? floor : null;
  }

  contains(x: number, y: number, z: number, margin: number): boolean {
    const floor = this.floorWithin(x, z, this.halfWidth - margin);
    return floor !== null && y >= floor + margin && y <= floor + this.height - margin;
  }
}
