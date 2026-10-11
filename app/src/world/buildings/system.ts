import { type BufferGeometry, type Material, Mesh, type Object3D } from "three";
import type { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import type { WorldSystem } from "../systems";

export const BUILDINGS_PATH = "assets/generated/buildings.glb";

export type BuildingsDeps = {
  readonly load: (loader: GLTFLoader, url: string) => Promise<Object3D>;
};

const DEFAULT_DEPS: BuildingsDeps = {
  load: async (loader, url) => (await loader.loadAsync(url)).scene,
};

function disposeObject(object: Object3D): void {
  object.traverse((child) => {
    if (!(child instanceof Mesh)) return;
    (child.geometry as BufferGeometry).dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materials as Material[]) material.dispose();
  });
}

/**
 * The two visitor-centre buildings (`buildings.glb`, E3): flat-coloured volumes, one draw call
 * each. They are decoration (no ground surface, no light), so they load in the background after
 * the walk starts, like the vegetation; a file that cannot be loaded is reported as `missing` and
 * the walk goes on without them.
 */
export function createBuildingsSystem(deps: BuildingsDeps = DEFAULT_DEPS): WorldSystem {
  let object: Object3D | null = null;
  let disposed = false;
  return {
    id: "buildings",
    phase: "postPlayer",
    load: "background",
    async init(ctx) {
      let loaded: Object3D;
      try {
        loaded = await deps.load(ctx.assets.gltf(), ctx.assets.url(BUILDINGS_PATH));
      } catch (cause) {
        if (disposed) return { status: "ready" };
        return {
          status: "missing",
          message: `The visitor-centre buildings could not be loaded. ${
            cause instanceof Error ? cause.message : String(cause)
          }`,
        };
      }
      if (disposed) {
        disposeObject(loaded);
        return { status: "ready" };
      }
      loaded.traverse((child) => {
        if (!(child instanceof Mesh)) return;
        const geometry = child.geometry as BufferGeometry;
        if (geometry.boundingSphere === null) geometry.computeBoundingSphere();
      });
      loaded.name = "buildings";
      ctx.root.add(loaded);
      object = loaded;
      return { status: "ready" };
    },
    update: () => undefined,
    dispose() {
      disposed = true;
      if (object !== null) disposeObject(object);
      object = null;
    },
  };
}
