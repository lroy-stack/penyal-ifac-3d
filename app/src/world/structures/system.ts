import { type Material, Mesh, type Object3D } from "three";
import { attachAtmosphere } from "../atmosphere";
import type { WorldSystem } from "../systems";
import { loadTunnelView, type TunnelView } from "../tunnelView";
import {
  loadStructures,
  STRUCTURES_DIRECTORY,
  STRUCTURES_PATH,
  TreadsGroundSurface,
} from "./structures";

export type StructuresSystemDeps = {
  readonly loadStructures: typeof loadStructures;
  readonly loadView: typeof loadTunnelView;
};

const DEFAULT_DEPS: StructuresSystemDeps = { loadStructures, loadView: loadTunnelView };

/**
 * The staircases as a world system. Its init (beforeWalk: the walk gate waits for it, but the
 * preview does not) registers the treads with the ground registry before the walk locks it; the
 * meshes load in the background of that init and a failure degrades the system instead of
 * failing it, because the player can still walk the treads.
 */
export function createStructuresSystem(deps: StructuresSystemDeps = DEFAULT_DEPS): WorldSystem {
  let view: TunnelView | null = null;
  let disposed = false;
  return {
    id: "structures",
    phase: "postPlayer",
    load: "beforeWalk",
    async init(ctx) {
      const file = await deps.loadStructures(ctx.assets.url(STRUCTURES_PATH), ctx.signal);
      if (file.status === "missing") {
        return { status: "missing", message: "The staircases have not been generated." };
      }
      if (file.status === "error") throw new Error(file.message);
      const { structures } = file;
      ctx.ground.addSurface(
        new TreadsGroundSurface(structures.staircases.flatMap((s) => s.collision.treads)),
      );
      deps
        .loadView(ctx.assets.gltf(), ctx.assets.url(`${STRUCTURES_DIRECTORY}${structures.glb}`))
        .then(
          (loaded) => {
            if (disposed) {
              loaded.dispose();
              return;
            }
            view = loaded;
            loaded.object.traverse((child) => {
              if (!(child instanceof Mesh)) return;
              const materials = Array.isArray(child.material) ? child.material : [child.material];
              for (const material of materials as Material[]) {
                attachAtmosphere(material, ctx.atmosphere);
              }
            });
            ctx.root.add(loaded.object as Object3D);
          },
          (cause: unknown) => {
            if (disposed) return;
            ctx.report({
              state: "degraded",
              message: `The staircase meshes could not be loaded. ${
                cause instanceof Error ? cause.message : String(cause)
              }`,
            });
          },
        );
      return { status: "ready" };
    },
    update() {
      // Static geometry: nothing to do per frame.
    },
    dispose() {
      disposed = true;
      view?.dispose();
      view = null;
    },
  };
}
