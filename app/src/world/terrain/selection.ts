import type { TerrainTile, TileBounds, TileLod } from "./manifest";

export type Vec3 = { readonly x: number; readonly y: number; readonly z: number };

/** What selection needs to know about the camera and the screen. */
export type View = {
  readonly position: Vec3;
  /** Unit view direction. */
  readonly forward: Vec3;
  /** Vertical field of view (radians). */
  readonly fovY: number;
  /** Viewport height in device pixels. */
  readonly viewportHeight: number;
};

/** Screen-space error budget (px): 2 on fine pointers, 4 on coarse ones. */
export function sseThreshold(coarsePointer: boolean): number {
  return coarsePointer ? 4 : 2;
}

/** A coarser LOD is chosen only once its error is below `threshold / HYSTERESIS`. */
export const HYSTERESIS = 1.5;
/** Tiles entirely behind the camera and at least this far (m) stay at the coarsest LOD. */
export const BEHIND_FAR_DISTANCE = 150;

/** Pixel error of a geometric error `maxError` (m) seen from `distance` (m). */
export function screenSpaceError(
  maxError: number,
  distance: number,
  view: Pick<View, "fovY" | "viewportHeight">,
): number {
  if (distance <= 1e-6) return Number.POSITIVE_INFINITY;
  return (maxError * view.viewportHeight) / (2 * Math.tan(view.fovY / 2) * distance);
}

/** Distance from `point` to the 3D axis-aligned box (0 inside it). */
export function distanceToBounds(point: Vec3, b: TileBounds): number {
  const dx = Math.max(b.minX - point.x, 0, point.x - b.maxX);
  const dy = Math.max(b.minY - point.y, 0, point.y - b.maxY);
  const dz = Math.max(b.minZ - point.z, 0, point.z - b.maxZ);
  return Math.hypot(dx, dy, dz);
}

/** True when all eight corners lie behind the camera plane. */
export function isBehindCamera(b: TileBounds, view: Pick<View, "position" | "forward">): boolean {
  for (const x of [b.minX, b.maxX]) {
    for (const y of [b.minY, b.maxY]) {
      for (const z of [b.minZ, b.maxZ]) {
        const along =
          (x - view.position.x) * view.forward.x +
          (y - view.position.y) * view.forward.y +
          (z - view.position.z) * view.forward.z;
        if (along > 0) return false;
      }
    }
  }
  return true;
}

function byLevel(lods: readonly TileLod[]): TileLod[] {
  return [...lods].sort((a, b) => a.level - b.level);
}

export function finestLevel(tile: TerrainTile): number {
  return Math.min(...tile.lods.map((l) => l.level));
}

export function coarsestLevel(tile: TerrainTile): number {
  return Math.max(...tile.lods.map((l) => l.level));
}

/**
 * LOD level for a tile at `distance` (m to its box): the coarsest one whose screen-space error
 * is within `threshold`; the finest when none is. With `previous` (the level chosen last frame)
 * the choice is sticky: it refines as soon as `previous` exceeds the threshold, but coarsens
 * only to a level whose error is below `threshold / HYSTERESIS`, so a camera hovering at a
 * boundary does not flap between two levels.
 */
export function selectLod(
  tile: TerrainTile,
  distance: number,
  view: Pick<View, "fovY" | "viewportHeight">,
  threshold: number,
  previous?: number,
): number {
  const lods = byLevel(tile.lods);
  const within = (lod: TileLod, limit: number): boolean =>
    screenSpaceError(lod.maxError, distance, view) <= limit;

  let ideal = (lods[0] as TileLod).level;
  for (let i = lods.length - 1; i >= 0; i--) {
    if (within(lods[i] as TileLod, threshold)) {
      ideal = (lods[i] as TileLod).level;
      break;
    }
  }
  if (previous === undefined || !lods.some((l) => l.level === previous)) return ideal;
  if (ideal <= previous) return ideal;

  let chosen = previous;
  for (const lod of lods) {
    if (lod.level > previous && lod.level <= ideal && within(lod, threshold / HYSTERESIS)) {
      chosen = lod.level;
    }
  }
  return chosen;
}

export type TilePlan = {
  readonly id: string;
  /** Level that should be on screen. */
  readonly wanted: number;
  /** Distance (m) from the camera to the tile's box. */
  readonly distance: number;
};

/** Picks the wanted LOD of every near tile for this view. */
export function planTiles(
  tiles: readonly TerrainTile[],
  view: View,
  threshold: number,
  previous: ReadonlyMap<string, number>,
): TilePlan[] {
  return tiles.map((tile) => {
    const distance = distanceToBounds(view.position, tile.bounds);
    const wanted =
      distance >= BEHIND_FAR_DISTANCE && isBehindCamera(tile.bounds, view)
        ? coarsestLevel(tile)
        : selectLod(tile, distance, view, threshold, previous.get(tile.id));
    return { id: tile.id, wanted, distance };
  });
}

/** Adjacent tiles may differ by at most this many LOD levels (one texel-density doubling). */
export const DEFAULT_MAX_LOD_STEP = 1;

const EDGE_EPSILON = 1e-3;

function sharesEdge(a: TileBounds, b: TileBounds): boolean {
  const overlapX = Math.min(a.maxX, b.maxX) - Math.max(a.minX, b.minX);
  const overlapZ = Math.min(a.maxZ, b.maxZ) - Math.max(a.minZ, b.minZ);
  const touchX =
    Math.abs(a.maxX - b.minX) < EDGE_EPSILON || Math.abs(b.maxX - a.minX) < EDGE_EPSILON;
  const touchZ =
    Math.abs(a.maxZ - b.minZ) < EDGE_EPSILON || Math.abs(b.maxZ - a.minZ) < EDGE_EPSILON;
  return (touchX && overlapZ > EDGE_EPSILON) || (touchZ && overlapX > EDGE_EPSILON);
}

const neighbourCache = new WeakMap<
  readonly TerrainTile[],
  ReadonlyMap<string, readonly string[]>
>();

/** Ids of the tiles that share an edge with each tile (corner contact does not count). */
export function tileNeighbours(
  tiles: readonly TerrainTile[],
): ReadonlyMap<string, readonly string[]> {
  const cached = neighbourCache.get(tiles);
  if (cached !== undefined) return cached;
  const result = new Map<string, string[]>(tiles.map((t) => [t.id, []]));
  for (let i = 0; i < tiles.length; i++) {
    for (let j = i + 1; j < tiles.length; j++) {
      const a = tiles[i] as TerrainTile;
      const b = tiles[j] as TerrainTile;
      if (!sharesEdge(a.bounds, b.bounds)) continue;
      result.get(a.id)?.push(b.id);
      result.get(b.id)?.push(a.id);
    }
  }
  neighbourCache.set(tiles, result);
  return result;
}

/**
 * Refines (never coarsens) plans so that edge-adjacent tiles differ by at most `maxStep` levels:
 * a tile whose neighbour is more than `maxStep` levels finer moves to the coarsest of its own
 * levels within `maxStep` of that neighbour. Each tile's texture density therefore changes at most
 * by 2^maxStep across a seam. Tiles are only ever refined, so the pass terminates. Tiles behind
 * the camera are refined too when they touch a fine tile; that costs at most one extra LOD load.
 */
export function constrainLodSteps(
  tiles: readonly TerrainTile[],
  plans: readonly TilePlan[],
  maxStep: number,
): TilePlan[] {
  if (!(maxStep >= 0) || maxStep === Number.POSITIVE_INFINITY) return [...plans];
  const neighbours = tileNeighbours(tiles);
  const tileById = new Map(tiles.map((t) => [t.id, t]));
  const wanted = new Map(plans.map((p) => [p.id, p.wanted]));
  let changed = true;
  while (changed) {
    changed = false;
    for (const [id, level] of wanted) {
      const tile = tileById.get(id);
      if (tile === undefined) continue;
      let finestNeighbour = level;
      for (const other of neighbours.get(id) ?? []) {
        finestNeighbour = Math.min(finestNeighbour, wanted.get(other) ?? level);
      }
      if (level <= finestNeighbour + maxStep) continue;
      const cap = finestNeighbour + maxStep;
      const allowed = byLevel(tile.lods).filter((l) => l.level <= cap);
      const next =
        allowed.length > 0 ? (allowed[allowed.length - 1] as TileLod).level : finestLevel(tile);
      if (next < level) {
        wanted.set(id, next);
        changed = true;
      }
    }
  }
  return plans.map((p) => ({ ...p, wanted: wanted.get(p.id) ?? p.wanted }));
}

export type LoadRequest = {
  readonly id: string;
  readonly level: number;
  /** 0: the far mesh, 1: coarsest level of a near tile, 2: finer levels. Lower loads first. */
  readonly tier: 0 | 1 | 2;
  readonly distance: number;
};

export const FAR_ID = "far";

/**
 * Everything that should be loaded, in the order to load it: the far mesh, then the coarsest
 * LOD of every near tile, then the finer wanted LODs, each tier nearest first. `isResident`
 * filters out what is already loaded.
 */
export function loadRequests(
  tiles: readonly TerrainTile[],
  plans: readonly TilePlan[],
  isResident: (id: string, level: number) => boolean,
): LoadRequest[] {
  const requests: LoadRequest[] = [];
  if (!isResident(FAR_ID, 0)) requests.push({ id: FAR_ID, level: 0, tier: 0, distance: 0 });
  const byId = new Map(tiles.map((t) => [t.id, t]));
  for (const plan of plans) {
    const tile = byId.get(plan.id);
    if (tile === undefined) continue;
    const coarsest = coarsestLevel(tile);
    if (!isResident(plan.id, coarsest)) {
      requests.push({ id: plan.id, level: coarsest, tier: 1, distance: plan.distance });
    }
    if (plan.wanted !== coarsest && !isResident(plan.id, plan.wanted)) {
      requests.push({ id: plan.id, level: plan.wanted, tier: 2, distance: plan.distance });
    }
  }
  return requests.sort((a, b) => a.tier - b.tier || a.distance - b.distance || a.level - b.level);
}

/**
 * The level to display for a tile: the wanted one once it is loaded; until then the one already
 * on screen (so there is never a hole); failing that the loaded level closest to the wanted one.
 */
export function chooseDisplayed(
  wanted: number,
  displayed: number | undefined,
  resident: ReadonlySet<number>,
): number | undefined {
  if (resident.has(wanted)) return wanted;
  if (displayed !== undefined && resident.has(displayed)) return displayed;
  let best: number | undefined;
  for (const level of resident) {
    if (best === undefined || Math.abs(level - wanted) < Math.abs(best - wanted)) best = level;
  }
  return best;
}
