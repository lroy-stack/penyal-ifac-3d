import { loadPois } from "../content/loadPois";
import type { AtmosphereWriter } from "./atmosphere";
import { createAtmosphereSystem } from "./atmosphere/system";
import { createTrailDebugSystem } from "./debugTrailSystem";
import { createPoiSystem, type PoiRegistryControl } from "./poi";
import { createSeaSystem } from "./sea/system";
import { createSkySystem } from "./sky";
import type { WorldSystem } from "./systems";
import { createTerrainSystem, type TerrainHandle } from "./terrain/system";
import { createTunnelSystem, type TunnelHandle } from "./tunnelSystem";

export type WorldSystemsDeps = {
  /** The writer goes to the `atmosphere` system alone; every other system reads `ctx.atmosphere`. */
  readonly atmosphere: AtmosphereWriter;
  /** `?debug=trail` lists the trail overlay. */
  readonly debugTrail: boolean;
  /** Where the poi system places the cards and announces discoveries. */
  readonly pois: PoiRegistryControl;
  /** Drafts are placed only in development. */
  readonly showDrafts: boolean;
};

/** Typed handles the bootstrap reads to feed `__appState.terrain` and `__appState.tunnel`. */
export type WorldHandles = {
  readonly terrain: TerrainHandle;
  readonly tunnel: TunnelHandle;
};

/**
 * The one list of world systems. A lane adds one import and one entry. Order matters: it is the
 * update order inside a phase and the creation order of the materials (and so three's opaque
 * sort), so entries keep the order the scene was built in before the registry existed.
 */
export function createWorldSystems(deps: WorldSystemsDeps): {
  readonly systems: readonly WorldSystem[];
  readonly handles: WorldHandles;
} {
  const terrain = createTerrainSystem();
  const tunnel = createTunnelSystem();
  const systems: WorldSystem[] = [
    createAtmosphereSystem(deps.atmosphere),
    createSkySystem(),
    createSeaSystem(),
    terrain.system,
    tunnel.system,
  ];
  systems.push(
    createPoiSystem({ control: deps.pois, load: loadPois, showDrafts: deps.showDrafts }),
  );
  if (deps.debugTrail) systems.push(createTrailDebugSystem());
  return { systems, handles: { terrain: terrain.handle, tunnel: tunnel.handle } };
}
