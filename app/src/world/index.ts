import type { AtmosphereWriter } from "./atmosphere";
import { createAtmosphereSystem } from "./atmosphere/system";
import { createSeaSystem } from "./sea/system";
import { createSkySystem } from "./sky";
import type { WorldSystem } from "./systems";

export type WorldSystemsDeps = {
  /** The writer goes to the `atmosphere` system alone; every other system reads `ctx.atmosphere`. */
  readonly atmosphere: AtmosphereWriter;
};

/**
 * The one list of world systems. A lane adds one import and one entry. Order matters: it is the
 * update order inside a phase and the creation order of the materials (and so three's opaque
 * sort), so entries keep the order the scene was built in before the registry existed.
 */
export function createWorldSystems(deps: WorldSystemsDeps): readonly WorldSystem[] {
  return [createAtmosphereSystem(deps.atmosphere), createSkySystem(), createSeaSystem()];
}
