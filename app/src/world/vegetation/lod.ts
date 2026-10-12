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

/** Level for a squared distance to the camera; -1 beyond the far band. */
export function levelFor(distanceSq: number, bands: LodBands): Level {
  if (distanceSq <= bands[0] * bands[0]) return 0;
  if (distanceSq <= bands[1] * bands[1]) return 1;
  if (distanceSq <= bands[2] * bands[2]) return 2;
  return -1;
}

/** Writes each instance's level (or -1) into `out`; pure apart from `out`. */
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
    out[i] = levelFor(dx * dx + dy * dy + dz * dz, bands);
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
