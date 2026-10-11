import { type Mesh, MeshStandardMaterial, type PlaneGeometry } from "three";
import { describe, expect, it } from "vitest";
import { makeWorldDeps } from "../fixtures";
import { createWorld } from "../systems";
import { workAreaCentre } from "../workArea";
import { createSeaSystem, SEA_SIZE } from "./system";

describe("sea system", () => {
  it("puts one flat plane at sea level under its root, centred on the work area", async () => {
    const { deps } = makeWorldDeps();
    const world = createWorld([createSeaSystem()], deps);
    await world.init("critical");
    const root = deps.scene.getObjectByName("system:sea");
    const sea = deps.scene.getObjectByName("sea") as Mesh;
    expect(sea.parent).toBe(root);
    const centre = workAreaCentre();
    expect(sea.position.toArray()).toEqual([centre.x, 0, centre.z]);
    expect((sea.geometry as PlaneGeometry).parameters.width).toBe(SEA_SIZE);
    expect(sea.material).toBeInstanceOf(MeshStandardMaterial);
    expect(SEA_SIZE).toBe(20_000);
  });

  it("disposes its geometry and material", async () => {
    const { deps } = makeWorldDeps();
    const world = createWorld([createSeaSystem()], deps);
    await world.init("critical");
    const sea = deps.scene.getObjectByName("sea") as Mesh;
    let disposed = 0;
    sea.geometry.addEventListener("dispose", () => disposed++);
    (sea.material as MeshStandardMaterial).addEventListener("dispose", () => disposed++);
    world.dispose();
    expect(disposed).toBe(2);
  });
});
