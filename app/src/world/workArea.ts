/** Extent of the modelled area in the local frame (ADR 0004): x east, z south. */
export const WORK_AREA = { minX: -600, maxX: 2000, minZ: -2000, maxZ: 550 } as const;

export type WorkArea = typeof WORK_AREA;

export function workAreaCentre(area: WorkArea = WORK_AREA): { x: number; z: number } {
  return { x: (area.minX + area.maxX) / 2, z: (area.minZ + area.maxZ) / 2 };
}

/** Longest straight line inside the work area. */
export function workAreaDiagonal(area: WorkArea = WORK_AREA): number {
  return Math.hypot(area.maxX - area.minX, area.maxZ - area.minZ);
}

/** Camera far plane: the whole work area is inside it from any point, plus headroom for relief. */
export function cameraFar(area: WorkArea = WORK_AREA): number {
  return Math.ceil((workAreaDiagonal(area) + 200) / 100) * 100;
}

/** Horizontal distance from (x, z) to the nearest edge of the work area (0 outside). */
export function distanceToWorkAreaEdge(x: number, z: number, area: WorkArea = WORK_AREA): number {
  return Math.max(0, Math.min(x - area.minX, area.maxX - x, z - area.minZ, area.maxZ - z));
}
