/** Distances (m) of the three levels: lod0 up to `near`, lod1 up to `mid`, the far card up to `far`. */
export type LodBands = readonly [near: number, mid: number, far: number];

/** -1: not drawn. */
export type Level = -1 | 0 | 1 | 2;

export type InstanceColumns = {
  readonly count: number;
  readonly x: ArrayLike<number>;
  readonly y: ArrayLike<number>;
  readonly z: ArrayLike<number>;
  /** 0-99; an instance is drawn when `keep < 100 * density`. */
  readonly keep: ArrayLike<number>;
};

export const isKept = (keep: number, density: number): boolean => keep < 100 * density;

/**
 * Share of a band edge's distance by which an instance must cross it before its level changes:
 * without it, an instance on an edge flickers between two meshes as the third-person camera
 * orbits (7.5 %: 2.25 m at 30 m, 9 m at 120 m).
 */
export const LOD_HYSTERESIS = 0.075;

/** Index of the level beyond `edge` (3 for "not drawn"), so -1 orders after the far card. */
const rank = (level: Level): number => (level < 0 ? 3 : level);

/**
 * Level for a squared distance to the camera; -1 beyond the far band. With the `previous` level
 * of the instance, each edge moves out by `LOD_HYSTERESIS` for an instance on its near side and
 * in for one on its far side, so it keeps its level within that margin.
 */
export function levelFor(distanceSq: number, bands: LodBands, previous?: Level): Level {
  for (let edge = 0; edge < 3; edge++) {
    const limit = bands[edge] as number;
    const factor =
      previous === undefined ? 1 : rank(previous) <= edge ? 1 + LOD_HYSTERESIS : 1 - LOD_HYSTERESIS;
    if (distanceSq <= limit * limit * factor * factor) return edge as Level;
  }
  return -1;
}

/**
 * Writes each instance's level (or -1) into `out`; pure apart from `out`, whose current values
 * are the previous levels the hysteresis keeps (-1 for an instance not drawn).
 */
export function selectLevels(
  columns: InstanceColumns,
  camera: { readonly x: number; readonly y: number; readonly z: number },
  density: number,
  bands: LodBands,
  out: Int8Array,
): void {
  for (let i = 0; i < columns.count; i++) {
    if (!isKept(columns.keep[i] as number, density)) {
      out[i] = -1;
      continue;
    }
    const dx = (columns.x[i] as number) - camera.x;
    const dy = (columns.y[i] as number) - camera.y;
    const dz = (columns.z[i] as number) - camera.z;
    out[i] = levelFor(dx * dx + dy * dy + dz * dz, bands, out[i] as Level);
  }
}

/** Instances per level (index 0-2) among the drawn ones. */
export function countLevels(levels: Int8Array, count: number): [number, number, number] {
  const counts: [number, number, number] = [0, 0, 0];
  for (let i = 0; i < count; i++) {
    const level = levels[i] as number;
    if (level >= 0) counts[level] = (counts[level] as number) + 1;
  }
  return counts;
}
