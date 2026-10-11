import { z } from "zod";
import { fetchJson } from "../core/http";

const point3 = z.tuple([z.number(), z.number(), z.number()]);
const point2 = z.tuple([z.number(), z.number()]);

const anchorSchema = z.object({
  x: z.number(),
  y: z.number(),
  z: z.number(),
  osm: z.string().optional(),
});

/** `trail.json` from the pipeline (OSM-derived, ODbL: ADR 0007). Extra keys are ignored. */
export const trailSchema = z.object({
  licence: z.string(),
  attribution: z.string(),
  route: z.object({
    segments: z
      .array(
        z.object({
          id: z.string(),
          name: z.string().optional(),
          points: z.array(point3).min(2),
        }),
      )
      .min(1),
  }),
  corridor: z.object({ polygon: z.array(point2).min(3) }),
  anchors: z.record(z.string(), anchorSchema),
});

export type Trail = z.infer<typeof trailSchema>;
export type Anchor = z.infer<typeof anchorSchema>;
export type RoutePoint = readonly [number, number, number];

export const TRAIL_PATH = "assets/generated/trail.json";

export function parseTrail(json: unknown): Trail {
  return trailSchema.parse(json);
}

export function loadTrail(url: string, signal?: AbortSignal): Promise<Trail> {
  return fetchJson(url, trailSchema, signal);
}

/** All route points in walking order, with the repeated joint between consecutive segments dropped. */
export function routePoints(trail: Trail): RoutePoint[] {
  const points: RoutePoint[] = [];
  for (const segment of trail.route.segments) {
    for (const point of segment.points) {
      const last = points[points.length - 1];
      if (
        last !== undefined &&
        last[0] === point[0] &&
        last[1] === point[1] &&
        last[2] === point[2]
      ) {
        continue;
      }
      points.push(point);
    }
  }
  return points;
}

/** The start anchor (turnstile), or the Centre d'Informacio when the turnstile is not mapped. */
/**
 * Where the walk starts: the `requested` anchor (from `?start=`) when it exists and lies inside
 * the walkable corridor, otherwise the turnstile, otherwise the Centre d'Informació.
 */
export function startAnchor(
  trail: Trail,
  requested?: string | null,
  corridor?: { contains(x: number, z: number): boolean },
): { name: string; anchor: Anchor } {
  if (requested) {
    const anchor = trail.anchors[requested];
    if (anchor !== undefined && corridor?.contains(anchor.x, anchor.z) === true) {
      return { name: requested, anchor };
    }
  }
  for (const name of ["turnstile", "centre"]) {
    const anchor = trail.anchors[name];
    if (anchor !== undefined) return { name, anchor };
  }
  throw new Error('trail.json has neither a "turnstile" nor a "centre" anchor to start from.');
}

/**
 * Yaw (the player's convention: 0 looks along -Z, positive turns left) that faces along the
 * route at `from`: towards the first route point at least `lookAhead` metres (2D) further along
 * the route than the vertex nearest to `from`.
 */
export function headingAlongRoute(
  points: readonly RoutePoint[],
  from: { readonly x: number; readonly z: number },
  lookAhead = 8,
): number {
  if (points.length < 2) throw new Error("A route needs at least two points to give a heading.");
  let nearest = 0;
  let nearestDistance = Number.POSITIVE_INFINITY;
  points.forEach((p, index) => {
    const d = Math.hypot(p[0] - from.x, p[2] - from.z);
    if (d < nearestDistance) {
      nearestDistance = d;
      nearest = index;
    }
  });
  const origin = points[nearest] as RoutePoint;
  let target: RoutePoint | undefined;
  for (let i = nearest + 1; i < points.length; i++) {
    const candidate = points[i] as RoutePoint;
    target = candidate;
    if (Math.hypot(candidate[0] - origin[0], candidate[2] - origin[2]) >= lookAhead) break;
  }
  if (target === undefined) {
    // The nearest vertex is the last one: face the way the route arrived.
    const previous = points[nearest - 1] as RoutePoint;
    return Math.atan2(-(origin[0] - previous[0]), -(origin[2] - previous[2]));
  }
  return Math.atan2(-(target[0] - origin[0]), -(target[2] - origin[2]));
}

/** Adds to `reached` every anchor within `radius` metres (2D) of the position; returns the new ones. */
export function markReachedAnchors(
  position: { readonly x: number; readonly z: number },
  anchors: Readonly<Record<string, Anchor>>,
  radius: number,
  reached: Set<string>,
): string[] {
  const added: string[] = [];
  for (const [name, anchor] of Object.entries(anchors)) {
    if (reached.has(name)) continue;
    if (Math.hypot(anchor.x - position.x, anchor.z - position.z) <= radius) {
      reached.add(name);
      added.push(name);
    }
  }
  return added;
}
