import { Mesh, MeshStandardMaterial, PlaneGeometry } from "three";
import type { WorldSystem } from "../systems";
import { workAreaCentre } from "../workArea";

/** Side of the sea plane (m): far beyond the work area so no edge is ever seen. */
export const SEA_SIZE = 20_000;

/**
 * Flat sea at y = 0 (orthometric heights are referred to mean sea level, ADR 0004). It hides the
 * pipeline's seabed proxy at -3 m. F3 replaces the material with animated Gerstner waves.
 */
export function createSea(): Mesh {
  const geometry = new PlaneGeometry(SEA_SIZE, SEA_SIZE);
  geometry.rotateX(-Math.PI / 2);
  const material = new MeshStandardMaterial({ color: 0x1f6f9c, roughness: 0.35, metalness: 0 });
  const sea = new Mesh(geometry, material);
  sea.name = "sea";
  const centre = workAreaCentre();
  sea.position.set(centre.x, 0, centre.z);
  return sea;
}

/** The flat sea as a world system; L4 replaces the material with waves behind the same id. */
export function createSeaSystem(): WorldSystem {
  let sea: Mesh | null = null;
  return {
    id: "sea",
    phase: "postPlayer",
    load: "critical",
    async init(ctx) {
      sea = createSea();
      ctx.root.add(sea);
      return { status: "ready" };
    },
    update: () => undefined,
    dispose() {
      if (sea === null) return;
      sea.geometry.dispose();
      (sea.material as MeshStandardMaterial).dispose();
      sea = null;
    },
  };
}
