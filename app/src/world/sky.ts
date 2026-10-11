import {
  BackSide,
  BufferAttribute,
  Color,
  DirectionalLight,
  Fog,
  Group,
  HemisphereLight,
  Mesh,
  MeshBasicMaterial,
  type Object3D,
  SphereGeometry,
  Vector3,
} from "three";
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

export function createFog(viewpoint: { readonly x: number; readonly z: number }): Fog {
  const { near, far } = fogRangeFor(viewpoint);
  return new Fog(HORIZON_COLOR, near, far);
}

function createSkyDome(radius: number): Mesh {
  const geometry = new SphereGeometry(radius, 32, 16);
  const position = geometry.getAttribute("position");
  const horizon = new Color(HORIZON_COLOR);
  const zenith = new Color(ZENITH_COLOR);
  const mixed = new Color();
  const colors = new Float32Array(position.count * 3);
  for (let i = 0; i < position.count; i++) {
    const elevation = Math.max(0, position.getY(i) / radius);
    mixed.copy(horizon).lerp(zenith, Math.sqrt(elevation));
    colors.set([mixed.r, mixed.g, mixed.b], i * 3);
  }
  geometry.setAttribute("color", new BufferAttribute(colors, 3));
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
  /** Keeps the dome centred on the camera. */
  readonly update: (cameraPosition: {
    readonly x: number;
    readonly y: number;
    readonly z: number;
  }) => void;
  readonly dispose: () => void;
};

/**
 * Gradient sky dome plus the lights that go with it. `radius` must be inside the camera far plane. */
export function createSky(radius: number): Sky {
  const group = new Group();
  group.name = "sky";

  const dome = createSkyDome(radius);
  group.add(dome);
  group.add(new HemisphereLight(0xcfe6ff, 0x6b5a3c, 1.1));
  const sun = new DirectionalLight(0xfff1d6, 2.6);
  sun.position.copy(SUN_DIRECTION).multiplyScalar(1000);
  group.add(sun);

  return {
    object: group,
    update: (camera) => dome.position.set(camera.x, camera.y, camera.z),
    dispose: () => {
      dome.geometry.dispose();
      (dome.material as MeshBasicMaterial).dispose();
    },
  };
}
