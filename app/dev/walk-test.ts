import {
  BoxGeometry,
  BufferAttribute,
  BufferGeometry,
  Color,
  DirectionalLight,
  HemisphereLight,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  Scene,
} from "three";
import { createLoop } from "../src/core/loop";
import { createRenderer } from "../src/core/renderer";
import { createPlayer, type PlayerState } from "../src/player";
import {
  type Corridor,
  type GroundSurface,
  type HeightField,
  PolygonCorridor,
} from "../src/world/ground";

// Dev-only synthetic course for checking walking by hand and in Playwright. It is not product
// scenery: a gentle slope, two 0.3 m steps, a 0.6 m wall with a gap, and a tunnel under rock.
// Player coordinates are the local frame (ADR 0004); the route heads north (-Z).

const SLOPE_PER_METRE = 0.04;
const SLOPE_END_Z = -45;
const STEPS_Z = [-10, -18] as const;
const STEP_RISE = 0.3;
const WALL = { zNear: -26, zFar: -27, xMin: -2.5, xMax: 0.5, rise: 0.6 } as const;
const TUNNEL = { zNear: -50, zFar: -60, halfWidth: 1.5, rockHalfWidth: 4, rockHeight: 8 } as const;
const CORRIDOR_HALF_WIDTH = 2.5;
const ROUTE_NORTH_Z = -70;
const ROUTE_SOUTH_Z = 8;

function baseHeight(z: number): number {
  const slope = SLOPE_PER_METRE * Math.min(Math.max(-z, 0), -SLOPE_END_Z);
  const steps = STEPS_Z.filter((stepZ) => z < stepZ).length * STEP_RISE;
  return slope + steps;
}

const tunnelFloorY = baseHeight(TUNNEL.zNear);

class CourseHeightField implements HeightField {
  heightAt(x: number, z: number): number | null {
    if (Math.abs(x) > 40 || z > ROUTE_SOUTH_Z + 10 || z < ROUTE_NORTH_Z - 10) return null;
    const ground = baseHeight(z);
    if (Math.abs(x) <= TUNNEL.rockHalfWidth && z <= TUNNEL.zNear && z >= TUNNEL.zFar) {
      return tunnelFloorY + TUNNEL.rockHeight;
    }
    if (x >= WALL.xMin && x <= WALL.xMax && z <= WALL.zNear && z >= WALL.zFar) {
      return ground + WALL.rise;
    }
    return ground;
  }
}

const tunnelFloor: GroundSurface = {
  surfaceBelow(x, y, z, maxDrop) {
    const inside = Math.abs(x) <= TUNNEL.halfWidth && z <= TUNNEL.zNear && z >= TUNNEL.zFar;
    return inside && tunnelFloorY <= y && tunnelFloorY >= y - maxDrop ? tunnelFloorY : null;
  },
};

const corridor: Corridor = new PolygonCorridor([
  [-CORRIDOR_HALF_WIDTH, ROUTE_SOUTH_Z],
  [CORRIDOR_HALF_WIDTH, ROUTE_SOUTH_Z],
  [CORRIDOR_HALF_WIDTH, ROUTE_NORTH_Z],
  [-CORRIDOR_HALF_WIDTH, ROUTE_NORTH_Z],
]);

function buildTerrainMesh(field: HeightField): Mesh {
  const edges = (...values: number[]): number[] => values.flatMap((v) => [v - 1e-3, v + 1e-3]);
  const xs = unique([
    ...range(-12, 12, 1),
    ...edges(WALL.xMin, WALL.xMax, -TUNNEL.rockHalfWidth, TUNNEL.rockHalfWidth),
  ]);
  const zs = unique([
    ...range(ROUTE_NORTH_Z - 5, ROUTE_SOUTH_Z + 5, 1),
    ...edges(...STEPS_Z, WALL.zNear, WALL.zFar, TUNNEL.zNear, TUNNEL.zFar),
  ]);

  const positions: number[] = [];
  for (const z of zs) for (const x of xs) positions.push(x, field.heightAt(x, z) ?? 0, z);
  const indices: number[] = [];
  const row = xs.length;
  for (let j = 0; j < zs.length - 1; j++) {
    for (let i = 0; i < row - 1; i++) {
      const a = j * row + i;
      indices.push(a, a + row, a + 1, a + 1, a + row, a + row + 1);
    }
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return new Mesh(geometry, new MeshStandardMaterial({ color: 0x9a9577, roughness: 1 }));
}

function range(from: number, to: number, step: number): number[] {
  const values: number[] = [];
  for (let v = from; v <= to; v += step) values.push(v);
  return values;
}

function unique(values: number[]): number[] {
  return [...new Set(values)].sort((a, b) => a - b);
}

function box(
  scene: Scene,
  color: number,
  size: [number, number, number],
  center: [number, number, number],
): void {
  const mesh = new Mesh(
    new BoxGeometry(...size),
    new MeshStandardMaterial({ color, roughness: 1 }),
  );
  mesh.position.set(...center);
  scene.add(mesh);
}

function buildTunnelRock(scene: Scene): void {
  const length = TUNNEL.zNear - TUNNEL.zFar;
  const centerZ = (TUNNEL.zNear + TUNNEL.zFar) / 2;
  const wallWidth = TUNNEL.rockHalfWidth - TUNNEL.halfWidth;
  const side = (TUNNEL.rockHalfWidth + TUNNEL.halfWidth) / 2;
  const roofBottom = tunnelFloorY + 3;
  const roofHeight = TUNNEL.rockHeight - 3;
  for (const sign of [-1, 1]) {
    box(
      scene,
      0x6f6a58,
      [wallWidth, TUNNEL.rockHeight, length],
      [sign * side, tunnelFloorY + TUNNEL.rockHeight / 2, centerZ],
    );
  }
  box(
    scene,
    0x6f6a58,
    [TUNNEL.rockHalfWidth * 2, roofHeight, length],
    [0, roofBottom + roofHeight / 2, centerZ],
  );
  box(scene, 0xb0aa90, [TUNNEL.halfWidth * 2, 0.05, length], [0, tunnelFloorY - 0.025, centerZ]);
}

function buildWall(scene: Scene): void {
  const centerZ = (WALL.zNear + WALL.zFar) / 2;
  const ground = baseHeight(centerZ);
  box(
    scene,
    0xb55d4a,
    [WALL.xMax - WALL.xMin, WALL.rise, WALL.zNear - WALL.zFar],
    [(WALL.xMin + WALL.xMax) / 2, ground + WALL.rise / 2, centerZ],
  );
}

declare global {
  interface Window {
    __walkState?: {
      readonly x: number;
      readonly y: number;
      readonly z: number;
      readonly grounded: boolean;
      readonly cameraMode: PlayerState["cameraMode"];
      readonly yaw: number;
      readonly pitch: number;
      readonly corridorHit: boolean;
      readonly elapsed: number;
      readonly frames: number;
    };
  }
}

function requireElement<T extends HTMLElement>(id: string, type: new () => T): T {
  const element = document.getElementById(id);
  if (!(element instanceof type)) throw new Error(`walk-test.html is missing the #${id} element.`);
  return element;
}

function bootstrap(): void {
  const canvas = requireElement("scene", HTMLCanvasElement);
  const hud = requireElement("hud", HTMLPreElement);
  const camera = new PerspectiveCamera(70, 1, 0.05, 300);
  const handle = createRenderer(canvas, (width, height) => {
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  });
  if (!handle.ok) {
    hud.textContent = handle.message;
    return;
  }

  const scene = new Scene();
  scene.background = new Color(0x9ec9ee);
  scene.add(new HemisphereLight(0xcfe6ff, 0x6b5a3c, 1.4));
  const sun = new DirectionalLight(0xfff1d6, 2.5);
  sun.position.set(30, 60, 20);
  scene.add(sun);

  const heightField = new CourseHeightField();
  scene.add(buildTerrainMesh(heightField));
  buildWall(scene);
  buildTunnelRock(scene);

  const params = new URLSearchParams(location.search);
  const start = {
    x: Number(params.get("x") ?? 0),
    z: Number(params.get("z") ?? 4),
  };

  const player = createPlayer({
    scene,
    camera,
    canvas,
    heightField,
    groundSurfaces: [tunnelFloor],
    corridor,
    start,
  });

  let frames = 0;
  const loop = createLoop((dt) => {
    player.update(dt);
    handle.renderer.render(scene, camera);
    frames++;
    const { position, grounded, cameraMode, yaw, pitch, corridorHit, elapsed } = player.state;
    window.__walkState = {
      x: position.x,
      y: position.y,
      z: position.z,
      grounded,
      cameraMode,
      yaw,
      pitch,
      corridorHit,
      elapsed,
      frames,
    };
    hud.textContent =
      `pos ${position.x.toFixed(2)} ${position.y.toFixed(2)} ${position.z.toFixed(2)}  ` +
      `${grounded ? "grounded" : "airborne"}  ${cameraMode}-person` +
      (corridorHit ? "  [corridor]" : "") +
      "\nWASD/arrows move, Shift run, C camera, click canvas for mouse look (Esc releases)\n" +
      "touch: left half joystick, right half look, button toggles camera";
  });
  loop.start();

  window.addEventListener("pagehide", () => {
    loop.stop();
    player.dispose();
    handle.dispose();
  });
}

bootstrap();
