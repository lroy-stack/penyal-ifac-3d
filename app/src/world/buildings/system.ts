import { type BufferGeometry, type Material, Mesh, type Object3D } from "three";
import type { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { fetchBuffer, NotFoundError } from "../../core/http";
import { attachAtmosphere } from "../atmosphere";
import { disposeObject } from "../disposal";
import type { WorldSystem } from "../systems";

export const BUILDINGS_PATH = "assets/generated/buildings.glb";

export type BuildingsDeps = {
  /** Rejects with `NotFoundError` when the file does not exist; any other rejection is a failure. */
  readonly load: (loader: GLTFLoader, url: string, signal: AbortSignal) => Promise<Object3D>;
};

const DEFAULT_DEPS: BuildingsDeps = {
  load: async (loader, url, signal) => {
    const buffer = await fetchBuffer(url, signal);
    const gltf = await loader.parseAsync(buffer, url.slice(0, url.lastIndexOf("/") + 1));
    signal.throwIfAborted();
    return gltf.scene;
  },
};

/**
 * The two visitor-centre buildings (`buildings.glb`, E3): a few textured meshes (KTX2), one draw
 * call per material. They are decoration (no ground surface, no light), so they load in the
 * background after the walk starts, like the vegetation. A file that was never generated is
 * `missing` and the walk goes on without it; any other failure (HTTP error, corrupt GLB) fails
 * the system through the contract's failure path.
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
        loaded = await deps.load(ctx.assets.gltf(), ctx.assets.url(BUILDINGS_PATH), ctx.signal);
      } catch (cause) {
        if (disposed) return { status: "ready" };
        if (!(cause instanceof NotFoundError)) throw cause;
        return {
          status: "missing",
          message: "The visitor-centre buildings have not been generated.",
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
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        for (const material of materials as Material[]) attachAtmosphere(material, ctx.atmosphere);
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
