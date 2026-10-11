/**
 * Local frame of the whole project (ADR 0004): EPSG:25830 (ETRS89 / UTM 30N) shifted to a local
 * origin so float32 keeps millimetre precision. Same transform as `penyal_pipeline.geo`.
 *
 *   x = E - 767000      (east)
 *   y = H               (orthometric height, metres)
 *   z = -(N - 4280000)  (north is -Z, as in three.js)
 */
export const ORIGIN_EASTING = 767000;
export const ORIGIN_NORTHING = 4280000;

export type LocalPoint = { readonly x: number; readonly y: number; readonly z: number };
export type Utm25830Point = { readonly e: number; readonly n: number; readonly h: number };

export function toLocal(e: number, n: number, h: number): LocalPoint {
  return { x: e - ORIGIN_EASTING, y: h, z: -(n - ORIGIN_NORTHING) };
}

export function fromLocal(x: number, y: number, z: number): Utm25830Point {
  return { e: x + ORIGIN_EASTING, n: ORIGIN_NORTHING - z, h: y };
}
