import type { Object3D } from "three";
import type { WorldSystem } from "./systems";
import {
  loadTunnel,
  TUNNEL_DIRECTORY,
  TUNNEL_PATH,
  type Tunnel,
  TunnelGroundSurface,
} from "./tunnel";
import { createTunnelLamp, loadTunnelView, type TunnelLamp, type TunnelView } from "./tunnelView";

export type TunnelMeshResult =
  | { readonly ok: true }
  | { readonly ok: false; readonly message: string };

/** What the bootstrap reads from the tunnel system: the typed handle `createWorldSystems` returns. */
export type TunnelHandle = {
  /** The tunnel file was found and valid: the floor, the enclosure and the lamp exist. */
  readonly available: () => boolean;
  /** Why `tunnel.json` could not be used, when it was present but invalid. */
  readonly error: () => string | null;
  /** Called once when the interior mesh has loaded or failed; set before `world.init`. */
  onMesh: ((result: TunnelMeshResult) => void) | null;
};

export type TunnelSystemDeps = {
  readonly loadTunnel: typeof loadTunnel;
  readonly loadView: typeof loadTunnelView;
};

const DEFAULT_DEPS: TunnelSystemDeps = { loadTunnel, loadView: loadTunnelView };

/** Height above the feet the "inside the tunnel" probe looks at (m). */
const INSIDE_PROBE_HEIGHT = 0.8;

/**
 * The tunnel as a world system. Its init (critical) reads `tunnel.json` and registers the floor
 * and the enclosure with the ground registry, which must happen before the walk; the visual
 * shell loads in the background of that init and reports its failure instead of failing the
 * system. The lamp moves with the player and is switched on only inside, so the light count
 * never changes.
 */
export function createTunnelSystem(deps: TunnelSystemDeps = DEFAULT_DEPS): {
  readonly system: WorldSystem;
  readonly handle: TunnelHandle;
} {
  let surface: TunnelGroundSurface | null = null;
  let lamp: TunnelLamp | null = null;
  let view: TunnelView | null = null;
  let error: string | null = null;
  let disposed = false;

  const handle: TunnelHandle = {
    available: () => surface !== null,
    error: () => error,
    onMesh: null,
  };

  const system: WorldSystem = {
    id: "tunnel",
    phase: "postPlayer",
    load: "critical",
    async init(ctx) {
      const file = await deps.loadTunnel(ctx.assets.url(TUNNEL_PATH), ctx.signal);
      if (file.status === "missing") {
        return { status: "missing", message: "The tunnel has not been generated." };
      }
      if (file.status === "error") {
        error = file.message;
        throw new Error(file.message);
      }
      const tunnel: Tunnel = file.tunnel;
      surface = new TunnelGroundSurface(tunnel);
      ctx.ground.addSurface(surface);
      ctx.ground.addEnclosure(surface);
      lamp = createTunnelLamp();
      ctx.root.add(lamp.light);

      const meshUrl = ctx.assets.url(`${TUNNEL_DIRECTORY}${tunnel.mesh}`);
      deps.loadView(ctx.assets.gltf(), meshUrl).then(
        (loaded) => {
          if (disposed) {
            loaded.dispose();
            return;
          }
          view = loaded;
          ctx.root.add(loaded.object as Object3D);
          handle.onMesh?.({ ok: true });
        },
        (cause: unknown) => {
          if (disposed) return;
          const message = `The tunnel interior could not be loaded. ${
            cause instanceof Error ? cause.message : String(cause)
          }`;
          ctx.report({ state: "degraded", message });
          handle.onMesh?.({ ok: false, message });
        },
      );
      return { status: "ready" };
    },
    update(frame) {
      if (surface === null || lamp === null || frame.player === null) return;
      const feet = frame.player.position;
      lamp.update(
        { x: feet.x, y: feet.y, z: feet.z },
        surface.contains(feet.x, feet.y + INSIDE_PROBE_HEIGHT, feet.z, 0),
      );
    },
    dispose() {
      disposed = true;
      view?.dispose();
      lamp?.light.dispose();
      view = null;
      lamp = null;
    },
  };
  return { system, handle };
}
