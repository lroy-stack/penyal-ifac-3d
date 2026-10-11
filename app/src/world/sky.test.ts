import {
  Color,
  DirectionalLight,
  HemisphereLight,
  Light,
  type Mesh,
  type SphereGeometry,
} from "three";
import { describe, expect, it } from "vitest";
import { makeWorldDeps } from "./fixtures";
import { createSkySystem, fogRangeFor, SUN_DIRECTION } from "./sky";
import { createWorld } from "./systems";

describe("fogRangeFor", () => {
  it("is opaque exactly at the nearest work-area edge seen from the summit", () => {
    const { near, far } = fogRangeFor({ x: 613.893, z: -754.184 });

    expect(far).toBeCloseTo(1213.893, 3);
    expect(near).toBeCloseTo(far * 0.2, 6);
  });

  it("never exceeds the distance to the nearest edge from any viewpoint", () => {
    const { far } = fogRangeFor({ x: 1136, z: -482 });

    expect(far).toBe(864);
  });
});

describe("SUN_DIRECTION", () => {
  it("is a unit vector pointing above the horizon", () => {
    expect(SUN_DIRECTION.length()).toBeCloseTo(1, 9);
    expect(SUN_DIRECTION.y).toBeGreaterThan(0.5);
  });
});

describe("sky system", () => {
  const frame = {
    frame: 1,
    dt: 0.016,
    time: 0,
    realMs: 16,
    drawingBufferHeight: 720,
    player: null,
  };

  async function boot() {
    const { deps, writer } = makeWorldDeps();
    const world = createWorld([createSkySystem()], deps);
    await world.init("critical");
    const root = deps.scene.getObjectByName("system:sky");
    const dome = deps.scene.getObjectByName("sky-dome") as Mesh;
    const lights: Light[] = [];
    deps.scene.traverse((object) => {
      if (object instanceof Light) lights.push(object);
    });
    return { deps, writer, world, root, dome, lights };
  }

  it("adds the dome and exactly two lights under its root", async () => {
    const { root, dome, lights } = await boot();
    expect(dome.parent?.parent).toBe(root);
    expect(lights.map((light) => light.type).sort()).toEqual([
      "DirectionalLight",
      "HemisphereLight",
    ]);
  });

  it("lights with today's constants, bit for bit", async () => {
    const { lights } = await boot();
    const hemisphere = lights.find((l) => l instanceof HemisphereLight) as HemisphereLight;
    const sun = lights.find((l) => l instanceof DirectionalLight) as DirectionalLight;
    expect(hemisphere.color.toArray()).toEqual(new Color(0xcfe6ff).toArray());
    expect(hemisphere.groundColor.toArray()).toEqual(new Color(0x6b5a3c).toArray());
    expect(hemisphere.intensity).toBe(1.1);
    expect(sun.color.toArray()).toEqual(new Color(0xfff1d6).toArray());
    expect(sun.intensity).toBe(2.6);
    expect(sun.position.toArray()).toEqual(SUN_DIRECTION.clone().multiplyScalar(1000).toArray());
  });

  it("sizes the dome from the camera far plane and keeps it on the camera", async () => {
    const { deps, world, dome } = await boot();
    expect((dome.geometry as SphereGeometry).parameters.radius).toBeCloseTo(3000 * 0.9, 9);
    deps.camera.position.set(10, 20, 30);
    world.update("postPlayer", frame);
    expect(dome.position.toArray()).toEqual([10, 20, 30]);
  });

  it("follows a new atmosphere without adding lights", async () => {
    const { deps, writer, world, dome, lights } = await boot();
    const before = dome.geometry.getAttribute("color").getX(0);
    writer.set({
      horizon: { r: 0.9, g: 0.9, b: 0.9 },
      zenith: { r: 0.2, g: 0.2, b: 0.2 },
      sun: { direction: { x: 0, y: 1, z: 0 }, color: { r: 1, g: 0, b: 0 }, intensity: 1 },
    });
    world.update("postPlayer", frame);
    const sun = lights.find((l) => l instanceof DirectionalLight) as DirectionalLight;
    expect(sun.color.toArray()).toEqual([1, 0, 0]);
    expect(sun.position.toArray()).toEqual([0, 1000, 0]);
    // Vertex 0 is the pole: the zenith colour.
    expect(dome.geometry.getAttribute("color").getX(0)).toBeCloseTo(0.2, 6);
    expect(before).not.toBeCloseTo(0.2, 6);
    let count = 0;
    deps.scene.traverse((object) => {
      if (object instanceof Light) count++;
    });
    expect(count).toBe(2);
  });
});
