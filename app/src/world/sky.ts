import {
  BackSide,
  BufferAttribute,
  Color,
  DirectionalLight,
  Group,
  HemisphereLight,
  Mesh,
  MeshBasicMaterial,
  type Object3D,
  type PerspectiveCamera,
  SphereGeometry,
  Vector3,
} from "three";
import type { AtmosphereReader } from "./atmosphere";
import type { WorldSystem } from "./systems";
import { distanceToWorkAreaEdge, WORK_AREA, type WorkArea } from "./workArea";

export const HORIZON_COLOR = 0xbcd6ea;
export const ZENITH_COLOR = 0x4f8fd0;

/**
 * Fixed daytime sun direction (towards the sun): south-east, about 45 degrees up. Replaced by
 * SunCalc positions for the real place and time in F3.
 */
export const SUN_DIRECTION = new Vector3(0.5, 0.75, 0.6).normalize();

/**
 * Linear fog range that is fully opaque at the work area edge nearest to `viewpoint`, so the
 * edge of the terrain is never seen as a hard line from there. From the summit the nearest edge
 * is the west one, 1214 m away.
 */
export function fogRangeFor(
  viewpoint: { readonly x: number; readonly z: number },
  area: WorkArea = WORK_AREA,
): { near: number; far: number } {
  const far = distanceToWorkAreaEdge(viewpoint.x, viewpoint.z, area);
  return { near: far * 0.2, far };
}

function paintDome(geometry: SphereGeometry, radius: number, atmosphere: AtmosphereReader): void {
  const position = geometry.getAttribute("position");
  const { horizon: h, zenith: z } = atmosphere.state;
  const horizon = new Color().setRGB(h.r, h.g, h.b);
  const zenith = new Color().setRGB(z.r, z.g, z.b);
  const mixed = new Color();
  const existing = geometry.getAttribute("color");
  const colors =
    existing instanceof BufferAttribute
      ? existing
      : new BufferAttribute(new Float32Array(position.count * 3), 3);
  for (let i = 0; i < position.count; i++) {
    const elevation = Math.max(0, position.getY(i) / radius);
    mixed.copy(horizon).lerp(zenith, Math.sqrt(elevation));
    colors.setXYZ(i, mixed.r, mixed.g, mixed.b);
  }
  colors.needsUpdate = true;
  if (existing !== colors) geometry.setAttribute("color", colors);
}

function createSkyDome(radius: number, atmosphere: AtmosphereReader): Mesh {
  const geometry = new SphereGeometry(radius, 32, 16);
  paintDome(geometry, radius, atmosphere);
  const material = new MeshBasicMaterial({
    vertexColors: true,
    side: BackSide,
    fog: false,
    depthWrite: false,
  });
  const dome = new Mesh(geometry, material);
  dome.name = "sky-dome";
  dome.frustumCulled = false;
  dome.renderOrder = -1;
  return dome;
}

export type Sky = {
  /** Dome, hemisphere light and sun; add to the scene. */
  readonly object: Object3D;
  /** Keeps the dome centred on the camera and follows the atmosphere when its version changes. */
  readonly update: (cameraPosition: {
    readonly x: number;
    readonly y: number;
    readonly z: number;
  }) => void;
  readonly dispose: () => void;
};

/**
 * Gradient sky dome plus the lights that go with it, coloured by the atmosphere. `radius` must be
 * inside the camera far plane. The lights are created here, once: a change in their count would
 * recompile every lit material, so a new atmosphere only changes their values.
 */
export function createSky(radius: number, atmosphere: AtmosphereReader): Sky {
  const group = new Group();
  group.name = "sky";

  const dome = createSkyDome(radius, atmosphere);
  group.add(dome);
  const hemisphere = new HemisphereLight();
  const sun = new DirectionalLight();
  group.add(hemisphere);
  group.add(sun);

  let applied = -1;
  const apply = (): void => {
    const { ambient, sun: light } = atmosphere.state;
    hemisphere.color.setRGB(ambient.sky.r, ambient.sky.g, ambient.sky.b);
    hemisphere.groundColor.setRGB(ambient.ground.r, ambient.ground.g, ambient.ground.b);
    hemisphere.intensity = ambient.intensity;
    sun.color.setRGB(light.color.r, light.color.g, light.color.b);
    sun.intensity = light.intensity;
    sun.position.set(light.direction.x, light.direction.y, light.direction.z).multiplyScalar(1000);
    paintDome(dome.geometry as SphereGeometry, radius, atmosphere);
    applied = atmosphere.version;
  };
  apply();

  return {
    object: group,
    update: (camera) => {
      if (atmosphere.version !== applied) apply();
      dome.position.set(camera.x, camera.y, camera.z);
    },
    dispose: () => {
      dome.geometry.dispose();
      (dome.material as MeshBasicMaterial).dispose();
    },
  };
}

/** The sky as a world system: after the camera has moved, so the dome is centred on this frame's eye. */
export function createSkySystem(): WorldSystem {
  let sky: Sky | null = null;
  let camera: PerspectiveCamera | null = null;
  return {
    id: "sky",
    phase: "postPlayer",
    load: "critical",
    async init(ctx) {
      sky = createSky(ctx.camera.far * 0.9, ctx.atmosphere);
      camera = ctx.camera;
      ctx.root.add(sky.object);
      return { status: "ready" };
    },
    update() {
      if (sky !== null && camera !== null) sky.update(camera.position);
    },
    dispose() {
      sky?.dispose();
      sky = null;
    },
  };
}
