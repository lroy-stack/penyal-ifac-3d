import { PerspectiveCamera, Scene, type WebGLRenderer } from "three";
import { profileFor } from "../core/quality";
import { type AtmosphereWriter, createAtmosphere } from "./atmosphere";
import { dayAtmosphere } from "./atmosphere/defaults";
import { createGroundRegistry, type WorldDeps } from "./systems";

/** Test helpers: world dependencies around a real scene and camera, a stub renderer and the day atmosphere. */
export function makeWorldDeps(overrides: Partial<WorldDeps> = {}): {
  readonly deps: WorldDeps;
  readonly writer: AtmosphereWriter;
} {
  const writer = createAtmosphere(dayAtmosphere({ x: 0, z: 0 }));
  const deps: WorldDeps = {
    scene: new Scene(),
    camera: new PerspectiveCamera(65, 1, 0.2, 3000),
    renderer: { toneMapping: 0, toneMappingExposure: 1 } as unknown as WebGLRenderer,
    assets: { gltf: () => ({}) as never, url: (path) => `/${path}` },
    atmosphere: writer,
    quality: { current: profileFor("medium", { coarsePointer: false, softwareRenderer: false }) },
    ground: createGroundRegistry(),
    pois: { list: () => [], onDiscover: () => () => undefined },
    route: new Promise(() => undefined),
    collision: new Promise(() => undefined),
    params: new URLSearchParams(),
    testHooks: false,
    ...overrides,
  };
  return { deps, writer };
}
