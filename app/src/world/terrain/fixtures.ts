import type { TerrainManifest, TerrainTile } from "./manifest";

/** Test helpers: tiles shaped like the plan's manifest contract. */
export function makeTile(i: number, j: number, size = 256): TerrainTile {
  const id = `t_${i}_${j}`;
  return {
    id,
    bounds: {
      minX: i * size,
      maxX: (i + 1) * size,
      minZ: j * size,
      maxZ: (j + 1) * size,
      minY: 0,
      maxY: 100,
    },
    lods: [
      {
        level: 0,
        url: `tiles/${id}_lod0.glb`,
        maxError: 0.25,
        texture: 1024,
        triangles: 0,
        bytes: 0,
      },
      { level: 1, url: `tiles/${id}_lod1.glb`, maxError: 1, texture: 512, triangles: 0, bytes: 0 },
      { level: 2, url: `tiles/${id}_lod2.glb`, maxError: 3, texture: 256, triangles: 0, bytes: 0 },
    ],
  };
}

export function makeManifest(tiles: readonly TerrainTile[]): TerrainManifest {
  return {
    version: 1,
    frame: { crs: "EPSG:25830", origin: { e: 767000, n: 4280000 } },
    near: { tileSize: 256, tiles: [...tiles] },
    far: {
      url: "far.glb",
      maxError: 4,
      texture: 2048,
      bounds: { minX: -600, maxX: 2000, minZ: -2000, maxZ: 550, minY: -3, maxY: 330 },
      triangles: 0,
      bytes: 0,
    },
  };
}
